---
skill: auditor-gate
version: "1.0"
agent: claim-auditor
phase: REVIEW
inputs:
  - content: string
  - claims: list[string]
  - source_urls: list[string]
  - language: "ja|en|zh"
  - skill_ref: string
outputs:
  - verdict: "PASS|FAIL|UNVERIFIABLE"
  - fail_reasons: list[string]
  - confidence: "HIGH|MED|LOW|UNVERIFIABLE"
  - rationalizations_triggered: list[string]
auditor_required: false
memory_read:
  - 事実層
memory_write:
  - 事実層
---

# 20-auditor-gate — Claim-Auditor LLM-free Verdict Gate

**INV-R2**: verdict は LLM-free 決定論的ロジックのみ。
**INV-R1**: PASS なしに WordPress 投稿は不可。

すべての WF01-09 パイプラインにおいて、SHIP 前に必ず実行する。

---

## DEFINE

**目的**: コンテンツの著作権・品質・セキュリティを
決定論的ルールで検査し、PASS / FAIL / UNVERIFIABLE を返す。

**LLM-free 保証**:
- 全チェックはルールベース (Python regex / difflib / 文字数カウント)
- 確率的判断は一切行わない
- FAIL 理由は機械可読な enum コード

**成功条件**: verdict = PASS

---

## PLAN

```
Pre-flight (Rationalizations Table):
  R1. ハードコード認証情報検出 → FAIL:HARDCODED_CREDENTIAL
  R2. 「動くはず」「たぶん動く」等の推量表現 → WARN:UNVERIFIED_CLAIM
  R3. 本番呼び出し実績なし (LIBRARY_ONLY 未登録) → WARN:NO_PROD_CALLER

著作権チェック (著作権法32条 引用5要件):
  ①主従: count_quoted(content) / count_total(content) > 0.34（引用 ≤ 1/3、要件§17-1） → FAIL:QUOTE_DOMINANCE
  ②明瞭区別: blockquote タグなしの引用ブロック検出 → FAIL:MISSING_BLOCKQUOTE
  ③必要性: re.findall(r'^#{2} ', content) < 3 → FAIL:INSUFFICIENT_SECTIONS
  ④出所明示: source_urls が content 内に全件存在しない → FAIL:MISSING_SOURCE_URL
  ⑤改変禁止 (同言語): blockquote 内が原文に見つからない (SequenceMatcher < 0.85) → WARN:QUOTE_ALTERED:<ratio>（要件§32-1 D7）
  丸写し (同言語): blockquote 外の本文が原文と >= 0.85 → WARN:VERBATIM_COPY:<ratio>（要件§32-1 D2）
  翻訳ラベル: ZH/EN ソース使用かつ翻訳注記なし → WARN:MISSING_TRANSLATION_LABEL（要件§32-1 D3）

品質チェック:
  - claims が空 → WARN:NO_CLAIMS
  - UNVERIFIABLE claims > 50% → verdict = UNVERIFIABLE

FAIL 蓄積:
  - 事実層に { content_hash, fail_reasons, skill_ref, audited_at } を書き込む
  - 同一ハッシュの再提出 → verdict は再計算し WARN:ALREADY_REJECTED:<fact_id> を付与（facts に重複行なし、要件§32-1 D5）
```

---

## BUILD

Auditor gate の実装は本リポジトリの `scripts/content_audit.py`（verdict ロジック）と
`scripts/auditor_server.py`（HTTP サービス、要件 §28）。仕様と実装の差分は要件 §32 の
ドリフト表が唯一の正（PLAN のうち `VERBATIM_COPY` / `MISSING_TRANSLATION_LABEL` /
`ALREADY_REJECTED` は §32-2 に従い `WARN:` として実装、`VERBATIM_COPY` の本来の定義と `QUOTE_ALTERED` は T-24 第2ラウンド、`INSUFFICIENT_LENGTH` は不採用）。
このスキルは n8n からの HTTP Request で呼び出す:

```json
{
  "method": "POST",
  "url": "{{ $env.CLAIM_AUDITOR_URL }}/audit",
  "body": {
    "content": "{{ $json.article_draft }}",
    "claims": "{{ $json.claims }}",
    "source_urls": "{{ $json.source_urls }}",
    "language": "{{ $json.language }}",
    "skill_ref": "20-auditor-gate"
  }
}
```

IF ノード分岐:
```
{{ $json.verdict === 'PASS' }} → true branch (30-wp-publisher へ)
{{ $json.verdict === 'FAIL' }}  → false branch (retry / human-review)
{{ $json.verdict === 'UNVERIFIABLE' }} → 人間レビュー待ち
```

---

## REVIEW

Auditor は自分自身をレビューしない。
かわりに `scripts/check_active_witnessed.py` によって
すべての ACTIVE 判定ロジックがテストで witnessed されていることを確認する。

---

## SHIP

verdict = PASS のみ `30-wp-publisher` に進む。
FAIL は最大 3 回 BUILD 差し戻し後、人間レビュー待ちキューへ。
すべての FAIL 理由は事実層に蓄積し、claim-evolve の学習データとする。

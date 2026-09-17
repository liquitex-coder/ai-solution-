---
skill: auditor-gate
version: "1.0"
agent: ainavi-gate
phase: REVIEW
inputs:
  - content: string
  - source_urls: list[string]
  - source_text: string          # 任意。[S0]..[Sn] 連結ソース（要件 §34-3）
  - source_lang: "ja|en|zh"      # 任意
  - evidence: EvidencePack       # 任意。要件 §34-4 v1
  - language: "ja|en|zh"
  - skill_ref: string
outputs:
  - verdict: "PASS|FAIL|UNVERIFIABLE"
  - fail_reasons: list[string]
  - confidence: "HIGH|MED|LOW|UNVERIFIABLE"
  - rationalizations_triggered: list[string]
  - evidence_summary: object   # evidence がある場合のみ（要件 §34-4）
auditor_required: false
memory_read:
  - 事実層
memory_write:
  - 事実層
---

# 20-auditor-gate — AI Navi Auditor Gate: LLM-free Verdict Gate

**INV-R2**: verdict は LLM-free 決定論的ロジックのみ。
**INV-R1**: PASS なしに WordPress 投稿は不可。
**INV-R2a**: Evidence Pack は verdict を下げる方向にしか作用しない（要件 §34-2）。

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

Evidence Pack（要件 §34-5、決定論ルール、初期は全て WARN:）:
  逐語照合: SUPPORTED/CONTRADICTED の evidence が source_text に無い → EVIDENCE_MISSING に格下げ
  WARN:CLAIM_CONTRADICTED:<n> / WARN:CLAIM_UNGROUNDED:<k>/<N>（OPINION 除外、N≥3、比率>0.5）
  WARN:TECHNIQUE_IMPLAUSIBLE:<n> / WARN:EVIDENCE_NOT_IN_SOURCE:<n> / WARN:NUMBER_MISMATCH:<v>/<gt>
  WARN:URL_DEAD:<url> / WARN:REPO_NOT_FOUND:<repo> / WARN:NO_SOURCE_FOR_FACTCHECK / WARN:FACTCHECK_UNAVAILABLE:<why>
  昇格条件は要件 §34-5 の表。evidence 欠落は verdict 不変（INV-R2a）

FAIL 蓄積:
  - 事実層に { content_hash, fail_reasons, skill_ref, audited_at } を書き込む
  - 同一ハッシュの再提出 → verdict は再計算し WARN:ALREADY_REJECTED:<fact_id> を付与（facts に重複行なし、要件§32-1 D5）
  - 全 WARN: は verdict を問わず warnings テーブルへ 1 行ずつ記録（要件 §34-6、30日観察の根拠）
```

---

## BUILD

Auditor gate の実装は本リポジトリの `scripts/content_audit.py`（verdict ロジック）と
`scripts/auditor_server.py`（HTTP サービス、要件 §28）。仕様と実装の差分は要件 §32 の
ドリフト表が唯一の正（PLAN のうち `VERBATIM_COPY` / `MISSING_TRANSLATION_LABEL` /
`ALREADY_REJECTED` は §32-2 に従い `WARN:` として実装、`VERBATIM_COPY` の本来の定義と `QUOTE_ALTERED` は T-24 第2ラウンド、`INSUFFICIENT_LENGTH` は不採用）。
Evidence Pack の受理と §34-5 の規則は T-34、配線は T-35/T-36（要件 §34-9）。
このスキルは n8n からの HTTP Request で呼び出す:

```json
{
  "method": "POST",
  "url": "{{ $env.AINAVI_GATE_URL }}/audit",
  "body": {
    "content": "{{ $json.article_draft }}",
    "source_urls": "{{ $json.source_urls }}",
    "source_text": "{{ $json.source_text }}",
    "source_lang": "{{ $json.source_lang }}",
    "evidence": "{{ $json.evidence }}",
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

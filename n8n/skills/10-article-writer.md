---
skill: article-writer
version: "1.0"
agent: claim-llm
phase: REVIEW
inputs:
  - topic: string
  - keyword: string
  - language: "ja|en|zh"
  - sources: list[SourceItem]
  - style: "informative|opinion|tutorial"
outputs:
  - article_draft: string
  - word_count: integer
  - source_citations: list[Citation]
  - confidence: "HIGH|MED|LOW|UNVERIFIABLE"
auditor_required: true
memory_read:
  - ペルソナ層
  - 事実層
memory_write:
  - 会話層
---

# 10-article-writer — 記事生成スキル

WF07 (JA/EN → Claude) / WF08 (ZH → Kimi) で使用。
claim-llm の言語検出ルーティングにより自動的に適切なモデルが選択される。

---

## DEFINE

**目的**: 取材結果 (sources) をもとに、SEO を意識した日本語記事を生成する。
英語メタデータは Phase 1 で付与。英語本文は Phase 2 高価値記事のみ。

**言語ルーティング** (claim-llm 内部):
- `language: ja` または `language: en` → Claude API
- `language: zh` → Kimi API (moonshot-v1-128k)

**制約**:
- 本文 ≥ 2,000 字 (JA) / 800 words (EN)
- 引用 ≤ 全体の 30%。blockquote タグ必須
- ≥ 3 つの独自 ## 見出し
- 各出所に title + URL を明記
- ペルソナ層のトーン・スタイルに従う
- 記事テーマ・構成は NoimosAI 編集脳の指示に沿う

**成功条件**:
- `word_count` ≥ 2,000 (JA) or 800 (EN)
- `source_citations` が sources と対応
- Auditor verdict = PASS

---

## PLAN

```
1. ペルソナ層からトーン・文体・禁止語を取得
2. 事実層から関連済み事実 (同 topic) を取得
3. sources を著作権ルールに従って整理:
   - 同言語: 要約 + blockquote (≤30%)
   - 他言語: 翻訳ラベル付き要約 (翻訳元 URL + 翻訳注記)
4. claim-llm へリクエスト (言語自動ルーティング)
5. 生成結果の字数・見出し数・引用比率を検証
6. 不足なら再生成 (最大 2 回)
7. 会話層に { session_id, topic, draft_v1, generated_at } を書き込む
```

---

## BUILD

claim-llm HTTP Request (n8n):
```json
{
  "method": "POST",
  "url": "{{ $env.CLAIM_LLM_URL }}/generate",
  "body": {
    "language": "{{ $json.language }}",
    "topic": "{{ $json.topic }}",
    "keyword": "{{ $json.keyword }}",
    "style": "{{ $json.style }}",
    "sources": "{{ $json.sources }}",
    "persona": "{{ $json.persona_from_memory }}",
    "copyright_prompt": "n8n/prompts/00-copyright-transform.md"
  }
}
```

claim-llm 内部でのルーティング疑似コード:
```python
if detect_language(source_texts) == 'zh':
    return kimi_generate(prompt, model='moonshot-v1-128k')
else:
    return claude_generate(prompt, model='claude-sonnet-5')
```

---

## REVIEW

Auditor gate チェック項目 (著作権法32条 引用5要件):
- [ ] ①主従: 生成字数 / 引用字数 > 2.0
- [ ] ②明瞭区別: blockquote タグ使用
- [ ] ③必要性: ## 見出し ≥ 3
- [ ] ④出所明示: source URL 全件検出
- [ ] ⑤改変禁止: 同言語 difflib 類似度 ≤ 0.85
- [ ] 翻訳ラベル: 他言語ソース使用時に先頭ラベル付与
- [ ] word_count ≥ 2,000 (JA) / 800 (EN)

---

## SHIP

後続の `11-seo-meta-writer` と `20-auditor-gate` に渡す。
最終 PASS 後に `30-wp-publisher` が実行。

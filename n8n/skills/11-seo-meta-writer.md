---
skill: seo-meta-writer
version: "1.0"
agent: claim-llm
phase: SHIP
inputs:
  - article_draft: string
  - keyword: string
  - language: "ja|en"
  - phase: "1|2"
outputs:
  - title: string
  - meta_description: string
  - og_title: string
  - og_description: string
  - slug: string
  - en_title: string
  - en_description: string
auditor_required: true
memory_read:
  - ペルソナ層
memory_write: []
---

# 11-seo-meta-writer — SEO メタデータ生成スキル

WF07/08 の記事生成後に実行。Phase 1: JA 本文 + EN SEO メタデータ。
Phase 2 (高価値記事): EN 本文も生成。

---

## DEFINE

**目的**: 記事本文から SEO 最適化されたメタデータを生成する。

**Phase 1 (全記事)**:
- JA: title (30-35 字) / meta_description (80-120 字)
- EN: en_title (50-60 chars) / en_description (120-160 chars)
- OGP: og_title / og_description (SNS シェア用)
- slug: ASCII kebab-case, ≤ 60 chars

**Phase 2 (高価値記事のみ)**:
- EN 本文全文翻訳 (claim-llm Claude 経由)
- EN 記事も WordPress に別投稿

**制約**:
- title に keyword を必ず含める
- meta_description は CTA を含むことが望ましい
- slug に日本語・記号を含めない

**成功条件**:
- 全フィールドが文字数制約を満たす
- Auditor verdict = PASS

---

## PLAN

```
1. ペルソナ層からブランドトーン・禁止語取得
2. keyword を軸に JA タイトル案 3 件生成
3. claim-builder council ループで 3 案から最適選択
4. meta_description・og_* を生成
5. slug を ASCII 変換 (transliteration + kebab)
6. Phase 2 判定: PV 予測スコア ≥ 閾値 → EN 本文生成
7. 全フィールド文字数検証
```

---

## BUILD

Function ノード (slug 生成):
```javascript
const title = $json.title || '';
// 簡易ローマ字変換 + kebab
const slug = title
  .toLowerCase()
  .replace(/[^a-z0-9\s-]/g, '')
  .replace(/\s+/g, '-')
  .replace(/-+/g, '-')
  .slice(0, 60);
return { slug };
```

claim-llm SEO 生成リクエスト:
```json
{
  "task": "seo_meta",
  "article_excerpt": "{{ $json.article_draft.slice(0, 500) }}",
  "keyword": "{{ $json.keyword }}",
  "language": "{{ $json.language }}",
  "constraints": {
    "ja_title_max": 35,
    "ja_desc_max": 120,
    "en_title_max": 60,
    "en_desc_max": 160
  }
}
```

---

## REVIEW

Auditor gate チェック項目:
- [ ] title に keyword 含む
- [ ] JA title ≤ 35 字
- [ ] JA meta_description ≤ 120 字
- [ ] EN en_title ≤ 60 chars
- [ ] EN en_description ≤ 160 chars
- [ ] slug が ASCII kebab のみ
- [ ] Phase 2 の場合: EN 本文の著作権チェック

---

## SHIP

出力を `30-wp-publisher` に渡す。

---
skill: rss-reporter
version: "1.0"
agent: claim-crew
phase: BUILD
inputs:
  - feed_urls: list[string]
  - keywords: list[string]
  - max_items: integer
  - hours_back: integer
outputs:
  - articles: list[Article]
  - confidence: "HIGH|MED|LOW|UNVERIFIABLE"
  - source_urls: list[string]
auditor_required: true
memory_read:
  - シーン層
  - 事実層
memory_write:
  - 事実層
---

# 02-rss-reporter — RSS 記事取材スキル

WF02 で使用。指定 RSS フィードからキーワードマッチ記事を収集し、
重複排除・確度スコア付きで返す。

---

## DEFINE

**目的**: 複数 RSS フィードをポーリングし、keywords に合致する記事の
title / summary / url / published_at を取得する。

**制約**:
- 同一 URL はシーン層で 24 時間ブロック（事実層に記録）
- summary は 500 字以内（超過はトランケート + `[...]` 付与）
- ライセンス不明な記事は引用なし・要約のみ

**成功条件**:
- keywords マッチ記事が 1 件以上
- Auditor verdict = PASS

---

## PLAN

```
1. 事実層クエリ → 過去 24h 取得済み URL 一覧
2. 各 feed_url に HTTP GET (XML/Atom 解析)
3. published_at ≥ NOW - hours_back でフィルタ
4. keywords を含む item のみ残す (case-insensitive, any keyword)
5. 事実層既出 URL を除外
6. 確度スコア:
   - 既知メディア (TechCrunch/Wired/ZDNet 等) → HIGH
   - 個人ブログ / 不明ドメイン → LOW
   - パース失敗 → UNVERIFIABLE
7. 事実層に { url, title, keywords_matched, fetched_at } を書き込む
```

---

## BUILD

n8n RSS Read ノード → Function ノード:

```javascript
const known_media = [
  'techcrunch.com', 'wired.com', 'zdnet.com',
  'gigazine.net', 'itmedia.co.jp', 'ascii.jp'
];
const keywords = $json.keywords || [];

return $input.all().flatMap(item =>
  item.json.items
    .filter(a => keywords.some(k =>
      (a.title + ' ' + (a.contentSnippet || '')).toLowerCase().includes(k.toLowerCase())
    ))
    .map(a => {
      const domain = new URL(a.link).hostname.replace('www.', '');
      return {
        title: a.title,
        url: a.link,
        summary: (a.contentSnippet || '').slice(0, 500),
        published_at: a.isoDate,
        confidence: known_media.includes(domain) ? 'HIGH' : 'LOW'
      };
    })
);
```

---

## REVIEW

Auditor gate チェック項目:
- [ ] summary が引用なら blockquote タグ付き（記事書き込み時）
- [ ] 全 article に `url` あり
- [ ] 事実層重複チェック済み

---

## SHIP

後続の `10-article-writer` に `articles` を渡す。単体 SHIP なし。

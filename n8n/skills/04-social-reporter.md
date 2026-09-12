---
skill: social-reporter
version: "1.0"
agent: claim-crew
phase: BUILD
inputs:
  - platforms: list["threads|note|reddit|hackernews|zh"]
  - keywords: list[string]
  - time_range: "24h|7d"
  - max_posts: integer
outputs:
  - posts: list[SocialPost]
  - confidence: "HIGH|MED|LOW|UNVERIFIABLE"
  - source_urls: list[string]
auditor_required: true
memory_read:
  - シーン層
  - 事実層
memory_write:
  - 事実層
  - シーン層
---

# 04-social-reporter — SNS/コミュニティ取材スキル

WF04 / WF09 で使用。Threads・note・Reddit・Hacker News・中国語ソース (Kimi 経由)
から話題を収集し、9 媒体横断調査の一部を担う。

---

## DEFINE

**目的**: 複数 SNS/コミュニティから keywords に関連する投稿・スレッドを収集し、
確度スコア付きで返す。中国語ソースは claim-llm (Kimi ルーティング) で処理。

**制約**:
- Reddit: 公開 API のみ (OAuth 不要、`r/MachineLearning` 等)
- Hacker News: Algolia Search API (無料)
- Threads/note: RSS エンドポイントまたは公開 Web スクレイプ
- 中国語ソース (ZH): claim-llm → Kimi (moonshot-v1-128k) 経由
- 同一投稿 URL はシーン層で 48 時間ブロック

**成功条件**:
- 1 件以上の投稿取得
- Auditor verdict = PASS

---

## PLAN

```
1. シーン層クエリ → 既取材 URL (48h)
2. platforms ごとに並列取材:
   a. reddit   → https://www.reddit.com/search.json?q={keyword}&sort=new&t=day
   b. hn        → https://hn.algolia.com/api/v1/search?query={keyword}&hitsPerPage=20
   c. note      → https://note.com/search?q={keyword}&context=note&mode=search (HTML)
   d. threads   → 公開 RSS (利用可能な場合) / 手動 URL リスト
   e. zh        → claim-llm (lang=zh) → Kimi API
3. 各プラットフォーム結果をシーン層重複除外
4. 確度スコア:
   - HN score ≥ 100 OR Reddit upvotes ≥ 500 → HIGH
   - HN score 20-99 OR Reddit upvotes 50-499 → MED
   - その他 → LOW
   - スクレイプ失敗 → UNVERIFIABLE
5. 事実層: { url, platform, title, score, fetched_at } を書き込む
6. シーン層: { url, researched_at } を書き込む
```

---

## BUILD

Reddit HTTP Request:
```json
{
  "method": "GET",
  "url": "https://www.reddit.com/search.json",
  "headers": { "User-Agent": "claim-crew/1.0" },
  "qs": {
    "q": "{{ $json.keywords.join(' OR ') }}",
    "sort": "new",
    "t": "{{ $json.time_range === '24h' ? 'day' : 'week' }}",
    "limit": "{{ $json.max_posts || 20 }}"
  }
}
```

Hacker News HTTP Request:
```json
{
  "method": "GET",
  "url": "https://hn.algolia.com/api/v1/search",
  "qs": {
    "query": "{{ $json.keywords.join(' ') }}",
    "hitsPerPage": "20",
    "tags": "story"
  }
}
```

中国語ソース (claim-llm Kimi 経由) は `08-kimi-zh.md` プロンプトを使用。

---

## REVIEW

Auditor gate チェック項目:
- [ ] 引用は blockquote タグ付き
- [ ] 全 post に `source_url` あり
- [ ] ZH ソースに翻訳ラベル付与済み
- [ ] シーン層重複なし (48h)
- [ ] Reddit API User-Agent 設定済み

---

## SHIP

後続の `10-article-writer` に `posts` を渡す。単体 SHIP なし。

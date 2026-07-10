---
skill: trending-researcher
version: "1.0"
agent: claim-crew
phase: BUILD
inputs:
  - topic: string
  - language: "ja|en|zh"
  - date_range: "24h|7d|30d"
  - max_repos: integer
outputs:
  - trending_items: list[TrendingItem]
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

# 01-trending-researcher — GitHub Trending 取材スキル

WF01 で使用。GitHub Trending から技術トレンドを収集し、
事実層の重複チェックを経て確度スコア付きの取材結果を返す。

---

## DEFINE

**目的**: 指定 topic・言語・期間の GitHub Trending リポジトリを収集し、
星数・概要・ライセンスを構造化データとして取得する。

**制約**:
- GitHub API: `GITHUB_TOKEN` 必須 (rate limit 5,000 req/h)
- 同一リポジトリの再取材はシーン層で 7 日間ブロック
- `README.md` 引用は 300 字以内、出所 URL 必須

**成功条件**:
- `trending_items` が 1 件以上
- 全 item に `source_url` が存在する
- Auditor verdict = PASS

---

## PLAN

```
1. シーン層クエリ → 過去 7 日取材済みリポジトリ一覧を取得
2. GitHub Trending API / RSS 取得 (topic, language, date_range)
3. 取得結果からシーン層既出を除外
4. 各リポジトリの README 先頭 300 字を抽出
5. 確度スコア付与ルール:
   - stars ≥ 500 AND description あり → HIGH
   - stars 100-499 → MED
   - stars < 100 → LOW
   - README 取得失敗 → UNVERIFIABLE
6. 事実層に { repo_url, stars, summary, scraped_at } を書き込む
7. シーン層に { repo_url, researched_at } を書き込む
```

---

## BUILD

n8n HTTP Request ノード設定:

```json
{
  "method": "GET",
  "url": "https://api.github.com/search/repositories",
  "headers": {
    "Authorization": "token {{ $env.GITHUB_TOKEN }}",
    "Accept": "application/vnd.github.v3+json"
  },
  "qs": {
    "q": "topic:{{ $json.topic }} language:{{ $json.language }} stars:>100",
    "sort": "stars",
    "order": "desc",
    "per_page": "{{ $json.max_repos || 10 }}"
  }
}
```

出力変換 (Function ノード):
```javascript
const items = $input.all();
return items[0].json.items.map(repo => ({
  name: repo.full_name,
  url: repo.html_url,
  stars: repo.stargazers_count,
  description: repo.description || '',
  license: repo.license?.spdx_id || 'UNKNOWN',
  confidence: repo.stargazers_count >= 500 ? 'HIGH'
            : repo.stargazers_count >= 100 ? 'MED' : 'LOW'
}));
```

---

## REVIEW

Auditor gate チェック項目:
- [ ] 引用文字数 ≤ 全体の 30%
- [ ] 全 item に `source_url` あり
- [ ] シーン層重複なし (7 日ルール)
- [ ] `GITHUB_TOKEN` ハードコードなし

---

## SHIP

このスキル単体は SHIP しない。
後続の `10-article-writer` に `trending_items` を渡す。
記憶層書き込みのみ実行。

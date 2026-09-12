# AI Navi — Fully Automated AI News Media

> **Language / 言語:** 🇺🇸 English (primary) &nbsp;|&nbsp; 🇯🇵 [日本語はこちら](#japanese)

An automated Japanese AI news hub for beginners and intermediate learners. Collects information from GitHub, official AI blogs, YouTube, SNS, and note; generates Japanese articles via Claude API; and auto-publishes to WordPress.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Data Sources                           │
│  GitHub API  RSS (Blogs)  YouTube API  Threads  note RSS   │
│              Perplexity API                                 │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────┐
│                  n8n Orchestrator                            │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐   │
│  │ WF-01    │ │ WF-02    │ │ WF-03~05 │ │ WF-06        │   │
│  │ GitHub   │ │ RSS      │ │ YouTube  │ │ Weekly       │   │
│  │ Trending │ │ Monitor  │ │ Threads  │ │ Report       │   │
│  │ 08:00JST │ │ 30min    │ │ note     │ │ Every Mon    │   │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └──────┬───────┘   │
│       └────────────┴────────────┴──────────────┘            │
│                          │                                   │
│                    ┌─────▼──────┐                            │
│                    │n8n/prompts │  (Git-managed Markdown)    │
│                    └─────┬──────┘                            │
└──────────────────────────┼──────────────────────────────────┘
                           │
                           ▼
            ┌──────────────────────────┐
            │       Claude API         │
            │  haiku  : WF-01 ~ 05    │
            │  sonnet-5: WF-06        │
            └──────────────┬───────────┘
                           │
                           ▼
            ┌──────────────────────────┐
            │   WordPress REST API     │
            │   /wp-json/wp/v2/posts   │
            │   status: draft (safe)   │
            └──────────────────────────┘
```

---

## Quick Start (Local Sandbox)

```bash
# 1. Configure environment variables
cp .env.example .env
# Edit .env and fill in your API keys

# 2. Start services
docker-compose up -d

# 3. Initialize WordPress (auto-create categories & tags)
bash scripts/wp-init.sh

# 4. Install MCP server dependencies
cd mcp && npm install && cd ..

# 5. Restart Claude Code → WordPress MCP is auto-detected
```

### Service URLs

| Service | URL | Purpose |
|---|---|---|
| WordPress | http://localhost:8080 | CMS / REST API |
| n8n | http://localhost:5678 | Workflow management |
| MySQL | localhost:3306 | DB (no direct access needed) |

---

## Workflows

| # | File | Trigger | Description | Model |
|---|---|---|---|---|
| 01 | `01-github-ai-trending-daily.json` | 08:00 JST daily | GitHub AI repos → explanatory article | haiku |
| 02 | `02-rss-monitor.json` | Every 30 min | Official AI blog RSS → summary article | haiku |
| 03 | `03-youtube-summary.json` | Every 1 h | YouTube AI videos → summary article | haiku |
| 04 | `04-threads-influencer.json` | Every 3 h | Threads AI posts → digest article | haiku |
| 05 | `05-note-monitor.json` | Every 1 h | note AI articles → summary article | haiku |
| 06 | `06-weekly-trend-report.json` | Every Monday | Perplexity trends → weekly report | sonnet-5 |

---

## Prompt Management (`n8n/prompts/`)

All Claude API prompts are managed as Git-tracked Markdown files. Hardcoding prompts inside workflow JSON is prohibited.

```
n8n/prompts/
├── 01-github-trending.md
├── 02-rss-monitor.md
├── 03-youtube-summary.md
├── 04-threads-influencer.md
├── 05-note-monitor.md
└── 06-weekly-report.md
```

Workflows fetch prompts dynamically at runtime via GitHub API:

```
GitHub API → base64 decode (Code node) → Claude API (dynamic prompt injection)
```

---

## WordPress MCP Server (Development)

Allows Claude Code to operate WordPress directly via MCP stdio protocol.

```bash
cd mcp && npm install
export WP_URL=http://localhost:8080
export WP_USERNAME=admin
export WP_APP_PASSWORD="xxxx xxxx xxxx xxxx xxxx xxxx"
# After restarting Claude Code you can say:
# "List draft posts"
# "Post this HTML as a WordPress draft"
```

### Available Tools

| Tool | Description |
|---|---|
| `wp_get_site_info` | Get site name and URL |
| `wp_list_posts` | List posts (filter by status / search) |
| `wp_get_post` | Get post details by ID |
| `wp_create_post` | Create a new post (default: draft) |
| `wp_update_post` | Update an existing post |
| `wp_delete_post` | Move a post to trash |
| `wp_list_categories` | List categories |
| `wp_list_tags` | List tags |
| `wp_create_category` | Create a new category |
| `wp_create_tag` | Create a new tag |

---

## Authentication Setup

### WordPress Application Password

```
WP Admin → Users → Profile
→ "Application Passwords" section
→ Enter app name (e.g. n8n) → "Add New Application Password"
→ Copy the generated password into .env as WP_APP_PASSWORD
```

n8n credential setup:
```
Credential Type : Header Auth
Name            : Authorization
Value           : Basic <base64(username:app_password)>

# Encode in terminal:
echo -n "admin:xxxx xxxx xxxx xxxx xxxx xxxx" | base64
```

---

## Environment Variables (`.env`)

| Variable | Where to get it |
|---|---|
| `ANTHROPIC_API_KEY` | https://console.anthropic.com |
| `GITHUB_TOKEN` | GitHub → Settings → Developer settings → PAT |
| `YOUTUBE_API_KEY` | Google Cloud Console → YouTube Data API v3 |
| `PERPLEXITY_API_KEY` | https://www.perplexity.ai/settings/api |
| `WP_APP_PASSWORD` | WordPress Admin (generate after starting services) |

---

## Development Rules

See [CLAUDE.md](./CLAUDE.md) for full details. Key rules:

- **Requirements first**: update `docs/requirements.md` before writing any code
- **English for Git**: commit messages, PRs, and code comments in English; chat in Japanese
- **No hallucination**: cite file + line number or API output as evidence
- **Test before ship**: design without running is prohibited — minimum bar is n8n manual run → WP draft confirmed

---

## Phase Roadmap

| Phase | Scope | Status |
|---|---|---|
| Phase 0 | Sandbox setup (Docker + n8n + WordPress) | ✅ Complete |
| Phase 1 | Core pipeline in production (GitHub Trending + RSS) | ⏳ Pending |
| Phase 2 | SNS expansion (YouTube · Threads · note) | ⏳ Pending |
| Phase 3 | Monetization & how-to content | ⏳ Pending |

---

## Related Docs

- [docs/requirements.md](./docs/requirements.md) — Requirements specification
- [n8n/SETUP_GUIDE.md](./n8n/SETUP_GUIDE.md) — n8n setup & error recovery guide
- [.claude/settings.json](./.claude/settings.json) — Claude Code MCP configuration

---

<details>
<summary id="japanese">🇯🇵 日本語版 / Japanese Version</summary>

# AIナビ — 全自動AI情報メディア

AI初心者〜中級者向けの日本語AI情報ハブ。GitHub・各社ブログ・YouTube・SNSから情報を自動収集し、Claude APIで日本語記事を生成してWordPressへ自動投稿するパイプライン。

## アーキテクチャ

```
情報収集ソース（GitHub / RSS / YouTube / Threads / note / Perplexity）
         ↓
n8n オーケストレーター（WF-01〜06）
         ↓
n8n/prompts/ （Git管理Markdownプロンプトを動的取得）
         ↓
Claude API（haiku: WF01-05 / sonnet-5: WF06）
         ↓
WordPress REST API（status: draft で安全投稿）
```

## クイックスタート

```bash
cp .env.example .env   # APIキーを入力
docker-compose up -d
bash scripts/wp-init.sh
cd mcp && npm install && cd ..
# Claude Code を再起動 → WordPress MCP 自動認識
```

## ワークフロー一覧

| # | トリガー | 処理 | モデル |
|---|---|---|---|
| 01 | 毎朝 8:00 JST | GitHub AI リポジトリ → 解説記事 | haiku |
| 02 | 30分ごと | 各社ブログ RSS → 要約記事 | haiku |
| 03 | 1時間ごと | YouTube AI 動画 → 解説記事 | haiku |
| 04 | 3時間ごと | Threads AI 投稿 → まとめ記事 | haiku |
| 05 | 1時間ごと | note AI 記事 → 紹介記事 | haiku |
| 06 | 毎週月曜 | Perplexity トレンド → 週次レポート | sonnet-5 |

## プロンプト管理

すべての Claude API プロンプトは `n8n/prompts/` で Markdown ファイルとして Git 管理。ワークフロー JSON へのハードコード禁止。実行時に GitHub API 経由で動的取得。

## WordPress MCP サーバー

Claude Code から WordPress を直接操作できる MCP サーバー（`mcp/wordpress-mcp.js`）。10ツール搭載: 投稿CRUD・カテゴリ/タグ管理など。デフォルト `status: draft` で誤公開防止。

## 開発規約

- **要件先行**: `docs/requirements.md` を更新してからコードを実装
- **英語コミット**: コミットメッセージ・PR・コメントは英語、チャットは日本語
- **ハルシネーション禁止**: ファイル+行番号またはAPI出力を根拠として示す
- **テスト済み確認**: n8n 手動実行 → WP 下書き確認が最低ライン

## フェーズロードマップ

| フェーズ | 内容 | ステータス |
|---|---|---|
| Phase 0 | サンドボックス構築 | ✅ 完了 |
| Phase 1 | コアパイプライン本番稼働 | ⏳ 待機中 |
| Phase 2 | SNS拡張 | ⏳ 待機中 |
| Phase 3 | マネタイズ・ノウハウ記事化 | ⏳ 待機中 |

## 関連ドキュメント

- [docs/requirements.md](./docs/requirements.md) — 要件定義書
- [n8n/SETUP_GUIDE.md](./n8n/SETUP_GUIDE.md) — セットアップ・エラー対応手順
- [.claude/settings.json](./.claude/settings.json) — Claude Code MCP 設定

</details>

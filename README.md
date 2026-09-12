# AI Navi — Fully Automated AI News Media

> **Language / 言語:** 🇺🇸 English (primary) &nbsp;|&nbsp; 🇯🇵 [日本語はこちら](#japanese)

An automated Japanese AI news hub for beginners and intermediate learners. n8n collects AI information, generates articles, audits claims, and sends articles to WordPress.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ GitHub, official RSS, YouTube, Threads, note, Perplexity,   │
│ Kimi/Moonshot → n8n orchestrator (WF01–WF09; Git prompts)  │
└─────────────────────────────┬───────────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ Claude API / Kimi-Moonshot API                               │
└─────────────────────────────┬───────────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ Auditor Gate (Code node) → scripts/auditor_server.py         │
│ POST /audit; CLAIM_AUDITOR_MODE: report_only | canary | full │
└─────────────────────────────┬───────────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ WordPress REST API                                            │
└─────────────────────────────────────────────────────────────┘
```

`report_only` is the default and never auto-publishes; `canary` publishes about 10%; `full` publishes passing content. FAIL and UNVERIFIABLE verdicts are written to the `facts` table in `data/memory.db`; `scripts/ratchet_check.py` reads it to propose ratchet entries.

## Quick Start (Local Sandbox)

```bash
# 1. Configure environment variables
cp .env.example .env
# 2. Start services
docker-compose up -d
# 3. Initialize WordPress categories and tags
bash scripts/wp-init.sh
# 4. Install MCP server dependencies
cd mcp && npm install && cd ..
```

Docker Compose waits for the auditor healthcheck before starting n8n.

### Service URLs

| Service | URL | Purpose |
|---|---|---|
| WordPress | http://localhost:8080 | CMS / REST API |
| n8n | http://localhost:5678 | Workflow management |
| MySQL | localhost:3306 | Database (no direct access needed) |
| auditor | internal: http://auditor:8090 (no host port) | Claim-Auditor gate HTTP service |

## Workflows

| # | File | Trigger | Description | Model | Category slug |
|---|---|---|---|---|---|
| 01 | `01-github-ai-trending-daily.json` | Daily 08:00 JST | GitHub AI trending repositories → explanatory article | `claude-haiku-4-5-20251001` | `github-trending` |
| 02 | `02-rss-monitor.json` | Every 30 min | Official AI blog RSS → summary article | `claude-haiku-4-5-20251001` | `ai-official-news` |
| 03 | `03-youtube-summary.json` | Every 1 h | YouTube AI videos → summary article | `claude-haiku-4-5-20251001` | `youtube-summary` |
| 04 | `04-threads-influencer.json` | Every 3 h | Threads AI posts → digest article | `claude-haiku-4-5-20251001` | `sns-pickup` |
| 05 | `05-note-monitor.json` | Every 1 h | note AI articles → summary article | `claude-haiku-4-5-20251001` | `note-creator` |
| 06 | `06-weekly-trend-report.json` | Every Monday | Perplexity trend research → weekly report | `claude-sonnet-5`; Perplexity `llama-3.1-sonar-large-128k-online` | `weekly-trend-report` |
| 07 | `07-article-writer.json` | Manual trigger only | How-to article writer | `claude-sonnet-5` | `howto-guide` |
| 08 | `08-kimi-zh.json` | Every 6 h | Kimi/Moonshot Chinese AI source translation | `moonshot-v1-128k` | `overseas-ai` |
| 09 | `09-multi-source-research.json` | Friday 07:00 JST (cron `0 22 * * 4` UTC) | Multi-source research → deep-dive article | `claude-sonnet-5` | `deep-dive` |

## Prompt Management (`n8n/prompts/`)

Git-tracked Markdown prompts (workflow JSON must not hardcode prompts):

```
00-copyright-transform.md
01-github-trending.md
02-rss-monitor.md
02-rss-summary.md             # LIBRARY_ONLY legacy; superseded by 02-rss-monitor.md
03-youtube-summary.md
04-threads-influencer.md
04-threads-summary.md         # LIBRARY_ONLY legacy; superseded by 04-threads-influencer.md
05-note-monitor.md
05-note-summary.md            # LIBRARY_ONLY legacy; superseded by 05-note-monitor.md
06-weekly-report.md
08-kimi-zh.md
09-multi-source-research.md
article-base.md
```

Workflows fetch prompts dynamically through the GitHub API, decode base64 in a Code node, and inject the prompt into the model request.

## WordPress MCP Server (Development)

Allows Claude Code to operate WordPress directly via the MCP stdio protocol.

```bash
cd mcp && npm install
export WP_URL=http://localhost:8080
export WP_USERNAME=admin
export WP_APP_PASSWORD="xxxx xxxx xxxx xxxx xxxx xxxx"
# Restart Claude Code; WordPress MCP is auto-detected.
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

## Authentication Setup

### WordPress Application Password

```
WP Admin → Users → Profile
→ “Application Passwords” section
→ Enter an app name (for example, n8n) → “Add New Application Password”
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

## Environment Variables (`.env`)

| Variable | Where to get it / purpose |
|---|---|
| `ANTHROPIC_API_KEY` | https://console.anthropic.com |
| `GITHUB_TOKEN` | GitHub Settings → Developer settings → PAT |
| `YOUTUBE_API_KEY` | Google Cloud Console → YouTube Data API v3 |
| `PERPLEXITY_API_KEY` | https://www.perplexity.ai/settings/api |
| `WP_APP_PASSWORD` | Local sandbox: WordPress Admin |
| `WP_SITE` / `WP_BEARER_TOKEN` | Production WordPress.com OAuth2 variables (requirements §24) |
| `CLAIM_AUDITOR_MODE` | `report_only` (default), `canary`, or `full` |
| `KIMI_API_KEY` | WF08 Kimi/Moonshot AI Chinese-source translation |
| `FAL_API_KEY` | Reserved for future featured-image generation (Flux.1 via fal.ai); not yet wired into a workflow |

## Development Rules

See [CLAUDE.md](./CLAUDE.md) for full rules. Key rules:

- **Requirements first**: update `docs/requirements.md` before writing code.
- **English for Git**: commit messages, PRs, and code comments are English; chat is Japanese.
- **No hallucination**: cite a file and line number or API output as evidence.
- **Test before ship**: the minimum bar is an n8n manual run and confirmed WordPress draft.

## Local Gates

```bash
python3 scripts/check_wired.py       # W1–W11
python3 scripts/run_eval.py
python3 -m unittest discover -s tests
python3 scripts/ratchet_check.py
```

The pre-push hook runs them in that order. Enable it with `git config core.hooksPath .githooks`.

## Phase Roadmap

| Phase | Scope | Status |
|---|---|---|
| Phase 0 | Sandbox setup (Docker + n8n + WordPress) | ✅ Complete |
| Phase 1 | Core pipeline in production (GitHub Trending + RSS); see [docs/ROADMAP.md](./docs/ROADMAP.md) for task-level status | ⏳ In progress |
| Phase 2 | SNS expansion (YouTube / Threads / note) | ⏳ Pending |
| Phase 3 | Monetization & how-to content | ⏳ Pending |

## Related Docs

- [docs/requirements.md](./docs/requirements.md)
- [docs/ROADMAP.md](./docs/ROADMAP.md)
- [n8n/SETUP_GUIDE.md](./n8n/SETUP_GUIDE.md)
- [.claude/settings.json](./.claude/settings.json) — Claude Code MCP configuration

<details>
<summary id="japanese">🇯🇵 日本語版 / Japanese Version</summary>

# AI Navi — AIニュース自動配信メディア

初学者から中級者向けの日本語AIニュースハブです。n8nがAI情報を収集し、記事を生成・監査してWordPressへ送ります。

## アーキテクチャ

```
┌─────────────────────────────────────────────────────────────┐
│ GitHub、公式RSS、YouTube、Threads、note、Perplexity、        │
│ Kimi/Moonshot → n8nオーケストレーター（WF01〜WF09、Git管理） │
└─────────────────────────────┬───────────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ Claude API / Kimi-Moonshot API                               │
└─────────────────────────────┬───────────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ Auditor Gate（Codeノード）→ scripts/auditor_server.py         │
│ POST /audit; CLAIM_AUDITOR_MODE: report_only | canary | full │
└─────────────────────────────┬───────────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ WordPress REST API                                            │
└─────────────────────────────────────────────────────────────┘
```

既定の`report_only`では自動公開しません。`canary`は約10%を公開し、`full`は合格コンテンツを公開します。FAILとUNVERIFIABLEの判定は`data/memory.db`の`facts`テーブルに保存され、`scripts/ratchet_check.py`がratchetエントリー案の作成に読み取ります。

## クイックスタート（ローカルサンドボックス）

```bash
# 1. 環境変数を設定
cp .env.example .env
# 2. サービスを起動
docker-compose up -d
# 3. WordPressのカテゴリーとタグを初期化
bash scripts/wp-init.sh
# 4. MCPサーバーの依存関係をインストール
cd mcp && npm install && cd ..
```

Docker Composeはauditorのヘルスチェック完了後にn8nを起動します。

### サービスURL

| サービス | URL | 用途 |
|---|---|---|
| WordPress | http://localhost:8080 | CMS / REST API |
| n8n | http://localhost:5678 | ワークフロー管理 |
| MySQL | localhost:3306 | データベース（直接アクセス不要） |
| auditor | internal: http://auditor:8090（ホストポートなし） | Claim-AuditorゲートのHTTPサービス |

## ワークフロー

| # | ファイル | トリガー | 概要 | モデル | カテゴリースラッグ |
|---|---|---|---|---|---|
| 01 | `01-github-ai-trending-daily.json` | 毎日 08:00 JST | GitHubのAIトレンドリポジトリ → 解説記事 | `claude-haiku-4-5-20251001` | `github-trending` |
| 02 | `02-rss-monitor.json` | 30分ごと | AI公式ブログRSS → 要約記事 | `claude-haiku-4-5-20251001` | `ai-official-news` |
| 03 | `03-youtube-summary.json` | 1時間ごと | YouTubeのAI動画 → 要約記事 | `claude-haiku-4-5-20251001` | `youtube-summary` |
| 04 | `04-threads-influencer.json` | 3時間ごと | ThreadsのAI投稿 → ダイジェスト記事 | `claude-haiku-4-5-20251001` | `sns-pickup` |
| 05 | `05-note-monitor.json` | 1時間ごと | noteのAI記事 → 要約記事 | `claude-haiku-4-5-20251001` | `note-creator` |
| 06 | `06-weekly-trend-report.json` | 毎週月曜日 | Perplexityのトレンド調査 → 週次レポート | `claude-sonnet-5`、Perplexity `llama-3.1-sonar-large-128k-online` | `weekly-trend-report` |
| 07 | `07-article-writer.json` | 手動トリガーのみ | ハウツー記事作成 | `claude-sonnet-5` | `howto-guide` |
| 08 | `08-kimi-zh.json` | 6時間ごと | Kimi/Moonshotの中国語AIソース翻訳 | `moonshot-v1-128k` | `overseas-ai` |
| 09 | `09-multi-source-research.json` | 金曜07:00 JST（cron `0 22 * * 4` UTC） | 複数ソース調査 → 深掘り記事 | `claude-sonnet-5` | `deep-dive` |

## プロンプト管理（`n8n/prompts/`）

Git管理のMarkdownプロンプトです。ワークフローJSONへのハードコードは禁止です。

```
00-copyright-transform.md
01-github-trending.md
02-rss-monitor.md
02-rss-summary.md             # LIBRARY_ONLY旧版。02-rss-monitor.mdへ置換済み
03-youtube-summary.md
04-threads-influencer.md
04-threads-summary.md         # LIBRARY_ONLY旧版。04-threads-influencer.mdへ置換済み
05-note-monitor.md
05-note-summary.md            # LIBRARY_ONLY旧版。05-note-monitor.mdへ置換済み
06-weekly-report.md
08-kimi-zh.md
09-multi-source-research.md
article-base.md
```

ワークフローはGitHub API経由でプロンプトを動的に取得し、Codeノードでbase64をデコードしてモデル要求へ注入します。

## WordPress MCP サーバー（開発用）

Claude CodeからMCP stdioプロトコル経由でWordPressを直接操作できます。

```bash
cd mcp && npm install
export WP_URL=http://localhost:8080
export WP_USERNAME=admin
export WP_APP_PASSWORD="xxxx xxxx xxxx xxxx xxxx xxxx"
# Claude Codeを再起動するとWordPress MCPが自動認識されます。
```

### 利用可能なツール

| ツール | 説明 |
|---|---|
| `wp_get_site_info` | サイト名とURLを取得 |
| `wp_list_posts` | 投稿一覧を取得（ステータス / 検索で絞り込み可能） |
| `wp_get_post` | IDで投稿詳細を取得 |
| `wp_create_post` | 投稿を作成（既定: draft） |
| `wp_update_post` | 既存投稿を更新 |
| `wp_delete_post` | 投稿をゴミ箱へ移動 |
| `wp_list_categories` | カテゴリー一覧を取得 |
| `wp_list_tags` | タグ一覧を取得 |
| `wp_create_category` | カテゴリーを作成 |
| `wp_create_tag` | タグを作成 |

## 認証設定

### WordPressアプリケーションパスワード

```
WP Admin → Users → Profile
→ 「Application Passwords」セクション
→ アプリ名（例: n8n）を入力 → 「Add New Application Password」
→ 生成されたパスワードをWP_APP_PASSWORDとして.envへコピー
```

n8nの認証情報設定:

```
Credential Type : Header Auth
Name            : Authorization
Value           : Basic <base64(username:app_password)>

# ターミナルでエンコード:
echo -n "admin:xxxx xxxx xxxx xxxx xxxx xxxx" | base64
```

## 環境変数（`.env`）

| 変数 | 取得先 / 用途 |
|---|---|
| `ANTHROPIC_API_KEY` | https://console.anthropic.com |
| `GITHUB_TOKEN` | GitHub Settings → Developer settings → PAT |
| `YOUTUBE_API_KEY` | Google Cloud Console → YouTube Data API v3 |
| `PERPLEXITY_API_KEY` | https://www.perplexity.ai/settings/api |
| `WP_APP_PASSWORD` | ローカルサンドボックス用: WordPress Admin |
| `WP_SITE` / `WP_BEARER_TOKEN` | 本番WordPress.com OAuth2変数（requirements §24） |
| `CLAIM_AUDITOR_MODE` | `report_only`（既定）、`canary`、`full` |
| `KIMI_API_KEY` | WF08のKimi/Moonshot AI中国語ソース翻訳用 |
| `FAL_API_KEY` | 将来のアイキャッチ画像生成（fal.aiのFlux.1）用に予約済み。現時点でワークフローには未接続 |

## 開発ルール

完全なルールは[CLAUDE.md](./CLAUDE.md)を参照してください。主なルール:

- **要件を先に**: コード作成前に`docs/requirements.md`を更新します。
- **Gitは英語**: コミットメッセージ、PR、コードコメントは英語、チャットは日本語です。
- **推測で書かない**: ファイルと行番号、またはAPI出力を根拠として示します。
- **出荷前にテスト**: 最低限、n8nの手動実行とWordPressのdraft確認が必要です。

## ローカルゲート

```bash
python3 scripts/check_wired.py       # W1〜W11
python3 scripts/run_eval.py
python3 -m unittest discover -s tests
python3 scripts/ratchet_check.py
```

pre-pushフックはこの順序ですべてを実行します。有効化コマンドは`git config core.hooksPath .githooks`です。

## フェーズロードマップ

| フェーズ | 範囲 | ステータス |
|---|---|---|
| Phase 0 | サンドボックス設定（Docker + n8n + WordPress） | ✅ 完了 |
| Phase 1 | 本番コアパイプライン（GitHub Trending + RSS）。タスク単位の状況は[docs/ROADMAP.md](./docs/ROADMAP.md)を参照 | ⏳ 進行中 |
| Phase 2 | SNS拡張（YouTube / Threads / note） | ⏳ 保留 |
| Phase 3 | 収益化とハウツーコンテンツ | ⏳ 保留 |

## 関連ドキュメント

- [docs/requirements.md](./docs/requirements.md)
- [docs/ROADMAP.md](./docs/ROADMAP.md)
- [n8n/SETUP_GUIDE.md](./n8n/SETUP_GUIDE.md)
- [.claude/settings.json](./.claude/settings.json) — Claude Code MCP設定

</details>

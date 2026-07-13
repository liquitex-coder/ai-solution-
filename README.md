# AIナビ — 全自動AI情報メディア

AI初心者〜中級者向けの日本語AI情報ハブ。GitHub・各社ブログ・YouTube・SNSから情報を自動収集し、Claude APIで日本語記事を生成してWordPressへ自動投稿するパイプライン。

## アーキテクチャ

```
┌─────────────────────────────────────────────────────────────┐
│                    情報収集ソース                              │
│  GitHub API  RSS(各社Blog)  YouTube API  Threads  note RSS  │
│              Perplexity API                                  │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────┐
│               n8n オーケストレーター                            │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐   │
│  │ WF-01    │ │ WF-02    │ │ WF-03〜05│ │ WF-06        │   │
│  │ GitHub   │ │ RSS      │ │ YouTube  │ │ 週次レポート  │   │
│  │ Trending │ │ Monitor  │ │ Threads  │ │              │   │
│  │ 毎朝8:00 │ │ 30分ごと │ │ note     │ │ 毎週月曜     │   │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └──────┬───────┘   │
│       └────────────┴────────────┴──────────────┘            │
│                          │                                   │
│                    ┌─────▼──────┐                            │
│                    │ n8n/prompts│ (Git管理Markdownプロンプト)  │
│                    └─────┬──────┘                            │
└──────────────────────────┼──────────────────────────────────┘
                           │
                           ▼
            ┌──────────────────────────┐
            │      Claude API          │
            │  haiku: WF 01-05         │
            │  sonnet-5: WF 06         │
            └──────────────┬───────────┘
                           │
                           ▼
            ┌──────────────────────────┐
            │   WordPress REST API     │
            │   /wp-json/wp/v2/posts   │
            │   status: draft (安全)   │
            └──────────────────────────┘
```

## クイックスタート（ローカルサンドボックス）

```bash
# 1. 環境変数を設定
cp .env.example .env
# .env を編集して各APIキーを入力

# 2. サービスを起動
docker-compose up -d

# 3. WordPress 初期化（カテゴリ/タグ自動作成）
bash scripts/wp-init.sh

# 4. MCP サーバー依存インストール
cd mcp && npm install && cd ..

# 5. Claude Code を再起動 → WordPress MCP が自動認識される
```

### サービス URL

| サービス | URL | 用途 |
|---|---|---|
| WordPress | http://localhost:8080 | CMS・REST API |
| n8n | http://localhost:5678 | ワークフロー管理 |
| MySQL | localhost:3306 | DB（直接接続不要） |

## n8n ワークフロー一覧

| # | ファイル | トリガー | 処理 | モデル |
|---|---|---|---|---|
| 01 | `01-github-ai-trending-daily.json` | 毎朝 8:00 JST | GitHub AI リポジトリ → 解説記事 | haiku |
| 02 | `02-rss-monitor.json` | 30分ごと | 各社ブログ RSS → 要約記事 | haiku |
| 03 | `03-youtube-summary.json` | 1時間ごと | YouTube AI 動画 → 解説記事 | haiku |
| 04 | `04-threads-influencer.json` | 3時間ごと | Threads AI 投稿 → まとめ記事 | haiku |
| 05 | `05-note-monitor.json` | 1時間ごと | note AI 記事 → 要約記事 | haiku |
| 06 | `06-weekly-trend-report.json` | 毎週月曜 | Perplexity トレンド → 週次レポート | sonnet-5 |

## プロンプト管理（n8n/prompts/）

Claude API へのプロンプトはすべて Markdown ファイルで Git 管理。ワークフロー JSON へのハードコードは禁止。

```
n8n/prompts/
├── article-base.md       # 全ワークフロー共通フォーマット規則
├── 01-github-trending.md # WF-01 用プロンプト
├── 02-rss-summary.md     # WF-02 用プロンプト
├── 03-youtube-summary.md # WF-03 用プロンプト
├── 04-threads-summary.md # WF-04 用プロンプト
├── 05-note-summary.md    # WF-05 用プロンプト
└── 06-weekly-report.md   # WF-06 用プロンプト（sonnet-5）
```

ワークフローは GitHub API 経由でプロンプトを動的に取得:

```
HTTP Request → github.com/repos/…/contents/n8n/prompts/XX.md
     ↓
Code Node (base64 decode)
     ↓
Claude API node (プロンプトを動的注入)
```

## WordPress MCP サーバー（開発用）

Claude Code から WordPress を直接操作できる MCP サーバー。

```bash
cd mcp && npm install
export WP_URL=http://localhost:8080
export WP_USERNAME=admin
export WP_APP_PASSWORD="xxxx xxxx xxxx xxxx xxxx xxxx"
# Claude Code 再起動後、以下のように指示できる:
# 「下書き記事の一覧を表示して」
# 「このHTMLをWordPressの下書きとして投稿して」
```

### 利用可能ツール

| ツール | 説明 |
|---|---|
| `wp_get_site_info` | サイト情報取得 |
| `wp_list_posts` | 投稿一覧（status/検索でフィルター） |
| `wp_get_post` | 投稿ID指定で詳細取得 |
| `wp_create_post` | 新規投稿作成（デフォルト: draft） |
| `wp_update_post` | 既存投稿更新 |
| `wp_delete_post` | 投稿をゴミ箱へ |
| `wp_list_categories` | カテゴリ一覧 |
| `wp_list_tags` | タグ一覧 |
| `wp_create_category` | 新規カテゴリ作成 |
| `wp_create_tag` | 新規タグ作成 |

## 認証設定

### WordPress Application Password

```
WordPress管理画面 → ユーザー → プロフィール
→「アプリケーションパスワード」セクション
→ アプリ名を入力（例: n8n） → 「新しいアプリケーションパスワードを追加」
→ 生成されたパスワードを .env の WP_APP_PASSWORD に設定
```

n8n での設定:
```
Credential Type: Header Auth
Name: Authorization
Value: Basic <base64(username:app_password)>

# base64 エンコード（ターミナル）:
echo -n "admin:xxxx xxxx xxxx xxxx xxxx xxxx" | base64
```

## 必要な環境変数（.env）

| 変数 | 取得先 |
|---|---|
| `ANTHROPIC_API_KEY` | https://console.anthropic.com |
| `GITHUB_TOKEN` | GitHub → Settings → Developer settings → PAT |
| `YOUTUBE_API_KEY` | Google Cloud Console → YouTube Data API v3 |
| `PERPLEXITY_API_KEY` | https://www.perplexity.ai/settings/api |
| `WP_APP_PASSWORD` | WordPress 管理画面（サービス起動後に生成） |

## 開発規約

詳細は [CLAUDE.md](./CLAUDE.md) 参照。主な規則:

- **要件先行**: `docs/requirements.md` を更新してからコードを実装
- **英語コミット**: コミットメッセージ・PR・コメントは英語、チャットは日本語
- **ハルシネーション禁止**: ファイル+行番号またはAPI出力を根拠として示す
- **テスト済み確認**: 「設計したが動かない」は禁止。n8n 手動実行 → WP 下書き確認が最低ライン

## 記者フレームワーク（reporters/）— 「動かない記者」を作らない仕組み

新しいAI記者（WF-07〜13）は、n8n JSON にロジックを埋め込まず、**外部依存ゼロの純関数モジュール**として実装する。全記者はマージ前に**ドライラン検証ゲート**を必ず通る（詳細は [docs/requirements.md §15](./docs/requirements.md)）。

```
reporters/
├── core.mjs            # 共通ヘルパー（Claude リクエスト / WP ペイロード生成）
├── validators.mjs      # 記事ルールの機械検証（article-base.md を強制）
├── registry.mjs        # 全記者の単一ソース（native 07-13 + legacy 01-06）
├── dryrun.mjs          # フィクスチャで全段を実行（HTTP なし）
├── run.mjs             # CLI ドライラン
├── reporters/NN-*.mjs  # 各記者モジュール（normalize/buildClaudeRequest/parseArticle/buildWpPayload）
└── fixtures/NN-*.json  # 各記者の固定入力（{ rawSource, claudeResponse }）
```

### ローカル検証（プッシュ前・APIキー不要）

```bash
npm test                       # node --test（単体 + ドライラン + 生成JSONの鮮度/実行一致）
npm run check:reporters        # No-Dead-Reporter ゲート（1件でも動かなければ exit 1）
npm run reporters:dry-run      # 全 native 記者のドラフト生成を確認
npm run gen:n8n                # モジュールから WF-07-13 の n8n JSON を再生成
node reporters/run.mjs --id 07 --json  # 単一記者の WP ペイロードを表示
```

### E2E スモーク（実クレデンシャル疎通）

オフライン検証とは別に、**実 Claude → 実 WordPress 投稿（201）** を確認するスクリプト。

```bash
# キーが揃った環境で: 実Claude生成 → 実WP投稿 → 201/記事ID を確認
ANTHROPIC_API_KEY=... WP_URL=... WP_USERNAME=... WP_APP_PASSWORD=... \
  npm run e2e -- --id 07

npm run e2e -- --id 07 --offline   # Claudeはフィクスチャ・WPだけ実投稿
```

- 認証情報が未設定なら「何が必要か」を表示して安全にSKIP（偽の成功を出さない）。
- WP 投稿シーム（`reporters/wp_client.mjs`）は**モックHTTPサーバに対する実ソケットのテスト**を持つ
  （`reporters/wp_client.test.mjs` → 201/ID・認証・下書き既定を検証）。WordPress イメージ不要。

### 本番 n8n JSON はモジュールから生成する（手書き禁止）

`n8n/workflows/07-13.json` は `scripts/gen_n8n.mjs` が記者モジュールの関数を**そのままインライン展開**して
生成する。Code ノードを手で編集しない。モジュールを変更したら `npm run gen:n8n` を実行する（忘れると
`node --test` の鮮度テストが落ちる）。生成物の Code ノードは `node:vm` で実行され、モジュールのドライラン結果と
一致することも検証される（ドリフト排除＋実行証明、docs §15-8）。

> ⚠️ **記者を1本追加するたびに** ゲート対象が増える。フィクスチャ＋プロンプト＋登録が揃い、
> `check:reporters` が green になるまで DONE にしない（DoD は docs §15-9）。CI（`.github/workflows/reporters.yml`）でも同じゲートが走る。

## フェーズロードマップ

| フェーズ | 内容 | ステータス |
|---|---|---|
| Phase 0 | サンドボックス構築（Docker + n8n + WordPress） | 🔄 進行中 |
| Phase 1 | コアパイプライン本番稼働（GitHub Trending + RSS） | ⏳ 待機中 |
| Phase 2 | SNS拡張（YouTube・Threads・note） | ⏳ 待機中 |
| Phase 3 | マネタイズ・ノウハウ記事化 | ⏳ 待機中 |

## 関連ドキュメント

- [docs/requirements.md](./docs/requirements.md) — 要件定義書（詳細設計）
- [n8n/SETUP_GUIDE.md](./n8n/SETUP_GUIDE.md) — n8n セットアップ・エラー対応手順
- [.claude/settings.json](./.claude/settings.json) — Claude Code MCP 設定

# AI情報専門サイト 要件定義書

**バージョン**: 1.4  
**最終更新**: 2026-07-12  
**ステータス**: 設計中（ホスティング先未確定）

---

## 1. サイト概要

| 項目 | 内容 |
|---|---|
| サイト名 | AIナビ（仮） |
| 目的 | AI初心者〜中級者が「使える・試せる」情報を得られる日本語ハブ |
| ターゲット | AIを使いたいが何から始めればいいか分からない人、業務効率化したいビジネスマン |
| 言語 | 日本語メイン |
| CMS | WordPress |
| コンセプト | **人間の介入を最小化した全自動AI情報メディア** |
| ノウハウ化 | このサイト構築プロセス自体を記事化・販売する予定 |

---

## 2. コンテンツ構成

### 2-1. ページ構成

| ページ | 内容 | 更新方式 |
|---|---|---|
| トップ | 注目ツール・最新ニュース・入門ガイド | 自動 |
| AIツールカタログ | 厳選ツール一覧（カテゴリ・料金フィルター） | 手動 + 自動 |
| ツール詳細 | 各ツールの詳細・使い方・メリデメ・比較 | 手動 + 自動 |
| 使い方ガイド | ステップバイステップのHowToガイド | 自動生成 |
| 連携・自動化 | NoimosAI連携・Makeセn8n統合手順 | 手動 |
| AIニュース | 最新アップデート・リリース情報 | 全自動 |
| GitHubトレンド | 今日の注目AIリポジトリ | 全自動（毎朝） |
| プロンプト集 | コピーして使えるプロンプトテンプレート | 自動 + UGC（将来） |
| インフルエンサー発信 | SNS上のAIノウハウ・話題まとめ | 全自動 |

### 2-2. デザイン方针

- **イラスト・アイコン主体**（文字より視覚で先に会わせる）
- **カード型レイアウト**（一覧性重視、スキャンしやすい）
- **ステップ図解**（HowToはテキストより図フロー）
- **初心者導線**（「あなたはどのタイプ？」でユーザーを振り分け）
- ダークモード対応
- モバイルファースト

---

## 3. ネタ収集ソース（フェーズ別）

### Phase 1：無料ソースのみ（初期構築）

| ソース | 取得方法 | コスト | 対象コンテンツ |
|---|---|---|---|
| OpenAI Blog | RSS | 無料 | GPT新機能・リリース情報 |
| Anthropic Blog | RSS | 無料 | Claude新機能・研究 |
| Google AI Blog | RSS | 無料 | Gemini・AI研究 |
| Meta AI Blog | RSS | 無料 | LLaMA・AI研究 |
| GitHub Trending | GitHub API（公式） | 無料 | 今日の注目AIリポジトリ |
| GitHub Search | GitHub API（公式） | 無料 | スター急上昇・新着AIツール |
| YouTube | YouTube Data API v3 | 無料（1万units/日） | AI系チャンネルの新動画 |
| Threads | Threads API | 無料 | AIインフルエンサーの投稿 |
| note.com | RSS | 無料 | AI系クリエイターの記事 |
| Perplexity API | Perplexity API | 無料枠あり | AIトレンドキーワード検索 |

### Phase 2：有料ソース追加（成長後）

| ソース | 取得方法 | コスト | 追加タイミング |
|---|---|---|---|
| X (Twitter) | X API v2 | $100/月〜 | 収益化後 |
| X スクレイピング | Apify | $49/月〜 | 収益化後 |
| Instagram | Instagram Graph API | 無料枠あり | Phase 2 |

### 収集対象インフルエンサー（例）

- chroniki_claude（Claude Code専門家・Threads）
- AI_Trend_Daily（GitHubトレンド系・Instagram）
- その他：AIツール解説・プロンプトエンジニア系アカウント

---

## 4. 自動化パイプライン（全体アーキテクチャ）

```
【ネタ収集】
├── GitHub API  ─────────────────┬
├── 公式RSS（各社ブログ）          │
├── YouTube Data API              ├──→【n8n オーケストレーター】
├── Threads API                   │         ↓
├── note RSS                      │  新ネタ検知・重複排除・スコアリング
└── Perplexity API ──────────┘         ↓
                                   【Claude API】
                                   日本語記事自動生成
                                            ↓
                                   【WordPress REST API】
                                   自動投稿（下書き or 即公開）
                                            ↓
                                   【NoimosAI】
                                   ├── SEOエージェント（Search Console連携）
                                   ├── SNSエージェント（X・Instagram・TikTok・note・Threads）
                                   ├── 競合分析エージェント
                                   └── 週次レポート自動生成
```

### n8nワークフロー一覧

| ワークフロー名 | トリガー | 処理内容 |
|---|---|---|
| github-trending-daily | 毎朝8:00 | GitHubトレンドAIリポジトリ取得→記事生成→投稿 |
| rss-monitor | 30分ごと | 各社ブログRSS監視→新記事検知→日本語記事生成 |
| youtube-new-video | 1時間ごと | 対象チャンネル新動画検知→要約→記事生成 |
| threads-influencer | 3時間ごと | 対象アカウント投稿収集→まとめ記事生成 |
| note-monitor | 1時間ごと | note RSS監視→AI関連記事抽出→転載記事生成 |
| weekly-trend-report | 毎週月曜 | Perplexity でトレンド検索→週次まとめ記事生成 |

### プロンプト管理

Claude API へ送るプロンプトは `n8n/prompts/` ディレクトリで Markdown ファイルとして Git 管理する。
ワークフロー JSON へのハードコードは禁止。プロンプト変更は PR でレビューし、品質のPDCAを回す。

| ファイル | 用途 |
|---|---|
| `n8n/prompts/article-base.md` | 全ワークフロー共通の記事フォーマット指示 |
| `n8n/prompts/01-github-trending.md` | GitHubトレンド記事生成プロンプト |
| `n8n/prompts/02-rss-summary.md` | RSSフィード要約プロンプト |
| `n8n/prompts/03-youtube-summary.md` | YouTube動画要約プロンプト |
| `n8n/prompts/04-threads-summary.md` | Threadsまとめプロンプト |
| `n8n/prompts/05-note-summary.md` | note記事要約プロンプト |
| `n8n/prompts/06-weekly-report.md` | 週次トレンドレポートプロンプト |

---

## 5. NoimosAI連携（A+B両方）

### A：サイトのマーケティング自動化

| エージェント | 役割 | 連携サービス |
|---|---|---|
| SEOエージェント | キーワード最適化・内部リンク改善 | Google Analytics・Search Console |
| ソーシャルメディアエージェント | SNS自動投稿・スケジュール管理 | X・Instagram・TikTok・YouTube・Threads・note |
| 競合分析エージェント | 競合AI情報サイトの動向監視 | 自動 |
| 成長戦略エージェント | KPI設定・改善提案 | GA4・Search Console |

### B：サイト内コンテンツとしてNoimosAIを紹介

- AIツールカタログにNoimosAIを欲載（詳細ページ・使い方ガイド）
- 「このサイト自体がNoimosAIで動いている」を差別化ポイントとして前面に出す
- 連携手順をガイド記事化（ノウハウ販売コンテンツの一部にもなる）

### NoimosAI用エンドポイント（WordPressサイト側）

| エンドポイント | 用途 |
|---|---|
| `/feed` (WordPress標準RSS) | 新記事の自動検知・SNS配信トリガー |
| `/sitemap.xml` | Google Search Console・SEOエージェント用 |
| `/wp-json/wp/v2/posts` | NoimosAI WordPressプラグイン連携 |

---

## 6. GitHubトレンドコンテンツ（独自コンテンツとして作成）

### 判断理由：既存アカウントの転載ではなく自前で作る

- **SEO**: オリジナルコンテンツのため検索流入が取れる
- **差別化**: 単なるリポジトリ紹介に留まらず「日本語解説＋使い方＋連携方法」まで踏み込む
- **API**: GitHub APIは公式・無料で使いやすい

### 取得ロジック

```
GitHub API Search
└── q: topic:ai OR topic:llm OR topic:claude OR topic:openai
    created: >YYYY-MM-DD（過去7日間）
    sort: stars（スター数降順）
    
→ Claude APIで日本語化
  ・リポジトリ名・説明の翻訳
  ・「何ができるか」「誰に使えるか」「使い方」を生成
  ・難易度タグ付与（入門/中級/上級）
  
→ WordPress自動投稿
  カテゴリ: GitHubトレンド
  タグ: 言語・トピック・スター数帯
```

---

## 7. サンドボックス環境

本番デプロイ前にローカルで全パイプラインをテストできる環境。

### 起動方法

```bash
cp .env.example .env        # APIキーを .env に設定
docker-compose up -d        # 全サービスをバックグラウンドで起動
```

### サービス構成

| サービス | URL / ポート | 用途 |
|---|---|---|
| WordPress | http://localhost:8080 | 記事投稿先・REST API テスト |
| n8n | http://localhost:5678 | ワークフロー実行・動作確認 |
| MySQL | localhost:3306 | WordPress データベース |

### 環境変数（.env.example からコピー）

| 変数名 | 説明 |
|---|---|
| `MYSQL_ROOT_PASSWORD` | MySQL root パスワード |
| `MYSQL_PASSWORD` | WordPress 用 DB パスワード |
| `N8N_USER` / `N8N_PASSWORD` | n8n 管理画面ログイン |
| `ANTHROPIC_API_KEY` | Claude API キー |
| `GITHUB_TOKEN` | GitHub Personal Access Token |
| `YOUTUBE_API_KEY` | YouTube Data API v3 キー |
| `PERPLEXITY_API_KEY` | Perplexity API キー |
| `WP_APP_PASSWORD` | WordPress Application Password（WP起動後に設定） |

### サンドボックスで検証できること

- [ ] `docker-compose up -d` → WordPress が http://localhost:8080 で応答
- [ ] n8n が http://localhost:5678 で応答
- [ ] ワークフロー01（GitHub AI Trending）手動実行 → WP下書き記事作成
- [ ] ワークフロー02（RSS Monitor）手動実行 → WP下書き記事作成
- [ ] Claude API がJSON構造の記事を返す
- [ ] WordPress REST API POST `/wp-json/wp/v2/posts` → 201レスポンスと記事ID
- [ ] NoimosAI WordPress連携テスト
- [ ] RSS / Sitemapの出力確認

---

## 8. 技術スタック

| 層 | 技術 | 備考 |
|---|---|---|
| CMS | WordPress | ホスティング先未確定 |
| テーマ | カスタムテーマ（Astra + Elementorまたはフルカスタム） | 要検討 |
| オーケストレーター | n8n | セルフホスト or n8n.cloud |
| コンテンツ生成AI | Claude API（Anthropic） | メイン |
| コンテンツ生成AI | OpenAI GPT API | サブ・比較用 |
| マーケティング自動化 | NoimosAI | $99/月〜 |
| SEOプラグイン | Rank Math（無料） | Search Console連携 |
| 画像生成（将来） | DALL-E 3 or Stable Diffusion | アイキャッチ自動生成 |
| ローカル開発 | Docker Compose | サンドボックス |
| 開発ツール | Claude Code + WordPress MCP | WordPress 直操作（§13参照） |

### WordPress 認証方式

| 環境 | 認証方式 | 備考 |
|---|---|---|
| ローカル（サンドボックス） | Application Passwords | n8n HTTP Header Auth（Basic）で設定 |
| 本番（WordPress.com） | Application Passwords | OAuth Token より有効期限の問題が少ない |

Application Passwords は WordPress 管理画面 → ユーザー → プロフィール → アプリケーションパスワード から生成。
`Authorization: Basic base64(username:app_password)` をヘッダーに付与。

**認証切り替えの履歴**:

| 旧方式 | 新方式 | 切り替え理由 |
|---|---|---|
| OAuth Token（WordPress.com） | Application Passwords | トークン有効期限なし・設定簡単 |

---

## 9. WordPressプラグイン構成

| プラグイン | 用途 | コスト |
|---|---|---|
| Rank Math SEO | SEO最適化・Sitemapクラス | 無料 |
| WP REST API | n8nからの自動投稿 | WordPress標準 |
| Classic Editor | n8nからの投稿に対応 | 無料 |
| WP Super Cache | 表示高速化 | 無料 |
| Akismet | スパム対策 | 無料（個人） |
| Advanced Custom Fields | カスタムフィールド（ツール詳細用） | 無料 |

---

## 10. 実装フェーズ

### Phase 0：サンドボックス構築（進行中）
- [x] 要件定義書作成
- [x] docker-compose.yml 作成（WordPress + n8n + MySQL）
- [x] .env.example 作成（APIキープレースホルダー）
- [x] n8nワークフロー雛形作成（01〜06）
- [x] n8n/prompts/ ディレクトリ作成（7ファイル）
- [x] SETUP_GUIDE.md エラーハンドリング拡充
- [x] MCP サーバー設定（Claude Code ↔ WordPress）
- [ ] WordPress 初回セットアップ（管理画面・Application Password 発行）
- [ ] エンドツーエンドサンドボックステスト（§7 チェックリスト全項目）

### Phase 1：コアパイプライン（ホスティング確定後）
- [ ] 本番WordPressセットアップ
- [ ] GitHub Trendingワークフロー稼働
- [ ] 公式RSSワークフロー稼働
- [ ] NoimosAI初期連携

### Phase 2：SNS拡張
- [ ] YouTube APIワークフロー追加
- [ ] Threads APIワークフロー追加
- [ ] note RSSワークフロー追加
- [ ] NoimosAI SNSエージェント全連携

### Phase 3：マネタイズ・ノウハウ化
- [ ] このサイト構築プロセスの記事化
- [ ] 有料SNSソース（X API等）追加
- [ ] UGCプロンプト投稿機能
- [ ] アイキャッチ画像自動生成

---

## 11. エラー対応方鷑

本番・サンドボックス共通のエラーハンドリング方鷑。詳細な対処手順は `n8n/SETUP_GUIDE.md` の「エラーハンドリング」セクションを参照。

| エラー | 原因 | 対応方鷑 |
|---|---|---|
| `401 Unauthorized` | トークン・App Password 無効 | 再発行・再設定 |
| `403 Forbidden` (GitHub) | API レート制限 | Conditional header / Wait ノード追加 |
| `429 Too Many Requests` | Claude API レート制限 | Retry on Fail 設定 + 60秒待機 |
| `529 Overloaded` (Claude) | Claude API 過負荷 | 指数バックオフ（Wait ノード） |
| `410 Gone` (WordPress) | REST API エンドポイント変更 | WP バージョン確認・エンドポイント更新 |
| n8n タイムアウト | 処理時間超過 | ワークフローを分割・非同期化 |
| RSS 404 | RSS URL 変更 | 実際のサイトでURLを再確認 |

---

## 12. 未確定事項（要確認）

| 項目 | ステータス | 確認予定 |
|---|---|---|
| WordPressホスティング先 | **未確定** | オーナー確認後 |
| n8n運用方式（セルフホスト or クラウド） | 未確定 | ホスティング決定後 |
| サイト正式名称 | 仮「AIナビ」 | 要相談 |
| ドメイン | 未確定 | 要相談 |
| Claude APIキー / OpenAI APIキー | 保有確認必要 | 要確認 |

---

## 13. 開発ツール（MCP サーバー）

### 概要

Claude Code から WordPress REST API を直接操作するための MCP（Model Context Protocol）サーバー。
n8n ワークフローを経由せず、開発・デバッグ・コンテンツ確認を Claude Code 上で完結できる。

```
【Claude Code (開発時)】
      ↓ MCP protocol (stdio)
【wordpress-mcp.js】
      ↓ HTTP + Basic Auth
【WordPress REST API】
  /wp-json/wp/v2/posts
  /wp-json/wp/v2/categories
  /wp-json/wp/v2/tags
  /wp-json/wp/v2/media
```

### 構成ファイル

| ファイル | 役割 |
|---|---|
| `.claude/settings.json` | Claude Code の MCP サーバー登録設定 |
| `mcp/wordpress-mcp.js` | WordPress CRUD MCP サーバー本体（Node.js ESM） |
| `mcp/package.json` | 依存パッケージ（`@modelcontextprotocol/sdk`） |

### 提供ツール一覧

| ツール名 | 説明 |
|---|---|
| `wp_get_site_info` | サイト情報（名前・URL・バージョン）取得 |
| `wp_list_posts` | 投稿一覧（status・キーワード・カテゴリでフィルター） |
| `wp_get_post` | 投稿 ID 指定で詳細取得 |
| `wp_create_post` | 新規投稿作成（title・content・status・categories・tags） |
| `wp_update_post` | 既存投稿の更新 |
| `wp_delete_post` | 投稿をゴミ箱へ移動（force=true で完全削除） |
| `wp_list_categories` | カテゴリ一覧取得 |
| `wp_list_tags` | タグ一覧取得（キーワード検索可） |
| `wp_create_category` | 新規カテゴリ作成 |
| `wp_create_tag` | 新規タグ作成 |

### セキュリティ考慮

- 認証情報は **環境変数** で管理（`WP_URL`, `WP_USERNAME`, `WP_APP_PASSWORD`）
- `.claude/settings.json` に資格情報をハードコードしない
- MCP サーバーはローカルプロセスとして stdio 通信（外部ポート不使用）
- 本番 WordPress への誤操作防止：`status: 'draft'` がデフォルト（明示しないと公開されない）

### セットアップ手順

```bash
# 1. 依存パッケージインストール
cd mcp && npm install

# 2. 環境変数設定（.env からコピーして設定済みであれば不要）
export WP_URL=http://localhost:8080
export WP_USERNAME=admin
export WP_APP_PASSWORD=xxxx xxxx xxxx xxxx xxxx xxxx

# 3. Claude Code を再起動（MCPサーバーが自動起動される）
# .claude/settings.json の mcpServers が読み込まれる

# 4. 動作確認（Claude Code から）
# "WordPress のサイト情報を取得して" と指示するとMCPが使われる
```

### 利用例

```
ユーザー: 「下書きの記事を一覧表示して」
Claude Code → wp_list_posts({ status: 'draft' }) → 記事一覧を返答

ユーザー: 「このMarkdownをWordPressの下書きとして投稿して」
Claude Code → wp_create_post({ title: '...', content: '<h2>...', status: 'draft' })
             → 記事ID・URLを返答
```

---

## 14. AI記者 拡張ユースケース（提案）

### 背景と方針

現行の AI 記者（WF-01〜06）はいずれも **収集 → 要約・翻訳 → 投稿** の「アグリゲーション型」であり、
一次情報を日本語に噛み砕いて流すことに主眼がある。差別化のため、次フェーズでは
Claim-Auditor ファミリーの強みである **証拠主義・反ハルシネーション（INV-R1 / INV-R2）** を
記事品質に転用した「新しい使い方の AI 記者」を追加する。

- **単なる転載メディアとの決別**: 検証・実体験・比較という「一次的な付加価値」を持つ記事を自動生成する。
- **クロスリポジトリ連携**: 判定が必要なユースケース（ファクトチェック）は Claim-Auditor の
  LLM-free 判定エンジン（INV-R2）を上流プロポーザーとして利用し、真偽判定そのものは決定論的に行う。
- **安全既定の踏襲**: 追加ワークフローもすべて `status: draft` 投稿を既定とし、人間レビューを挟む（INV-R1）。

### 追加ワークフロー一覧（WF-07〜13）

| # | 記者名 | トリガー | 入力ソース | 出力 | モデル案 |
|---|---|---|---|---|---|
| 07 | **ファクトチェック記者** | イベント/日次 | RSS・SNSの誇大表現クレーム | 検証記事（真偽判定つき） | sonnet-5 |
| 08 | **体験レビュー記者** | 週次 | ツールカタログ + サンドボックス実行 | 再現手順つきハンズオンレビュー | sonnet-5 |
| 09 | **比較記者** | オンデマンド/週次 | 既存カタログエントリ2件以上 | 比較表つき「〇〇 vs △△」記事 | haiku |
| 10 | **速報記者** | 5分ごと | 主要ソース横断（RSS+SNS） | 「速報」バッジつき短報 | haiku |
| 11 | **読者Q&A記者** | フォーム受信時 | 読者質問（UGC） | 質問回答記事 | haiku |
| 12 | **アップデート追跡記者** | 日次 | 主要ツールのchangelog/リリースノート | 「何が変わり、なぜ重要か」記事 | haiku |
| 13 | **深掘り解説記者** | 週次 | トレンドトピック + 内部記事群 | 内部リンク配置つきピラー長文 | sonnet-5 |

### 本命3案（優先度: 高）

#### WF-07 ファクトチェック記者（検証記者）

- **目的**: AIツールの誇大な宣伝文句（例「〇〇はGPTを超えた」「10倍速い」）を検出し、実際に検証して記事化する。
- **差別化**: Claim-Auditor の判定エンジンを流用 → 真偽判定は **LLM-free で決定論的（INV-R2）**。LLMは
  クレーム抽出・記事文面生成という上流プロポーザーに限定する。
- **フロー案**:
  ```
  RSS/SNS収集 → Claude API（クレーム抽出: claim / 主張元 / 検証可能な条件）
    → Claim-Auditor 判定（is_ears / verdict: 決定論）
    → Claude API（判定結果を根拠に日本語検証記事を生成）
    → WordPress 下書き投稿（カテゴリ: ファクトチェック）
  ```
- **必須検証（Test-Before-Ship）**: Claim-Auditor 判定APIが verdict を返すこと、記事本文に
  「主張 / 検証条件 / 判定 / 根拠」の4要素が含まれること。

#### WF-08 体験レビュー記者（ハンズオン記者）

- **目的**: 収集して終わりにせず、**API/サンドボックスで実際に動かした結果**を証拠として添付したレビューを生成する。
- **差別化**: CLAUDE.md の「証拠なしに完了と言わない」思想を記事品質にそのまま適用。実出力・スクショを掲載。
- **必須検証**: レビュー対象ツールの実行ログ（API レスポンス or サンドボックス出力）が記事に紐づくこと。

#### WF-09 比較記者（〇〇 vs △△）

- **目的**: ツールカタログの既存エントリを2件以上組み合わせ、比較表つき記事を自動生成する。
- **差別化**: 「Claude vs ChatGPT」等の比較クエリはSEO流入が非常に強い。新規収集ゼロで既存資産から量産可能（低コスト高リターン）。
- **必須検証**: 比較表の各行が実カタログエントリのフィールドに由来すること（捏造フィールド禁止）。

### 追加4案（優先度: 中）

| # | 記者名 | 狙い | 補足 |
|---|---|---|---|
| 10 | 速報記者 | 鮮度・回遊率 | 主要発表をリアルタイム検知し「速報」バッジで即投稿。後追いで正式記事に昇格。 |
| 11 | 読者Q&A記者 | エンゲージメント・UGC | 読者質問を記事化。将来のUGCプロンプト投稿機能（Phase 3）と接続。 |
| 12 | アップデート追跡記者 | 継続流入 | 主要ツールのchangelogを監視し差分を解説。バージョン別に記事が積み上がる。 |
| 13 | 深掘り解説記者 | SEOピラー | トレンドを長文解説化し内部リンクを自動配置。回遊とドメイン権威を強化。 |

### プロンプト管理

追加記者のプロンプトも §4 の規約に従い `n8n/prompts/` に Markdown で Git 管理する（JSONハードコード禁止）。

| ファイル（予定） | 用途 |
|---|---|
| `n8n/prompts/07-factcheck.md` | ファクトチェック記者（クレーム抽出 + 記事生成の2段） |
| `n8n/prompts/08-hands-on-review.md` | 体験レビュー記者 |
| `n8n/prompts/09-comparison.md` | 比較記者 |
| `n8n/prompts/10-breaking-news.md` | 速報記者 |
| `n8n/prompts/11-reader-qa.md` | 読者Q&A記者 |
| `n8n/prompts/12-changelog-tracker.md` | アップデート追跡記者 |
| `n8n/prompts/13-deep-dive.md` | 深掘り解説記者 |

### 実装フェーズへの割り当て（案）

| フェーズ | 追加記者 | 前提 |
|---|---|---|
| Phase 1.5 | WF-09 比較記者 | カタログ整備（既存資産で完結、収集不要のため最優先） |
| Phase 2 | WF-10 速報 / WF-12 アップデート追跡 | 収集パイプライン安定後 |
| Phase 2.5 | WF-07 ファクトチェック / WF-08 体験レビュー | Claim-Auditor 判定API連携・サンドボックス実行基盤 |
| Phase 3 | WF-11 読者Q&A / WF-13 深掘り解説 | UGC受付・内部リンク基盤 |

> ⚠️ 本節は **提案（未確定）**。実装着手前に §10 実装フェーズへ正式に取り込み、各記者ごとに
> Test-Before-Ship の検証項目（§4）を定義してから WF JSON / プロンプトを作成すること。

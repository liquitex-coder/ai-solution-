# AI情報専門サイト 要件定義書

**バージョン**: 2.0  
**最終更新**: 2026-08-07  
**ステータス**: 設計中（"実演する"ショーケース §19 / 動画パイプライン §20 追加）

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
| 中核体験 | **「Claude × 〇〇 で何ができるか」を動画＋再現手順で"実演"して見せるショーケース**（§19） |
| 発信形式 | テキスト記事に加え **動画（デモ／ショート）** で「できること」を見せる（§20） |
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
| **組み合わせレシピ** | **Claude × ツール/MCP/API の実演レシピ（動画＋再現手順＋実出力）**（§19） | 自動 + 実演 |
| **動画デモ** | **画面録画・ショート動画で「できること」を見せる**（§20） | 自動 + 手動 |
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

> **収集ソースのスコープと段階（重要）**: 情報収集は SNS（Threads / YouTube / note / X 等）からも行う方針で**確定**。
> ただし各 **SNS/動画 API の取得・配線は「後日」**（オーナーのキー取得・§17 G0 の意思決定後）に実施する。
> それまでは (a) 無料 RSS と GitHub API を先行稼働させ、(b) 動画は**手動公開**（§20 Stage A）でパイプラインを回す。
> → API 未取得は **ローンチのブロッカーにしない**（後付けで各ソースを有効化できる設計にする）。

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
| SNS/動画 API 取得（YouTube・Threads・X 等） | **後日**（キー取得後に配線） | オーナー確認後 |
| 動画ホスティング（YouTube一次 or 自前） | 提案: YouTube埋め込み（§20-4） | 要確認 |
| 動画制作の自動化度（手動→半自動→自動） | 段階導入（§20-3 Stage A→C） | 要検討 |
| TTS / 画面録画 / 編集ツールの選定 | 未確定（§20-7） | 要検討 |

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

---

## 15. 「動かない記者」を作らない仕組み（No-Dead-Reporter 設計）

### 15-1. 問題定義

記者を増やすほど「書いたが一度も動かしていない記者」が混入する。原因は、記者の実ロジック
（ソース正規化・プロンプト整形・記事パース・WP ペイロード生成）が **n8n ワークフロー JSON の
Code ノード内に埋め込まれ、単体で実行・検証できない**こと。これは §4「設計したが動かない」の禁止事項そのもの。

### 15-2. 設計原則

> **記者ロジックは n8n JSON から切り出し、外部依存ゼロで実行できる純関数モジュールにする。**
> **全記者はマージ前に「ドライラン検証ゲート」を必ず通す。ゲートを通らない記者はマージ不可。**

これにより「動かない記者が存在しえない」状態を構造的に保証する（Claim-Auditor の
`check_wired` / `check_active_witnessed` と同一思想）。

### 15-3. 記者コントラクト（共通インターフェース）

各記者は `reporters/reporters/NN-slug.mjs` に、以下の**純関数**を持つモジュールとして実装する。
外部 I/O（HTTP・API キー・n8n）は一切含めない。

| メンバ | 型 | 責務 |
|---|---|---|
| `id` / `slug` / `title` / `category` / `model` / `trigger` | メタ | 記者の識別・分類 |
| `normalize(rawSource)` | 純関数 | 収集した生データ → 正規化アイテム配列 |
| `buildClaudeRequest({items, prompt, model})` | 純関数 | 正規化アイテム＋プロンプト → Claude API リクエスト body |
| `parseArticle(claudeResponse)` | 純関数 | Claude レスポンス → `{ title, html }` |
| `buildWpPayload(article, opts)` | 純関数 | 記事 → WordPress REST ペイロード（既定 `status: draft`） |

### 15-4. フィクスチャとドライラン

各記者は `reporters/fixtures/NN-slug.json` に **`{ rawSource, claudeResponse }`** の固定入力を持つ。
ドライランハーネス（`reporters/run.mjs`）は HTTP を一切呼ばず、フィクスチャを使って
`normalize → buildClaudeRequest → parseArticle → buildWpPayload` の全段を実行し、
生成された WP ペイロードを検証する。→ **外部APIキー不要・ネットワーク不要で「実際に動く」ことを証明**。

### 15-5. 記事ルールの機械検証（validators）

`reporters/validators.mjs` が §4・`article-base.md` のルールをコードで強制する。

| 検証 | 内容 |
|---|---|
| `assertArticleHtml(html)` | 先頭が `<h2` / 禁止タグ（`html`,`body`,`script`,`style`）なし / コードフェンスなし / 非空 |
| `assertWpPayload(p)` | `status` 既定 `draft` / `title` 非空 / `content` が `assertArticleHtml` を通過 |
| 禁止フレーズ検査 | 「おそらく」「かもしれません」等（`article-base.md`）を含まない |

### 15-6. ゲート（マージ阻止）

`scripts/check_reporters.mjs` が **レジストリ（`reporters/registry.mjs`）の全記者**について次を検査し、
1件でも失敗すれば **exit 1**（＝マージ不可）。

| 記者種別 | witness（証拠）要件 |
|---|---|
| native（07〜13） | プロンプトファイル存在 ＋ フィクスチャ存在 ＋ **ドライラン全段成功** ＋ ペイロードが validators 通過 |
| n8n（01〜06） | ワークフロー JSON が parse 可能 ＋ Claude ノードと WP ノードを含む ＋ 参照プロンプトが存在 |

### 15-7. テストと CI

- 単体テスト: `node --test`（`reporters/*.test.mjs`）。**ランタイム依存パッケージゼロ**（Node 標準のみ）→ `npm install` 不要で必ず走る。
- CI: `.github/workflows/reporters.yml` が push/PR で `node --test` とゲートを実行。ネットワーク不使用のため設定段階で落ちない。
- ローカルゲート（プッシュ前）:
  ```bash
  node --test reporters
  node scripts/check_reporters.mjs
  ```

### 15-8. 本番（n8n）との整合 — JSON はモジュールから生成する

n8n の Code ノードは、テスト済みモジュールと**同一ロジック**でなければならない。手書き転記はドリフトの温床
なので、**ワークフロー JSON は `scripts/gen_n8n.mjs` がモジュールから自動生成する**。

- 生成器は各記者モジュールの関数を `Function.prototype.toString()` で取得し、Code ノードへ**そのままインライン
  展開**する（`normalize` / `buildClaudeRequest` / `parseArticle` / `buildWpPayload` ＋ 依存する共通ヘルパ・
  validators）。→ Code ノードの中身 ＝ テスト済みソースそのもの。
- 生成される 7 ノード構成: トリガー → ソース入力（フィクスチャ例入り）→ プロンプト読込み → リクエスト生成
  （`normalize`+`buildClaudeRequest`）→ Claude API → 記事生成（`parseArticle`+`buildWpPayload`+`assertWpPayload`）
  → WordPress 下書き投稿 → エラートリガー。
- ソース入力ノードにフィクスチャの `rawSource` を例として埋め込むため、n8n で**手動実行するとそのまま WP 下書き
  が生成**される（§4「manual execute → WP draft」を満たす）。
- 記事生成ノードは投稿前に `assertWpPayload` を実行する。壊れた記事は**投稿されずにワークフローが失敗**する
  （fail-closed）。

**鮮度ゲート**: `reporters/generated.test.mjs` が「モジュールから再生成した JSON」＝「ディスク上の JSON」を検証。
モジュールを変更して `npm run gen:n8n` を忘れると**テストが落ちる**。さらに生成された Code ノードのコードを
`node:vm` で実行し、モジュールのドライラン結果と一致することを確認する（本番コードが実際に動く証拠）。

```bash
npm run gen:n8n     # モジュールから WF-07〜13 の JSON を生成（決定論的）
node --test reporters/*.test.mjs   # 鮮度 + vm 実行一致を検証
```

### 15-10. E2E スモーク（実クレデンシャル疎通）

オフライン検証（§15-4〜15-8）は「ロジックが動く」ことを保証するが、**実 Claude API 呼び出し**と
**実 WordPress 投稿（201）** は別レイヤ。これを `scripts/e2e_smoke.mjs` で検証する。

| モード | Claude | WordPress | 用途 |
|---|---|---|---|
| `--offline`（既定でキー無しなら自動） | フィクスチャ応答 | 実POST（WP_URL） | WP 投稿シームだけ確認 |
| 実行（キーあり） | 実API | 実POST | 完全な E2E 疎通 |

- WP 投稿は `reporters/wp_client.mjs` の `postDraft()` が担当（Basic 認証・`status: draft` 既定）。
- `postDraft()` は**モックHTTPサーバに対する実ソケットのテスト**を持つ（`reporters/wp_client.test.mjs`）。
  → WordPress イメージが無くても、ペイロード→HTTP POST→201/ID 解釈のシームを検証できる。
- 必要な環境変数: `ANTHROPIC_API_KEY`（実Claude時）, `WP_URL` または `WP_POSTS_URL`, `WP_USERNAME`,
  `WP_APP_PASSWORD`。未設定時はスキップ理由を明示して exit 0（安全）。

> ⚠️ 本番の完全 E2E（実キー・実WP）は、APIキーと WordPress ホスティングが揃った環境で
> `node scripts/e2e_smoke.mjs` を実行して確認する（§4 の「201 レスポンスと記事ID」を満たす）。
> サンドボックス内では組織のegressポリシーで WordPress/n8n イメージを取得できないため、
> WP シームはモックサーバ実ソケットテストで代替検証する。

### 15-9. 記者追加時のチェックリスト（DoD）

新記者は次を**すべて**満たすまで DONE にしない:

- [ ] `reporters/reporters/NN-slug.mjs` 実装（コントラクト準拠・I/Oなし）
- [ ] `reporters/fixtures/NN-slug.json` 追加
- [ ] `n8n/prompts/NN-slug.md` 追加
- [ ] `reporters/registry.mjs` に登録
- [ ] `node --test reporters` green（出力を PR に貼る）
- [ ] `node scripts/check_reporters.mjs` green（出力を PR に貼る）

---

## 16. 収益化モデル（Monetization）

> ⚠️ 本章は **設計提案**。金額・料率・チャネルは市場調査後に確定する（`未確定`を明記）。
> 本章は法務助言ではない。景品表示法・ステマ規制・各ASP規約の適用可否は施行前に専門家レビューを要する。

### 16-1. 大原則 — 「信頼を売らない」収益化

このメディアの一次的価値は **証拠主義・ファクトチェック（INV-R1 / INV-R2）** にある。収益化はこの資産を
**消費する**方向に働きやすい（スポンサーに不利な検証を書けなくなる 等）。したがって全モデルは次の
**編集独立原則**に従う。破る収益は取らない。

| 原則 | 内容 |
|---|---|
| **P1 判定の非売品化** | ファクトチェック記者（WF-07）・比較記者（WF-09）の**判定/評点はスポンサー対象外**。真偽判定は LLM-free 決定論（INV-R2）で、広告主に応じて変えない。 |
| **P2 全面開示** | アフィリンク・タイアップ・PR は記事内に**機械可読なフラグ**（`disclosure` メタ）で明示。ステマ規制（景表法・2023-10 施行）に準拠。 |
| **P3 人間署名ゲート** | 収益リンクを含む記事は自動公開しない。`status: draft` のまま**人間が広告該否を承認**してから公開（INV-R1）。 |
| **P4 分離配置** | 「編集記事」と「広告/PR記事」はカテゴリ・URL・視覚デザインで分離。混同させない。 |

### 16-2. モデル一覧

| # | モデル | 収益源 | 接続する記者/ページ | 開始フェーズ | 主要リスク |
|---|---|---|---|---|---|
| M1 | **アフィリエイト** | ASP経由の成果報酬 | ツールカタログ・比較(WF-09)・ハンズオン(WF-08) | Phase 1.5 | 利益相反・料率変動・規約BAN |
| M2 | **企業タイアップ（案件）** | 記事1本あたり固定フィー | 体験レビュー(WF-08)・深掘り(WF-13) | Phase 2 | 編集独立の毀損・PR表記漏れ |
| M3 | **ディスプレイ広告** | インプレッション/クリック | 全記事の枠 | Phase 1.5 | トラフィック依存・低単価 |
| M4 | **情報商材/ノウハウ販売** | 単発購入（既存 §1・§10） | 「このサイトの作り方」記事群 | Phase 3 | 陳腐化・サポート負荷 |
| M5 | **有料会員（サブスク）** | 月額 | 限定プロンプト集・先行速報(WF-10) | Phase 3 | 継続コンテンツ供給 |
| M6 | **リード送客/代理店** | 紹介手数料・代理店マージン | NoimosAI・SaaS紹介(§5) | Phase 2 | 送客品質・成約計測 |
| M7 | **ニュースレター/スポンサー枠** | 号あたり掲載料 | メルマガ（WordPress `/feed`起点） | Phase 2.5 | 読者基盤の規模 |
| M8 | **データ/トレンドAPI提供** | B2B利用料 | 収集パイプラインの二次利用 | Phase 3+ | 一次ソース規約・提供責任 |

### 16-3. 各モデル詳細

#### M1. アフィリエイト（最優先・最も相性が良い）
- **なぜ最優先か**: 既存資産（ツールカタログ・比較記事）に**追加収集ゼロ**でリンクを差せる。§14 の「低コスト高リターン」思想と一致。
- **商材**: AI SaaS（各ツールの公式アフィリエイト）、クラウド/API、書籍・講座、汎用ASP（A8.net・もしもアフィリエイト・afb 等）。
- **実装接点**: カタログの各ツール詳細に `affiliate_url` フィールド（ACF, §9）。比較表(WF-09)・ハンズオン(WF-08)の末尾に定型CTA。
- **ガバナンス**: P1（比較の評点はリンク有無で変えない）・P2（`rel="sponsored nofollow"` + 「本記事にはアフィリエイトリンクを含みます」を冒頭表示）。
- **検証（Test-Before-Ship）**: リンク切れ検査ジョブ、`disclosure`メタ欠落記事を公開させない validator（`reporters/validators.mjs` に `assertDisclosure()` 追加）。

#### M2. 企業タイアップ／案件（スポンサード）
- **形態**: (a) スポンサード体験レビュー、(b) 純広（記事上部バナー）、(c) 導入事例記事。
- **編集独立の担保**: タイアップ記事は**専用カテゴリ「PR」+ URLプレフィックス `/pr/`** に隔離（P4）。ファクトチェック/比較の**判定ロジックには一切介入させない**（P1）。「弊社が検証した結果」と「スポンサー提供情報」を記事内で節分離。
- **料金**: 未確定（フォロワー/PV連動の相場を Phase 2 実測後に設定）。
- **リスク**: PR表記漏れ＝景表法違反。→ 公開前チェックリストに「PRラベル・冒頭明示・`sponsored`属性」を必須ゲート化。

#### M3. ディスプレイ広告
- **段階**: 初期 Google AdSense → PV成長後にメディアネットワーク/純広へ。
- **UX方針**: §2-2 の「カード型・スキャンしやすい」を壊さない広告密度。速報(WF-10)の回遊で面を作る。
- **リスク**: 単価が低くトラフィック規模依存。**主収益ではなく下支え**と位置づける。

#### M4. 情報商材／ノウハウ販売（既定路線の具体化）
- **原資**: 「このサイト構築プロセス自体を記事化・販売」（§1, §10 Phase 3）。
- **商品形態**: note有料マガジン / Zenn Book / 電子書籍 / 動画講座（Udemy）/ テンプレート販売（n8nワークフロー・プロンプト集）。
- **強み**: **ドッグフーディングの証拠**（本サイト自体が全自動で動いている）を実証データとして同梱でき、反ハルシネーション思想と親和。
- **注意**: 陳腐化が速い領域。バージョン明記＋更新差分販売（M5へ橋渡し）。

#### M5. 有料会員（サブスク）
- **提供価値**: 限定プロンプト集（§2 プロンプト集の有料階層）、速報(WF-10)の先行通知、限定深掘り(WF-13)、質問優先(WF-11 読者Q&A)。
- **前提**: 無料層で信頼と回遊を確立してから。継続供給できる記者ラインが揃う Phase 3。
- **課金基盤**: 未確定（WordPress会員プラグイン / 外部（Stripe, note メンバーシップ））。

#### M6. リード送客・代理店（B2B）
- **形態**: NoimosAI（§5, $99/月〜）や各SaaSへの送客紹介料、または**代理店契約**でマージンを取る（アフィリの上位版）。
- **強み**: 「このサイト自体が NoimosAI で動く」実例（§5-B）が最強の営業素材。導入ガイド記事＝送客導線。
- **計測**: UTM + 成約フックの計測設計が必須（未確定）。

#### M7. ニュースレター／スポンサー枠
- **導線**: WordPress `/feed`（§5）を起点にメルマガ化。号ごとに1スポンサー枠。
- **前提**: 購読者規模。Phase 2.5 で速報・週次レポート(WF-06)を号コンテンツに転用。

#### M8. データ／トレンドAPI提供（将来）
- **構想**: 収集・正規化した「AIトレンドデータ」を B2B に提供。
- **障壁**: 一次ソース（GitHub/YouTube/各API）の規約で**再配布可否**が割れる。提供前に規約精査が必須（未確定・優先度低）。

### 16-4. 利益相反・開示ガバナンス（全モデル共通ゲート）

収益リンク/PRを含む記事は、公開前に**機械チェック**を通す（§4 Test-Before-Ship の拡張）。

| ゲート | 内容 | 実装 |
|---|---|---|
| G1 開示メタ必須 | `disclosure ∈ {none, affiliate, sponsored, ad}` が空でない | `validators.mjs: assertDisclosure()` |
| G2 冒頭明示 | affiliate/sponsored は本文先頭に定型開示文 | `assertArticleHtml` 拡張 |
| G3 属性付与 | 収益リンクに `rel="sponsored nofollow"` | ペイロード生成時に強制 |
| G4 判定隔離 | WF-07/09 の判定ノードは収益メタを**入力に取らない** | 記者コントラクトで分離（§15-3） |
| G5 人間承認 | 収益記事は `draft` 固定・自動公開禁止 | INV-R1（§16-1 P3） |

### 16-5. フェーズ割り当て

| フェーズ | 投入モデル | 前提 |
|---|---|---|
| Phase 1.5 | M1 アフィリエイト / M3 AdSense | カタログ整備・記事量産開始（既存資産で開始可能） |
| Phase 2 | M2 タイアップ / M6 送客 | PV実績（媒体資料が作れる規模） |
| Phase 2.5 | M7 ニュースレター | 購読者基盤 |
| Phase 3 | M4 情報商材 / M5 サブスク | 信頼確立・継続供給ライン |
| Phase 3+ | M8 データ提供 | 一次ソース規約クリア |

### 16-6. KPI・計測（未確定・要設計）

- 収益系: RPM（1000PVあたり収益）、アフィリEPC、案件単価、サブスク MRR/解約率、送客成約率。
- 信頼系（収益と両立させる守りの指標）: PR記事比率の上限、開示メタ欠落率＝0、判定記事のスポンサー混入＝0。
- 計測基盤: GA4 + Search Console（§5 SEOエージェント）+ ASP管理画面。UTM設計は未確定。

### 16-7. 未確定事項（§12 に追記予定）

| 項目 | ステータス |
|---|---|
| 各ASP・アフィリプログラムの選定と規約適合 | 未確定 |
| タイアップ料金表・媒体資料 | 未確定（PV実測後） |
| サブスク課金基盤（Stripe / note / WPプラグイン） | 未確定 |
| ステマ規制・景表法の記事テンプレ法務レビュー | **必須・未実施** |
| 収益計測（UTM・成約フック）設計 | 未確定 |

---

## 17. ローンチ・ロードマップ（"回り出す"までに必要な要素）

> 目的: 本プロダクトが **自走状態（全記者が cron で回り、監視付きで人間承認だけ挟む）** に到達するまでの
> クリティカルパスを、準備ゲート **G0→G6** で定義する。各ゲートは前ゲートの完了を前提とする。

### 17-0. 現在地（証拠）

| 事実 | 根拠 |
|---|---|
| フェーズは Phase 0（サンドボックス）進行中 | §10 |
| オフライン記者基盤は稼働（WF-07〜13 生成・ドライラン・vm実行一致） | §15, README §記者フレームワーク |
| **未確定ブロッカー**: ホスティング / ドメイン / APIキー保有 / n8n運用方式 | §12 |
| 実クレデンシャルでの Claude→WP 201 は**未実施** | §15-10（E2Eは設計済・未実行） |

→ ロジックは動く。**「本番インフラ・意思決定・運用/安全体制」が欠けている**のが自走までのギャップ。

### 17-1. 準備ゲート一覧（クリティカルパス）

| ゲート | 名称 | 目的 | 完了条件（DoD） | 主依存 |
|---|---|---|---|---|
| **G0** | 意思決定ロック | ブロッカー解消 | ホスティング先・ドメイン・n8n運用方式を確定、全APIキー保有を確認（§12 を全て「確定」に） | オーナー判断 |
| **G1** | サンドボックス緑 | ロジック証明 | `node --test reporters` + `check_reporters.mjs` green、`docker-compose up` で WP/n8n 応答（§4・§7チェックリスト） | G0一部 |
| **G2** | 実疎通（初ドラフト） | シーム証明 | 実キーで `e2e_smoke.mjs` 実行 → 実Claude生成 → 実WP **201＋記事ID**（§15-10） | G0（キー・WP） |
| **G3** | 本番インフラ稼働 | 常時稼働 | 本番WP（テーマ・§9プラグイン・§data taxonomy投入・App Password）＋ n8n本番に全WF投入＋プロンプトGitHub取得配線（README §プロンプト管理） | G2 |
| **G4** | 編集安全体制 | 信頼の担保 | 人間レビューキュー（`draft`承認フロー・INV-R1）＋ 開示ゲート G1–G5（§16-4）＋ 法務ページ（プライバシー/運営者情報/免責）＋ ステマ規制テンプレ法務レビュー | G3 |
| **G5** | 流通・計測 | 見つかる/測れる | Sitemap＋Search Console登録＋Rank Math＋GA4計測＋ NoimosAI初期連携（§5）＋ `/feed` 稼働 | G3 |
| **G6** | 自走運用 | 回り出す | 全WFが cron 稼働＋ n8n エラーワークフロー＋アラート＋運用Runbook（§11・SETUP_GUIDE）＋ **§18 品質ループ稼働** | G4,G5 |

### 17-2. ゲート別・必要要素の内訳

**G0 意思決定ロック（最優先・非技術ブロッカー）**
- WordPress ホスティング先確定（本番）／独立ドメイン取得／n8n（セルフホスト or n8n.cloud）確定。
- APIキー保有確認: `ANTHROPIC_API_KEY` / `GITHUB_TOKEN` / `YOUTUBE_API_KEY` / `PERPLEXITY_API_KEY`。
- → これが解けるまで G2 以降は**着手不能**（§12 の未確定が実装の律速）。

**G3 本番インフラ（"作る"の本体）**
- WordPress: テーマ（§8）、プラグイン一式（§9）、カテゴリ/タグ（`data/wp-taxonomy.json`）投入、Application Password 発行。
- n8n: 本番デプロイ、クレデンシャル（WP Basic / Claude / GitHub / YouTube / Perplexity）登録、WF-01〜13 インポート、スケジュール有効化。
- プロンプト配線: 各WFが GitHub `contents/n8n/prompts/*.md` を動的取得（ハードコード禁止・README準拠）。

**G4 編集安全体制（"信頼を守る"の本体・差別化の核）**
- 人間レビューキュー: 全記事 `status: draft` → 承認して公開（INV-R1）。承認UI/運用ルール。
- 収益記事ゲート G1–G5（§16-4）を validators に実装（`assertDisclosure()` 等）。
- 法務: 運営者情報・プライバシーポリシー・免責/PR方針ページ、ステマ規制テンプレの法務レビュー（§16-7 未実施）。

**G5 流通・計測（"届ける/測る"）**
- SEO: Sitemap（Rank Math）、Search Console 登録、内部リンク（WF-13）。
- 計測: GA4 設置、収益/信頼KPI（§16-6）のダッシュボード。
- 配信: NoimosAI 連携（§5）、`/feed` からのSNS/メルマガ配信トリガー。

**G6 自走運用（"回り続ける"）**
- 全WF cron 稼働（毎朝/30分/1時間/週次…§4-2）。
- 監視: n8n エラーワークフロー（§15-8 fail-closed）、失敗アラート（メール/Slack）、§11 エラー対応表の Runbook 化。
- **§18 の品質ループを常時稼働**（ここで初めて "改善しながら回る" 状態）。

### 17-3. クリティカルパス（要約）

```
G0 意思決定 ──▶ G2 実疎通(初201) ──▶ G3 本番インフラ ──┬─▶ G4 編集安全 ──┐
     │                                                └─▶ G5 流通・計測 ─┤
     └─▶ G1 サンドボックス緑（並行・ほぼ完了）                            ▼
                                                              G6 自走運用 ＋ §18品質ループ
```

- **律速は G0（非技術）**。技術側（G1）はほぼ緑なので、意思決定が解ければ G2→G3 は速い。
- G4 を G5 と**並行**可能だが、G4 未了のまま公開してはならない（INV-R1 / 開示義務）。

---

## 18. 継続的品質改善ループ（Quality Loop アーキテクチャ）

> 目的: 記事品質を**一度の実装で終わらせず、計測→評価→改善→検証を閉じたループ**で絶えず上げ続ける。
> 設計の芯は本プラットフォームのDNAの転用: **判定は決定論・提案だけLLM（INV-R2）** ＋ **prompt-as-code の PDCA（§4）**。

### 18-1. 原則

| 原則 | 内容 |
|---|---|
| **Q1 決定論ゲート** | 「公開してよいか」「改善案を採用してよいか」の**合否は決定論ルーブリック**が下す。LLMは採点の**提案者**に留める（INV-R2 の思想を品質判定に適用）。 |
| **Q2 退行させない** | プロンプト/記者の変更は、**ゴールデン評価セットで基準値を下回ったらマージ不可**（`check_test_count` の baseline 方式を品質に拡張）。 |
| **Q3 証拠で回す** | 改善の起点は感覚でなく**計測データ**（レビュー判断・GA4・Search Console・アフィリEPC・判定精度）。 |
| **Q4 人手の訂正を資産化** | レビュアーの修正/却下を**ゴールデン事例と少数ショット例に還元**（学習の代わりに評価セットと few-shot を強化）。 |
| **Q5 fail-closed** | 品質未達の記事は**投稿されずワークフロー失敗**（§15-8 の `assertWpPayload` を品質スコアまで拡張）。 |

### 18-2. 品質の3層（どこで測るか）

| 層 | タイミング | シグナル | 既存資産 |
|---|---|---|---|
| **L1 生成時（pre-publish）** | 投稿前・自動 | validator 合否＋品質スコア | `reporters/validators.mjs`（`assertArticleHtml`/`assertWpPayload`） |
| **L2 人間レビュー** | 公開前・人手 | 承認/編集/却下＋編集差分 | INV-R1 レビューキュー（G4） |
| **L3 本番（post-publish）** | 公開後・自動 | 滞在時間/直帰/CTR、検索順位・表示回数、アフィリEPC、ファクトチェック的中 | GA4 / Search Console（§5）/ ASP |

### 18-3. ループ全体図

```
        ┌──────────────────────────────────────────────────────────┐
        │                    QUALITY LOOP (QLOOP)                    │
        │                                                            │
   ┌────▼─────┐   ┌───────────┐   ┌───────────┐   ┌──────────────┐  │
   │ MEASURE  │──▶│ EVALUATE  │──▶│ DIAGNOSE  │──▶│  PROPOSE     │  │
   │ 3層の    │   │ ゴールデン │   │ 弱い記者/  │   │ 改善案生成    │  │
   │ シグナル  │   │ 評価+採点  │   │ プロンプト │   │ (LLM提案      │  │
   │ 収集     │   │ (決定論)   │   │ を特定    │   │  +反証 S4/S5)│  │
   └────▲─────┘   └───────────┘   └───────────┘   └──────┬───────┘  │
        │                                                 │          │
        │         ┌───────────┐        ┌───────────┐      ▼          │
        │         │  SHIP     │◀───────│   GATE    │◀── PR (prompt   │
        └─────────│ 本番反映   │ 人間署名 │ 回帰評価   │    -as-code)   │
                  │ (GitHub    │ (INV-R1)│ (退行不可) │                │
                  │  取得)     │        │ +validator│                │
                  └───────────┘        └───────────┘                │
        └──────────────────────────────────────────────────────────┘
              A/B・カナリア（新プロンプトを一部トラフィックで比較）
```

### 18-4. 各ステージ

1. **MEASURE** — 3層（§18-2）のシグナルを収集し、記者/プロンプト単位で正規化してメトリクスストアに蓄積。
   L2 のレビュー判断（承認/編集/却下＋差分）を必ず記録（Q4の原資）。
2. **EVALUATE** — **ゴールデン評価セット**（記者ごとの固定入力＋期待品質）に対し、候補プロンプトの出力を
   **ルーブリック（§18-5）で採点**。LLM-critic は所見を提案するが、**スコア集計は決定論**（Q1）。
3. **DIAGNOSE** — スコア最下位・却下率最大・CTR最悪の記者/プロンプトを**改善バックログ**として順位付け。
4. **PROPOSE** — 改善プロンプト案を生成。Claim-builder の **S4生成→S5反証（adversarial rebuttal）** を踏襲し、
   相関誤りを削ってから **PR（prompt-as-code）** 化。
5. **GATE** — オフライン**回帰ゲート**: 候補は (a) ゴールデンで基準値を上回る (b) validators 通過
   (c) **どの記者もスコアを下げない**、を全て満たすときのみ緑（Q2）。最後に**人間署名**（INV-R1）。
6. **SHIP** — マージされたプロンプトは GitHub 動的取得で即本番反映（README §プロンプト管理）。
   可能なら**カナリア/A-B**で新旧を一部トラフィック比較 → MEASURE に戻る。

### 18-5. 品質スコア・ルーブリック（決定論・機械採点）

`reporters/quality.mjs`（新設）が各記事に対し加点式スコアを算出。**LLM不要の項目を主**とする。

| 次元 | 判定 | 種別 |
|---|---|---|
| 構造 | `<h2>`始まり・禁止タグなし・コードフェンスなし（`assertArticleHtml` 準拠） | 決定論 |
| 開示 | `disclosure` メタ整合・収益リンク属性（§16-4 G1–G3） | 決定論 |
| 証拠性 | 出典/一次リンクの本数、ファクトチェック記事は「主張/条件/判定/根拠」4要素（§14 WF-07） | 決定論 |
| 禁止表現 | 「おそらく」「かもしれません」等の不在（`article-base.md`・§15-5） | 決定論 |
| 可読性 | 見出し密度・段落長・文字数レンジ | 決定論 |
| 妥当性（補助） | LLM-critic による事実整合の**所見**（スコアには重み低・参考） | LLM提案 |

> スコアは fail-closed 閾値（L1）と、改善採否の基準値（GATE）の両方に使う。

### 18-6. 回帰ゲート（baseline 方式）

- `reporters/fixtures/golden/NN-*.json` に**期待品質つきゴールデン入力**を持つ。
- `scripts/check_quality_baseline.mjs` が現行プロンプトのスコアを `quality-baseline.json` として固定。
- プロンプト変更 PR は `node scripts/check_quality_baseline.mjs --compare` を実行し、**基準値割れで exit 1**。
  基準を上げるときのみ `--update-baseline`（`check_test_count` と同じ運用・§7）。
- CI（`.github/workflows/reporters.yml`）に同ゲートを追加（ネットワーク不使用で設定段階落ちなし・§15-7）。

### 18-7. 人手の訂正を資産化（学習なしで賢くなる）

- L2 でレビュアーが編集/却下したら、その **before/after 差分**を収集。
- 定期ジョブが差分から (a) **新ゴールデン事例**（再発防止テスト）と (b) **few-shot 例**（プロンプトの手本）を提案 PR 化。
- → モデル微調整なしで、**評価セットとプロンプトが人手の判断を蓄積**して改善する（Q4）。これは §15 の
  「No-Dead-Reporter」を品質面に延長した「No-Regressing-Reporter」に相当。

### 18-8. データフローと計測基盤

```
L1 validators/quality.mjs ─┐
L2 レビュー判断ログ        ─┼─▶ メトリクスストア ─▶ EVALUATE/DIAGNOSE ─▶ 改善PR
L3 GA4 / Search Console / ─┘        (集約)              (週次バッチ)
   ASP(EPC)
```

- 収集は既存導線を再利用: `/feed`・GA4・Search Console（§5）、ASP管理画面（§16）。
- 週次の DIAGNOSE は WF-06（週次レポート）を**内部品質レポート**にも転用可能。

### 18-9. 実装への割り当て（新規/拡張）

| 対象 | 追加/拡張 | ゲート |
|---|---|---|
| `reporters/quality.mjs` | ルーブリック採点（新規） | §18-5 |
| `reporters/validators.mjs` | `assertDisclosure()` 等 L1 拡張（§16 G1–G3） | §16-4 |
| `reporters/fixtures/golden/` | 記者別ゴールデン＋期待品質（新規） | §18-6 |
| `scripts/check_quality_baseline.mjs` | 回帰ゲート（新規） | §18-6 |
| `.github/workflows/reporters.yml` | 品質ゲート追加 | §15-7 |
| L2 レビューキュー | 承認UI＋差分ログ（G4） | §17 G4 |

### 18-10. 未確定事項

| 項目 | ステータス |
|---|---|
| メトリクスストアの実体（DB / スプレッドシート / n8n data table） | 未確定 |
| A/B・カナリアの配信基盤（WP/エッジで実現するか） | 未確定 |
| ファクトチェック的中の「後日正解」判定プロセス | 未確定 |
| LLM-critic の採点重み（参考値以上に上げるか） | 未確定（Q1 は死守） |

---

## 19. プロダクト・ポジショニング — "実演する" AIショーケース

> 本サイトの一次的価値を **「まとめて伝える」から「組み合わせて実演して見せる」へ引き上げる**。
> 中核コンテンツは **組み合わせレシピ（Combination Recipe）** = 「**Claude × 〇〇 で何ができるか**」を
> **動画＋再現手順＋実出力**で証明するコンテンツ。既存の証拠主義（INV-R1/R2）・WF-08 ハンズオンの正統進化。

### 19-1. ポジショニング転換

| 旧（アグリゲーション型） | 新（ショーケース型・追加） |
|---|---|
| 収集 → 要約・翻訳 → 投稿（WF-01〜06） | **Claude × ツールの組み合わせを実際に動かして見せる** |
| 一次情報の日本語化が主眼 | **「何と組み合わせれば何ができるか」を再現可能な形で提示** |
| 差別化＝速さ・網羅 | 差別化＝**実演の証拠**（動画・手順・実出力） |

> アグリゲーション記者は**廃止しない**。ネタ発見・トレンド把握の入口として残し、そこから
> 「レシピ化する価値のある組み合わせ」を選んで旗艦コンテンツ（レシピ）に昇格させる。

### 19-2. 中核コンテンツ = 組み合わせレシピ

**定義**: `Claude × [組み合わせ対象] → [できること / 成果]`

| 組み合わせ対象の型 | 例 |
|---|---|
| MCP サーバー | Claude × WordPress MCP（本サイト自体・§13）、Claude × Figma、Claude × Google Drive |
| 外部 API | Claude × GitHub API、Claude × YouTube、Claude × Perplexity |
| 他ツール / 基盤 | Claude × n8n（本パイプライン）、Claude × スプレッドシート、Claude × Docker |
| データソース | Claude × RSS、Claude × 自社DB |
| 別のAI/機能 | Claude × 画像生成、Claude × TTS（§20） |

### 19-3. レシピの必須要素（"実際に見せる" ＝ 証拠主義）

各レシピは次を**すべて**含む。欠けたら公開しない（fail-closed・INV-R1）。

| 要素 | 内容 |
|---|---|
| 組み合わせ | 何と組み合わせるか（対象・前提・必要なもの） |
| できること | 1文の価値（例「議事録PDFを渡すと要約タスクを自動でチケット化」） |
| **実演（動画）** | §20 のデモ動画 or ショート（埋め込み） |
| **再現手順** | コピペ可能なステップ（コマンド/プロンプト/設定） |
| **実出力** | 実際のAPIレスポンス/スクショ（WF-08 と同じ証拠要件） |
| 難易度 | 入門 / 中級 / 上級 |
| 関連レシピ | 内部リンク（回遊・§14 WF-13 と連携） |

### 19-4. 単一ソース・複数レンダリング

1つのレシピを単一データとして持ち、複数面へ展開する（記者フレームワークの純関数コントラクトに乗せる）。

```
Recipe（単一ソース）
  ├─▶ 記事HTML（WordPress 下書き）
  ├─▶ 動画デモ（§20）
  ├─▶ SNSショート（§5 SNSエージェント配信）
  └─▶ レシピカタログのカード（§2 一覧）
```

### 19-5. データモデル（提案・ACF で保持）

```jsonc
Recipe {
  id, title,
  combo: { base: "Claude", with: "WordPress MCP" },
  canDo: "一文の価値",
  difficulty: "入門|中級|上級",
  steps: [ "手順1", "手順2", ... ],          // 再現手順
  evidence: { videoId?: "yt:...", output?: "実出力", screenshots?: [...] },
  links: [ recipeId, ... ]                    // 内部リンク
}
```

### 19-6. 記者・品質ゲートへの統合

- **新記者 WF-14「レシピ実演記者」（提案）**: `normalize(recipe)` → `buildClaudeRequest` → `parseArticle` →
  `buildWpPayload`。§15 のコントラクト・ドライラン検証を必須とする（動かないレシピを作らない）。
- **§18 ルーブリック拡張**: レシピ記事には「**実演の証拠**」次元を追加 —
  `evidence.videoId` か 手順ブロック か 実出力のいずれかが存在すること（`quality.mjs` に `recipe_evidence` 次元）。
  → No-Dead-Reporter を **「No-Unproven-Recipe（証拠なきレシピは出さない）」** に拡張。

### 19-7. フェーズ割り当て（§17 と整合）

| フェーズ | 内容 |
|---|---|
| Phase 1.5 | レシピのデータモデル＋カタログページ＋WF-14 レシピ記者（**手動動画**・§20 Stage A） |
| Phase 2 | 動画の半自動化（§20 Stage B）、SNSショート配信（API取得後） |
| Phase 3 | サンドボックス実行キャプチャによる自動実演（§20 Stage C） |

---

## 20. 動画コンテンツ・パイプライン

> 目的: **文字だけでなく動画で「できること」を見せる**。テキスト＝検索流入、動画＝**理解と信頼**
> （実際に動く証拠）。§19 レシピの「実演」本体を担う。

### 20-1. 動画タイプ

| タイプ | 尺 | 用途 | 連携 |
|---|---|---|---|
| デモ動画 | 2〜5分 | レシピの実演本体（画面録画＋ナレーション） | §19 レシピに埋め込み |
| ショート（縦型） | 30〜60秒 | SNS配信・回遊入口 | §5 SNSエージェント（API後日） |
| 長尺解説 | 任意 | 深掘り（ピラー） | §14 WF-13 |

### 20-2. 制作パイプライン（自動化を段階導入）

> **どの段階でも「台本(script)とメタ(manifest)はモジュールで生成・検証」**する。実レンダリング/実アップロードは
> 別シーム（E2E 層・§15-10 と同型）に分離し、台本生成は HTTP/キー無しでドライラン検証できるようにする。

| Stage | Claude | 制作 | 公開 | いつ |
|---|---|---|---|---|
| **A 手動主体** | 台本/絵コンテを生成 | 人間が画面録画・編集 | YouTube 手動 → 記事に埋め込み | **最初（API取得前でも回る）** |
| **B 半自動** | 台本 | TTSナレーション＋スライド/画面キャプチャ自動合成 | 半自動アップロード | Phase 2 |
| **C 自動（将来）** | 手順を**サンドボックスで実行しキャプチャ** | 実出力をそのまま動画化（究極の証拠主義） | 自動 | Phase 3 |

### 20-3. ホスティング・配信

- **一次ホスト = YouTube**（埋め込み・無料・SEO・被リンク）。WordPress へ `<iframe>`/oEmbed 埋め込み。
- ショートは各 SNS（§3・§5）へ。**自前動画ストレージは持たない**（コスト・運用回避）。
- **YouTube/SNS への API アップロードは「後日」**（キー取得後）。それまでは手動アップロード（Stage A）。

### 20-4. 記者フレームワーク統合（動画台本記者）

「動画台本」を**純関数で生成**する記者を追加（レンダリングは含めない）。

| メンバ | 責務 |
|---|---|
| `normalize(recipe)` | レシピ → シーン配列（各シーン: 画面指示 + ナレーション） |
| `buildScript({scenes, prompt})` | Claude リクエスト（台本生成プロンプト注入） |
| `parseScript(claudeResponse)` | レスポンス → `{ title, scenes[] }` |
| `buildVideoManifest(script)` | `{ title, scenes[], durationEst, ttsVoice, sourceRecipeId }` |

- フィクスチャ（`reporters/fixtures/NN-video-*.json`）＋ドライランで**台本生成が動くこと**を証明（§15-4）。

### 20-5. 検証（Test-Before-Ship）

| ゲート | 内容 | 実装 |
|---|---|---|
| 台本 validator | シーン数>0／各シーンに画面指示＋ナレーション／禁止表現なし（`article-base.md` 流用）／尺見積り範囲内 | `reporters/validators.mjs` に `assertVideoManifest()` |
| 公開ゲート | レシピ記事は「動画ID or 台本manifest」が紐づくまで**公開不可**（fail-closed） | §19-3 |
| 実レンダリング/アップロード | 実TTS・実YouTube は E2E スモーク層で確認（キー環境） | `scripts/e2e_smoke.mjs` 拡張（§15-10） |

### 20-6. 未確定事項

| 項目 | ステータス |
|---|---|
| TTS/音声サービス（どれを使うか） | 未確定 |
| 画面録画・キャプチャ自動化（Stage B/C の実現手段） | 未確定 |
| 動画編集の自動化（テロップ・カット） | 未確定 |
| YouTube Data API アップロード自動化の時期 | **後日**（§3・SNS API後回し方針と整合） |
| ショート量産の可否・本数 | 未確定 |

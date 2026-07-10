# AI情報専門サイト 要件定義書

**バージョン**: 2.0  
**最終更新**: 2026-07-10  
**ステータス**: 設計中（ホスティング先未確定）

---

## 1. サイト概要

| 項目 | 内容 |
|---|---|
| サイト名 | AIナビ（仮） |
| 目的 | AI初心者〜中級者が「使える・試せる」情報を得られる日本語ハブ |
| ターゲット | 日本語圈（メイン）・英語圈（技術SNS・動画経由でリーチ拡大） |
| 言語 | 日本語メイン / 英語SEOメタ・将来英語記事化 |
| CMS | WordPress |
| コンセプト | **人間の介入を最小化した全自動AI情報メディア** |
| 戦略軽層 | **このパイプライン自体がClaim Platformの実動デモ・宣伝媦体** |
| ノウハウ化 | サイト構築プロセス自体を記事化・販売する予定 |

---

## 2. コンテンツ構成

### 2-1. ページ構成

| ページ | 内容 | 更新方式 |
|---|---|---|
| トップ | 注目ツール・最新ニュース・入門ガイド | 自動 |
| AIツールカタログ | 厳選ツール一覧（カテゴリ・料金フィルター） | 手動 + 自動 |
| ツール詳細 | 各ツールの詳細・使い方・メリデメ・比較 | 手動 + 自動 |
| 使い方ガイド | ステップバイステップのHow Toガイド | 自動生成 |
| 連携・自動化 | NoimosAI連携・n8n統合手順 | 手動 |
| AIニュース | 最新アップデート・リリース情報 | 全自動 |
| GitHubトレンド | 今日の注目 AIリポジトリ | 全自動（毎朝） |
| プロンプト集 | コピーして使えるプロンプトテンプレート | 自動 + UGC（将来） |
| インフルエンサー発信 | SNS上のAIノウハウ・話題まとめ | 全自動 |
| **Claim Platform紹介** | claim-auditor / crew / security活用事例 | 自動生成 + 手動 |

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
| Perplexity API | Perplexity API | 無料枚あり | AIトレンドキーワード検索 |
| **NoimosAI** | **Google Docs経由** | **別途計上** | **戦略立案・SEO記事** |

### Phase 2：有料ソース追加（成長後）

| ソース | 取得方法 | コスト | 追加タイミング |
|---|---|---|---|
| X (Twitter) | X API v2 | $100/月〜 | 収益化後 |
| X スクレイピング | Apify | $49/月〜 | 収益化後 |
| Instagram | Instagram Graph API | 無料枚あり | Phase 2 |

---

## 4. 自動化パイプライン（全体アーキテクチャ）

```
【ネタ収集・コンテンツ生成層】
WF01: GitHub AI Trending ──────────┬
WF02: RSS Monitor ────────────────┬
WF03: YouTube新動画 ────────────┬
WF04: Threadsインフルエンサー ───┬── claim-crew（記者エージェント）
WF05: note監視 ───────────────┬
WF06: 週次トレンドレポート ─────┬
WF07: NoimosAI（Google Docs） ───┘
                                    ↓
                        【claim-builder + councilループ】
                        N案生成→コンセンサス選択
                                    ↓
                        【claim-llm】LLM抗象層
                                    ↓
┌────────────────────────────────────────────────┐
│        Claim-Auditor ゲート（全生成物必須）        │
│  ✅ PASS        → 次工程へ                   │
│  ❌ FAIL        → 人間レビューキュー          │ ← INV-R1
│  ⚠️ UNVERIFIABLE → ドラフト+フラグ表示       │ ← INV-R2
└────────────────────────────────────────────────┘
                    ↓ PASSのみ
          【ビジュアル生成】
          ├─ Mermaid図解（Kroki.ioで無料レンダリング）
          ├─ Flux.1アイキャッチ（fal.ai ~¥1/枚）
          └─ Higgsfield動画（英語圈SNS配信）
                    ↓
          【claim-security-】APIエンドポイント保護
                    ↓
          WordPress（下書き投稿）
                    ↓
          人間が最終承認・公開 ← INV-R1
                    ↓
          【claim-evolve】プロンプト・品質継続改善
```

### n8nワークフロー一覧

| # | ワークフロー名 | トリガー | 処理内容 |
|---|---|---|---|
| 01 | github-trending-daily | 毎朝8:00 | GitHubトレンドAIリポジトリ取得→記事生成→Auditor→投稿 |
| 02 | rss-monitor | 30分ごと | 各社ブログRSS監視→新記事検知→日本語記事生成→Auditor→投稿 |
| 03 | youtube-new-video | 1時間ごと | 対象チャンネル新動画検知→要約→記事生成→Auditor→投稿 |
| 04 | threads-influencer | 3時間ごと | 対象アカウント投稿収集→まとめ記事生成→Auditor→投稿 |
| 05 | note-monitor | 1時間ごと | note RSS監視→AI関連記事抽出→転載記事生成→Auditor→投稿 |
| 06 | weekly-trend-report | 毎週月曜 | Perplexityでトレンド検索→週次まとめ記事生成→Auditor→投稿 |
| **07** | **noimosai-google-docs** | **Google Drive新規ファイル** | **NoimosAI記事取得→Claude整形→Auditor→投稿** |

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
| `n8n/prompts/07-noimosai-format.md` | NoimosAI記事整形プロンプト（新規） |

---

## 5. Claim Platform連携戦略

**核心思想**: パイプライン自体がClaim Platformのユースケースデモであり、「AIナビを動かすために使ったツールの紹介」自体が最強の宣伝媦体となる。

### 5-1. 各プロダクトの役割

| プロダクト | パイプライン内の役割 | 宣伝切り口 |
|---|---|---|
| **claim-auditor** | 全生成物のファクトチェックゲート | 「このメディアは全記事をAuditor検証済」 |
| **claim-crew** | 記者エージェント（多角度取材・整理） | 「AIエージェントが假想記者として取材」 |
| **claim-builder + council** | 記事品質向上（N案生成→コンセンサス選択） | 「複数Claudeの協議で記事を生成」 |
| **claim-llm** | LLM抗象層（ネットワークポリシー制御） | 「LLM呼び出しを安全に制御」 |
| **claim-security-** | APIエンドポイント保護・アドミッションサンドイッチ | 「AIシステムのセキュリティを定式化」 |
| **claim-evolve** | プロンプト・パイプラインの継続改善 | 「記事品質が自律進化する仕組み」 |

### 5-2. Auditorゲートの詳細

**大前提: 全ソースの全生成物に対してAuditorを通す。例外なし。**

| 生成物 | チェック対象 | 判定基準 |
|---|---|---|
| NoimosAI記事本文 | 事実主張・数値・固有名詞 | ソース確認可能か |
| GitHubトレンド記事 | スター数・技術説明・トレンド予測 | GitHub API値と照合 |
| RSS・ YouTube要約 | オリジナルソースとの整合性 | URL履歴と照合 |
| Mermaid図解 | 図が本文と整合するか | 構造的一貫性 |
| SEOメタ（タイトル/description） | 誤大表現・事実誤認 | 本文との整合性 |

### 5-3. 宣伝コンテンツ戰略

```
「この記事はclaim-auditorでファクトチェック済み」→ バッジ表示
「claim-crewのAI記者が取材・整理」→ 記事の著者欄に記載
「複数Claudeの議論で生成」→ councilループを記事内で言及
「セキュリティスキャン済み」→ claim-security-のバッジ
```

**Claimプロダクト紹介ページ**をAIツールカタログに載れる：
- 「claim-auditor — 記事の嫌正を検出するAIファクトチェッカー」
- 「claim-crew — 自律取材するAI記者エージェント」
- 「claim-security- — AIシステムを守るセキュリティエンジン」

---

## 6. NoimosAI連携

### NoimosAIの役割：編集長（戦略脳）

```
NoimosAI
├── キーワード戦略立案（SEOリサーチ）
├── 記事構成・本文生成（SEO最適化済み）
├── Google Docsへ写き出し
└── SNSエージェントで配信拡散
```

### A：サイトのマーケティング自動化

| エージェント | 役割 | 連携サービス |
|---|---|---|
| SEOエージェント | キーワード最適化・内部リンク改善 | Google Analytics・Search Console |
| ソーシャルメディアエージェント | SNS自動投稿・スケジュール管理 | X・Instagram・TikTok・YouTube・Threads・note |
| 競合分析エージェント | 競合AI情報サイトの動向監視 | 自動 |
| 成長戦略エージェント | KPI設定・改善提案 | GA4・Search Console |

### B：サイト内コンテンツとしてNoimosAIを紹介

- AIツールカタログにNoimosAIを掲載（詳細ページ・使い方ガイド）
- 「このサイト自体がNoimosAIで動いている」を差別化ポイントとして前面に出す
- 連携手順をガイド記事化（ノウハウ販売コンテンツの一部にもなる）

### C：ワークフロー07 — NoimosAI→Google Docs→n8n

```
NoimosAI（記事生成）
    ↓
Google Docs（SEOメタデータ付き記事）
    ↓ Google Drive Trigger（新規ファイル検知）
n8n WF07
    ↓
Claude API（WordPress用HTML整形 + カテゴリ/タグ割り当て）
    ↓
Claim-Auditorゲート
    ↓ PASS
WordPress（下書き）
```

**役割分担の明確化**：

| 層 | 担当 | 内容 |
|---|---|---|
| 編集長 | NoimosAI | キーワード戦略・SEO設計・記事本文 |
| 入稿担当 | Claude API | WordPress用整形・カテゴリ/タグ割り当て |
| 質保証 | Claim-Auditor | 全記事の事実検証 |
| 自動化 | n8n | 全体パイプライン制御 |

---

## 7. ビジュアル自動化戦略（80/20ルール）

全記事に豪華な画像は不要。役割分担によりブランドイメージとコスト効率を両立する。

| 割合 | 種別 | ツール | コスト |
|---|---|---|---|
| **80%** | 図解・フロー | Mermaid.js + Kroki.io | 無料 |
| **15%** | アイキャッチ静止画 | Flux.1 / fal.ai | ~¥1/枚 |
| **5%** | 動画（英語圈SNS向け） | Higgsfield AI | 高価値記事のみ |

### Mermaid + Kroki.io（図解）

```
n8n → Claude API（Mermaidコード生成）
  ↓
Kroki.io API（無料レンダリング）
  ↓
WordPress本文中にimgタグとして埋め込み
```

**備考**: Kroki.io公開サーバーは無料だが高負荷時レート制限あり。月100記事以上になったらDockerセルフホスト推奨。

### Flux.1 / fal.ai（アイキャッチ）

- DALL-E 3を1/10以下のコストで同等品質
- n8nからHTTP Requestノードでfal.ai APIを呼び出し
- 必要環境変数: `FAL_API_KEY`

### Higgsfield AI（動画・英語圈拡大）

```
高価値記事（少数選択）
    ↓
Higgsfield AI（30秒展示動画生成）
    ↓
YouTube Shorts / TikTok / Instagram Reels
    （英語標記）
    ↓
動画の概要欄 → WordPress記事へ誘導
```

---

## 8. 言語戦略（JAメイン + EN圈ターゲット）

| 層 | 言語 | 内容 | 実装タイミング |
|---|---|---|---|
| 記事本文 | 日本語 | 全記事 | Phase 1（現在） |
| SEOメタ | 英語 | title / description / slug / alt | Phase 1（全記事に並走） |
| 英語翻訳記事 | 英語 | 高価値記事のみ別投稿 | Phase 2（流入が出たら） |
| SNS配信 | 英語 | Higgsfield動画 + YouTube / TikTok | Phase 2 |

**当面の実装方針（Phase 1）**: 
- 記事本文は日本語
- 全記事にClaudeが英語SEOメタを並行生成（title・description・slug・alt）
- Auditorは日英両方に対して適用

---

## 9. GitHubトレンドコンテンツ（独自コンテンツとして作成）

### 判断理由

- **SEO**: オリジナルコンテンツのため検索流入が取れる
- **差別化**: 単なるリポジトリ紹介に留まらず「日本語解説＋使い方＋連携方法」まで踏み込む
- **API**: GitHub APIは公式・無料で使いやすい

### Auditorでチェックする項目

| 項目 | 判定 |
|---|---|
| スター数・フォーク数 | GitHub API直接取得 → PASS |
| 「『○○分野』で最も注目」等の主張 | LLM誤張の可能性 → 要チェック |
| 技術的説明（READMEから引用） | ソースURLと照合 → PASS |
| トレンド予測・将来性の言及 | 検証不能 → UNVERIFIABLEフラグ |

### 取得ロジック

```
GitHub API Search
└── q: topic:ai OR topic:llm OR topic:claude OR topic:openai
    created: >過去7日間
    sort: stars

→ Claude APIで日本語化
  ・「何ができるか」「誰に使えるか」「使い方」を生成
  ・難易度タグ付与（入門/中級/上級）
  ・英語SEOメタ並行生成

→ Claim-Auditorゲート

→ WordPress自動投稿
  カテゴリ: GitHubトレンド
  タグ: 言語・トピック・スター数帯
```

---

## 10. サンドボックス環境

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
| `FAL_API_KEY` | fal.ai API キー（Flux.1アイキャッチ用） |
| `GOOGLE_DRIVE_CREDENTIALS` | Google Drive API認証（WF07 NoimosAI用） |

### サンドボックスで検証できること

- [ ] `docker-compose up -d` → WordPress が http://localhost:8080 で応答
- [ ] n8n が http://localhost:5678 で応答
- [ ] ワークフロー01（GitHub AI Trending）手動実行 → Auditor PASS → WP下書き記事作成
- [ ] ワークフロー02（RSS Monitor）手動実行 → Auditor → WP下書き
- [ ] Claude APIがJSON構造の記事を返す
- [ ] Mermaid図解がWordPress本文に埋め込まれる
- [ ] WordPress REST API POST `/wp-json/wp/v2/posts` → 201レスポンスと記事ID
- [ ] NoimosAI WordPress連携テスト
- [ ] RSS / Sitemapの出力確認

---

## 11. 技術スタック

| 層 | 技術 | 備考 |
|---|---|---|
| CMS | WordPress | ホスティング先未確定 |
| テーマ | カスタムテーマ（Astra + Elementorまたはフルカスタム） | 要検討 |
| オーケストレーター | n8n | セルフホスト or n8n.cloud |
| コンテンツ生成AI | Claude API（Anthropic） | メイン（入稿・整形・Mermaid生成） |
| 戦略・SEO | NoimosAI | 編集長役（$99/月〜） |
| **記者エージェント** | **claim-crew** | **多角度取材・整理** |
| **コンテンツ品質** | **claim-builder + council** | **N案生成→コンセンサス選択** |
| **ファクトチェックゲート** | **claim-auditor** | **全生成物必須** |
| **LLM制御** | **claim-llm** | **ネットワークポリシー・抗象層** |
| **API保護** | **claim-security-** | **エンドポイントセキュリティ** |
| **継続改善** | **claim-evolve** | **プロンプト・パイプライン自律進化** |
| SEOプラグイン | Rank Math（無料） | Search Console連携 |
| 図解生成 | Mermaid.js + Kroki.io | 完全無料 |
| アイキャッチ画像 | Flux.1 / fal.ai | ~¥1/枚 |
| 動画生成 | Higgsfield AI | 高価値記事・EN市場向け |
| ローカル開発 | Docker Compose | サンドボックス |
| 開発ツール | Claude Code + WordPress MCP | WordPress 直操作（§16参照） |

### WordPress 認証方式

| 環境 | 認証方式 | 備考 |
|---|---|---|
| ローカル（サンドボックス） | Application Passwords | n8n HTTP Header Auth（Basic）で設定 |
| 本番（WordPress.com） | Application Passwords | OAuth Token より有効期限の問題が少ない |

---

## 12. WordPressプラグイン構成

| プラグイン | 用途 | コスト |
|---|---|---|
| Rank Math SEO | SEO最適化・Sitemap生成 | 無料 |
| WP REST API | n8nからの自動投稿 | WordPress標準 |
| Classic Editor | n8nからの投稿に対応 | 無料 |
| WP Super Cache | 表示高速化 | 無料 |
| Akismet | スパム対策 | 無料（個人） |
| Advanced Custom Fields | カスタムフィールド（ツール詳細用） | 無料 |

---

## 13. 実装フェーズ

### Phase 0：サンドボックス構築（進行中）
- [x] 要件定義書作成
- [x] docker-compose.yml 作成（WordPress + n8n + MySQL）
- [x] .env.example 作成（APIキープレースホルダー）
- [x] n8nワークフロー雛形作成（01〜06）
- [x] n8n/prompts/ ディレクトリ作成（7ファイル）
- [x] SETUP_GUIDE.md エラーハンドリング拡充
- [x] MCP サーバー設定（Claude Code ↔ WordPress）
- [ ] Claim-Auditorゲートをn8nに組み込み（WF01〜06）
- [ ] Mermaid + Kroki.io図解自動入れ込み実装
- [ ] WordPress 初回セットアップ（管理画面・Application Password 発行）
- [ ] エンドツーエンドサンドボックステスト

### Phase 1：コアパイプライン（ホスティング確定後）
- [ ] 本番WordPressセットアップ
- [ ] GitHub Trendingワークフロー稼働（Auditorゲート付き）
- [ ] 公式RSSワークフロー稼働
- [ ] NoimosAI初期連携（WF07）
- [ ] Flux.1アイキャッチ実装
- [ ] 英語SEOメタ並行生成

### Phase 2：SNS拡張・EN市場
- [ ] YouTube APIワークフロー追加
- [ ] Threads APIワークフロー追加
- [ ] note RSSワークフロー追加
- [ ] NoimosAI SNSエージェント全連携
- [ ] Higgsfield動画実装（英語圈SNS配信）
- [ ] claim-crew記者エージェント統合
- [ ] claim-evolveによるプロンプト自律改善

### Phase 3：マネタイズ・ノウハウ化
- [ ] このサイト構築プロセスの記事化
- [ ] 「Claim Platformで動くメディア」としてブランド化
- [ ] 有料SNSソース（X API等）追加
- [ ] UGCプロンプト投稿機能
- [ ] 英語全文翻訳記事（流入が出た高価値記事）

---

## 14. エラー対応方鷗

本番・サンドボックス共通のエラーハンドリング方鷗。詳細な対処手順は `n8n/SETUP_GUIDE.md` の「エラーハンドリング」セクションを参照。

| エラー | 原因 | 対応方鷗 |
|---|---|---|
| `401 Unauthorized` | トークン・App Password 無効 | 再発行・再設定 |
| `403 Forbidden` (GitHub) | API レート制限 | Conditional header / Wait ノード追加 |
| `429 Too Many Requests` | Claude API レート制限 | Retry on Fail 設定 + 60秒待機 |
| `529 Overloaded` (Claude) | Claude API 過負荷 | 指数バックオフ（Wait ノード） |
| `410 Gone` (WordPress) | REST API エンドポイント変更 | WP バージョン確認・エンドポイント更新 |
| Auditor FAIL | 事実誤認の投稿 | 人間レビューキューに转送（公開しない） |
| n8n タイムアウト | 処理時間超過 | ワークフローを分割・非同期化 |
| RSS 404 | RSS URL 変更 | 実際のサイトでURLを再確認 |

---

## 15. 未確定事項（要確認）

| 項目 | ステータス | 確認予定 |
|---|---|---|
| WordPressホスティング先 | **未確定** | オーナー確認後 |
| n8n運用方式（セルフホスト or クラウド） | 未確定 | ホスティング決定後 |
| サイト正式名称 | 仮「AIナビ」 | 要相談 |
| ドメイン | 未確定 | 要相談 |
| Higgsfield APIアクセス | 要確認 | コスト確認後 |
| claim-auditorのn8n組み込み方法 | HTTP API or CLI | 要設計 |

---

## 16. 開発ツール（MCP サーバー）

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
| `wp_delete_post` | 投稿をゴミ算へ移動（force=true で完全削除） |
| `wp_list_categories` | カテゴリ一覧取得 |
| `wp_list_tags` | タグ一覧取得（キーワード検索可） |
| `wp_create_category` | 新規カテゴリ作成 |
| `wp_create_tag` | 新規タグ作可 成 |

### セキュリティ考慮

- 認証情報は **環境変数** で管理（`WP_URL`, `WP_USERNAME`, `WP_APP_PASSWORD`）
- `.claude/settings.json` に資格情報をハードコードしない
- MCP サーバーはローカルプロセスとして stdio 通信（外部ポート不使用）
- 本番 WordPress への誤操作防止：`status: 'draft'` がデフォルト（明示しないと公開されない）

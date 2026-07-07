# AI情報専門サイト 要件定義書

**バージョン**: 1.0  
**最終更新**: 2026-07-07  
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
| 連携・自動化 | NoimosAI連携・Make・n8n統合手順 | 手動 |
| AIニュース | 最新アップデート・リリース情報 | 全自動 |
| GitHubトレンド | 今日の注目AIリポジトリ | 全自動（毎朝） |
| プロンプト集 | コピーして使えるプロンプトテンプレート | 自動 + UGC（将来） |
| インフルエンサー発信 | SNS上のAIノウハウ・話題まとめ | 全自動 |

### 2-2. デザイン方針

- **イラスト・アイコン主体**（文字より視覚で先に伝える）
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
├── GitHub API  ─────────────────┐
├── 公式RSS（各社ブログ）          │
├── YouTube Data API              ├──→【n8n オーケストレーター】
├── Threads API                   │         ↓
├── note RSS                      │  新ネタ検知・重複排除・スコアリング
└── Perplexity API ───────────────┘         ↓
                                   【Claude API / GPT API】
                                   日本語記事自動生成
                                   ・タイトル（SEO最適化）
                                   ・本文（構造化・図解指示付き）
                                   ・メタディスクリプション
                                   ・カテゴリ・タグ自動付与
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

- AIツールカタログにNoimosAIを掲載（詳細ページ・使い方ガイド）
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
- **AI_Trend_Dailyの参考**: 同様のコンテンツへの需要が高いことが確認済み

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

```
docker-compose up で起動
├── WordPress  : http://localhost:8080
├── n8n        : http://localhost:5678
├── MySQL      : localhost:3306
└── ngrok      : Webhookのローカルテスト用

→ 動作確認後、同じ設定を本番サーバーに適用
```

### サンドボックスで検証できること

- [ ] n8nワークフローの動作確認
- [ ] 各APIからのデータ取得テスト
- [ ] Claude APIによる記事生成品質確認
- [ ] WordPress REST API経由の自動投稿テスト
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

### Phase 0：サンドボックス構築（今ここ）
- [x] 要件定義書作成
- [ ] docker-compose.yml作成（WordPress + n8n）
- [ ] WordPress自動セットアップスクリプト
- [ ] n8nワークフロー雛形作成

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

## 11. 未確定事項（要確認）

| 項目 | ステータス | 確認予定 |
|---|---|---|
| WordPressホスティング先 | **未確定** | オーナー確認後 |
| n8n運用方式（セルフホスト or クラウド） | 未確定 | ホスティング決定後 |
| サイト正式名称 | 仮「AIナビ」 | 要相談 |
| ドメイン | 未確定 | 要相談 |
| Claude APIキー / OpenAI APIキー | 保有確認必要 | 要確認 |

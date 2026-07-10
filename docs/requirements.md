# AI情報専門サイト 要件定義書

**バージョン**: 2.2  
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

### 2-2. デザイン方針

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
| YouTube | YouTube Data API v3 + yt-dlp | 無料（1万units/日） | AI系チャンネルの新動画・字幕 |
| Threads | Threads API | 無料 | AIインフルエンサーの投稿 |
| note.com | RSS | 無料 | AI系クリエイターの記事 |
| Reddit | Reddit API（公式） | 無料 | r/MachineLearning・r/LocalLLaMA 等 |
| Hacker News | HN Algolia API | 無料 | AI技術記事・コメントの要点 |
| Perplexity API | Perplexity API | 無料枠あり | AIトレンドキーワード検索 |
| **NoimosAI** | **Google Docs経由** | **別途計上** | **戦略立案・SEO記事** |

### Phase 2：有料ソース追加（成長後）

| ソース | 取得方法 | コスト | 追加タイミング |
|---|---|---|---|
| X (Twitter) | X API v2 | $100/月〜 | 収益化後 |
| X スクレイピング | Apify | $49/月〜 | 収益化後 |
| Instagram | Instagram Graph API | 無料枠あり | Phase 2 |
| **中国語ソース（知乎/CSDN/B站/少数派）** | **RSS or スクレイピング** | **Kimi API年契約内** | **Phase 2（WF08）** |

---

## 4. 自動化パイプライン（全体アーキテクチャ）

```
【ネタ収集・コンテンツ生成層】
WF01: GitHub AI Trending ──────────┬
WF02: RSS Monitor ────────────────┬
WF03: YouTube + yt-dlp字幕 ──────┬
WF04: Threads インフルエンサー ───┬── 言語検出（claim-llm）
WF05: note 監視 ──────────────┬       ├─ ZH → Kimi API (moonshot-v1-128k)
WF06: 週次トレンドレポート ────┬       ├─ EN → Claude API
WF07: NoimosAI（Google Docs）──┤       └─ JA → Claude API
WF08: ZH ソース（知乎/CSDN）───┤             ↓
WF09: 9媒体横断調査（週次）───┘    著作権変換（00-copyright-transform）
                                    要約 + 独自分析 + 出所明示
                                         ↓
                 【claim-crew（記者エージェント）】
                 ├─ SKILL.md 型取材スキル（§18参照）
                 ├─ 9媒体横断取材・情報整理・補完
                 ├─ エージェント記憶層参照（§19参照）
                 └─ 確度スコア付与（HIGH/MED/LOW/UNVERIFIABLE）
                                         ↓
                        【claim-builder + councilループ】
                        N案生成→コンセンサス選択
                                         ↓
                        【claim-llm】LLM抽象層
                                         ↓
┌────────────────────────────────────────────────┐
│        Claim-Auditor ゲート（全生成物必須）        │
│  ✅ PASS        → 次工程へ                   │
│  ❌ FAIL        → 人間レビューキュー + 記憶層蓄積│ ← INV-R1
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
          【claim-evolve】SKILL.md 自律改善ループ
```

### n8nワークフロー一覧

| # | ワークフロー名 | トリガー | 処理内容 |
|---|---|---|---|
| 01 | github-trending-daily | 毎朝8:00 | GitHubトレンドAIリポジトリ取得→記事生成→Auditor→投稿 |
| 02 | rss-monitor | 30分ごと | 各社ブログRSS監視→新記事検知→日本語記事生成→Auditor→投稿 |
| 03 | youtube-new-video | 1時間ごと | 新動画検知→**yt-dlp字幕取得**→要約→記事生成→Auditor→投稿 |
| 04 | threads-influencer | 3時間ごと | 対象アカウント投稿収集→まとめ記事生成→Auditor→投稿 |
| 05 | note-monitor | 1時間ごと | note RSS監視→AI関連記事抽出→転載記事生成→Auditor→投稿 |
| 06 | weekly-trend-report | 毎週月曜 | Perplexityでトレンド検索→週次まとめ記事生成→Auditor→投稿 |
| 07 | noimosai-google-docs | Google Drive新規ファイル | NoimosAI記事取得→Claude整形→Auditor→投稿 |
| 08 | zh-sources | スケジュール or RSS | 知乎/CSDN/B站取得→Kimi ZH→JA変換→著作権変換→Auditor→投稿 |
| **09** | **multi-source-research** | **週次 or オンデマンド** | **9媒体横断（GitHub/RSS/YT/Threads/note/Reddit/HN/ZH/NoimosAI）→確度スコア付き引用要約→Auditor→深掘り記事生成** |

### プロンプト・スキル管理

Claude API / Kimi API へ送るプロンプトは `n8n/prompts/` で、エージェントの行動規律は `n8n/skills/` で Git 管理する。ワークフロー JSON へのハードコードは禁止。

#### n8n/prompts/ — プロンプトテンプレート

| ファイル | 用途 |
|---|---|
| `n8n/prompts/00-copyright-transform.md` | 著作権コンプライアンス変換（全WF共通・最優先） |
| `n8n/prompts/article-base.md` | 全ワークフロー共通の記事フォーマット指示 |
| `n8n/prompts/01-github-trending.md` | GitHubトレンド記事生成 |
| `n8n/prompts/02-rss-summary.md` | RSSフィード要約 |
| `n8n/prompts/03-youtube-summary.md` | YouTube動画要約（字幕ベース） |
| `n8n/prompts/04-threads-summary.md` | Threadsまとめ |
| `n8n/prompts/05-note-summary.md` | note記事要約 |
| `n8n/prompts/06-weekly-report.md` | 週次トレンドレポート |
| `n8n/prompts/07-noimosai-format.md` | NoimosAI記事整形 |
| `n8n/prompts/08-kimi-zh.md` | Kimi API ZH→JA変換（WF08専用） |

#### n8n/skills/ — エージェントスキル（§18参照）

| ファイル | エージェント | 機能 |
|---|---|---|
| `n8n/skills/skill-base.md` | 全エージェント | 共通ヘッダー・フェーズ定義 |
| `n8n/skills/01-trending-researcher.md` | claim-crew | GitHub/HN/Reddit横断取材 |
| `n8n/skills/02-rss-reporter.md` | claim-crew | RSS多媒体取材 |
| `n8n/skills/03-video-reporter.md` | claim-crew | YouTube字幕取材（yt-dlp） |
| `n8n/skills/04-social-reporter.md` | claim-crew | SNS横断取材 |
| `n8n/skills/10-article-writer.md` | claim-builder | 記事生成・構造化 |
| `n8n/skills/11-seo-meta-writer.md` | claim-builder | 英語SEOメタ生成 |
| `n8n/skills/20-auditor-gate.md` | claim-auditor | ファクトチェック+著作権検証 |
| `n8n/skills/30-wp-publisher.md` | n8n | WordPress投稿 |
| `n8n/skills/90-evolve-loop.md` | claim-evolve | SKILL.md自律改善ループ |

---

## 5. Claim Platform連携戦略

**核心思想**: パイプライン自体がClaim Platformのユースケースデモであり、「AIナビを動かすために使ったツールの紹介」自体が最強の宣伝媒体となる。

### 5-1. 各プロダクトの役割

| プロダクト | パイプライン内の役割 | 宣伝切り口 |
|---|---|---|
| **claim-auditor** | 全生成物のファクトチェック + 著作権コンプライアンスゲート | 「このメディアは全記事をAuditor検証済」 |
| **claim-crew** | SKILL.md型記者エージェント（9媒体横断取材・整理） | 「AIエージェントが仮想記者として取材」 |
| **claim-builder + council** | 記事品質向上（N案生成→コンセンサス選択） | 「複数Claudeの協議で記事を生成」 |
| **claim-llm** | LLM抽象層（言語検出・ルーティング・NetworkPolicy） | 「LLM呼び出しを安全に制御」 |
| **claim-security-** | APIエンドポイント保護・アドミッションサンドイッチ | 「AIシステムのセキュリティを定式化」 |
| **claim-evolve** | SKILL.md自律改善ループ | 「記事品質が自律進化する仕組み」 |

### 5-2. Auditorゲートの詳細

**大前提: 全ソースの全生成物に対してAuditorを通す。例外なし。GitHubコンテンツも含む。**

| 生成物 | チェック対象 | 判定基準 |
|---|---|---|
| NoimosAI記事本文 | 事実主張・数値・固有名詞 | ソース確認可能か |
| GitHubトレンド記事 | スター数・技術説明・トレンド予測 | GitHub API値と照合 |
| RSS・YouTube要約 | オリジナルソースとの整合性 | URL履歴と照合 |
| ZH翻訳記事（Kimi経由） | 著作権5要件 + 翻訳ラベル | 著作権コンプライアンスチェッカー |
| EN翻訳記事 | 著作権5要件 + 翻訳ラベル | 著作権コンプライアンスチェッカー |
| 9媒体横断調査記事 | 確度スコア LOW 以下の主張 | 確度スコア閾値チェック |
| Mermaid図解 | 図が本文と整合するか | 構造的一貫性 |
| SEOメタ（タイトル/description） | 誇大表現・事実誤認 | 本文との整合性 |

### 5-3. 宣伝コンテンツ戦略

```
「この記事はclaim-auditorでファクトチェック済み」→ バッジ表示
「claim-crewのAI記者が9媒体を横断取材」→ 記事の著者欄に記載
「複数Claudeの議論で生成」→ councilループを記事内で言及
「セキュリティスキャン済み」→ claim-security-のバッジ
```

---

## 6. NoimosAI連携 + Kimi ZH連携

### 6-1. NoimosAIの役割：JA/EN編集長（戦略脳）

```
NoimosAI
├── キーワード戦略立案（SEOリサーチ）
├── 記事構成・本文生成（SEO最適化済み）
├── Google Docsへ書き出し
└── SNSエージェントで配信拡散
```

### 6-2. Kimiの役割：ZH編集長（中国語情報源処理）

```
Kimi（Moonshot AI / moonshot-v1-128k）
├── 中国語ソース取得（知乎/CSDN/B站/少数派等）
├── ZH→JA 翻訳+要約+著作権変換（全文翻訳禁止）
├── 長文技術記事の一括処理（200K tokenコンテキスト）
└── OpenAI互換API → n8n HTTP Requestノードで直接呼び出し
```

**n8n WF08 接続設定（HTTP Requestノード）**:
```
URL:    https://api.moonshot.cn/v1/chat/completions
Method: POST
Auth:   Bearer {{ $env.KIMI_API_KEY }}
Body:   { "model": "moonshot-v1-128k", "messages": [...] }
```

### 6-3. LLM役割分担表

| 層 | 担当 | 内容 |
|---|---|---|
| ZH編集長 | Kimi | ZHソース翻訳・要約・加工 |
| JA/EN編集長 | NoimosAI | キーワード戦略・SEO設計・記事本文 |
| 入稿担当 | Claude API | WordPress用整形・カテゴリ/タグ割り当て |
| LLMルーティング | claim-llm | 言語検出→Kimi/Claude振り分け |
| 質保証 | Claim-Auditor | 全記事の事実検証 + 著作権コンプライアンス |
| 自動化 | n8n | 全体パイプライン制御 |

### 6-4. ワークフロー07 — NoimosAI→Google Docs→n8n

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

### 6-5. ワークフロー08 — ZHソース→Kimi→n8n

```
ZHソース（RSS or スクレイピング）
    ↓
Kimi API（ZH→JA翻訳+要約 / 08-kimi-zh.md）
    ↓
著作権変換（00-copyright-transform.md適用）
    ↓
Claude API（日本語品質仕上げ + 構造統一）← オプション
    ↓
Claim-Auditor（copyright_compliance: cross_lingual=ZH）
    ↓ PASS
WordPress（下書き）
```

---

## 7. ビジュアル自動化戦略（80/15/5ルール）

全記事に豪華な画像は不要。役割分担によりブランドイメージとコスト効率を両立する。

| 割合 | 種別 | ツール | コスト |
|---|---|---|---|
| **80%** | 図解・フロー | Mermaid.js + Kroki.io | 無料 |
| **15%** | アイキャッチ静止画 | Flux.1 / fal.ai | ~¥1/枚 |
| **5%** | 動画（英語圈SNS向け） | Higgsfield AI | 高価値記事のみ |

### Mermaid + Kroki.io（図解）

```
n8n → Claude API（Mermaidコード生成）→ Kroki.io API（無料レンダリング）→ WordPress img埋め込み
```

備考: 月100記事以上はKroki.ioをDockerセルフホスト推奨。

### Flux.1 / fal.ai（アイキャッチ）
- DALL-E 3比1/10以下のコストで同等品質 / 必要環境変数: `FAL_API_KEY`

### Higgsfield AI（動画・英語圈拡大）
- 高価値記事の5%のみ / YouTube Shorts / TikTok / Instagram Reels（英語）→ WP記事へ誘導

---

## 8. 言語戦略（JAメイン + EN圈ターゲット）

| 層 | 言語 | 内容 | 実装タイミング |
|---|---|---|---|
| 記事本文 | 日本語 | 全記事 | Phase 1（現在） |
| SEOメタ | 英語 | title / description / slug / alt | Phase 1（全記事に並走） |
| 英語翻訳記事 | 英語 | 高価値記事のみ別投稿 | Phase 2 |
| SNS配信 | 英語 | Higgsfield動画 + YouTube / TikTok | Phase 2 |
| ZH→JA 翻訳記事 | 日本語（翻訳ラベル付き） | Kimi経由 | Phase 2（WF08） |

---

## 9. GitHubトレンドコンテンツ

### 取得ロジック

```
GitHub API Search（topic:ai OR topic:llm / 過去7日 / sort:stars）
    ↓
claim-crew: 難易度タグ付与（入門/中級/上級）+ 英語SEOメタ並行生成
    ↓
Claim-Auditorゲート（スター数はAPI直接取得=PASS / 予測発言=UNVERIFIABLE）
    ↓
WordPress自動投稿（カテゴリ: GitHubトレンド）
```

---

## 10. サンドボックス環境

### 起動方法

```bash
cp .env.example .env
docker-compose up -d
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
| `MYSQL_ROOT_PASSWORD` / `MYSQL_PASSWORD` | MySQL パスワード |
| `N8N_USER` / `N8N_PASSWORD` | n8n 管理画面ログイン |
| `ANTHROPIC_API_KEY` | Claude API キー |
| `KIMI_API_KEY` | Moonshot AI APIキー（WF08 ZHソース処理用） |
| `GITHUB_TOKEN` | GitHub Personal Access Token |
| `YOUTUBE_API_KEY` | YouTube Data API v3 キー |
| `PERPLEXITY_API_KEY` | Perplexity API キー |
| `WP_APP_PASSWORD` | WordPress Application Password |
| `FAL_API_KEY` | fal.ai API キー（Flux.1アイキャッチ用） |
| `GOOGLE_DRIVE_CREDENTIALS` | Google Drive API認証（WF07用） |

### サンドボックス検証チェックリスト

- [ ] `docker-compose up -d` → WP/n8n 応答確認
- [ ] WF01 手動実行 → Auditor PASS → WP下書き作成
- [ ] WF03 手動実行 → yt-dlp字幕取得 → 記事生成 → Auditor → WP下書き
- [ ] WF08 手動実行 → Kimi API → 著作権変換 → Auditor → WP下書き
- [ ] WF09 手動実行 → 9媒体横断 → 確度スコア付与 → Auditor → WP下書き
- [ ] エージェント記憶層 SQLite 初期化 → 読み書き確認
- [ ] WordPress REST API POST `/wp-json/wp/v2/posts` → 201 + 記事ID

---

## 11. 技術スタック

| 層 | 技術 | 備考 |
|---|---|---|
| CMS | WordPress | ホスティング先未確定 |
| オーケストレーター | n8n | セルフホスト or n8n.cloud |
| コンテンツ生成AI | Claude API（Anthropic） | メイン（入稿・整形・Mermaid生成） |
| ZH言語処理 | Kimi（Moonshot AI / moonshot-v1-128k） | ZHソース翻訳・加工（年契約済） |
| 戦略・SEO | NoimosAI | 編集長役 |
| 記者エージェント | claim-crew | SKILL.md型・9媒体横断取材 |
| コンテンツ品質 | claim-builder + council | N案生成→コンセンサス選択 |
| ファクトチェックゲート | claim-auditor | 全生成物必須（著作権コンプライアンス含む） |
| LLM制御 | claim-llm | 言語検出・ルーティング・抽象層 |
| API保護 | claim-security- | エンドポイントセキュリティ |
| 継続改善 | claim-evolve | SKILL.md自律改善ループ |
| **エージェント記憶層** | **SQLite + sqlite-vec** | **claim-crew 4層記憶（§19参照）** |
| **字幕取得** | **yt-dlp** | **YouTube字幕抽出（WF03）** |
| SEOプラグイン | Rank Math（無料） | Search Console連携 |
| 図解生成 | Mermaid.js + Kroki.io | 完全無料 |
| アイキャッチ画像 | Flux.1 / fal.ai | ~¥1/枚 |
| 動画生成 | Higgsfield AI | 高価値記事・EN市場向け |
| ローカル開発 | Docker Compose | サンドボックス |
| 開発ツール | Claude Code + WordPress MCP | WordPress 直操作（§16参照） |

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
- [x] .env.example 作成
- [x] n8nワークフロー雛形作成（01〜06）
- [x] n8n/prompts/ ディレクトリ作成（9ファイル）
- [x] SETUP_GUIDE.md エラーハンドリング拡充
- [x] MCP サーバー設定（Claude Code ↔ WordPress）
- [x] 著作権コンプライアンスプロンプト（00-copyright-transform.md）
- [ ] Claim-Auditorゲートをn8nに組み込み（WF01〜09）
- [ ] Mermaid + Kroki.io 図解自動挿入実装
- [ ] yt-dlp 字幕取得ノード実装（WF03）
- [ ] エージェント記憶層 SQLite 初期化スクリプト
- [ ] n8n/skills/ ディレクトリ作成（SKILL.md 10ファイル）
- [ ] WordPress 初回セットアップ（Application Password 発行）
- [ ] エンドツーエンドサンドボックステスト

### Phase 1：コアパイプライン（ホスティング確定後）
- [ ] 本番WordPressセットアップ
- [ ] WF01-02 稼働（Auditorゲート付き）
- [ ] NoimosAI初期連携（WF07）
- [ ] WF08稼働（知乎/CSDN/B站 → Kimi → JA記事）
- [ ] Flux.1アイキャッチ実装
- [ ] 英語SEOメタ並行生成
- [ ] SKILL.md形式への移行（n8n/skills/ 運用開始）

### Phase 2：SNS拡張・EN市場・記憶層
- [ ] WF03-05 稼働（YouTube/Threads/note）
- [ ] WF09 稼働（9媒体横断調査・確度スコア付き）
- [ ] エージェント記憶層本番稼働（claim-crew 4層記憶）
- [ ] NoimosAI SNSエージェント全連携
- [ ] Higgsfield動画実装（英語圈SNS）
- [ ] claim-crew 記者エージェント本格統合
- [ ] claim-evolve SKILL.md自律改善ループ稼働

### Phase 3：マネタイズ・ノウハウ化
- [ ] このサイト構築プロセスの記事化
- [ ] 「Claim Platformで動くメディア」としてブランド化
- [ ] 有料SNSソース（X API等）追加
- [ ] UGCプロンプト投稿機能
- [ ] 英語全文翻訳記事（高価値記事）

---

## 14. エラー対応方針

| エラー | 原因 | 対応方針 |
|---|---|---|
| `401 Unauthorized` | トークン・App Password 無効 | 再発行・再設定 |
| `403 Forbidden` (GitHub) | API レート制限 | Conditional header / Wait ノード追加 |
| `429 Too Many Requests` | Claude / Kimi API レート制限 | Retry on Fail 設定 + 60秒待機 |
| `529 Overloaded` (Claude) | Claude API 過負荷 | 指数バックオフ（Wait ノード） |
| `410 Gone` (WordPress) | REST API エンドポイント変更 | WP バージョン確認・エンドポイント更新 |
| Auditor FAIL | 事実誤認 or 著作権違反 | 人間レビューキューに転送 + 記憶層蓄積 |
| n8n タイムアウト | 処理時間超過 | ワークフローを分割・非同期化 |
| RSS 404 | RSS URL 変更 | 実際のサイトでURLを再確認 |
| Kimi API エラー | ZHソース取得失敗 | WF08 Retry on Fail + フォールバック処理 |
| yt-dlp エラー | 字幕なし or 地域制限 | テキスト説明文（description）にフォールバック |
| 記憶層クエリ失敗 | SQLite アクセスエラー | ログ記録してスキップ（記憶なしで継続） |

---

## 15. 未確定事項（要確認）

| 項目 | ステータス | 確認予定 |
|---|---|---|
| WordPressホスティング先 | **未確定** | オーナー確認後 |
| n8n運用方式（セルフホスト or クラウド） | 未確定 | ホスティング決定後 |
| サイト正式名称 | 仮「AIナビ」 | 要相談 |
| ドメイン | 未確定 | 要相談 |
| Higgsfield APIアクセス・コスト | 要確認 | Phase 2開始前 |
| claim-auditorのn8n組み込み方法 | HTTP API or CLI | 要設計 |
| ZHソースのスクレイピング方法 | RSS or Apify | WF08実装時に決定 |
| 日本語Embeddingモデル選定 | multilingual-e5-small 候補 | 記憶層実装時に決定 |
| Reddit API レート制限 | 無料枠確認必要 | WF09実装時 |

---

## 16. 開発ツール（MCP サーバー）

### 概要

Claude Code から WordPress REST API を直接操作するための MCP サーバー。

```
【Claude Code (開発時)】→ MCP protocol (stdio) →【wordpress-mcp.js】→ HTTP + Basic Auth →【WordPress REST API】
```

### 構成ファイル

| ファイル | 役割 |
|---|---|
| `.claude/settings.json` | Claude Code の MCP サーバー登録設定 |
| `mcp/wordpress-mcp.js` | WordPress CRUD MCP サーバー本体（Node.js ESM） |
| `mcp/package.json` | 依存パッケージ（`@modelcontextprotocol/sdk`） |

### セキュリティ考慮

- 認証情報は環境変数で管理（`WP_URL`, `WP_USERNAME`, `WP_APP_PASSWORD`）
- MCP サーバーはローカルプロセスとして stdio 通信（外部ポート不使用）
- 本番 WordPress への誤操作防止：`status: 'draft'` がデフォルト

---

## 17. 著作権コンプライアンス（Auditorプラグイン）

### 17-1. 引用5要件（著作権法32条）と Auditor マッピング

| 引用5要件 | Auditorチェック | 実装方法 | LLM-free |
|---|---|---|---|
| ①主従関係 | 生成字数 / 引用字数 > 2.0 | 字数カウント | ✅ |
| ②明瞭区別 | `<blockquote>` または `>` が存在 | 正規表現 | ✅ |
| ③必要性 | `##` 見出しブロック ≥ 3 | 構造チェック | ✅ |
| ④出所明示 | 記事内に原文URLが存在 | URL検出 | ✅ |
| ⑤改変禁止 | 同言語: blockquote内テキスト類似度 > 0.85 | difflib | ✅ |

### 17-2. 4シナリオ別ルール

| シナリオ | 位置づけ | ⑤ | 追加要件 |
|---|---|---|---|
| JA→JA | 引用（32条） | difflib | — |
| EN→JA | 翻案（27条） | 免除 | 翻訳ラベル必須 |
| ZH→JA | 翻案 + ベルヌ条約 | 免除 | 翻訳ラベル必須 |
| JA→EN | 自著翻訳 | 不適用 | Phase 2のみ |

### 17-3. 翻訳シナリオ追加チェック（cross-lingual）

```python
def check_cross_lingual(source_url, generated_text):
    required = (
        ("本記事は" in generated_text and "翻訳" in generated_text)
        and source_url in generated_text
    )
    optional = (generated_text.count("##") >= 3)
    return "PASS" if (required and optional) else "FAIL"
```

### 17-4. SNS投稿での注意

- スクリーンショット投稿は原則NG
- 最も安全: リンクのみ + 自分の意見（WF04 Threadsも同ルール適用）

---

## 18. エージェントスキル体系（agent-skills 応用）

> **参考**: `addyosmani/agent-skills`（MIT License）のアイデアを採用・発展。コードは使用しない。

### 18-1. コンセプト

AIエージェントの行動規律を **SKILL.md 単位で型化・独立管理** する。
現在の `n8n/prompts/*.md`（プロンプトテンプレート）を超えて、各エージェントの**フェーズ・入出力・品質条件**まで含めた実行仕様として定義する。

```
n8n/prompts/*.md   → 「何を生成するか」のテンプレート（現状）
n8n/skills/*.md    → 「どのフェーズで何をすべきか」の行動仕様（追加）
```

### 18-2. SKILL.md 構造

各スキルファイルは以下の構造を持つ:

```markdown
---
skill: article-generation
version: 1.0
agent: claim-crew
phase: BUILD
inputs: [source_url, source_text, language, confidence_score]
outputs: [article_markdown, seo_meta_en, confidence_score_updated]
auditor_required: true
memory_read: [facts, scenes]
memory_write: [scenes]
---

### DEFINE（取材対象の定義）
...

### PLAN（取材角度・情報源の設計）
...

### BUILD（記事生成・変換）
...

### REVIEW（claim-auditor ゲート）
PASS条件: 著作権5要件 + 確度スコア >= MED + 出典明記
FAIL時: 人間レビューキュー + 記憶層のfacts層にFAIL事例を格納

### SHIP（WordPress投稿）
...
```

### 18-3. Rationalizations Table → Auditor 統合

agent-skills の「言い訳ブロックリスト」を claim-auditor のプレフライトチェックに統合する:

| 言い訳パターン（NGフレーズ） | Auditor 判定 |
|---|---|
| 「動くはずです」「動くと思います」 | FAIL — テスト出力なし |
| 「たぶん大丈夫」「おそらく」 | FAIL — 根拠なし主張 |
| 「あとで確認します」 | FAIL — 未検証のまま投稿 |
| 「URLだけ貼っておきます」 | FAIL — 出典不備（§17参照） |
| 「引用なので問題ない」（要件未確認） | UNVERIFIABLE — 5要件チェック必要 |

### 18-4. claim-evolve による SKILL.md 自律改善ループ

```
記事投稿 → WordPress アクセス解析
    ↓
claim-evolve: 低パフォーマンス記事の担当 SKILL.md を特定
    ↓
DEFINE / PLAN フェーズの改善案を生成（councilループ）
    ↓
claim-auditor が改善案を検証（ハルシネーション・品質後退チェック）
    ↓
SKILL.md を PR 経由で更新（人間レビュー後マージ）
    ↓
次回から改善版 SKILL.md が稼働
```

---

## 19. エージェント記憶層（TencentDB-Agent-Memory 応用）

> **参考**: `TencentCloud/TencentDB-Agent-Memory`（MIT License）のアイデアを採用・発展。コードは使用しない。

### 19-1. コンセプト

claim-crew の記者エージェントが **4層の記憶** を持ち、過去の取材コンテキストを活かして質の高い記事を継続生成する。同じ情報を何度も調査する無駄を排除し、ブランドトーンの一貫性を保つ。

### 19-2. claim-crew の4層記憶設計

| 層 | 内容 | 例 | 保持期間 |
|---|---|---|---|
| **会話層** | 現在の記事ブリーフ・取材指示 | 「今日はClaude 4の新機能について書く」 | セッション中のみ |
| **事実層** | 検証済みソース + Auditor FAIL事例の蓄積 | 「GPT-5パラメータ数は非公開（UNVERIFIABLE実績）」 | 永続 |
| **シーン層** | 過去記事のコンテキスト（重複防止） | 「先週 agent-skills 記事を投稿済み（URL）」 | 90日間 |
| **ペルソナ層** | サイトトーン・禁止表現・ブランドガイドライン | 「誇大表現禁止・断言より確認を促す表現」 | 永続（人間管理） |

### 19-3. Auditor FAIL 事例の学習ループ

```
Auditor FAIL 発生
    ↓
FAIL理由 + 元テキスト + ソースURLを事実層に格納
    ↓
次回同テーマの取材時に WideSearch で参照
    ↓
「前回この主張は検証不能だった」と claim-crew に通知
    ↓
取材角度を変えて別ソースで裏取りを試みる
```

### 19-4. 重複コンテンツ防止（シーン層活用）

```
新記事生成前
    ↓
シーン層を類似度検索
    ↓
類似度 > 0.85 の過去記事が存在する場合
    → 「差分情報」「新角度」「アップデート記事」としてリフレーム指示
    → 全文重複なら生成スキップ + ログ記録
```

### 19-5. 技術実装方針

| 項目 | 選択 | 理由 |
|---|---|---|
| ストレージ | SQLite + sqlite-vec | ローカル完結・外部依存ゼロ |
| テキスト検索 | BM25（FTS5） | 日本語トークナイザー対応可 |
| ベクトル検索 | sqlite-vec + Embedding | 意味的類似検索 |
| 統合検索 | RRF（Reciprocal Rank Fusion） | BM25とベクトルの長所を統合 |
| 日本語Embedding | multilingual-e5-small（ローカル）候補 | プライバシー保護・無料 |
| token削減 | 記憶層から必要箇所のみ抽出してClaudeへ渡す | Claude API コスト削減（目標: -60%） |

### 19-6. 確度スコア（last30days-skill 応用）

9媒体横断取材の結果に **確度スコア** を付与し、Auditorの判定精度を向上させる。

| 確度 | 条件 | Auditor処理 |
|---|---|---|
| **HIGH** | 複数独立ソースで同一情報を確認 | PASS候補（ファクトチェック簡略化） |
| **MED** | 1ソースのみ確認・信頼性高い媒体 | 通常のAuditorチェック |
| **LOW** | 1ソースのみ・信頼性不明 | 要追加取材 or UNVERIFIABLEフラグ |
| **UNVERIFIABLE** | ソース確認不能・予測・見解 | UNVERIFIABLEフラグ必須 |

確度スコアは事実層に蓄積され、同じ情報が再登場した際に参照される。

### 19-7. n8n との統合フロー

```
WF01-09 実行前
    ↓
記憶層クエリ（シーン層 + 事実層 / WideSearch）
    ↓
コンテキスト注入（SKILL.md の PLAN フェーズへ追加）
    ↓
claim-crew 記事生成（確度スコア付与）
    ↓
Claim-Auditor ゲート
    ↓ PASS
WordPress 投稿
    ↓
記憶層更新（会話 → シーン層昇格 / 新事実 → 事実層追加）
```

---

## 20. オープンソース活用ポリシー

本プロジェクトで参考にしたOSSの権利関係:

| リポジトリ | ライセンス | 活用方法 |
|---|---|---|
| addyosmani/agent-skills | MIT | アイデア採用（SKILL.md構造・フェーズ設計） |
| TencentCloud/TencentDB-Agent-Memory | MIT | アイデア採用（4層記憶・RRF統合設計） |
| mvanhorn/last30days-skill | MIT | アイデア採用（9媒体横断・確度スコア設計） |

**ポリシー**: コードは使用せずアイデアのみ採用（著作権の対象外）。コードを使用する場合はLICENSEファイルを `third_party/` に格納してクレジット表示する。

---

## 21. 配線ゲート（design-vs-wired）— 「設計したが動いていない」の必須防止

> 背景: 本プロジェクトでは「設計・文書・プロンプトは存在するが、どの本番パスからも
> 呼ばれていない」状態が繰り返し発生した（例: 00-copyright-transform.md 未配線、
> WF06 の Auditor ゲートなし自動公開、WF07/08 のワークフロー未作成）。
> 以後、これは人手の監査ではなく決定論的ゲートで機械的に防ぐ（**必須**）。

### 21-1. ゲート仕様（scripts/check_wired.py）

| # | チェック | FAIL条件 |
|---|---|---|
| W1 | requirements の WF一覧（WF01〜09）に対応する `n8n/workflows/*.json` が存在 | 対応JSONなし |
| W2 | 全ワークフローに Auditor Gate ノードが存在（`CLAIM_AUDITOR_URL` 参照で判定） | ゲートなしWF |
| W3 | 全ワークフローのプロンプト読込みが `00-copyright-transform.md` を含む | 著作権プロンプト未読込 |
| W4 | WordPress 投稿の `status` はゲート出力（`wp_status`）経由 | `'publish'` ハードコード |
| W5 | `n8n/prompts/*.md` は少なくとも1つのWFから参照される | 未参照（LIBRARY_ONLY 登録を除く） |
| W6 | ワークフローJSONに認証情報らしきリテラルが含まれない | 秘密情報パターン検出 |

- **LIBRARY_ONLY レジストリ**: 意図的に未配線のファイルはスクリプト内のレジストリに
  理由コメント付きで明示登録する。登録なしの未配線は FAIL。
- 終了コード: 全PASS=0 / FAILあり=1。出力は項目毎に PASS/FAIL を列挙。

### 21-2. 運用（必須化）

1. **ローカル**: push 前ゲート（CLAUDE.md §D）に組み込み。FAIL のまま push 禁止。
2. **CI**: `.github/workflows/wired-check.yml` が全 PR で実行（pure-stdlib・
   外部ネットワーク不要のためネットワークポリシー下でも完走する）。
3. **完了定義への組み込み**: 新機能は check_wired.py が検出できる形で本番パスに
   配線されるまで「完了」と報告しない（CLAUDE.md §A 絶対ルール）。

---

## 22. コンテンツ監査の評価セットと段階的ロールアウト

> 背景: Auditor Gate（§21 W2）は導入時点で PASS→即公開だったが、判定精度を測る
> 手段が無いまま自動公開するのは危険（ハーネス原則: 段階的ロールアウト）。
> Claim-Security- の FR-SEC-26（FP=0 まで ACTIVE 化禁止）と同じ規律を適用する。

### 22-1. 決定論的コンテンツ監査（scripts/content_audit.py）

LLM-free（INV-R2）。stdlib のみ。判定順: FAIL > UNVERIFIABLE > PASS。

| ルール | 判定 |
|---|---|
| 誇大表現（禁止語リスト） | FAIL:HYPE |
| blockquote 比率 > 40%（主従逆転） | FAIL:QUOTE_DOMINANCE |
| blockquote あり・出所リンクなし | FAIL:NO_ATTRIBUTION |
| 60字超の「」引用が blockquote 外（明瞭区別違反） | FAIL:UNMARKED_QUOTE |
| 見出し（h2）が3未満 | FAIL:STRUCTURE |
| 数値主張あり・ソースURLゼロ | UNVERIFIABLE:UNSOURCED_STATS |
| 上記すべて非該当 | PASS |

### 22-2. 評価セット（data/eval_set.json）

- 正常系 / 境界 / 敵対的 の3区分・計50件以上。各件 expected verdict をラベル付け。
- `scripts/run_eval.py` が混同行列を出力。**FP（PASS すべきものを block）= 0 かつ
  FN（block すべきものを PASS）= 0 でなければ exit 1**。
- 評価セットは push 前ゲート（§D）に含める — 監査ルール変更の回帰を常時検知。

### 22-3. 段階的ロールアウト（CLAIM_AUDITOR_MODE）

| モード | 動作 | 昇格条件 |
|---|---|---|
| `report_only`（既定） | 全件 draft + verdict をメタデータ記録 | — |
| `canary` | PASS の約10%のみ自動 publish | 評価セット FP=0/FN=0 + 本番 verdict 30日分レビュー |
| `full` | PASS を自動 publish | canary 30日で誤公開ゼロ + 人間署名（INV-R1） |

- モードは n8n 環境変数 `CLAIM_AUDITOR_MODE` で制御。コード変更なしで昇格・降格。
- FAIL / UNVERIFIABLE は全モードで draft（公開されない）。
- §21 W7: 全ワークフローの Auditor Gate はモード対応であること（check_wired が強制）。

---

## 23. ラチェット自動化（Phase R0: Report-Only 提案器）

> ハーネス原則「ラチェット」の仕組み化。CLAUDE.md §C への追記を人間の記憶に
> 頼らず、記憶層（§19）の Auditor FAIL 蓄積から**機械的に提案**する。
> 段階的ロールアウト（§22-3 と同じ規律）で、Phase R0 は提案のみ・変更しない。

### 23-1. 仕様（scripts/ratchet_check.py）

1. 入力: 記憶層 DB（`data/memory.db`、§19 の facts 層）。
2. 直近30日の `verdict='FAIL'` を `(skill_ref, fail_reason)` で集計。
3. 同一組合せが **閾値（既定3回）以上** → ラチェット提案を生成:
   - CLAUDE.md §C への追記案（1行、日本語）
   - 対応するプロンプトファイル（`n8n/prompts/` の skill_ref 対応ファイル）の見直し提案
4. 出力: Markdown（提案なしなら "no proposals"）。exit 0（Report-Only・変更しない）。
   `--strict` 指定時のみ提案ありで exit 3（将来 CI で昇格する時に使用）。

### 23-2. ロールアウト計画

| Phase | 動作 | 昇格条件 |
|---|---|---|
| **R0（現在）** | 提案を出力するのみ | — |
| R1 | 提案を Draft PR として自動起票（人間レビュー・署名で merge） | R0 の提案品質を人間が30日評価 |
| R2 | claim-evolve の gate（改善∧無退行）を通した自動 merge | INV-R1 の再検討が必要なため当面凍結 |

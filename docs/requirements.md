# AI情報専門サイト 要件定義書

**バージョン**: 2.8  
**最終更新**: 2026-09-25  
**ステータス**: 実装中（Phase 0 → Phase 1 移行、ロードマップ: `docs/ROADMAP.md`）

---

## 1. サイト概要

| 項目 | 内容 |
|---|---|
| サイト名 | AIナビ（仮） |
| 目的 | AI初心者〜中級者が「使える・試せる」情報を得られる日本語ハブ |
| ターゲット | 日本語圈（メイン）・英語圈（技術SNS・動画経由でリーチ拡大） |
| 言語 | 日本語原本 / 閲覧者のブラウザ言語で表示・段階展開（§8、JA → EN → ES/FR） |
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
│        Auditor Gate（全生成物必須）        │
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
| `n8n/skills/20-auditor-gate.md` | ainavi-gate | ファクトチェック+著作権検証 |
| `n8n/skills/30-wp-publisher.md` | n8n | WordPress投稿 |
| `n8n/skills/90-evolve-loop.md` | claim-evolve | SKILL.md自律改善ループ |

---

## 5. Claim Platform連携戦略

**核心思想**: パイプライン自体がClaim Platformのユースケースデモであり、「AIナビを動かすために使ったツールの紹介」自体が最強の宣伝媒体となる。

### 5-1. 各プロダクトの役割

| プロダクト | パイプライン内の役割 | 宣伝切り口 |
|---|---|---|
| **ainavi-gate** | 全生成物のファクトチェック + 著作権コンプライアンスゲート | 「このメディアは全記事をAuditor検証済」 |
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
「この記事はAI Navi Auditor Gateでファクトチェック済み」→ バッジ表示
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
| 質保証 | Auditor Gate | 全記事の事実検証 + 著作権コンプライアンス |
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
Auditor Gate
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
Auditor Gate（copyright_compliance: cross_lingual=ZH）
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

## 8. 言語戦略（閲覧者の言語で表示・段階展開）

> 2026-09-25 改訂（v2.8）。操作者の方針:「アクセスした人の言語で自動表示し、任意の言語も選べるようにする」。
> 旧版（日本語本文 + 英語SEOメタ、英語記事は Phase 2）は 8-6 に引き継ぐ。**この節は仕様であり、実装はまだない**（Phase I・T-53〜T-57）。

### 8-1. 基本方針

- 記事の**原本は日本語**のまま。他の言語版は、Auditor Gate を PASS した日本語原本から作る翻訳とする。
- 表示言語は**閲覧者のブラウザの言語設定**で決める。IP アドレスによる位置判定では決めない。
  - 理由: 位置と言語は一致しない。例えばフロリダの閲覧者の多くは英語話者で、スペイン語話者はブラウザ設定の方で拾える。VPN・旅行者・多言語国（スイス・カナダなど）でも位置判定は外れる。
- 閲覧者はいつでも**言語切替スイッチ**で任意の言語を選べる。選んだ言語は記憶し、次回以降はそれを優先する。
- 言語は**段階的に**増やす（8-4）。Auditor が検査できない言語は公開しない。

### 8-2. 表示言語の決め方（優先順）

| 順位 | 根拠 | 備考 |
|---|---|---|
| 1 | 閲覧者が切替スイッチで選んだ言語（Cookie で記憶） | 常に最優先 |
| 2 | ブラウザの言語設定（`Accept-Language`）| 公開済みの言語に一致するときだけ使う |
| 3 | 既定言語 = 日本語 | 一致しない場合・Googlebot を含む |

- **強制リダイレクトはしない**のを原則とする。一致する言語版があれば「English version available」のような**案内バナー**を出し、切り替えは閲覧者が選ぶ。
  - 根拠（Google Search Central「Managing Multi-Regional and Multilingual Sites」、2026-09-25 確認）: 言語ごとに別の URL を使うことを推奨し、推測した言語への自動リダイレクトは避けるよう求めている。Googlebot は通常米国から、`Accept-Language` なしで巡回するため、言語で出し分けると他の言語版が検索に載らない可能性がある。
- 多言語プラグイン Polylang の「ブラウザ言語の検出」は、**初回訪問時にトップページだけ**を自動リダイレクトする（polylang.pro の公式ガイドで確認）。上の原則とは緊張関係にあるが、**操作者の判断で ON とする（2026-09-25 決定）**。影響を抑えるため次を守る。
  - 自動で切り替えるのは Polylang の仕様どおり**トップページの初回訪問だけ**。記事ページは自動で切り替えない。
  - Googlebot は `Accept-Language` を送らないので既定言語（日本語）を受け取る。他の言語版は `/en/` などの URL と hreflang で見つけてもらう。
  - 切替スイッチは全ページのヘッダーに常に表示する（切り替えた先の言語は Cookie で記憶される）。
  - L1 公開後、Search Console で言語版ごとのインデックス数を確認し、問題があれば OFF に戻す（8-4 の 30 日運用の記録に含める）。

### 8-3. URL と検索エンジン向けの表示

- 日本語は**今の URL のまま**（ルート）。他の言語はサブディレクトリにする: `/en/` `/es/` `/fr/`。
- 各言語版のページに `hreflang` で全言語版（自分自身を含む）を列挙し、`x-default` は日本語版を指す。
- 1ページ1言語とする（本文と見出しを混在させない）。
- 実装手段の第一候補は Polylang（WordPress.com のプラグイン一覧に掲載を確認。有料プランが前提、§35-14）。**slug と WordPress.com での動作は、導入前に `wp_site_setup.py plan` と操作者の管理画面で確認する**。

### 8-4. 段階展開

| 段階 | 言語 | 昇格の条件（すべて満たすこと） |
|---|---|---|
| L0（現在） | 日本語 | — |
| L1 | ＋英語 | ① 英語の PR 表記を A1 が認識し、評価ケースで FP=0/FN=0（T-53）② 翻訳の忠実性チェック（8-5）が本番パスに配線済み（T-54）③ 翻訳 WF の手動実行ログ（CLAUDE.md §F）④ 操作者の署名（INV-R1）|
| L2 | ＋スペイン語・フランス語 | L1 と同じ条件を各言語で満たす。加えて L1 を 30 日運用し、英語版の Auditor 判定（FAIL/UNVERIFIABLE 率）を §34-9 と同じ形式で記録する |

- 新しい自動化は Report-Only → 人間承認付き → 自動 の順で昇格させる（CLAUDE.md §B-7）。各言語の**初回公開は下書きのみ**とする。

### 8-5. 翻訳と監査のルール

- **翻訳の元は Auditor Gate で PASS した日本語原本だけ**とする。FAIL / UNVERIFIABLE の記事は翻訳しない。
- 各言語版も**独立した記事として Auditor Gate を通す**。FAIL / UNVERIFIABLE は公開しない（INV-R2）。
- 翻訳の忠実性チェック（決定論的・LLM を使わない、T-54）: 原本と翻訳の間で、次が一致すること。
  - 数値（価格・日付・統計）の集合
  - リンク先 URL の集合（アフィリエイトリンクの `rel="sponsored"` を含む）
  - 見出しの数、引用ブロック（`<blockquote>`）の数
- **引用**（著作権5要件の「改変禁止」）: 引用ブロックの原文は翻訳せずにそのまま残し、訳は「参考訳」と明示して引用ブロックの外に置く。この扱いが各国法で足りるかは未確認のため、L1 の前に操作者が確認する（8-7）。
- **広告表示**: A1 の PR 表記は言語ごとに認識語を持つ（例: 英語 `Sponsored` / `Ad` / `Affiliate`、スペイン語 `Publicidad`、フランス語 `Publicité`）。現行の `content_audit.py` の `PR_LABEL_RE` は日本語と `PR` だけで、英語の表記は FAIL になる（2026-09-25 にコードで確認）。対象国の表示規制（日本の景品表示法ステマ規制、米国 FTC など）への適合は操作者が確認する。
- 翻訳記事にも §22 の監査規則（誇大表現・出典・構造）を各言語で適用する。現行の誇大表現リスト（`content_audit.py` の `HYPE_PHRASES`）は日本語なので、言語ごとの辞書を用意する（T-53）。

### 8-6. 旧版から引き継ぐ項目

| 層 | 言語 | 内容 | 状態 |
|---|---|---|---|
| 記事本文（原本） | 日本語 | 全記事 | 現行 |
| SEOメタ | 英語 | title / description / slug / alt | 設計済み・未実装（T-19）。L1 以降は各言語版が自分の言語のメタを持つ |
| SNS配信 | 英語 | Higgsfield動画 + YouTube / TikTok | Phase 2 |
| ZH→JA 翻訳記事 | 日本語（翻訳ラベル付き） | Kimi経由 | Phase 2（WF08）。多言語展開とは別の流れ（中国語の情報源を日本語記事にする）|

### 8-7. 未決事項（操作者の判断が必要）

1. ~~WordPress.com のプランが有料かどうか~~ → **決定済み（2026-09-25）**: **ビジネスプラン**（管理画面の表記は「仕事」、年払い 42,000円 = 月額換算 3,500円、2026-09-25 操作者のスクリーンショットで確認）。プラグインの導入とカスタムコード（JavaScript など）が使える（§35-14）
2. ~~Polylang の「ブラウザ言語の検出」を ON にするか~~ → **決定済み（2026-09-25）**: ON。条件と見直し方法は 8-2
3. ~~公開上限を言語ごとに数えるか合計で数えるか~~ → **決定済み（2026-09-25）**: **言語ごと**に数える（日本語3本・英語3本…）。現行の `/publish-slot` と `publish_slots` 表は言語を区別しないため、T-56 で `lang`（既定 `ja`）を追加する（§35-9）
4. 引用の「原文 + 参考訳」方式が、対象国の著作権法で足りるかの確認
5. 対象国の広告表示規制（FTC など）への適合確認と、各言語の PR 表記の文言
6. 翻訳に使うモデルとコスト上限（L1 の翻訳 WF を作る前に決める）

### 8-8. 範囲外

- 各言語版のテーマ文言（メニュー・フッター）の翻訳作業そのもの。プラグイン導入後に操作者が管理画面で行う。
- 中国語・韓国語など L2 に含まれない言語。L2 の運用結果を見てから検討する。

---

## 9. GitHubトレンドコンテンツ

### 取得ロジック

```
GitHub API Search（topic:ai OR topic:llm / 過去7日 / sort:stars）
    ↓
claim-crew: 難易度タグ付与（入門/中級/上級）+ 英語SEOメタ並行生成
    ↓
Auditor Gate（スター数はAPI直接取得=PASS / 予測発言=UNVERIFIABLE）
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
| `WP_APP_PASSWORD` | WordPress Application Password（ローカルサンドボックス / Basic認証用） |
| `WP_BEARER_TOKEN` | WordPress.com OAuth2 access_token（本番 / Bearer認証用。§24参照） |
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
| ファクトチェックゲート | ainavi-gate | 全生成物必須（著作権コンプライアンス含む） |
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

> 2026-09-24 更新: デザイン層はプラグインを使う方針に変更（§35-14）。正は `data/wp-site.json`。

| プラグイン | 用途 | コスト | 状態（§35-14） |
|---|---|---|---|
| Rank Math SEO（`seo-by-rank-math`） | SEO最適化・Sitemap生成 | 無料 | 採用 |
| WP REST API | n8nからの自動投稿 | WordPress標準 | 採用（コア機能） |
| Kadence Blocks（`kadence-blocks`） | カード・グリッド・ステップ図解 | 無料 | 採用 |
| WP Dark Mode（`wp-dark-mode`） | ダークモード | 無料 | 採用 |
| Easy Table of Contents（`easy-table-of-contents`） | 記事の目次 | 無料 | 採用 |
| WP Super Cache（`wp-super-cache`） | 表示高速化 | 無料 | 自己ホストのサンドボックスのみ（WordPress.com はサーバ側キャッシュ） |
| Akismet | スパム対策 | 無料（個人） | 未定（コメント機能を使うかで判断） |
| ~~Classic Editor~~ | ~~n8nからの投稿に対応~~ | — | **不採用**。ブロックエディタを無効化し、ブロック系デザインと両立しない。REST 投稿には不要 |
| ~~Advanced Custom Fields~~ | ~~ツール詳細用~~ | — | **現時点で不要**。ツール情報は `data/tools.json`（§35-11） |

テーマは Twenty Twenty-Five（ブロックテーマ）。プラグインの導入は WordPress.com の**有料プラン**が前提（§35-14）。

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
- [x] Auditor Gate**ノード**をn8nに組み込み（WF01〜09、§21 W2/W7 で機械検証）
- [ ] Auditor Gateの**呼び先サービス**実装（§28、ROADMAP T-02〜T-06）— 未実装のため現状は全件 `verdict: SKIP`
- [ ] Mermaid + Kroki.io 図解自動挿入実装（§31、T-10〜T-11）
- [ ] yt-dlp 字幕取得ノード実装（WF03、T-18・要設計）— 現状は YouTube Data API の `snippet.description` を要約入力に使用
- [x] エージェント記憶層 SQLite 初期化スクリプト（`scripts/memory_init.py`、§19）
- [ ] 記憶層への本番書込み経路（§28-2 FAIL蓄積、T-03）— 未実装のため `ratchet_check.py` は常に "no memory db"
- [x] n8n/skills/ ディレクトリ作成（SKILL.md 10ファイル、§18）
- [x] WordPress 初回セットアップ（本番 WordPress.com、§24-5 で検証済み）
- [ ] 自動テスト基盤（`tests/`、T-02/T-03/T-10）と CI ゲート拡張（T-06）
- [ ] エンドツーエンドサンドボックステスト（T-15、操作者側）

### Phase 1：コアパイプライン（ホスティング確定後）
- [ ] 本番WordPressセットアップ
- [ ] WF01-02 稼働（Auditorゲート付き）
- [ ] NoimosAI初期連携（WF07）— 現行 `07-article-writer.json` は Google Drive トリガー無しの手動汎用ライター（§6-4 と乖離、導入要否は未決定）
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

## 36. 将来拡張構想 — ハブ&スポーク（未着手・実装しない）

> ⚠️ 本章は**将来構想の記録**であり、設計確定でも実装対象でもない。今このリポジトリでは
> 何も実装しない。操作者の意思決定（2026-09-24）: 「単なるニュース配信で終わらせたくない。
> アイデアから物理的な商品を作り出し販売まで一気通貫で行うハブ的機能や、i am youのように
> 人と人をAIが繋ぐサービスを将来的に持ちたい」。

### 36-1. 構想の骨子

ai-solution-（本リポジトリ）は情報ハブ・入口の役割に留め、性質の異なる実処理（決済・製造連携・
マッチング）は**別スポークとして分離**する方向で検討する。理由:

- §27 で reporters 系との重複を一度解消した経緯があり、性質の違う機能を同一リポジトリに混在
  させると `scripts/check_wired.py` の誤検知や、Auditor Gate（記事の真偽判定用に最適化された
  LLM-free 決定論ゲート、INV-R1/INV-R2）の趣旨の希釈を招きやすい。
- Claim Platform の既存6リポジトリ（Auditor / Builder / Console / Crew / Evolve / Security /
  LLM）は既に「Auditor＝LLM-free judge」「Builder＝S0〜S8生成パイプライン」という型を持ち、
  新スポークはこの型の再利用を検討できる。

```
                         ┌─ ai-solution-（本リポジトリ・入口ハブ）
                         │   ニュース／ツール比較／Claim Platform紹介
                         │   各スポークへの導線（記事内CTA・ツールDB経由）
                         │
   Claim Platform ───────┤
   （既存6リポジトリ）    ├─ スポークA（構想）: アイデア→商品化ハブ
                         │   アイデア投稿→設計→試作先マッチング→販売
                         │
                         └─ スポークB（構想）: 人と人をAIが繋ぐサービス
                             個人情報を扱うため claim-security- の適用を要検討
```

### 36-2. 現時点での方針

| 項目 | 方針 |
|---|---|
| 実装着手 | **しない**。A・Bとも設計・実装ゼロ。リポジトリも未作成 |
| 現行コードへの影響 | 無し。§35 のツールページ・比較サイロの CTA 設計を、特定スポークの
  仕様に先回りして縛らない（汎用的な外部リンクとして留める）程度の配慮に留める |
| 着手判断 | 操作者が着手フェーズを判断した時点で、当該スポークの要件定義書を新規リポジトリ側に
  起こす（このリポジトリの docs/requirements.md には追記しない） |
| 未確定事項 | A・Bどちらを先に着手するか / 別リポジトリか同一リポジトリ内の別セクションか /
  「i am you」的サービスの具体的な参照仕様 — いずれも未確認・未決定 |

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
| WordPressホスティング先 | **確定**: WordPress.com（`liquitex929aa21393-eyqci.wordpress.com` → `aiguide.blog`、§24） | — |
| n8n運用方式 | **確定**: n8n cloud Pro（`liquitex-coder.app.n8n.cloud`、§25） | — |
| サイト正式名称 | 仮「AIナビ」 | 要相談 |
| ドメイン | **確定**: `aiguide.blog`（§24-1） | — |
| Higgsfield APIアクセス・コスト | 要確認 | Phase 2開始前 |
| auditor gateのn8n組み込み方法 | **確定: HTTP API**（§28） | — |
| Auditor サービスのホスティング先（n8n cloud から到達可能な HTTPS） | **未確定** | ROADMAP T-12 |
| n8n cloud で Code ノードの `$env` が参照可能か | **未検証**（docs.n8n.io は本セッションの egress ポリシーで取得不可） | ROADMAP T-13。不可なら `$vars` フォールバック（T-11） |
| ZHソースのスクレイピング方法 | **確定**: RSS 3ソース（`08-kimi-zh.json` 「ZH記事ソース設定」: 机器之心 / Synced Review / 雷锋网AI） | — |
| 日本語Embeddingモデル選定 | 未着手（`memory_init.py` は BM25 のみ、sqlite-vec 不在時フォールバック） | 記憶層本接続時（T-17 以降） |
| Reddit API レート制限 | WF09 は `reddit.com/search.json` を無認証で利用（実運用未確認） | T-15 の手動実行で確認 |

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
| ①主従関係 | 生成字数 / 引用字数 > 2.0（引用 ≤ 1/3） | 字数カウント | ✅ `QUOTE_DOMINANCE_RATIO = 0.34`（§32-1 D1、T-24、2026-09-13） |
| ②明瞭区別 | `<blockquote>` または `>` が存在 | 正規表現 | ✅ |
| ③必要性 | `##` 見出しブロック ≥ 3 | 構造チェック | ✅ |
| ④出所明示 | 記事内に原文URLが存在 | URL検出 | ✅ |
| ⑤改変禁止 | 同言語: blockquote内テキスト類似度 > 0.85 | difflib | **WARN のみ**（`WARN:QUOTE_ALTERED:<ratio>`、§32-1 D7、T-24 第2ラウンド。30日観察後に FAIL 昇格を判断） |

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

### REVIEW（Auditor Gate）
PASS条件: 著作権5要件 + 確度スコア >= MED + 出典明記
FAIL時: 人間レビューキュー + 記憶層のfacts層にFAIL事例を格納

### SHIP（WordPress投稿）
...
```

### 18-3. Rationalizations Table → Auditor 統合

agent-skills の「言い訳ブロックリスト」を auditor gate のプレフライトチェックに統合する:

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
auditor gate が改善案を検証（ハルシネーション・品質後退チェック）
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
Auditor Gate
    ↓ PASS
WordPress 投稿
    ↓
記憶層更新（会話 → シーン層昇格 / 新事実 → 事実層追加）
```

---

### 19-8. ライブラリ API（`scripts/memory_init.py`、§28 サービスからの本番書込み経路）

§28-2 の事実層書込みは、CLI をサブプロセス起動せず **同一プロセスから関数呼び出し**で行う
（LLM-free・stdlib のみ・失敗時は §14 の「ログを出して継続」）。CLI サブコマンド・フラグ・
出力 JSON キーは従来どおりで、CLI ハンドラは以下の関数を呼ぶだけの薄いラッパーとする。

| 関数 | 役割 | 呼び出し元（本番） |
|---|---|---|
| `ensure_schema(conn) -> None` | `SCHEMA` を冪等適用。既存 DB に `facts.content_hash` が無ければ `PRAGMA table_info` で検出して `ALTER TABLE` で追加（移行） | `auditor_server.py` 起動時 |
| `insert_fact(conn, content, source_url="", confidence="LOW", verdict="", fail_reason="", skill_ref="", content_hash="") -> int` | 事実層へ1行挿入し id を返す | `/audit` の FAIL / UNVERIFIABLE 時（§28-2） |
| `insert_scene(conn, title, url, summary="") -> int` | シーン層へ upsert（同一 url は更新） | WordPress 投稿後（T-17） |
| `find_duplicate(conn, title, summary="") -> dict` | §19-4 の類似度判定（`check-dup` と同じ payload） | `/check-dup`（T-17） |

- `facts.content_hash TEXT DEFAULT ''`（+ index）を追加する。§32-1 D5 `ALREADY_REJECTED` の検索キー。
- テスト: `tests/test_memory.py`（スキーマ冪等 / insert_fact の id / insert_scene の upsert / find_duplicate の真偽 / 旧スキーマ DB への移行）。
- 実装タスク: ROADMAP T-02（Codex）。

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
| W2 | 全ワークフローに Auditor Gate ノードが存在（`AINAVI_GATE_URL` 参照で判定） | ゲートなしWF |
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

### 22-3. 段階的ロールアウト（AINAVI_GATE_MODE）

| モード | 動作 | 昇格条件 |
|---|---|---|
| `report_only`（既定） | 全件 draft + verdict をメタデータ記録 | — |
| `canary` | PASS の約10%のみ自動 publish | 評価セット FP=0/FN=0 + 本番 verdict 30日分レビュー |
| `full` | PASS を自動 publish | canary 30日で誤公開ゼロ + 人間署名（INV-R1） |

- モードは n8n 環境変数 `AINAVI_GATE_MODE` で制御。コード変更なしで昇格・降格。
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

---

## 24. WordPress.com 認証方式（実運用で確定・2026-07-12）

### 24-1. 背景

`docker-compose.yml` のローカルサンドボックス（自己ホスト型 WordPress）は
Application Password + Basic認証で動作する（WordPress 5.6+の標準機能）。

しかし本番の投稿先（`liquitex929aa21393-eyqci.wordpress.com`、カスタムドメイン
`aiguide.blog` にマッピング済み）は **WordPress.com ホスト型**であり、二段階認証を
有効化した状態では `wp/v2` REST API が Basic認証（Application Password直用）を
`401 invalid_token` で拒否することを実運用で確認した。WordPress.com は
**OAuth2 password grant で取得した Bearer トークン**を要求する。

### 24-2. 認証フロー（本番・1回限りのセットアップ）

```
① wordpress.com/me/security で二段階認証を有効化
② 同ページに出現する Application Passwords で1つ発行（24文字）
③ developer.wordpress.com/apps/new/ で OAuth2 アプリを登録
      → Client ID / Client Secret を取得
④ oauth2/token に password grant でリクエスト
      （client_id, client_secret, grant_type=password,
        username, password=②のApplication Password, blog_url）
      → access_token を取得（無期限・原則失効しない）
⑤ access_token を WP_BEARER_TOKEN として保管
```

`wp/v2/sites/{blog}/posts` へは `Authorization: Bearer {access_token}` で投稿可能
（`201`・下書き作成を実運用で確認済み、post id 44 で検証・削除済み）。

### 24-3. 環境変数とスクリプトの対応

| 環境 | 認証方式 | 使用する環境変数 |
|---|---|---|
| ローカルサンドボックス（自己ホスト） | Basic（Application Password） | `WP_USERNAME` + `WP_APP_PASSWORD` |
| 本番（WordPress.com） | Bearer（OAuth2 access_token） | `WP_BEARER_TOKEN` |

`scripts/wp-init.sh` は `WP_BEARER_TOKEN` が設定されていれば Bearer を、
未設定なら従来どおり Basic を使う（後方互換・自動判定、追加フラグ不要）。
n8n 側は WordPress ノードの credential を `httpHeaderAuth` の
`Authorization: Bearer {{ $env.WP_BEARER_TOKEN 相当の値 }}` に設定する
（credential の値自体はn8n UIでの手動設定であり、ワークフローJSONは変更不要 —
既存の `httpHeaderAuth` credential 型のまま、ヘッダー値だけ差し替える）。

### 24-4. 既知の制約

- OAuth2 access_token は WordPress.com 側の失効操作（アプリのRevoke）まで有効。
  Application Password を再発行してもこのトークンには影響しない。
- `blog_id`/`blog_url` が `token` レスポンスで空（global scope）でも問題ない —
  同一ユーザーが所有する全サイトに有効なトークンとして機能することを確認済み。

### 24-5. wp-init 実行検証（2026-07-12・実機・Windows PowerShell）

`scripts/wp-init.ps1`（WSL bash不在環境向けのPowerShell移植版）を、実際の
WordPress.com本番サイトに対して実行し、エラーなしで完走することを確認した:

```
[OK] Authentication verified. (liquitex929aa21393)
--- Creating categories --- ： 8件すべて [CREATED]
--- Creating tags ---       ：30件すべて [CREATED]
=== Initialization complete ===
```

`scripts/wp-init.sh`（bash版）と同一の分岐ロジック（WP_BEARER_TOKEN + WP_SITE
優先、WP_APP_PASSWORD へフォールバック）を実装しており、これで両スクリプトとも
実運用で検証済みとなった。

---

## 25. n8n cloud API 経由デプロイ自動化（Proプラン、実運用）

### 25-1. 背景

n8n cloud の公開API（`/api/v1/*`）は無料トライアルでは無効化されており、
Proプラン以降で有効。ユーザーがProへアップグレードしAPIキーを発行したため、
手動UIインポート（9本のワークフロー + 7種のCredential手動作成・紐付け）を
スクリプト化する。ハーネス原則の「段階的ロールアウト」に従い、**ワークフローの
Active化はスクリプトでは行わず、人間が手動実行で確認してからONにする**
（SETUP_GUIDE Step 5 の既存フローを維持）。

### 25-2. スクリプト仕様（scripts/n8n_deploy.ps1）

1. 認証: n8n公開APIは `X-N8N-API-KEY` ヘッダー（`Authorization: Bearer` ではない）。
2. Credential作成（`POST /api/v1/credentials`）— 環境変数が設定されている分のみ、
   冪等（既存同名Credentialがあれば `[SKIP]`）:

   | Credential名 | ヘッダー名 | 環境変数 | 値のprefix | 必須 |
   |---|---|---|---|---|
   | Claude API Key | `x-api-key` | `ANTHROPIC_API_KEY` | なし | 必須 |
   | WordPress App Password | `Authorization` | `WP_BEARER_TOKEN` | `Bearer ` | 必須 |
   | GitHub API Token | `Authorization` | `GITHUB_TOKEN` | `token ` | 任意（WF01） |
   | Perplexity API Key | `Authorization` | `PERPLEXITY_API_KEY` | `Bearer ` | 任意（WF06） |
   | Kimi API Key | `Authorization` | `KIMI_API_KEY` | `Bearer ` | 任意（WF08） |
   | Threads API Token | `Authorization` | `THREADS_ACCESS_TOKEN` | `Bearer ` | 任意（WF04） |
   | YouTube Data API Key | `key`（既知の不整合、25-4参照） | `YOUTUBE_API_KEY` | なし | 任意（WF03/09） |

3. ワークフロー作成（`POST /api/v1/workflows`）— `n8n/workflows/*.json` を読み、
   `name`/`nodes`/`connections`/`settings` のみ送信（`active`/`tags`/`notes` は
   n8n API のスキーマ外のため除去）。各ノードの `credentials.*.id`
   プレースホルダーを、作成済みCredentialの実IDへ書き換える。
   同名ワークフローが既に存在すれば `[SKIP]`（冪等）。
4. **Active化はしない** — 作成後は人間が n8n UI で手動実行 → WordPress下書き
   確認 → Active ON、という既存フロー（SETUP_GUIDE Step 5）に委ねる。

### 25-3. 環境変数（n8n Environments、API対象外）

`GITHUB_TOKEN` は Credential ではなく、各WFの「プロンプト読込み」Code ノードが
`$env.GITHUB_TOKEN` として直接参照する（GitHub Contents APIからプロンプトを
取得するため）。これは n8n の Environments/Variables 機能で設定するもので、
本スクリプトのCredential作成とは別系統。Proプランで対応するUIから手動設定が必要
（`n8n/SETUP_GUIDE.md` に手順追記）。

### 25-4. 既知の不整合（解消済み・2026-07-12）

`03-youtube-summary.json` の「YouTube Data API動画取得」ノードは
`genericAuthType: httpHeaderAuth` で配線されていたが、Google の YouTube Data API
はAPIキーをヘッダーではなく **クエリパラメータ `key`** で要求するため認証が通らない
不整合があった。ノードを `genericAuthType: httpQueryAuth` に修正し、
`scripts/n8n_deploy.ps1` の YouTube Credential定義も対応する型（`httpQueryAuth`）で
作成するよう修正した。`09-multi-source-research.json` は元々Codeノード内で
`fetch()` に直接クエリパラメータとして `key=${YOUTUBE_API_KEY}` を付与しており、
この不整合の対象外だった。

---

## 26. Claude Code × Codex 協業ルール（開発ツール連携・MCP経由）

> 本節はAIナビ・パイプライン自体の仕様ではなく、**このリポジトリを開発する際の
> ツール連携方針**（操作者のローカル開発環境向け）。2026-09-12、操作者が
> 個人wikiで検証済みの構成を本リポジトリのCLAUDE.md/AGENT_WORKFLOW.mdに反映。

### 26-1. 役割分担

| 役割 | 担当 | 内容 |
|---|---|---|
| 司令塔（Orchestrator） | Claude Code | 要件整理・設計・作業分解・PRレビュー・リスク洗い出し・「本当にそれでいい？」の壁打ち |
| 実装者（Implementer） | Codex（MCP経由） | 実装・差分作成・リファクタの下ごしらえ・既存コードに沿った修正案生成・小さな修正の高速反復 |

Claude Codeは実装コードを直接書かず、Codexへの委譲・レビュー・統合に徹する
（Worker-Evaluator分離の原則をツール連携にも適用）。

### 26-2. 接続方式

Codexを MCP サーバーとして登録する（**操作者のローカル環境**で実行。クラウド
サンドボックスセッションでは Codex 未インストールのため適用不可）:

```bash
claude mcp add codex --scope user -- codex mcp-server
```

呼び出し時は必ず `approval-policy: never` / `sandbox: workspace-write` を渡す
（Codexの承認プロンプトは MCP elicitation 経由で非対応クライアントでは失敗するため）。

### 26-3. 呼び出し規律

1. 1回の `codex` 呼び出しにつき1サブタスクのみ。
2. 毎回 `cwd`（絶対パス）・`approval-policy=never`・`sandbox=workspace-write` を渡す。
3. プロンプトに以下を必ず含める: GOAL（目的）/ FILES（対象ファイル、それ以外は触らない）/
   ACCEPTANCE（成功基準となるコマンド）/ CONSTRAINTS（禁止事項）。
4. 呼び出し後は必ず `git diff` を確認してから次の指示を出す。
5. 継続作業は新規セッションでなく `codex-reply` + 既存thread idを使う。

詳細な運用契約テンプレート → `docs/AGENT_WORKFLOW.md` §9。

---

## 27. アーキテクチャ方向性の確定（2026-09-12・main分岐の解消）

main に別PR系列（#4〜#7）で並行開発されていた Node.js製「reporters」フレームワーク
（WF07〜13・disclosure gate・品質ベースライン・独自CLAUDE.md）と、本ブランチの
n8n + Auditor Gate パイプライン（WF01〜09・配線ゲート・評価セット・ラチェット・
規約ドリフト検出）が、共通の祖先から独立に分岐し重複していた。

**操作者の判断（2026-09-12）**: 本ブランチ（n8n + Auditor Gate 一式）を正とする。
reporters フレームワークの重複部分（`reporters/`, WF07-13の reporters 側実装,
`package.json`, `scripts/check_reporters.mjs` 等, `.github/workflows/reporters.yml`,
`data/wp-taxonomy.json` の reporters 向け拡張, 旧構成の README.md）は本マージで
削除。マネタイズ設計など reporters 側 requirements.md に存在した独自コンテンツで
拾う価値があるものは、必要になった時点で `main`（マージ前）または当該PRの履歴から
個別に参照する（今回は移植しない）。

理由: 両実装は `n8n/workflows/` 等のファイルパスを共有しない部分でも機能的に重複
しており（同じ「WF01-06に続く追加コンテンツタイプ」という役割）、両方を残すと
本ブランチの配線ゲート（`scripts/check_wired.py` W2/W3/W4/W7）が reporters 側の
ワークフローJSON（Auditor Gate 非搭載）を誤って評価しFAILする。

---

## 28. Auditor Gate HTTP サービス（`scripts/auditor_server.py`）— §15 組み込み方式の確定

### 28-1. 背景（コードで確認した事実・2026-09-12）

- WF01〜09 の全 Auditor Gate ノードは `fetch(`${auditorUrl}/audit`, {method:'POST', body:{content, source_urls, skill_ref}})`
  を実行し、`res.json()` の `verdict` で `wp_status` を決める（例: `n8n/workflows/01-github-ai-trending-daily.json`
  "Auditor Gate (WF-01)" ノード）。
- しかし `/audit` を提供するプロセスはリポジトリに存在しない。`scripts/content_audit.py` は CLI / ライブラリのみ。
  したがって本番では `AINAVI_GATE_URL` 未設定 → 全件 `verdict: 'SKIP'`・draft となり、
  §21 W2 が検証していたのは「ゲートノードの存在」だけで「呼び先の存在」ではなかった。
- 同様に §19-3 の「Auditor FAIL を事実層に蓄積」は書込み経路が無く、§23 の `ratchet_check.py` は入力ゼロ。

### 28-2. API 契約（LLM-free・stdlib のみ・INV-R2）

| Method / Path | Request | Response |
|---|---|---|
| `GET /health` | — | `200 {"status":"ok","service":"ainavi-auditor-gate","memory_db":true|false,"auth":true|false,"tools_catalog":true|false}`（`tools_catalog` は §35-13） |
| `POST /audit` | JSON `{content: string, source_urls?: string[], skill_ref?: string, title?: string}` | `200 {"verdict":"PASS|FAIL|UNVERIFIABLE","reasons":[...],"skill_ref":..., "audited_at": ISO8601, "fact_id": int|null, "requires_human_signature": bool}`（最後のフィールドは §35-6 A5） |
| `POST /embed-diagrams` | JSON `{content: string}` | `200 {"content": string, "diagrams": int}`（§31。verdict には無関係） |
| その他 | — | `404`。不正 JSON / `content` 欠落は `400 {"error": ...}` |
| 認証 | `AINAVI_GATE_TOKEN` が設定されている場合、すべての POST ルート（`/audit`・`/embed-diagrams`・`/publish-slot`（§35-9）・`/link-tools`（§35-13））は `Authorization: Bearer <token>` を要求する（不一致・欠落は `401 {"error":"unauthorized"}`、記憶層へは何も書かない）。`GET /health` は常に認証不要で `"auth": true|false` を返す。未設定時は挙動を変えず、起動時に stderr へ「unauthenticated mode (sandbox only)」を1行出す。比較は `hmac.compare_digest` を **bytes** で行う（str 比較は非 ASCII を含む Bearer 値で `TypeError` → `400` になる、2026-09-13 実測）。Bearer 値に非 ASCII が含まれる場合も `401`。トークンはログに出さない（T-27） | — |
| ポート | `AINAVI_GATE_PORT` → 無ければ `PORT`（Render / Fly.io 慣習）→ 無ければ 8090。**イメージ（`Dockerfile`）は `AINAVI_GATE_PORT` を `ENV` で焼き込まない** — PaaS が注入する `PORT` を無効化するため（2026-09-13 実測: `AINAVI_GATE_PORT=8090` + `PORT=10000` で 8090 に bind、10000 は応答なし）。`HEALTHCHECK` も同じ優先順位で解決する（T-26 第2ラウンド） | — |

- verdict は `content_audit.audit(content, source_urls)` をそのまま返す。判定ロジックの追加・変更は §22 の評価セットを通す。
- **事実層への書込み（§19-3）**: verdict が `FAIL` または `UNVERIFIABLE` のとき `facts` に1行挿入する。
  `fail_reason` = 先頭 reason の**カテゴリ部**（`FAIL:HYPE:革命的` → `FAIL:HYPE`、`UNVERIFIABLE:UNSOURCED_STATS` はそのまま）—
  §23-1 の `(skill_ref, fail_reason)` 集計キーとして安定させるため。`content` は先頭500字、`source_url` は先頭URL、
  `confidence` は UNVERIFIABLE→`UNVERIFIABLE`、FAIL→`LOW`。`PASS` は書き込まない（シーン層への記録は WordPress 投稿後・T-17）。
- 記憶層 DB が開けない場合は §14 の方針どおり**ログを出して verdict は返す**（`fact_id: null`）。ゲートを止めない。
- ゲート側は `{...$json, ...result}` で応答を展開するため、応答キーは既存フィールド（`title/content/wp_status/source_url`）と**衝突させない**。
- ログ: 1リクエスト1行の JSON（path, verdict, skill_ref, ms）。記事本文はログに出さない。
- 環境変数: `AINAVI_GATE_PORT`（既定 8090）/ `AINAVI_GATE_BIND`（既定 `0.0.0.0`）/ `AINAVI_GATE_MEMORY_DB`（既定 `data/memory.db`）/ `KROKI_BASE_URL`（§31）。

### 28-3. 配置

| 環境 | 配置 | n8n 側設定 |
|---|---|---|
| ローカルサンドボックス | `docker-compose.yml` の `auditor` サービス（`python:3.11-slim`、`./scripts` と `./data` をマウント、`python3 scripts/auditor_server.py`） | `n8n` サービスの環境変数 `AINAVI_GATE_URL=http://auditor:8090`、`AINAVI_GATE_MODE=${AINAVI_GATE_MODE:-report_only}` |
| 本番（n8n cloud） | **Fly.io** — T-26 の `Dockerfile` + `fly.toml`（1GB `data` volume、`internal_port: 8090` ピニング）。Fly CLI: `fly deploy -c fly.toml`。環境変数 `AINAVI_GATE_TOKEN` は `fly secrets set AINAVI_GATE_TOKEN=<value>` で設定。Fly app 名: `ainavi-auditor-gate`（Claim-Auditor リポジトリとの混同を避けるため `claim-auditor` から改名・2026-09-16）。ホスト: `https://ainavi-auditor-gate.fly.dev`（自動 HTTPS）。決定日: 2026-09-13、**デプロイ完了: 2026-09-17**（region `nrt`、volume `vol_40o0mnm90wnn5qk4` 1GB、`GET /health` → `{"status":"ok","auth":true,"memory_db":true}` 確認済み） | `AINAVI_GATE_URL` / `AINAVI_GATE_MODE=report_only` / `AINAVI_GATE_TOKEN` は n8n cloud の **Variables（`$vars`）** に設定する（T-13）。Code ノードで `$env` が読めるかは T-13 で実測し本表に記録。ゲートは `$vars` → `$env` の順で解決する（`cfg()`、要件 §32-1 D10）。T-13 では追加で Code ノードの `fetch` 可否・`require('crypto')` 可否の2点も実測し記録する（§34-9 P2b の前提） |

`.env.example` に `AINAVI_GATE_MODE=report_only` を追加する（URL は compose 内で固定するため .env 不要）。

**fly.toml 契約**（T-12、2026-09-15）: (i) `AINAVI_GATE_MEMORY_DB` のディレクトリ = `[[mounts]].destination`（`/app/data`）、
(ii) 公開は `[http_service]`（`internal_port` 8090, `force_https`, `auto_stop_machines` off / `min_machines_running` 1
— n8n からの呼び出しをコールドスタートで timeout させないため）、
(iii) Fly のボリュームは root 所有でマウントされ得るため、デプロイ後の完了条件は `/health` が `"auth": true` かつ
`"memory_db": true` を返すこと（`false` の場合は volume の所有権を `auditor` ユーザーへ chown する必要がある —
`FLY_DEPLOY.md` トラブルシューティング参照）。
`FLY_DEPLOY.md` の Fly.io 料金記載（"free tier available" / Cost Estimate）は現行料金を確認するまで「要確認」とする。

### 28-4. テスト（T-03）

`tests/test_auditor_server.py` — サーバをスレッドで起動（port 0）し `urllib` で叩く: health / PASS 応答 / FAIL 応答が facts に1行書かれる /
UNVERIFIABLE が `confidence=UNVERIFIABLE` で書かれる / 不正 JSON → 400 / DB パスが書込不可でも 200 で `fact_id: null`。
実行: `python3 -m unittest discover -s tests -v`（pytest 互換だが依存は追加しない）。§D ゲートと CI に組み込む（T-06）。

---

## 29. WordPressカテゴリ自動割当（Phase C2: WF01〜06）

> 番号注記: 実装時点でのローカル作業環境が §26/§27（本ドキュメント）および
> §28（PR #8、本PR作成時点で未マージ）を反映していない古いチェックアウトだった
> ため、当初「§26」として作成された。mainへの統合時に §29 へ採番し直した
> （§26〜§28 との重複を避けるため）。
> 2026-09-12 追記: PR #8 は #10 に置き換えて close。§28 は Auditor Gate HTTP サービスとなった。

### 29-1. 背景

`scripts/wp-init.ps1`（§24-5）の実行により、`data/wp-taxonomy.json` の
`categories` に定義された8カテゴリがWordPress.com本番サイトに作成済みで、
実際のカテゴリIDが判明した。しかし各ワークフローの「WordPressに下書き投稿」
ノードは `title`/`content`/`status` のみを送信しており、`categories` は
未指定のまま（WordPress側のデフォルト「未分類」に入る）。

`data/wp-taxonomy.json` の `workflow_category_map` は WF-01〜WF-06 の6件のみ
カテゴリが確定しており（`source_workflow` が埋まっている6カテゴリに対応）、
WF-07〜WF-09（記事ライター・ZH処理・複数ソース調査などの中間/汎用ワークフロー）
はカテゴリ名が未決定のため本タスクの対象外とする（別タスクで扱う）。

### 29-2. 実際に発行済みのカテゴリID（wp-init.ps1 実行結果より）

| ワークフロー | slug（wp-taxonomy.json） | WordPressカテゴリID |
|---|---|---|
| WF01: github-ai-trending-daily | github-trending | 790464620 |
| WF02: rss-monitor | ai-official-news | 790464621 |
| WF03: youtube-summary | youtube-summary | 1564589 |
| WF04: threads-influencer | sns-pickup | 790464623 |
| WF05: note-monitor | note-creator | 13765228 |
| WF06: weekly-trend-report | weekly-trend-report | 130534926 |

### 29-3. 実装方針

各ワークフローの「WordPress投稿データ整形」Codeノード（jsCode の `return`文）に
固定値 `category_id`（上記表の数値）を出力データへ追加し、後段の
「WordPressに下書き投稿」httpRequestノードの `jsonBody` に
`"categories": "={{ [$json.category_id] }}"` を追加してWordPress REST APIの
`categories` フィールド（配列指定）に渡す。カテゴリIDはワークフロー間で
再利用されない固定値のため、Codeノード側にハードコードする
（`data/wp-taxonomy.json` を実行時に読み込む仕組みは無く、n8n Code node は
ローカルファイルアクセスを行わないため。将来カテゴリ体系を変更する場合は
本ドキュメントの表とワークフローJSON双方を手動更新する）。

### 29-4. 対象外（別タスク）

WF07（article-writer）・WF08（kimi-zh）・WF09（multi-source-research）は
中間処理ワークフローで直接WordPressへ投稿するケースのカテゴリ名が未確定のため、
本タスクでは変更しない。

---

## 30. 配線ゲート拡張（W8〜W11）と WF→カテゴリ正規対応表

### 30-1. 追加チェック（`scripts/check_wired.py`）

| # | チェック | FAIL条件 |
|---|---|---|
| W8 | 各 Auditor Gate が送る `skill_ref` が `scripts/ratchet_check.py` の `SKILL_PROMPTS` に存在 | 未登録の skill_ref（ラチェットが提案不能） |
| W9 | `scripts/auditor_server.py` が存在し、`docker-compose.yml` に `auditor` サービスと `n8n` への `AINAVI_GATE_URL` がある | 呼び先未配線（§28-1 の再発） |
| W10 | `data/wp-taxonomy.json` の `workflow_category_map` のキー集合が `{WF-01..WF-09}` と一致し、各値の slug が `categories` に存在 | reporters 系残骸・欠落・不一致 |
| W11 | 各 WF の「WordPress投稿データ整形」が出力する `category_id` が、対応 category の `wp_id`（`data/wp-taxonomy.json`）と一致。`wp_id` 未記録の WF はチェックをスキップし PASS(skipped) と表示 | 固定値と正のずれ（§29 の ID 表が陳腐化した状態） |

### 30-2. WF→カテゴリ正規対応表（`data/wp-taxonomy.json` の唯一の正）

| WF | slug | 表示名 | 根拠 |
|---|---|---|---|
| WF-01 | `github-trending` | GitHubトレンド | 変更なし |
| WF-02 | `ai-official-news` | AI公式ニュース | 変更なし |
| WF-03 | `youtube-summary` | YouTube動画まとめ | 変更なし |
| WF-04 | `sns-pickup` | SNSピックアップ | 変更なし |
| WF-05 | `note-creator` | noteクリエイター | 変更なし |
| WF-06 | `weekly-trend-report` | 週次トレンドレポート | 変更なし |
| WF-07 | `howto-guide` | 使い方ガイド | `07-article-writer.json` は手動トリガーの任意テーマ記事（§2-1「使い方ガイド」） |
| WF-08 | `overseas-ai` | 海外AI動向 | `08-kimi-zh.json` は ZH ソース→JA（§6-5） |
| WF-09 | `deep-dive` | 深掘り解説 | `09-multi-source-research.json` は9媒体横断の深掘り記事（§4） |

reporters 系（WF-10〜13: `breaking-news` / `reader-qa` / `changelog-tracker` / `deep-dive` の WF-13 割当、
`factcheck` / `hands-on-review` / `comparison`）は §27 の判断どおり削除する。本番 WordPress.com に既に
作成済みのカテゴリは `wp-init` が slug で冪等スキップするため残っても害はない（不要分の削除は操作者判断）。

WordPress 側の数値カテゴリ ID の付与は §29（PR #9、WF01〜06 に `category_id` を固定値で埋め込み）が扱う。
ID は `data/wp-taxonomy.json` の各 category に `wp_id` として記録し**単一の正**とする（T-07）。WF07〜09 の ID は
T-14 の `wp-init` 再実行で発行後に同じ方式で追記する。ワークフロー JSON 側の固定値と `wp_id` の不一致は W11 が検出する。

---

## 31. Mermaid → Kroki 図解埋め込み（§7「80%」の実装確定）

### 31-1. 方式

- 生成プロンプト（`n8n/prompts/article-base.md`、T-11）で「図解が有効な場合のみ ```mermaid フェンスを最大1つ」を許可。
- `scripts/kroki_embed.py` の `embed_diagrams(html: str) -> tuple[str, int]` が ```mermaid フェンスを
  `<figure class="ai-navi-diagram"><img src="{KROKI_BASE_URL}/mermaid/svg/{base64url(zlib.compress(src))}" alt="図解" loading="lazy"></figure>`
  に置換する。**変換時にネットワークは使わない**（描画は読者ブラウザが Kroki GET を叩く）。stdlib のみ。
- エンコードは Kroki 仕様（deflate → base64url、パディング維持）。URL 長が 4000 を超える図は変換せず `<pre>` にフォールバックし件数に含めない。
- `KROKI_BASE_URL` 既定 `https://kroki.io`（月100記事超で self-host に切替、§7 備考）。
- 同一プロセス（§28 サービス）の `POST /embed-diagrams` として公開するが、モジュールは分離し **verdict に一切関与しない**。
- パイプライン順序: WP整形 → **図解埋め込み** → Auditor Gate → WP投稿。Auditor は埋め込み後の最終 HTML を審査する。

### 31-2. 未確定・制約

- n8n Code ノードで `zlib` が使えるか未検証のため、変換は n8n 側ではなくサービス側で行う（§28 と同じ到達性前提）。
- WordPress.com が `<img src="https://kroki.io/...">` を外部画像として表示できることは T-11 の手動実行で確認する（現時点で未確認）。
- ワークフロー JSON への配線（T-11）は CLAUDE.md §F により**操作者の n8n 手動実行→WP下書き確認後にのみ push**。
  T-10 完了時点では `/embed-diagrams` は本番パスから未消費（ROADMAP に明記、T-11 で解消）。

### 31-3. テスト（T-10）

`tests/test_kroki_embed.py` — フェンス1つ→`<figure>`1つ / フェンスなし→無変更 / エンコード結果が `zlib.decompress(base64.urlsafe_b64decode())` で原文に戻る /
4000 超は `<pre>` フォールバック / `/embed-diagrams` 経由で同じ結果。

---

## 32. Auditor 自己改善ループ — 仕様⇄実装の整合（2026-09-12 自己適用で検出）

> ハーネス原則「ラチェット」「Worker-Evaluator 分離」を Auditor 自身に適用する。
> 変更は必ず **評価セット先行**（§22-2: 期待 verdict をラベル付けした事例を先に追加し、
> FP=0/FN=0 を保ったまま実装）で行う。LLM は使わない（INV-R2）。

### 32-1. 検出したドリフト（コードで確認）

| # | 項目 | 仕様側 | 実装側（`scripts/content_audit.py`） | 決定 |
|---|---|---|---|---|
| D1 | 引用比率閾値 | §17-1「生成/引用 > 2.0」(引用 ≤ 1/3) / `n8n/skills/skill-base.md` L49「≤ 30%」/ §22-1「> 40%」 | **実装済み（2026-09-13, T-24）**: `QUOTE_DOMINANCE_RATIO = 0.34` | eval に「35% → FAIL」「30% → PASS」を追加してから 0.34 に変更。skill-base と §22-1 の数値は §17-1 参照に統一 |
| D2 | 丸写し検出 `VERBATIM_COPY`（`20-auditor-gate.md` PLAN の ⑤ 行を由来とするが、内容は「blockquote **外**の本文が原文と ≥ 0.85 で一致」の検出） | `20-auditor-gate.md` PLAN | **実装済み（2026-09-15, T-24 第2ラウンド `9539897` / PR #13）**: `scripts/content_audit.py` の D2 ブロックが blockquote を除いた本文を 200 字窓（step 100）で走査し `WARN:VERBATIM_COPY:<ratio>` を出す。第1ラウンド（`5012356`）は blockquote **内**照合（= D7）を本ラベルで出していたため差し戻し、D7 として改名して存置 | 定義: 原文との `find_longest_match ≥ 120` 字、または原文の任意の 200 字窓との `SequenceMatcher.ratio() ≥ 0.85`（`SIMILARITY_THRESHOLD`）で 1 監査につき最大 1 件。`source_text` 無し、または `source_lang` が `ja`/未指定以外はスキップ。verdict は変えない（§32-2）。`tests/test_content_audit.py` が正しい向きで検証（2026-09-17 再確認: unittest 46 OK、eval 52 FP=0/FN=0） |
| D3 | 翻訳ラベル（§17-3 `MISSING_TRANSLATION_LABEL`） | `20-auditor-gate.md` PLAN | **実装済み（2026-09-13, T-24）**: `/audit` の任意 `source_lang: ja|en|zh` | `en|zh` で「本記事は」∧「翻訳」∧ source_url 本文内出現 が揃わなければ verdict は変えず `reasons` 末尾に `WARN:MISSING_TRANSLATION_LABEL` を追加。WF08 ゲートが `source_lang:'zh'` を送る改修は T-11（WF JSON 変更） |
| D4 | `INSUFFICIENT_LENGTH`（JA 2000字未満） | `20-auditor-gate.md` PLAN | 未実装 | **採用しない**（§22-1 の FAIL 一覧に無く、WF04 Threads まとめ等の短文フォーマットと衝突）。skill 文書から削除 |
| D5 | `ALREADY_REJECTED`（同一ハッシュ再提出） | `20-auditor-gate.md` PLAN | **実装済み（2026-09-13, T-24）**: §28 サービスが facts の `content_hash` を照合 | 再提出時も verdict は再計算し（固定 FAIL にはしない）、一致する既存行があれば `reasons` 末尾に `WARN:ALREADY_REJECTED:<fact_id>` を追加し facts に重複行を書かない。第1ラウンドは `verdict = 'FAIL'` 行のみ照合し UNVERIFIABLE の再提出が重複行になっていた（Linux 実測: 同一内容 2 回投稿で facts 3 行 / 2 ハッシュ）→ **第2ラウンド（`9539897`）で解消**: `auditor_server.py` `find_prior_fact()` が `verdict != 'PASS'` で照合し、`tests/test_auditor_server.py` が UNVERIFIABLE 2 回投稿で facts 1 行のままを検証 |
| D6 | 実装場所 | `20-auditor-gate.md` BUILD「`src/claim_auditor/` 配下」 | 本リポジトリに存在しない | 文書を `scripts/content_audit.py` + `scripts/auditor_server.py` に訂正（本節と同コミット） |
| D7 | ⑤改変禁止の本来の意味（blockquote **内**テキストが原文と ≥ 0.85 で一致していること） | §17-1 表 | **実装済み（2026-09-15, T-24 第2ラウンド `9539897`）**: 第1ラウンドが `VERBATIM_COPY` の名で実装した blockquote 内照合を `scripts/content_audit.py` の D7 ブロックとして `WARN:QUOTE_ALTERED:<ratio>` にリネーム（`source_text` あり ∧ `source_lang` が `ja` または未指定のときのみ、閾値は D2 と共有の `SIMILARITY_THRESHOLD = 0.85`） | 2026-09-13 に D2 から分離。誤検出リスクは §32-2 の WARN 運用（verdict 不変・30日観察）で吸収し、FAIL 昇格は観察後に判断する |
| D8 | `claims: list[string]`（`20-auditor-gate.md` inputs / `skill-base.md` L73）と PLAN の「claims が空 → WARN:NO_CLAIMS」「UNVERIFIABLE claims > 50% → UNVERIFIABLE」 | `20-auditor-gate.md` / `skill-base.md` | **サーバ側実装済み（T-34, `181b607`）**: `/audit` は `evidence` を受理し §34-5 の決定論ルールを適用する。配線（n8n ワークフローが実際に `evidence`/`source_text` を送る）は T-35/T-36 で未了 | `claims` は廃止し §34-4 の `evidence` に置換（T-33 で文書、T-34 で実装、T-35/T-36 で配線）。`source_text`/`source_lang` の送信も T-35/T-36 で配線し D2/D7 を本番有効化 |
| D9 | §32-2「WARN を30日観察してから FAIL 昇格」 | §32-2 | **実装済み（T-34, `8615bf9`/`181b607`）**: `warnings` テーブル（`scripts/memory_init.py`）+ `scripts/ratchet_check.py --warn` で verdict を問わず全 `WARN:` を集計できる | §34-6 の `warnings` テーブルに verdict を問わず全 `WARN:` を記録し、`ratchet_check.py --warn` で集計（T-34）。D2/D3/D7 の観察もこれに乗る |
| D10 | ワークフロー JSON の生成手段 / Code ノードの `$env` | `scripts/patch_workflows.py`（2026-07-10 の一回限りパッチ）/ 全 Code ノードの `$env.*` 参照 | **再実行禁止**: `patch_workflows.py` はゲートノードを二重追加し `AINAVI_GATE_MODE`・`category_id` を持たない旧コードで上書きする（W7/W11 退行）。n8n 2.x は既定で Code ノードの `$env` を遮断（`N8N_BLOCK_ENV_ACCESS_IN_NODE=true`）し、参照は例外になる。n8n Cloud の Code ノードは `crypto`/`moment` のみ import 可、公式には HTTP 不可（既存ノードの `fetch` は未検証の前提） | T-35a: `patch_workflows.py` に実行ガード、新規 `scripts/patch_evidence_pack.py`（冪等）を正とする。全 Code ノードは `cfg()`（`$vars` → `$env`、各 try/catch）で設定を読む。T-13 で `$vars` 可読性・Code ノード `fetch`・`require('crypto')` の3点を実測し §28-3 に記録 |

### 32-2. ループの運用

```
自己適用（コードで裏取り） → ドリフト表に追記 → 評価セットに期待事例を追加（先）
   → 実装（Codex） → run_eval FP=0/FN=0 → unittest → 文書の「未実装」表記を解除
```

- 新しいチェックは **report_only の本番 verdict を30日観察してから** `FAIL` 判定に昇格させる（§22-3 と同じ段階的ロールアウト）。
  それまでは `reasons` に `WARN:` 接頭辞で記録し verdict に影響させない。
- 本節の表は「未実装」が残っている限り削除しない（ラチェット）。

---

## 33. ローカルゲートの可搬性（Windows cp932 環境・2026-09-13 実例）

### 33-1. 検出した事実（コードで確認）

- `scripts/check_wired.py`（3箇所）/ `run_eval.py`（1）/ `patch_workflows.py`（14）/ `build_eval_set.py`（1）/ `build_wf09.py`（1）の
  `Path.read_text()` / `write_text()` が `encoding` 未指定（計20箇所、AST 走査で確認）→ Windows（cp932）で `UnicodeDecodeError`。
  `write_text` は例外を出さずに cp932 の JSON を書き、n8n 側で日本語ノード名が壊れる（読み込みより発見が遅い）。
- `.githooks/pre-push` は `python3` を呼ぶが、操作者の Windows では Store スタブに解決し、フックは実質未実行だった
  （PR #9 本文にも「`python3` は Store スタブ」と記載）。
- これまでの「done」証拠は全て Linux（クラウドセッション）で取得されており、§D ゲートが操作者環境で動くことは未検証だった。

### 33-2. 規約

1. `scripts/` 配下のテキスト I/O は `encoding="utf-8"` を必ず明示する（バイナリモードは除外）。
2. `tests/test_encoding_guard.py` が `ast` で全 `scripts/*.py` を走査し、未指定の呼び出しを FAIL にする（センサー）。
3. `.githooks/pre-push` は `python3` が使えない場合 `py -3` にフォールバックする。
4. 「ゲート green」の報告には **操作者環境（Windows）での実行結果**を1回は含める（T-25 の完了条件）。

---

## 34. Evidence Pack — ファクトチェック層（ハルシネーション・矛盾・手法妥当性）

> 背景: Auditor Gate（§22, §28）は著作権・構造・誇大表現のみを検査し、「ソースに無い主張」「ソースと矛盾する主張」
> 「実際には使えない手法の記述」を検出する経路が無かった（§5-2 の表は設計のみ）。本節はこれを、INV-R2 を保ったまま
> 実装する設計を確定する。設計判断: 2026-09-17（Claude Fable 5.1 による設計・Claude Sonnet 5 による実装・操作者承認）。

### 34-1. 検出した事実（コードで確認・2026-09-17）

1. `scripts/auditor_server.py` `audit()` は `content` / `source_urls` / `skill_ref` / `source_text` / `source_lang` のみ読む。`claims` は無視（§32-1 D8）。
2. WF01〜09 の全ゲートノードは `{content, source_urls, skill_ref}` のみ送信。`source_text` 未送信のため D2/D7 は本番で休眠。
3. `20-auditor-gate.md` PLAN は既に「UNVERIFIABLE claims > 50% → UNVERIFIABLE」という**決定論的な集計規則**を規定しており、本節はその具体化である。
4. WF07 は topic / angle / keywords のみで生成し、ソースが存在しない。根拠照合は原理的に不可能（§34-11）。
5. WF01 / WF09 はスター数・URL・説明文などの構造化実測値をパイプライン内に持つ（`stargazers_count`, `items[]`）。
6. verdict=PASS は facts に書かれない（§28-2）ため、WARN の30日観察（§32-2）に記録が無い（§32-1 D9）。
7. `scripts/run_eval.py` は `audit(content, source_urls)` の2引数呼び出しで、`source_text` / `evidence` を渡せない。
8. n8n の Code ノードは credential を参照できないため、検証 LLM 呼び出しは既存の `Claude API Key` credential を持つ HTTP Request ノードで行う（記事生成ノードと同じ方式）。

### 34-2. 不変条件の明確化

- **INV-R2（確認）**: verdict（PASS / FAIL / UNVERIFIABLE）を決めるのは `scripts/content_audit.py` の決定論的ロジックのみ。LLM は verdict を決めない。LLM はパイプラインの BUILD 段階で**証拠（signals）**を生成してよく、決定論的ルールがそれを verdict に変換する。
- **INV-R2a（新設）**: Evidence Pack は verdict を**下げる方向にしか**作用しない。evidence の有無・内容によって FAIL / UNVERIFIABLE が PASS になることはない。evidence が欠落しても既存ルールの verdict は変わらない。LLM の「SUPPORTED」は何も緩和しない。
- **完全性の否認**: 本層はハルシネーション・不正確さを完全には防げない（操作者了承済み・2026-09-17）。検出できる範囲は §34-11 に明記する。

### 34-3. アーキテクチャ（3層 Evidence + 決定論ルール）

フェーズ配置: skill-base の順序は不変。Evidence Pack 生成は **BUILD の最終ステップ**（中間成果物）、消費は REVIEW（Auditor Gate）。

```
[生成 LLM] → [WordPress投稿データ整形]
   → [Evidence Probes (Code)]                       … Tier 1: URL / GitHub 実在確認（LLM-free）
   → [Fact-Check Verifier (HTTP Request → Claude)]  … Tier 2: claude-haiku-4-5、構造化出力
   → [Evidence Pack 整形 (Code)]                     … Tier 0 実測値 + Tier 1 + Tier 2 を §34-4 の形に
   → [Auditor Gate (Code)]  body に source_text / source_lang / evidence を追加
   → [WordPress]
```

| Tier | 生成主体 | 内容 | LLM |
|---|---|---|---|
| 0 | パイプライン既存データ | `source_text`（`[S0]`〜`[Sn]` 索引付き連結ソース）、`ground_truth`（WF01/09 のスター数等） | 無 |
| 1 | Code ノード（probes） | 記事中 URL の HEAD/GET、`github.com/<owner>/<repo>` の API 実在確認 | 無 |
| 2 | HTTP Request ノード | 主張抽出 + 各主張の status + ソースからの**逐語 evidence**。モデルは **`claude-haiku-4-5`**（操作者決定 2026-09-17、理由: コスト、§34-10）。プロンプト `n8n/prompts/50-fact-check.md`、`output_config.format`（json_schema）で JSON を強制。web/fetch ツール無し | 有 |

- Verifier に渡す `source_text` と、ゲートに送る `source_text` は**同一文字列**でなければならない（§34-5 の逐語照合が前提）。
- Verifier ノードは「continue on fail」。失敗時は `evidence.verifier.ok=false` にして送る（ゲートは止めない、§14）。
- スキル: `n8n/skills/15-fact-check.md`。プロンプト: `n8n/prompts/50-fact-check.md`（T-35b で配線するまで `check_wired.py` の LIBRARY_ONLY に理由付きで登録）。

#### WF 別ソース構成（T-36a で確定）

| WF | item ノード | source_text | ground_truth | source_lang | 備考 |
|---|---|---|---|---|---|
| 01 | 上位5件を整形 | GitHub リポジトリ情報（name/description/stars/language/topics/url） | `{name: {stars, forks, language}}` | `null` | 実測値あり |
| 02 | 新記事フィルタリング（重複除外） | `title` + `summary` | `{}` | `link` が note.com なら `'ja'`、それ以外 `'en'` | RSSは英語ソースが主、note経由のみ日本語 |
| 03 | 新動画フィルタリング | `title`/`channelTitle` + `description` + `videoUrl` | `{}` | `null` | API スニペットからは言語判定不可 |
| 04 | AI関連投稿をフィルタリング | `posts[]` を `[S0]`,`[S1]`... で連結 | `{}` | `null` | 投稿は日英混在 |
| 05 | 新記事フィルタリング | `title` + `summary` | `{}` | `'ja'` | note.com（日本語）専用ソース |
| 06 | トレンドデータ集約（`.first()`） | `sections[]`（Perplexity 出力）を `[S0]`,`[S1]`... で連結 | `{}` | `null` | 備考: ソースは Perplexity の生成文であり一次情報ではない（§34-11 item 6） |
| 07 | なし | `''` | `{}` | `null` | ソース無し。`WARN:NO_SOURCE_FOR_FACTCHECK` が常態 |
| 08 | 新ZH記事フィルタリング | `title_zh` + `summary_zh` | `{}` | `'zh'` | ZH原文をそのまま逐語照合に使う |
| 09 | 確度スコア付与 | `items[]`（最大20件）を `[S0]`,`[S1]`... で連結 | GitHub 由来項目（`medium==='github'`）のみ `{title: {stars}}` | `null` | 媒体混在。既存の `source_urls` 配列をゲートがそのまま転送（§34-5 body 拡張） |

### 34-4. `/audit` リクエスト拡張（スキーマ v1）

`claims: list[string]` は廃止。追加フィールドは全て任意。`evidence` が無い場合、`/audit` の挙動は §28-2 と完全に同一（INV-R2a）。

```json
{
  "content": "<article html>", "source_urls": ["..."], "skill_ref": "01-github-trending",
  "source_text": "[S0] ...\n\n[S1] ...", "source_lang": "en",
  "evidence": {
    "version": 1,
    "verifier": {
      "model": "claude-haiku-4-5", "prompt_ref": "50-fact-check.md",
      "prompt_sha256": "<hex64>", "ok": true, "error": null,
      "usage": {"input_tokens": 0, "output_tokens": 0}
    },
    "claims": [
      {"id": "c1", "text": "<記事中の主張（要約可）>",
       "type": "FACT|NUMBER|TECHNIQUE|OPINION",
       "status": "SUPPORTED|CONTRADICTED|NOT_IN_SOURCE|UNCHECKABLE",
       "evidence": "<source_text からの逐語抜粋 10〜300字、または null>",
       "source_index": 0,
       "value": null, "gt_ref": null,
       "feasibility": "PLAUSIBLE|IMPLAUSIBLE|UNKNOWN|null",
       "note": "<1文>"}
    ],
    "probes": [
      {"kind": "URL", "target": "https://...", "result": "OK|DEAD|TIMEOUT|SKIPPED", "detail": "404"},
      {"kind": "GITHUB_REPO", "target": "owner/repo", "result": "OK|NOT_FOUND|TIMEOUT|SKIPPED", "detail": {"stars": 1234}}
    ],
    "ground_truth": {"owner/repo": {"stars": 1234, "language": "Python"}}
  }
}
```

フィールド規則:
- `claims[].type=NUMBER` は `value`（数値）必須。`ground_truth` に対応値があれば `gt_ref="<key>.<field>"`。
- `claims[].type=TECHNIQUE` は `feasibility` 必須。他の type は `null`。
- `claims[].type=OPINION` は `status=UNCHECKABLE` 固定。
- `probes[].result`: `DEAD` は URL の HTTP 404/410 のみ。403/429/5xx/接続失敗は `TIMEOUT`。`NOT_FOUND` は GitHub API の 404 のみ。
- `verifier.prompt_sha256` は `50-fact-check.md` の UTF-8 バイト列の SHA-256（プロンプト版別に観察統計を分けるため）。
- Verifier（Tier 2）の JSON 出力は `{"claims": [...]}` のみ。`verifier` / `probes` / `ground_truth` は Evidence Pack 整形ノードが付与する。

レスポンス追加（`evidence` がある場合のみ。既存キー `title/content/wp_status/source_url` と衝突しない、§28-2）:

```json
"evidence_summary": {"claims": 0, "considered": 0, "supported": 0, "contradicted": 0,
                     "ungrounded": 0, "evidence_missing": 0, "implausible": 0,
                     "probes_failed": 0, "dropped": 0}
```

### 34-5. 決定論ルールと理由コード（`scripts/content_audit.py`、初期は全て `WARN:`）

定数（`content_audit.py`）: `EVIDENCE_MIN_CHARS = 10`, `EVIDENCE_MAX_CHARS = 300`, `MAX_CLAIMS = 40`, `MIN_CLAIMS_FOR_RATIO = 3`, `UNGROUNDED_RATIO = 0.5`, `NUMBER_TOLERANCE = 0.05`, `MAX_PROBE_WARNINGS = 5`。逐語照合の閾値は既存 `SIMILARITY_THRESHOLD = 0.85` を共有。

処理順（決定論・この順で `reasons` 末尾に追加）:

0. `evidence` 無し → 何もしない。`evidence` が dict でない / `version != 1` / `claims` が list でない → `WARN:FACTCHECK_UNAVAILABLE:schema` を出して終了。`verifier.ok` が真でない → `WARN:FACTCHECK_UNAVAILABLE:<error 先頭40字>` を出し、claims 規則（2〜7）を飛ばす（8〜9 は実行）。
1. claims を先頭 `MAX_CLAIMS` 件に切り、各要素を検証（必須キー・enum）。不正な要素は捨てて `dropped` に数える。
2. **逐語照合（中核規則）**: `status ∈ {SUPPORTED, CONTRADICTED}` の各 claim について、`normalize(evidence)` が `normalize(source_text)` の部分文字列であれば「検証済み」。部分文字列でなければ D7 と同じ窓走査（窓長 = evidence 長、step = 長さ//4）で `SequenceMatcher.ratio() ≥ SIMILARITY_THRESHOLD` なら「検証済み」。それ以外（`evidence` が null / 長さ範囲外 / `source_text` 無し / 不一致）は `status := EVIDENCE_MISSING`。`normalize` = `unicodedata.normalize("NFKC")` → 空白列を単一スペースに畳む → strip。
3. `type=NUMBER` かつ `gt_ref` あり: `value` の数字列（桁区切り除去）が `_text(content)` に無ければ `EVIDENCE_MISSING`。`ground_truth[key][field]` が数値で `|value − gt| > NUMBER_TOLERANCE × max(|gt|, 1)` → `WARN:NUMBER_MISMATCH:<value>/<gt>`。
4. 母数 `N` = `type ∈ {FACT, NUMBER, TECHNIQUE}` の件数（**OPINION は除外**—著作権プロンプトが独自分析 ≥50% を要求するため）。`ungrounded` = `NOT_IN_SOURCE + EVIDENCE_MISSING`。`N ≥ MIN_CLAIMS_FOR_RATIO` かつ `ungrounded / N > UNGROUNDED_RATIO` → `WARN:CLAIM_UNGROUNDED:<ungrounded>/<N>`。
5. 検証済み `CONTRADICTED` が `c ≥ 1` → `WARN:CLAIM_CONTRADICTED:<c>`。
6. `type=TECHNIQUE` かつ `feasibility=IMPLAUSIBLE` が `t ≥ 1` → `WARN:TECHNIQUE_IMPLAUSIBLE:<t>`。
7. `EVIDENCE_MISSING` が `m ≥ 1` → `WARN:EVIDENCE_NOT_IN_SOURCE:<m>`。
8. probes: `URL` の `DEAD` → `WARN:URL_DEAD:<url 先頭80字>`（最大 `MAX_PROBE_WARNINGS` 件）、`GITHUB_REPO` の `NOT_FOUND` → `WARN:REPO_NOT_FOUND:<owner/repo>`。
9. `source_text` 無し かつ `ground_truth` 空 かつ `evidence` あり → `WARN:NO_SOURCE_FOR_FACTCHECK`。

理由コード表と昇格条件（昇格は 1 コード = 1 PR、§32-2 どおり評価セット先行、INV-R1 の人間署名を §34-9 に記録）:

| コード | 発生条件 | 昇格先 | 昇格条件（T-37 の観察結果） |
|---|---|---|---|
| `WARN:URL_DEAD` | Tier 1 | FAIL | 人手ラベル精度 ≥ 0.95、標本 ≥ 10 |
| `WARN:REPO_NOT_FOUND` | Tier 1 | FAIL | 同上 |
| `WARN:NUMBER_MISMATCH` | Tier 0 照合 | FAIL | 同上 |
| `WARN:CLAIM_CONTRADICTED` | Tier 2 + 逐語検証済み | FAIL | 精度 ≥ 0.90、標本 ≥ 20 |
| `WARN:CLAIM_UNGROUNDED` | 比率規則 | UNVERIFIABLE | 精度 ≥ 0.80、標本 ≥ 20（`UNGROUNDED_RATIO` の調整可） |
| `WARN:TECHNIQUE_IMPLAUSIBLE` | Tier 2 | 当面 WARN のまま | 同一 target に `REPO_NOT_FOUND`/`URL_DEAD` が併発する場合の連動昇格は別途判断 |
| `WARN:EVIDENCE_NOT_IN_SOURCE` | 逐語照合失敗 | 昇格しない | Verifier / プロンプト改善の指標 |
| `WARN:NO_SOURCE_FOR_FACTCHECK` | ソース無し | 昇格しない | 情報のみ（WF07 は常時） |
| `WARN:FACTCHECK_UNAVAILABLE` | Verifier 失敗・不正 | 昇格しない | 7日率 > 20% で運用アラート（手動） |

標本が閾値未満のコードは観察を延長する（昇格しない）。

### 34-6. 観察用永続化（`warnings` テーブル）と観察レポート

`scripts/memory_init.py` の SCHEMA に追加（`ensure_schema` は `CREATE TABLE IF NOT EXISTS` で冪等）:

```sql
CREATE TABLE IF NOT EXISTS warnings (
    id INTEGER PRIMARY KEY,
    content_hash TEXT NOT NULL,
    skill_ref TEXT DEFAULT '',
    verdict TEXT NOT NULL,
    code TEXT NOT NULL,
    detail TEXT DEFAULT '',
    prompt_sha256 TEXT DEFAULT '',
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_warnings_skill ON warnings (skill_ref, code, created_at);
```

- `auditor_server.py` は verdict を問わず、`reasons` 中の各 `WARN:` について 1 行書く。`code` = 先頭2要素（`WARN:CLAIM_CONTRADICTED:3` → `WARN:CLAIM_CONTRADICTED`、§28-2 の fail_reason と同じ規則）、`detail` = 残り。`facts` の挙動（PASS は書かない、D5 の重複抑止）は不変。書込み失敗はログのみ（§14）。
- `scripts/ratchet_check.py --warn`: 直近30日の `warnings` を `(skill_ref, code)` で集計し、`COUNT(*)`, `COUNT(DISTINCT content_hash)`, `MAX(created_at)`, 上位3件の `detail` を Markdown で出力。常に exit 0（Report-Only、§23 R0 と同じ）。T-37 の週次レポートに用いる。

### 34-7. テスト方針（CI はオフラインのまま）

- `data/eval_set.json` の各 case に任意キー `source_text`, `source_lang`, `evidence`, `expected_warnings`（必ず含まれるべき code の配列）, `forbidden_warnings`（含まれてはならない code）を追加できる。`run_eval.py` はこれらを `audit()` に渡し、FP/FN（verdict 基準、定義不変）に加えて warnings の期待不一致も RED にする。
- T-34 で追加する最小 case（id `E01`〜`E16`）: E01 evidence 無し→既存と同一 / E02 SUPPORTED+実在 span→WARN 無し / E03 SUPPORTED+捏造 span→`EVIDENCE_NOT_IN_SOURCE` / E04 CONTRADICTED 検証済み→`CLAIM_CONTRADICTED` / E05 CONTRADICTED 未検証→`EVIDENCE_NOT_IN_SOURCE` のみ / E06 ungrounded 比率超→`CLAIM_UNGROUNDED` / E07 全て OPINION→WARN 無し / E08 NUMBER 不一致 / E09 NUMBER 許容内 / E10 URL DEAD / E11 REPO NOT_FOUND / E12 `ok=false`→`FACTCHECK_UNAVAILABLE` / E13 schema 不正 / E14 ソース無し→`NO_SOURCE_FOR_FACTCHECK` / E15 単調性: `FAIL:HYPE` 記事 + 全 SUPPORTED → verdict FAIL のまま / E16 英語ソースの逐語照合。
- 単体テスト（`tests/`）: 上記と同内容 + `warnings` 書込み/読出し + `ratchet_check --warn`。Verifier の精度そのもの（LLM 込み）は CI に入れない。T-37 で人手ラベルにより測る（§34-9 に記録）。

### 34-8. 配線ゲート（W12）と LIBRARY_ONLY

- **W12（T-35a で追加、対象レジストリ `EVIDENCE_REQUIRED_WORKFLOWS` は空で開始、T-35b で `01-`、T-36 で全件）**: レジストリ内の各ワークフローについて (a) 本文に `50-fact-check.md` が含まれ、`claude-haiku-4-5` と `output_config` を含むノードが存在、(b) `EVIDENCE_PROBES` マーカーを含む Code ノードが存在、(c) `AINAVI_GATE_URL` を含むゲートノードの jsCode に `source_text` と `evidence` が含まれる。いずれか欠落で FAIL。レジストリ外は「not required yet」として PASS 表示。
- T-35b より前は `50-fact-check.md` を `LIBRARY_ONLY_PROMPTS` に理由付きで登録（§21）。T-35b で登録を外す。
- 新しい理由コードは `fail_reason` の先頭2要素規則により、FAIL 昇格後は自動的に §23 のラチェット集計に乗る。

### 34-9. 段階的ロールアウト（ROADMAP Phase D2、T-33〜T-38）

| 段階 | タスク | 内容 | 完了条件 |
|---|---|---|---|
| P0 | T-33 | 本節・§32-1 D8/D9・ROADMAP・スキル 15/20/10/skill-base・プロンプト 50（LIBRARY_ONLY） | 単独 docs コミット + prompts コミット、§D ゲート green（Windows） |
| P1 | T-34 | `content_audit.py` 規則、`auditor_server.py` 透過 + `warnings`、`memory_init.py`、`run_eval.py` 拡張 + E01〜E16、単体テスト、`ratchet_check --warn`、Fly 再デプロイ | eval FP=0/FN=0 + warnings 不一致 0、unittest OK、既存 52 case の verdict 不変、`/health` ok → **done 2026-09-17**（eval 68 cases FP=0/FN=0 warning-mismatches=0、unittest 87 OK、52件の既存 verdict 不変を確認済み） |
| P2a | T-35a | 冪等パッチャ `scripts/patch_evidence_pack.py`（WF01 設定）、W12（空レジストリ）、生成 JS の node 実行テスト、`patch_workflows.py` 実行ガード。**workflow JSON は変更しない** | unittest に patcher 冪等性 + JS ハーネスが入り green |
| P2b | T-35b | **T-13 後**: パッチャで WF01 JSON 生成 → n8n cloud へ再取込 → 操作者の手動実行 → 実行ログに Evidence Pack 出力と `evidence_summary`、WP 下書き → JSON コミット、`EVIDENCE_REQUIRED_WORKFLOWS` に `01-`、`50-fact-check.md` の LIBRARY_ONLY 解除、§28-3 に T-13 実測3点 | W12 PASS（対象1）、W5 が LIBRARY_ONLY 無しで PASS、手動実行ログ貼付 |
| P3a | T-36a | パッチャ設定 WF02〜09 + 各 WF の patcher/JS テスト（JSON 変更なし） | unittest が9 WF分パラメータ化され green |
| P3b | T-36b | T-35b と同じ操作者手順を WF02〜09 に適用、`EVIDENCE_REQUIRED_WORKFLOWS` を全件に（WF07 は `NO_SOURCE_FOR_FACTCHECK` が常態） | 9/9 W12 PASS、手動実行ログ |
| P4 | T-37 | 30日観察: 週次 `ratchet_check.py --warn`、コード別に標本を人手ラベル、精度を下表に記録 | 下表が埋まり署名 |
| P5 | T-38 | §34-5 の条件を満たしたコードから 1 コード 1 PR で昇格（評価セット先行） | 各 PR の eval/unittest green + 署名 |

Fly 再デプロイ: **完了 2026-09-17** — `GET https://ainavi-auditor-gate.fly.dev/health` →
`{"status":"ok","service":"ainavi-auditor-gate","memory_db":true,"auth":true}`（`warnings` テーブルが volume 上の DB に追加された）

観察結果（T-37 で記入）:

| コード | 期間 | 標本 | 精度 | 判断 | 署名 |
|---|---|---|---|---|---|
| （T-37 で記入） | | | | | |

### 34-10. コスト（決定: `claude-haiku-4-5`）

- 操作者決定（2026-09-17）: Verifier は **Claude Haiku 4.5（`claude-haiku-4-5`）**。理由はコスト。Sonnet 5 / Opus 5 は不採用。
- 単価（2026-06-24 時点の一次料金表）: 入力 $1 / 出力 $5 per MTok。1記事あたり推定 入力 ~10k tokens（記事 3〜4k + ソース 3〜6k + プロンプト ~1.5k）/ 出力 ~1.5k → **約 $0.02/記事**。月300記事で約 $6、月1,000記事で約 $20。Tier 0/1 は無料。
- Verifier ノードは `thinking` を指定しない（Haiku 4.5 は `budget_tokens` 方式で本用途に不要）。`max_tokens: 4096`。
- **再判断トリガー（発生したら実装前に操作者へ確認）**: (a) T-37 で `CLAIM_CONTRADICTED` の精度 < 0.8 でモデル変更が対策候補になる、(b) 月間記事数 > 1,000、(c) LLM 呼び出しの追加（2段階抽出・再検証など）、(d) Batch API / prompt caching への切替。

### 34-11. 既知の限界（明記）

1. WF07 はソースが無く、根拠照合・矛盾検出は不可能。手法妥当性（`TECHNIQUE_IMPLAUSIBLE`）と既存 `UNSOURCED_STATS` のみ。
2. 同一ベンダーのモデルが検証するため、ソースが無い一般知識の誤りは共有され得る。
3. ソース（RSS/Reddit/HN/note）は攻撃者が書ける。対策は逐語照合・INV-R2a・構造化出力・データ区切り指示・ツール無し。注入が成功した場合の最悪は「今日と同じ verdict」または「保留」であり、公開方向には作用しない。
4. probes はサイト側の bot 対策で `TIMEOUT` になり得る。`DEAD` は 404/410 のみ。
5. 逐語 evidence はソース言語（EN/ZH）のまま。`source_lang` による D2/D7 のスキップ条件は本節の照合には適用しない。
6. WF06 のソースは Perplexity の生成文であり一次情報ではない。同 WF の照合は「Perplexity 出力との整合」にとどまる。

---

## 35. サイトアーキテクチャ（3サイロ + 信頼ページ）と収益層

> 背景: 外部記事「AIアフィリエイトで稼ぐ完全ガイド」（blogai.jp, 2026-03-16）を参照し、本サイトの構成を確定する。
> 同記事の数値（成功率・市場規模など）は出典がなく UNVERIFIABLE なので採用しない。採用するのは構造と失敗パターンのみ。
> 設計判断: 2026-09-24（操作者承認）。セッションメモ: `docs/sessions/2026-09-24-affiliate-structure-proposal.md`。

### 35-1. 検出した事実（コードで確認・2026-09-24）

| 事実 | 根拠 |
|---|---|
| カテゴリ9件はすべて親なしのフラット構造で、トレンド系だけで構成されている | `data/wp-taxonomy.json` |
| 起動間隔は WF02=30分、WF03/05=1時間、WF04=3時間、WF08=6時間。公開本数の上限はない | 各 WF の `scheduleTrigger` |
| Auditor Gate の既定は `report_only` で、全件下書き | 各 WF の Auditor Gate jsCode `decide()` |
| 収益リンク・PR表記を検査する規則がない | `scripts/content_audit.py`（HYPE / 引用 / 構造 / 統計のみ） |
| 収益化の旧設計は削除済み | 旧 §16（commit `5caa493`）と disclosure gate（commit `4be8c51`）。§27 のマージで削除 |
| 本番の WordPress.com プランは記録がない | §24。プラグイン（§12 の ACF / Rank Math）を使えるか不明 |

### 35-2. 操作者の決定（2026-09-24）

| 項目 | 決定 |
|---|---|
| サイト構造 | ① ニュース（フロー）／② ツール（ストック）／③ 選び方（収益）の3サイロ＋信頼ページ |
| ③ 選び方サイロ | **作る**。公開には人間の署名が必須（INV-R1）。§27 で削除した比較カテゴリを、この条件付きで復活させる |
| ① ニュースの自動公開上限 | **1日3本**。超えた分は下書きに残す |
| カテゴリ | 親子の2階層に再編する（親: `news` / `tools` / `compare`）。既存の wp_id は変えない |
| WordPress.com プラン | 不明。**プラグインに依存しない方式**で設計し、プランが確定したら ACF 方式への切替を別タスクで判断する |

### 35-3. サイト構造

```
aiguide.blog/
├─ トップ …… 初心者導線（§2-2）＋3サイロへの入口
├─ ① news（AIニュース）     子: ai-official-news(WF02) github-trending(WF01) youtube-summary(WF03)
│                            sns-pickup(WF04) note-creator(WF05) overseas-ai(WF08) weekly-trend-report(WF06)
├─ ② tools（AIツール）      子: howto-guide(WF07) deep-dive(WF09) ＋ ツール詳細の固定ページ /tools/{tool}/
├─ ③ compare（選び方・比較） 比較・ランキング記事（人間の署名のみで公開）
└─ 信頼ページ（固定ページ）  運営者情報 / 編集方針（Auditor Gate の説明）/ 広告・PRポリシー /
                             Claim Platform 紹介 / プライバシー / お問い合わせ
```

- `data/wp-taxonomy.json` の各カテゴリに、任意の `parent`（親の slug）を持たせる。親カテゴリは `source_workflow` を持たない。
  - 階層の妥当性は `scripts/check_wired.py` の W13 で検証する（親が存在する／2階層まで／WF カテゴリは必ずいずれかのサイロに属する）。
- `scripts/wp-init.sh` は2段階で処理する。まず全カテゴリを作成し、次に `parent` に従って親を割り当てる（既存カテゴリも親を付け直す・冪等）。
- ツールDBは `data/tools.json` を唯一の正とし、固定ページの HTML を生成する（プラグイン非依存）。
  - 料金の各行には `source_url` と `retrieved_at` を必須にする。

### 35-4. 内部リンク規則

| # | 規則 |
|---|---|
| R1 | ニュース記事は、タグ経由で1つ以上のツール詳細ページへリンクする（例: タグ `claude` → `/tools/claude/`） |
| R2 | ツール詳細ページは、同じタグの最新ニュースを列挙する |
| R3 | ③ 選び方の記事が料金・機能の根拠にするのは、ツール詳細ページ（`data/tools.json`）だけ |

### 35-5. 公開ポリシー（サイロ別）

| サイロ | 生成 | 追加の Auditor 規則 | 公開 |
|---|---|---|---|
| ① news | 全自動 | — | PASS なら段階的に自動公開。**1日3本まで**（T-44 / T-45） |
| ② tools | 自動＋鮮度チェック | A4 | PASS なら段階的に自動公開 |
| ③ compare | 自動では下書きのみ | A1〜A5 | **人間の署名のみ**（INV-R1） |

### 35-6. 収益系の Auditor 規則（決定論・LLM 不使用 / INV-R2）

**アフィリエイトリンクの定義**: `<a>` のうち、href のホストが `AFFILIATE_HOSTS`（ASP のリダイレクトホスト一覧。`scripts/content_audit.py` で定義）に含まれるもの、または `rel` に `sponsored` を含むもの。

| # | 条件 | 結果 | 段階 |
|---|---|---|---|
| A1 | アフィリエイトリンクがあるのに、最初の `<h2>` より前の本文に PR 表記（`広告` / `PR` / `プロモーション` / `アフィリエイト`）がない | `FAIL:NO_PR_LABEL` | 即時（法令対応）。対象はアフィリエイトリンクを含む記事だけ |
| A2 | ASP ホストへのリンクの `rel` に `sponsored` がない | `FAIL:AFFILIATE_NOT_SPONSORED` | 即時 |
| A3 | 体験の主張（`使ってみた` / `試してみた` / `実際に使` / `実際に試`）があるのに、`data-ainavi-evidence="hands-on"` の要素がない | `WARN:UNSUPPORTED_EXPERIENCE` | Report-Only。§34-5 の手順で昇格を判断する |
| A4a | 料金表現（`N円` / `¥N` / `$N` / `月額N`）があるのに、リンクも `source_urls` もない | `UNVERIFIABLE:UNSOURCED_PRICE` | 即時 |
| A4b | 料金表現があるのに、取得時点（`YYYY年M月` / `YYYY-MM-DD` / `時点`）がない | `WARN:PRICE_UNDATED` | Report-Only |
| A5 | アフィリエイトリンクを含む | 結果に `requires_human_signature: true` を付ける（verdict は変えない） | 判定はサーバ側で実装。`decide()` がこの値を尊重する配線は T-45（操作者の手動実行後） |

- PR 表記の要否は景品表示法のステマ規制に基づく。適用範囲の法的な確認は、公開前に専門家が行う（本節は法務助言ではない）。
- 評価セット（§22-2）に、A1〜A4 の各規則について PASS と FAIL の両側のケースを追加し、FP=0 / FN=0 を保つ。

### 35-8. ASP 方針（操作者決定・2026-09-24）

- **主軸は A8.net** とする。書籍などは楽天アフィリエイトで補う。各 AI ツールが自社の公式パートナープログラムを持っている場合は、そちらに直接登録してもよい。
- `AFFILIATE_HOSTS`（§35-6）は**利用するASPの一覧ではなく、検出対象の一覧**である。
  - 採用していない国内主要ASPのホストも検出対象に残す。未採用のASPリンクが紛れ込んだときに、PR表記の欠落（A1）を見逃さないためである。
- 公式パートナープログラムのリンクは、ホスト名が一定でない。そのため `rel="sponsored"` の付与で検出する（§35-6 のアフィリエイトリンク定義の後半）。

### 35-9. 1日の公開枠サービス（T-44）

ニュースサイロの自動公開を1日3本までに抑える仕組み（§35-5）を、Auditor Gate サービス（§28）に `POST /publish-slot` として実装する。枠の判定は決定論的に行い、LLM は使わない。

| 項目 | 仕様 |
|---|---|
| リクエスト | `{"silo": "news" / "tools" / "compare", "content_hash": "<sha256 hex>"}` |
| レスポンス | `200 {"granted": bool, "silo", "day", "used", "limit", "reason"}` |
| 日付の区切り | **JST（UTC+9 固定）**の暦日。`day` は `YYYY-MM-DD` |
| `news` | その日の付与済み件数が上限未満なら付与し、記録する。上限に達したら `granted:false, reason:"daily_limit_reached"` |
| 同じ記事の再要求 | 同じ日・同じ `content_hash` で再要求された場合は、枠を追加消費せずに `granted:true` を返す（再実行しても冪等） |
| `tools` | 上限なし。`granted:true` を返し、記録はしない |
| `compare` | 常に `granted:false, reason:"human_signature_required"`（INV-R1。人間の署名なしに自動公開しない） |
| 上限値 | 既定は 3。環境変数 `AINAVI_NEWS_DAILY_LIMIT` で上書きできる（0 なら全件下書き） |
| DB が使えない場合 | **閉じた側に倒す**。`granted:false, reason:"slot_store_unavailable"`（公開は外部に出る操作であり、下書きに留めれば安全なため） |
| 入力が不正な場合 | 400（未知の silo、`content_hash` が64桁の16進でない、JSON が不正） |
| 認証 | `AINAVI_GATE_TOKEN` を設定している場合は Bearer 認証を必須にする（§28-2 と同じ） |
| 記録先 | 記憶層 DB の `publish_slots(day, silo, content_hash, created_at)`。`(day, silo, content_hash)` に一意制約を付ける |
| 並行実行 | サーバのロックと DB の一意制約で、同時要求でも上限を超えないようにする |

- **多言語化後の数え方（2026-09-25 操作者決定、§8-7）**: 上限は**言語ごと**に数える。現行の実装はリクエストにも `publish_slots` の一意制約にも言語を持たないため、T-56 で `lang`（既定 `ja`、省略時は現行と同じ動作）を追加する。
- この段階ではサービス側の実装だけで、ワークフローはまだ呼ばない。
  - `decide()` が PASS かつ `requires_human_signature=false` かつ枠を得られた場合にだけ `publish` にする配線は、T-45（操作者の手動実行後）で行う。

### 35-10. 配線ゲート W14（サービスの POST ルートの配線）

- **検出した事実（2026-09-24）**: `POST /embed-diagrams`（§31）を呼ぶワークフロー JSON は1つもない。§31 では T-11 まで未消費と明記されているが、`check_wired` は機械的に検出していなかった。`POST /publish-slot`（§35-9）も T-45 までは同じ状態になる。
- **W14**: `scripts/auditor_server.py` の `ROUTES` にある POST ルートは、次のどちらかを満たすこと。満たさなければ FAIL とする。
  - 1つ以上のワークフロー JSON が、そのパスを参照している
  - `check_wired.py` の `LIBRARY_ONLY_ROUTES` に、理由と配線予定タスクを添えて登録されている
- 登録済みのルートが後で配線された場合も FAIL とする（登録を外し忘れないため）。
- `GET /health` はワークフローではなく Docker / Fly のヘルスチェックが使うので、W14 の対象外とする。

### 35-11. ツールDBとツール詳細ページ（T-46）

プラグインに依存しない方式（§35-2）で、`data/tools.json` を唯一の正とし、WordPress の固定ページを生成する。

**データ（`data/tools.json`）**

| フィールド | 必須 | 制約 |
|---|---|---|
| `slug` | ✓ | `data/wp-taxonomy.json` の tags に存在する slug（R1/R2 のタグ連携のため） |
| `name` / `vendor` / `summary` | ✓ | 空でない文字列。`summary` は日本語で、誇大表現（HYPE）を使わない |
| `official_url` | ✓ | `https://` で始まる |
| `pricing` | ✓（空配列可） | 各行は `plan` / `price` / `source_url`（https）/ `retrieved_at`（`YYYY-MM-DD`）がすべて必須（A4 と §35-4 R3 の根拠） |
| `affiliate` | 任意 | `{"url": https, "program": 文字列}`。ASP の管理画面で発行した実リンクだけを入れる |

- **初期データの方針（Auditor 自己適用）**
  - タグに存在する製品7件（ChatGPT / Claude / Gemini / Midjourney / Stable Diffusion / n8n / Perplexity）を、名前・提供元・公式 URL・中立的な概要だけで登録する。
  - `pricing` と `affiliate` は**空で始める**。取得日と出典を確認できない料金や、発行されていないアフィリエイト ID を書かないため。
  - 操作者（または出典つきの調査）が後から追加する。

**生成（`scripts/tool_pages.py`）**

- 各ツールページの構成
  - 概要
  - 料金：出典リンクと「YYYY-MM-DD 時点」を併記する。空の場合は「未登録」と表示する
  - 公式サイト
  - 関連ニュース：R2。タグアーカイブ `/tag/{slug}/` へのリンク。静的 HTML なので、プラグインなしで実現できる
  - `affiliate` がある場合は、最初の `<h2>` より前に PR 表記を置き、CTA リンクに `rel="sponsored nofollow"` を付ける（A1 / A2）
- 一覧ページ（`/tools/`）を生成する。各ツールページはその子ページにする。

**公開（`scripts/tool_pages.py publish`・操作者が実行）**

- 認証と接続先は `wp-init.sh` と同じ判定にする。`WP_BEARER_TOKEN` + `WP_SITE` があればそれを使い、なければ `WP_URL` + `WP_USERNAME` + `WP_APP_PASSWORD` を使う（§24）。
- **公開前に全ページを `content_audit` にかける。FAIL / UNVERIFIABLE のページは送信しない**（CLAUDE.md §A-5）。
- 常に `status: draft` で送る。人間が確認してから公開する（INV-R1）。
- slug で既存ページを探し、あれば更新、なければ作成する（冪等）。
  - ただし既存ページが公開済みで内容が変わる場合は、**更新せず `[HOLD]` を出す**。署名済みのページを無審査で書き換えないためである。

**ゲート**

- `check_wired` W15 で次を検査する。
  - `data/tools.json` がスキーマを満たす
  - 全ツールの slug がタグに存在する
  - 生成した全ページ（一覧を含む）が `content_audit` で PASS になる

### 35-12. 信頼ページ（T-47）

§35-3 に列挙した6ページを、ツールページ（§35-11）と同じ方式（プラグイン非依存・監査後に下書きのみ送信）で生成する。

**データ（`data/trust_pages.json`）** — ページごとに `status: "ready" | "pending"` を持つ。

| ページ slug | 内容 | 運営者の実データが要るか |
|---|---|---|
| `operator` | 運営者情報 | 要る（名称・連絡方法）。未確定なら `pending` |
| `editorial-policy` | 編集方針（Auditor Gate の説明） | 不要。§21/§22/§28 の仕様から生成できる |
| `ad-policy` | 広告・PRポリシー | 不要。§35-6 A1/A2/A5 の規則から生成できる |
| `claim-platform` | Claim Platform 紹介 | 不要。§5 の一次記述から生成できる |
| `privacy` | プライバシーポリシー | 要る（問い合わせ窓口・保有期間の方針）。未確定なら `pending` |
| `contact` | お問い合わせ | 要る（連絡先チャネル）。未確定なら `pending` |

- **`pending` の扱い（Auditor 自己適用）**: 運営者名・住所・連絡先は要件定義書のどこにも記録がなく、
  ここで作文すると捏造になる。`pending` のページは「運営者情報は確定次第掲載します」という正直な
  保留文だけを出し、**Auditor には掛けるが、公開判定は必ず保留のまま**（`status: "ready"` になるまで
  `tool_pages.py` の `publish` と同様、下書き送信の対象に含めない）。
- **`ready` のページ**は既存仕様（§5/§21/§22/§28/§35-6）から機械的に生成するため、事実の作文は発生しない。
- 生成・監査・公開のコード構造は `scripts/tool_pages.py` を参照実装とし、`scripts/trust_pages.py` として
  新規作成する（ツールDBとはデータ構造が異なるため別スクリプトとするが、`audit_pages()` 相当のロジックは
  共通化を検討してよい）。
- **ゲート（W16）**: `data/trust_pages.json` が §35-3 の6ページ全てを含み、`ready` の各ページが
  `content_audit` で PASS になることを検査する。`pending` のページは監査だけ行い（結果は記録するが）
  FAIL にはしない（未確定という事実そのものは誤りではないため）。

### 35-13. 内部リンク規則の実装（T-50）

**検出した事実（2026-09-24）**
- プロンプトは実行時に GitHub API で既定ブランチから取得される（各 WF の「プロンプト読込み」ノード）。
- `n8n/prompts/article-base.md` を読むのは WF07 のみで、ニュース系（WF01〜06・08）は読まない。
  したがって R1 を LLM への指示だけで実現すると、ニュース記事には効かず、効いても確実ではない。

**方針**: R1 は **LLM に頼らずコードで決定論的に挿入**し、漏れは Auditor が WARN で検出する（INV-R2 と同じ考え方）。

| 規則 | 実装 |
|---|---|
| R1 | `scripts/tool_links.py` の `link_tools()` が、記事中で `data/tools.json` のツール名が**最初に出現した箇所**に `/tools/{slug}/` へのリンクを挿入する。挿入しない場所: 既存の `<a>` の中、見出し（`h1`〜`h6`）、`<blockquote>`（引用の改変禁止、§17 ⑤）、`<code>`/`<pre>`。英字のツール名は前後が英数字でないときだけ一致させる（「n8n」が別語の一部に誤一致しないため） |
| R1 の監査 | `content_audit` に任意引数 `tools` を追加。ツール名が本文にあるのに `/tools/{slug}/` へのリンクがなければ `WARN:MISSING_TOOL_LINK:{slug}`（Report-Only。verdict は変えない） |
| R2 | 実装済み（§35-11、ツールページからタグアーカイブへのリンク） |
| R3 | 比較サイロのワークフロー（T-48）で実装する。本タスクでは扱わない |

- サービスには `POST /link-tools {content}` → `{content, links: [slug...]}` を追加する。
  ワークフローからの呼び出しは T-45 でまとめて配線するため、それまでは W14 の `LIBRARY_ONLY_ROUTES` に登録する。
- `/audit` はツールカタログを読み込めた場合だけ R1 を検査する。読み込めたかどうかは `/health` の `tools_catalog` で確認できるようにし、黙って無効にならないようにする。
- カタログの配置: Fly では `/app/data` がボリュームに置き換わり `data/tools.json` が見えないため、
  Docker イメージに `/app/catalog/tools.json` として同梱する。読み込み順は `AINAVI_TOOLS_FILE` → `data/tools.json` → `catalog/tools.json`。

### 35-14. プラグインによるサイトデザイン（T-51・操作者指示 2026-09-24）

操作者の指示「サイトデザインはプラグインを使ってみて」を受け、§35-2 の「プラグイン非依存」を**デザイン層に限って**改める。
コンテンツ（ツールページ・信頼ページ）の生成はプラグイン非依存のまま（§35-11/§35-12）とし、デザインの有無で壊れないようにする。

**確認した事実（2026-09-24、Exa 経由で一次情報を取得）**
- WordPress.com は**有料プラン（Personal・Premium・Business・Commerce）で**プラグインを導入できる。無料プランでは導入できない（wordpress.com/support/plugins/install-a-plugin/）。本番のプランは**ビジネスプラン**（2026-09-25 操作者のスクリーンショットで確認。管理画面の表記は「仕事」、年払い）なので、プラグインの導入とカスタムコードの追加が可能。
- コア REST API: `POST /wp/v2/plugins {slug, status}` は wordpress.org のプラグインをインストールする。`/wp/v2/themes` は**取得のみ**で、テーマの有効化は REST ではできない。
- `POST /wp/v2/global-styles/{id}` で `styles`（`styles.css` のカスタム CSS を含む。コアが CSS を検証する）と `settings` を更新できる（WP 5.9 以降、CSS 検証は 6.2 以降）。
- 以下の slug が wordpress.org に実在することを確認した: テーマ `twentytwentyfive`、プラグイン `seo-by-rank-math`・`kadence-blocks`・`easy-table-of-contents`・`wp-dark-mode`・`wp-super-cache`。

**構成（`data/wp-site.json` を唯一の正とする）**

| 要素 | 選定 | 目的（§2-2 との対応） |
|---|---|---|
| テーマ | Twenty Twenty-Five（ブロックテーマ） | グローバルスタイルで配色・文字・余白を API から適用できる |
| `kadence-blocks` | カード・グリッド・ステップ図解のブロック | カード型レイアウト・ステップ図解 |
| `wp-dark-mode` | 閲覧者の OS 設定に応じたダークモード | ダークモード対応 |
| `easy-table-of-contents` | 長文記事の目次 | 読みやすさ（800〜2000字の記事） |
| `seo-by-rank-math` | SEO メタ・サイトマップ（§12 の既定） | SEO |
| `wp-super-cache` | ページキャッシュ | **自己ホストのサンドボックスのみ**。WordPress.com はサーバ側のキャッシュを提供するため導入しない |

- **§12 の見直し**: Classic Editor は**導入しない**。ブロックエディタを無効化するため、ブロック系のデザイン（Kadence Blocks・ブロックテーマ）と両立しない。n8n からの REST 投稿は HTML 本文なので、Classic Editor が無くても影響しない。ACF はツールDB（§35-11）を JSON で持つため、現時点では不要。
- **デザイントークン**（配色・フォント・余白・角丸・カードの影）は `wp-site.json` の `global_styles` に置き、グローバルスタイルとして適用する。フォントは外部読み込みをせず、OS 標準の日本語フォントを使う（表示速度とプライバシーのため）。

**適用スクリプト（`scripts/wp_site_setup.py`・操作者が実行）**
- 既定は `plan`（変更内容の表示のみ）。`apply` で実行する。認証の判定は `wp-init.sh` / `tool_pages.py` と同じ（§24）。
- **追加だけで、削除はしない**: 未導入のプラグインは導入して有効化し、導入済みで無効なものは有効化する。既存プラグインの無効化・削除は一切しない。
- テーマが Twenty Twenty-Five でなければ `[TODO]` を出して止める（REST では有効化できないため、操作者が管理画面で切り替える）。
  グローバルスタイルは、有効なテーマが一致するときだけ更新する。
- WordPress.com の REST 経路でプラグイン API が使えるかは未検証。失敗したプラグインは `[WARN]` を出して次へ進み、操作者は管理画面から導入する。
- 各プラグインの詳細設定（Rank Math の初期設定、ダークモードの切替ボタンの位置など）は、プラグインごとに API が違うため対象外とし、操作者の手順とする。

**ゲート（W17）**: `data/wp-site.json` がスキーマを満たすこと。具体的には次を検査する。
- slug の形式が正しい
- 目的の記載がある
- 導入禁止のプラグイン（`classic-editor`）が含まれていない
- カスタム CSS に HTML タグを含まない（コアの CSS 検証と同じ条件）
- カラーパレットに前景・背景があり、その2色のコントラスト比が 4.5:1 以上（WCAG AA）

### 35-7. 範囲外（別タスク）

- n8n ワークフロー JSON の変更（公開上限・A5 の配線・R1 のプロンプト）は、CLAUDE.md §F に従い操作者の手動実行を経てから push する（T-45 / T-50）。
- `scripts/wp-init.ps1` の親割当対応は、Windows 実機での検証が必要（T-49）。
- ③ compare 用のワークフロー（T-48）と信頼ページの本文（T-47）。

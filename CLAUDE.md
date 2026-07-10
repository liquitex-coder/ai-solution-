# CLAUDE.md — ai-solution-（AIナビ）

AI content automation platform: n8n → Claude API → WordPress.
**このパイプライン自体が Claim Platform の実動デモ・宣伝媒体。**

**Chat**: 日本語 / **GitHub**: English primary（日本語は切り替え）
詳細ルール → `docs/AGENT_WORKFLOW.md`

---

## A. 絶対ルール / Absolute Rules — 違反したら作業を止める

1. 認証情報・APIキーをコード・コミット・計画に含めない（環境変数のみ）。
2. 証拠（ゲート出力）なしに「完了」と言わない。
3. ローカルゲート未実行で push しない。タスク指定ブランチ以外に push しない。
4. **設計＝配線まで**: 新機能は `scripts/check_wired.py` が検出できる形で本番パスに
   配線されるまで「完了」ではない。意図的な未配線は LIBRARY_ONLY 登録（理由必須）。
5. **Auditor gate 必須**: 全生成コンテンツは Claim-Auditor gate を通す。FAIL / UNVERIFIABLE は WordPress へ公開しない（INV-R2）。
6. **著作権**: 引用5要件（主従・明瞭区別・必要性・出所明示・改変禁止）に違反する処理を書かない。`n8n/prompts/00-copyright-transform.md` を全WFで読み込む。
7. 環境変数: `WP_URL` `WP_USERNAME` `WP_APP_PASSWORD` `GITHUB_TOKEN` `FAL_API_KEY` `GOOGLE_DRIVE_CREDENTIALS` `KIMI_API_KEY`。

---

## B. 必須フロー / Mandatory Flow — 順序固定

1. **Auditor 自己適用（ハルシネーション対策）** — 実装前に計画の主張を検証:
   実装∧テスト∧本番呼び出しが証明可能か / 設計文書に無い機能を作っていないか /
   「動くはず・たぶん・おそらく」を含まないか / 認証情報ハードコードが無いか。
   1つでも FAIL → 3. に戻る。
2. **いきなりコードを書かない** — コードより先に文書・テスト計画。
3. **要件定義書を詳細に書き上げる** — `docs/requirements.md` を先に更新し、
   単独の `docs:` コミットにしてから実装する。
4. **ロードマップを作成** — PR description に `T-NN` 形式でタスクを列挙。
5. **タスクを設定** — TaskCreate で登録 → in_progress → completed。
   完了毎に報告: `✅ T-XX — done / 📊 N/M (XX%)`。
6. **GitHub は英語メイン・切り替えで日本語** — README は英語 + `<details>` トグル。
   コミット・PR タイトル・コードコメントは英語。PR 本文は `<details>` で日本語併記。
7. **ハーネスエンジニアリングを意識して構築** —
   - Worker-Evaluator 分離: 自己評価に頼らず、決定論的ゲート（Auditor / CI / テスト）に判定させる
   - ラチェット: 失敗は §C に1行追記し、二度と繰り返さない
   - フィードバックループ: テスト・リンター・CI をセンサーとして全変更に通す
   - 段階的ロールアウト: 新しい自動化は Report-Only → 人間承認付き → 自動 の順で昇格

---

## C. よくあるミス（ラチェット） / Common Mistakes — 失敗したらここに追記

1. コミット本文に diff に含まれないファイル名を書かない —
   `commit_message_reality` が file_mention 違反として CI を落とす（2026-07-10 実例）。
2. 「実装しました。動くはずです」— テスト出力なしの完了報告は無効。

---

## D. Local Gates — push 前に必ず実行

初回のみ: `git config core.hooksPath .githooks`（以後は pre-push フックが下記を自動実行・失敗時 push 拒否）

```
python3 scripts/check_wired.py   # design-vs-wired gate（要件§21・必須）
# n8n workflow: 手動実行 → WP draft 作成を確認（実行ログ必須）
# WordPress REST: 201 + post ID / Claude API: raw response をログ確認
docker-compose up && curl -s -o /dev/null -w '%{http_code}' http://localhost:8080  # → 200
```

---

## E. コミット / PR 形式（要約）

- コミット: `<type>: <English summary>` + 本文 bullet、末尾に:
  ```
  Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
  Claude-Session: https://claude.ai/code/session_01HnkrZxy1ErLnP4eJwgm9Nx
  ```
- PR: Summary / Changes / 🇯🇵 `<details>` / Test plan（ゲート出力貼付）。
  フルテンプレート → `docs/AGENT_WORKFLOW.md` §4

---

## F. このリポジトリ固有 / Repo-Specific

- n8n workflow JSON は手動テスト実行なしで push しない。
- アーキテクチャ全体図・言語戦略・Claim連携戦略 → `docs/requirements.md` §参照。
- Key files: `docs/requirements.md`（最初に更新）/ `n8n/workflows/*.json` / `n8n/prompts/*.md` / `n8n/skills/*.md` / `scripts/memory_init.py`。
- 記事本文は日本語、SEOメタデータは英語（言語戦略）。ZH ソースは Kimi 経由。

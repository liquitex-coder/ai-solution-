# ai-solution- — Working in this Repo

AI content automation platform: n8n → Claude API → WordPress.
Automates article generation from GitHub trending, RSS, YouTube, Threads, note.

**このパイプライン自体が Claim Platform の実動デモ・宣伝媒体。**

**Chat language**: 日本語
**GitHub language** (commits, PRs, code comments): English primary

---

## 0. セッション開始の標準フロー（全プロダクト共通）

**どのリポジトリ・プロダクトを触る場合でも、必ずこの順番で進める。順序は変えない。**

```
① CLAUDE.md 確認
       ↓
② Auditor 自己適用（要件・設計の主張を事前検証）
       ↓
③ 要件定義書（docs/requirements.md）更新・確認
       ↓
④ ロードマップ作成（T-NN タスク一覧を PR description に記載）
       ↓
⑤ TaskCreate でタスク登録 → in_progress → completed
```

### ① CLAUDE.md 確認

セッション冒頭で必ず当ファイルを読む。前回セッションからの変更があればそれを反映した状態で作業する。

### ② Auditor 自己適用

Claim-Auditor はコンテンツのファクトチェックだけでなく、**設計・計画の主張にも適用する**。
実装を始める前に、計画内の主張を以下の基準で自己検証する:

| チェック項目 | 判定基準 |
|---|---|
| 実装対象は「実装 ∧ テスト ∧ 本番呼び出し」が証明できる形か | PASS / FAIL |
| 要件定義書に存在しない機能を実装しようとしていないか | PASS / FAIL |
| 「動くはず」「たぶん大丈夫」「おそらく」の表現が計画に含まれていないか | PASS / FAIL |
| 認証情報・APIキーがハードコードされた計画になっていないか | PASS / FAIL |
| 著作権・引用ルールに違反するコンテンツ処理が含まれていないか | PASS / FAIL |

**1つでも FAIL → ③ 要件定義書の更新に戻る。すべて PASS になってから実装へ進む。**

### ③ 要件定義書

`docs/requirements.md` を更新してから実装する（§2 参照）。要件なしにコードを書き始めない。

### ④ ロードマップ

PR description に `T-01`, `T-02` ... の形式でタスクを列挙する（§3 参照）。

### ⑤ TaskCreate

各タスクを TaskCreate ツールで登録し、`in_progress` → `completed` を追跡する（§3 参照）。

---

## 1. Anti-Hallucination

- **証拠なしに「完了」と言わない** — a passing test output or API response is required.
- **Cite before you claim.** Before asserting that something works, point to the file + line or API response.
- **Forbidden phrases without proof**: "should work", "it's probably", "I believe it's configured".
- **Cross-check against `docs/requirements.md`** before any design decision — if the requirement is not there, add it first.
- **When uncertain**, say so explicitly and list what needs verification.

---

## 2. Requirements-First Workflow

```
変更が必要 → docs/requirements.md を先に更新 → レビュー確認 → コード/ワークフロー実装
```

1. Open `docs/requirements.md`, update the relevant section, commit as a **standalone commit**:
   `docs: update requirements — <what changed>`
2. **Then** implement code / n8n workflow JSON.
3. PR body must reference both the requirements change and the implementation.
4. 要件定義なしにコードを書き始めない。

---

## 3. Roadmap & Task Tracking

At the start of any non-trivial work, draw a roadmap with numbered tasks (T-NN) in the
PR description.

- Register each task via **TaskCreate** before starting.
- Mark **in_progress** when starting, **completed** when done.
- **Progress report at every task completion and at session end**:

  ```
  ✅ T-XX <task name> — done
  📊 Progress: N / M tasks done (XX%)
  ```

  Formula: `% = completed / total × 100` (round to nearest integer).

---

## 4. GitHub Language Convention

| Artifact | Language |
|---|---|
| Commit messages | English (imperative: `add`, `fix`, `update`) |
| PR title | English |
| PR body | English primary; Japanese in `<details>` toggle |
| Code comments | English |
| Variable / function names | English |
| `docs/requirements.md` | Japanese (internal design doc) |
| `n8n/SETUP_GUIDE.md` | Japanese (operator runbook) |
| Daily chat replies | **日本語** |
| This file (`CLAUDE.md`) | Bilingual |

### Commit message format
```
<type>: <short English summary>

- <bullet: what changed>
- <bullet: why>

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01HnkrZxy1ErLnP4eJwgm9Nx
```

### PR body format
```markdown
## Summary
- bullet

## Changes
- `file`: what changed

<details>
<summary>🇯🇵 日本語補足 / Japanese notes</summary>

- 変更の背景・実装上の判断

</details>

## Test plan
- [ ] n8n manual run → WP draft confirmed
```

---

## 5. Test Discipline — No "Designed but not running"

```
実装 → テスト設計（実装と同時）→ テスト実行 → 出力確認 → DONE
```

| Component | Minimum verification |
|---|---|
| n8n workflow | Execute manually; confirm WP draft created |
| WordPress REST API | `curl` or n8n HTTP node returns 201 with post ID |
| Claude API call | Raw API response logged in n8n execution |
| GitHub API | Returned JSON contains expected `full_name` / `stargazers_count` |
| docker-compose | `docker-compose up` + `curl http://localhost:8080` returns 200 |

- **Never report "done" without test output.** Paste n8n execution log or API response.
- **Forbidden**: "実装しました。動くはずです" — no test output → not done.
- Pushing n8n workflow JSON without a manual test run is forbidden.

---

## 6. Key Files

| File | Purpose |
|---|---|
| `docs/requirements.md` | Source of truth for all features — update FIRST |
| `n8n/SETUP_GUIDE.md` | Operator runbook for credentials & workflow import |
| `n8n/workflows/*.json` | n8n workflow definitions (import via n8n UI) |
| `n8n/prompts/*.md` | Prompt templates (loaded dynamically at runtime) |
| `n8n/prompts/00-copyright-transform.md` | Copyright compliance rules — applied to ALL workflows |
| `docker-compose.yml` | Local sandbox (WP + n8n + MySQL) |
| `data/wp-taxonomy.json` | WordPress category/tag design |
| `scripts/wp-init.sh` | WordPress auto-initialization script |

---

## 7. Architecture Snapshot

```
Sources: GitHub API / RSS / YouTube / Threads / note / NoimosAI (Google Docs) / ZH (Kimi)
  └─→ n8n WF01-08 (orchestrator)
        ├─→ 言語検出 + LLMルーティング (claim-llm)
        │     ├─ ZH → Kimi API (moonshot-v1-128k)
        │     ├─ EN → Claude API
        │     └─ JA → Claude API
        ├─→ 著作権変換 (00-copyright-transform.md)
        ├─→ claim-crew       (journalist agents — gather & synthesize)
        ├─→ claim-builder    (N independent proposals)
        │     └─→ council loop (consensus selection)
        ├─→ claim-llm        (LLM abstraction + NetworkPolicy)
        ├─→ Claim-Auditor gate  ← ALL generated content passes here (INV-R2)
        │     ├─ PASS        → visuals + claim-security- → WordPress draft
        │     ├─ FAIL        → human review queue
        │     └─ UNVERIFIABLE→ draft + flag
        ├─→ Visuals
        │     ├─ 80% Mermaid + Kroki.io  (free)
        │     ├─ 15% Flux.1 / fal.ai     (~¥1/image)
        │     └─  5% Higgsfield           (EN video)
        ├─→ claim-security-  (API admission sandwich)
        └─→ WordPress REST API (draft)
              └─→ Human approval → publish
                    └─→ claim-evolve (continuous improvement)
```

WordPress: `liquitex929aa21393-eyqci.wordpress.com`
n8n cloud: `liquitex-coder.app.n8n.cloud`

**Security**: no hardcoded credentials — use env vars
(`WP_URL`, `WP_USERNAME`, `WP_APP_PASSWORD`, `GITHUB_TOKEN`,
 `FAL_API_KEY`, `GOOGLE_DRIVE_CREDENTIALS`, `KIMI_API_KEY`).

---

## 8. 言語戦略 (Language Strategy)

| コンテンツ種別 | 言語 | フェーズ |
|---|---|---|
| 記事本文 | **日本語**（メイン） | Phase 1〜 |
| SEOメタデータ (title / description / slug / alt) | **英語** | Phase 1 — 全記事 |
| 英語全文翻訳 | 英語（高価値記事のみ） | Phase 2 |
| Higgsfield 動画キャプション | 英語 | Phase 2 |
| ZH→JA 翻訳記事（Kimi） | 日本語（翻訳ラベル付き） | Phase 2 |

---

## 9. Claim Platform 連携戦略

**コアコンセプト**: このパイプラインを動かすことで Claim Platform の各製品を実際に使い、
その事実を記事のバッジ・メタデータとして自然に露出する。動いている証拠を見せる。

| 製品 | パイプライン内の役割 | 記事内での露出 |
|---|---|---|
| **claim-auditor** | 全生成物のゲート（コンテンツ + 著作権 + 設計主張） | `Auditor 検証済み` バッジ |
| **claim-crew** | 記者エージェント群 | 記事クレジットに「AI記者エージェントが取材」 |
| **claim-builder + council** | N案生成 → コンセンサス選択 | 「複数AIの議論で生成・選択」 |
| **claim-security-** | API エンドポイント保護 | 「セキュリティスキャン済み」バッジ |
| **claim-llm** | 言語検出・LLMルーティング | 内部のみ |
| **claim-evolve** | プロンプト自己改善ループ | 必要に応じて言及 |

**Auditor ゲートは全コンテンツに必須**（GitHub コンテンツも含む）。
FAIL または UNVERIFIABLE の場合、WordPress への投稿は行わない。

# ai-solution- — Working in this Repo

AI content automation platform: n8n → Claude API → WordPress.
Automates article generation from GitHub trending, RSS, YouTube, Threads, note.

**このパイプライン自体が Claim Platform の実動デモ・宣伝媒体。**

**Chat language**: 日本語
**GitHub language** (commits, PRs, code comments): English primary

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
| `docker-compose.yml` | Local sandbox (WP + n8n + MySQL) |
| `data/wp-taxonomy.json` | WordPress category/tag design |
| `scripts/wp-init.sh` | WordPress auto-initialization script |

---

## 7. Architecture Snapshot

```
Sources: GitHub API / RSS / YouTube / Threads / note / NoimosAI (Google Docs)
  └─→ n8n WF01-07 (orchestrator)
        ├─→ claim-crew       (journalist agents — multi-angle gather & synthesize)
        ├─→ claim-builder    (N independent proposals)
        │     └─→ council loop (consensus selection → correlated-error reduction)
        ├─→ claim-llm        (LLM abstraction + NetworkPolicy control)
        ├─→ Claim-Auditor gate  ← ALL generated content passes here (INV-R2)
        │     ├─ PASS        → visuals + claim-security- → WordPress draft
        │     ├─ FAIL        → human review queue
        │     └─ UNVERIFIABLE→ draft + flag
        ├─→ Visuals
        │     ├─ 80% Mermaid + Kroki.io  (free, diagrams)
        │     ├─ 15% Flux.1 / fal.ai     (~¥1/image, featured image)
        │     └─  5% Higgsfield           (EN video — YouTube Shorts / TikTok)
        ├─→ claim-security-  (API admission sandwich, deterministic verdict)
        └─→ WordPress REST API (draft)
              └─→ Human approval → publish
                    └─→ claim-evolve (continuous prompt self-improvement)
```

WordPress: `liquitex929aa21393-eyqci.wordpress.com`
n8n cloud: `liquitex-coder.app.n8n.cloud`

**Security**: no hardcoded credentials in committed files — use env vars
(`WP_URL`, `WP_USERNAME`, `WP_APP_PASSWORD`, `GITHUB_TOKEN`, `FAL_API_KEY`, `GOOGLE_DRIVE_CREDENTIALS`).

---

## 8. 言語戦略 (Language Strategy)

| コンテンツ種別 | 言語 | フェーズ |
|---|---|---|
| 記事本文 | **日本語**（メイン） | Phase 1〜 |
| SEOメタデータ (title / description / slug / alt) | **英語** | Phase 1 — 全記事 |
| 英語全文翻訳 | 英語（高価値記事のみ） | Phase 2（アクセスデータで需要確認後） |
| Higgsfield 動画キャプション | 英語 | Phase 2 |
| WordPress カテゴリ / タグ | 日本語（メイン）+ 英語スラグ | Phase 1〜 |

### Phase 1 — EN SEO メタデータ（全記事）
Claude API プロンプトで以下を英語生成：
- `post_title` (英語版 SEO タイトル → Yoast SEO `_yoast_wpseo_title`)
- `meta_description` 英語 (`_yoast_wpseo_metadesc`)
- `slug` (英語、ハイフン区切り)
- 画像 `alt` テキスト (英語)

### Phase 2 — EN 全文翻訳
- アクセス解析でEN流入需要を確認してから着手。
- Higgsfield 動画は Phase 2 の EN SNS チャネル向け（YouTube Shorts / TikTok / Instagram）。
- 動画は高価値記事の5%のみ生成（コスト管理）。

---

## 9. Claim Platform 連携戦略

**コアコンセプト**: このパイプラインを動かすことで Claim Platform の各製品を実際に使い、
その事実を記事のバッジ・メタデータとして自然に露出する。「宣伝のための宣伝」ではなく
**動いている証拠** を見せる。

### 各製品の役割と記事内プロモーション

| 製品 | パイプライン内の役割 | 記事内での露出 |
|---|---|---|
| **claim-auditor** | 全生成物のハルシネーション検証ゲート（必須） | `Auditor 検証済み` バッジを全記事フッターに表示 |
| **claim-crew** | 記者エージェント群 — 多角的取材・情報整理 | 記事クレジットに「AI記者エージェントが取材・整理」 |
| **claim-builder + council** | N案生成 → コンセンサス選択で品質向上 | 記事メタに「複数AIの議論で生成・選択」 |
| **claim-security-** | API エンドポイント保護・アドミッションサンドイッチ | フッターに「セキュリティスキャン済み」バッジ |
| **claim-llm** | LLM抽象化レイヤー + NetworkPolicy 制御 | 内部のみ（露出不要） |
| **claim-evolve** | プロンプト自己改善ループ | 必要に応じて「継続改善中」として言及 |

### Auditor ゲートは全コンテンツに必須
`全ての生成物に対して Auditor を適用は大前提`（GitHub コンテンツも含む）。
FAIL または UNVERIFIABLE の場合、WordPress への投稿は行わない。

### バッジ実装ガイドライン
- WordPress 記事本文の末尾に HTML スニペットとして挿入（n8n HTTP Request ノードで付与）。
- バッジはリンクとして claim 製品の GitHub/紹介ページに誘導する（Phase 2 で追加）。
- 過剰な宣伝文は避け、`検証済み` の事実のみ短く記載する。

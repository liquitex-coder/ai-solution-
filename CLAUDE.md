# ai-solution- — Working in this Repo

AI content automation platform: n8n → Claude API → WordPress.
Automates article generation from GitHub trending, RSS, YouTube, Threads, note.

**Chat language**: 日本語
**GitHub language** (commits, PRs, code comments): English primary

---

## 1. Anti-Hallucination

- **証拠なしに「完了」と言わない** — a passing test output or API response is required.
- **Cite before you claim.** Before asserting that something works, point to the file + line or API response.
- **Forbidden phrases without proof**: “should work”, “it’s probably”, “I believe it’s configured”.
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

## 5. Test Discipline — No “Designed but not running”

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

- **Never report “done” without test output.** Paste n8n execution log or API response.
- **Forbidden**: “実装しました。動くはずです” — no test output → not done.
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
Sources (GitHub API, RSS, YouTube, Threads, note)
  └─→ n8n (orchestrator)
        └─→ Claude API (article generation)
              └─→ WordPress REST API (auto-post as draft)
                    └─→ NoimosAI (SEO + SNS distribution)
```

WordPress: `liquitex929aa21393-eyqci.wordpress.com`
n8n cloud: `liquitex-coder.app.n8n.cloud`

**Security**: no hardcoded credentials in committed files — use env vars
(`WP_URL`, `WP_USERNAME`, `WP_APP_PASSWORD`, `GITHUB_TOKEN`).

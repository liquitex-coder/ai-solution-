# ai-solution- / Working in this Repo

**Chat language**: Japanese  
**GitHub language** (commits, PRs, code comments): English primary — Japanese in parentheses where helpful

---

## 1. Anti-Hallucination — Apply Auditor to Self

This project generates AI content automatically. The same honesty discipline applies to Claude's own work.

- **Cite before you claim.** Before asserting that something works, point to the file + line or API response that proves it.
- **Never say "done" without evidence.** A passing test output or API response is required.
- **Forbidden phrases without proof**: "should work", "it's probably", "I believe it's configured".
- **When uncertain, say so explicitly** and list what needs verification.
- **Cross-check against `docs/requirements.md`** before any design decision — if the requirement is not there, add it first.

---

## 2. Requirements-First Workflow

```
変更が必要 → docs/requirements.md を先に更新 → レビュー確認 → コード/ワークフロー実装
```

1. **New feature / change**: open `docs/requirements.md`, update the relevant section, commit it as a standalone commit with message `docs: update requirements — <what changed>`.
2. **Then** implement code / n8n workflow JSON.
3. PRの本文には「requirements.md の変更箇所」と「実装箇所」の両方を記載する。
4. 要件定義なしにコードを書き始めない。

---

## 3. GitHub Language Convention

| Artifact | Language |
|---|---|
| Commit messages | English (imperative: `add`, `fix`, `update`) |
| PR title & body | English primary, Japanese context in parentheses |
| Code comments | English |
| Variable / function names | English |
| `docs/requirements.md` | Japanese (internal design doc) |
| `n8n/SETUP_GUIDE.md` | Japanese (operator runbook) |
| This file (`CLAUDE.md`) | Bilingual |

### Commit message format
```
<type>: <short English summary>

- <bullet of what changed>
- <bullet of why>

(日本語補足がある場合はここに)
```
Types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`

---

## 4. Test-Before-Ship: No "Designed But Not Running"

Every seam (API call, workflow step, REST endpoint) must have a test or verification step **before** the feature is considered done.

### Rule
```
実装 → テスト作成 → テスト実行 → 出力確認 → DONE
```

### What counts as a test

| Component | Minimum verification |
|---|---|
| n8n workflow | Execute workflow manually; confirm WP draft created |
| WordPress REST API | `curl` or n8n HTTP node returns 201 with post ID |
| Claude API call | Raw API response logged in n8n execution |
| GitHub API | Returned JSON contains expected `full_name` / `stargazers_count` |
| docker-compose | `docker-compose up` + `curl http://localhost:8080` returns 200 |

### Sandbox checklist (Phase 0 — run before any Phase 1 push)

- [ ] `docker-compose up` → WordPress reachable at `http://localhost:8080`
- [ ] n8n reachable at `http://localhost:5678`
- [ ] Workflow 01 (GitHub AI Trending) manual execute → WP draft created
- [ ] Workflow 02 (RSS Monitor) manual execute → WP draft created
- [ ] Claude API returns structured article JSON
- [ ] WordPress REST API POST `/wp-json/wp/v2/posts` → 201 response with post ID

### Forbidden
- "実装しました。動くはずです" — テスト出力なしに完了と報告しない
- Pushing n8n workflow JSON without a manual test run first
- Changing Claude API prompts without logging before/after output samples

---

## 5. Key Files

| File | Purpose |
|---|---|
| `docs/requirements.md` | Source of truth for all features — update FIRST |
| `n8n/SETUP_GUIDE.md` | Operator runbook for credentials & workflow import |
| `n8n/workflows/*.json` | n8n workflow definitions (import via n8n UI) |
| `docker-compose.yml` | Local sandbox (WP + n8n + MySQL) — **to be created** |

---

## 6. Architecture Snapshot

```
Sources (GitHub API, RSS, YouTube, Threads, note)
  └─→ n8n (orchestrator)
        └─→ Claude API (article generation)
              └─→ WordPress REST API (auto-post as draft)
                    └─→ Distribution/analytics layer
                        (SEO: Rank Math + Search Console; SNS: deferred/self-built.
                         NoimosAI is NOT used — see docs/requirements.md §5)
```

WordPress: `liquitex929aa21393-eyqci.wordpress.com`  
n8n cloud: `liquitex-coder.app.n8n.cloud`

---

## 7. Current Phase

**Phase 0 — Sandbox** (in progress)

- [x] Requirements doc created (`docs/requirements.md`)
- [x] n8n workflow JSON stubs created (01–06)
- [ ] `docker-compose.yml` (WordPress + n8n + MySQL)
- [ ] WordPress auto-setup script
- [ ] End-to-end sandbox test (all checklist items in §4 above)

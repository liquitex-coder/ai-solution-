---
title: "ai-solution- roadmap v2 — to Phase 1 in production, with Codex prompts"
date: 2026-09-13
tags: [ai-solution, roadmap, codex, claim-auditor, session-log]
branch: claude/awesome-curie-mu3e69
related: ["[[ROADMAP]]", "[[2026-09-12-roadmap-codex-prompts]]", "docs/requirements.md §28 §30 §31 §32 §33"]
---

# Roadmap v2 (2026-09-13) — verified baseline, corrected order, Codex prompts

> English primary; 🇯🇵 Japanese summary at the end.
> Roles (requirements §26): **Claude Code = orchestrator**, **Codex = implementer**, **operator = production actions**.
> This note supersedes the sequencing in `docs/ROADMAP.md` (2026-09-12); task IDs T-01…T-24 are kept, T-25…T-28 are new.

## 0. Verified baseline (independent re-run on Linux, 2026-09-13)

Branch `claude/awesome-curie-mu3e69` (PR #10), fork point == `origin/main` (`fbf96ed`), CI `wired-check` green, `mergeable_state: clean`.

| Gate | Result |
|---|---|
| `python3 scripts/check_wired.py` | 79 PASS, 0 FAIL (W1–W11) |
| `python3 scripts/run_eval.py` | 50 cases, FP=0, FN=0 (GREEN) |
| `python3 -m unittest discover -s tests` | 18 tests OK |
| Claim-Auditor `check_conventions_cross_repo` against this branch's CLAUDE.md / AGENT_WORKFLOW.md | OK, all canonical blocks present |
| `docs/requirements.md` sections | §27 → §28 → §29 (kept from #9) → §30 → §31 → §32, no collision, v2.3 |

New facts found during verification (not in ROADMAP 2026-09-12):

| # | Fact | Consequence |
|---|---|---|
| F1 | `scripts/check_wired.py` (3 calls), `scripts/run_eval.py` (1), `scripts/patch_workflows.py` (14 read/write), `scripts/build_eval_set.py` (1 write), `scripts/build_wf09.py` (1 write) call `read_text()` / `write_text()` without `encoding=` | On Windows (cp932) the §D gates raise `UnicodeDecodeError`; `write_text` would silently emit cp932 JSON. All "done" evidence so far is Linux-only → **T-25 is a blocker for every later gate run on the operator's machine** |
| F2 | `.githooks/pre-push` calls `python3`; on the operator's Windows shell `python3` resolves to the Store stub | The pre-push gate has never actually run on Windows → absolute rule 3 is not machine-enforced there. Fixed in T-25 |
| F3 | T-11's "図解埋め込み" node calls `POST /embed-diagrams` on the §28 service | T-11 cannot meet its "done when" (Kroki image in a WP draft) until the service is reachable from n8n cloud → **T-12/T-13 must precede T-11** |
| F4 | `auditor_server.py` has no authentication; T-12 puts it on a public HTTPS host | An unauthenticated public `POST /audit` lets anyone write to `data/memory.db`, which feeds `ratchet_check.py` (§23) → poisoning vector. **T-27 (shared-secret) before T-12** |
| F5 | §32-1 D2 conflates two different §17-1 checks: ⑤改変禁止 (blockquote text must stay ≥ 0.85 similar to the source) and ①主従 / verbatim copying (body text outside blockquotes must **not** be ≥ 0.85 similar) | T-24 implements the second as `WARN:VERBATIM_COPY`; the first is recorded as **D7** in §32-1 and decided later (spec decision, not Codex) |
| F6 | `docker-compose.yml` runs the service by mounting `./scripts`; there is no image to deploy to a cloud host | **T-26 Dockerfile** is a prerequisite of T-12 |

## 1. Definition of "complete" (unchanged)

README "Phase 1 core pipeline in production": WF01–09 imported into n8n cloud, each Auditor Gate calling a *real*, *authenticated* `/audit`, all posts landing as WordPress drafts with a recorded verdict (`CLAIM_AUDITOR_MODE=report_only`), every code path covered by a local gate (`check_wired`, `run_eval`, `unittest`) that CI also runs **and that runs on the operator's Windows machine**.

## 2. Roadmap v2 — order of execution

Legend: ✅ done (evidence in ROADMAP.md) · ⏳ next · 🧑 operator · 🤖 Codex · 🧭 Claude Code

### Phase B — finish drift cleanup (blocker first)

| ID | Owner | Task | Done when |
|---|---|---|---|
| T-25 ⏳ | 🧭 docs → 🤖 | **Gate portability**: explicit `encoding="utf-8"` on every `read_text/write_text/open` in `scripts/`; `tests/test_encoding_guard.py` (AST sensor, fails on regression); `.githooks/pre-push` falls back to `py -3` when `python3` is the Store stub; CLAUDE.md §C-3 ratchet line; requirements §33 | unittest green incl. the guard; `check_wired` 79 PASS; **operator runs `py -3 scripts/check_wired.py` in a cp932 console → exit 0** |
| T-24 ⏳ | 🤖 | Auditor spec⇄code parity §32-1 D1/D2/D3/D5, eval-set first; new checks land as `WARN:` (no verdict change) per §32-2 | `run_eval` ≥ 52 cases FP=0/FN=0; `tests/test_content_audit.py` green; §32-1 rows flipped |

### Phase C — service hardening (prerequisites of hosting)

| ID | Owner | Task | Done when |
|---|---|---|---|
| T-27 ⏳ | 🧭 docs → 🤖 | `CLAIM_AUDITOR_TOKEN` shared secret on `POST /audit` and `POST /embed-diagrams` (`/health` open); sandbox stays zero-config with a logged warning | tests: correct token 200 / wrong 401 + no facts write / unset → 200 + `health.auth=false` |
| T-26 ⏳ | 🤖 | `Dockerfile` + `.dockerignore` for the service; honour `$PORT`; compose builds the image; memory DB on a volume | `docker build` + `curl /health` ok; `docker compose config` valid; W9 still PASS |
| T-11 | 🤖 + 🧑 | **Moved after T-13.** WF01–09 wiring: `$vars` fallback (if T-13 shows `$env` blocked), `Authorization: Bearer` header, WF08 `source_lang:'zh'`, "図解埋め込み" node, `article-base.md` mermaid rule | push **only after** the operator's manual WF01 run shows a WP draft with verdict metadata and a rendered Kroki image (CLAUDE.md §F) |

### Phase D — production rollout

| ID | Owner | Task | Done when |
|---|---|---|---|
| T-12 | 🧑 | Choose hosting (table §4 below) and deploy the T-26 image with `CLAIM_AUDITOR_TOKEN` set; record host in §28-3 | `GET https://<host>/health` → `{"status":"ok","auth":true}` |
| T-13 | 🧑 | In n8n cloud set `CLAIM_AUDITOR_URL`, `CLAIM_AUDITOR_MODE=report_only`, `CLAIM_AUDITOR_TOKEN` as **Variables** (`$vars`); run a throwaway Code node to record whether `$env` is readable; write the result into §28-3 / §15 | one execution log shows the values readable via `$vars` (and the `$env` answer recorded) |
| T-14 | 🧑 | Re-run `scripts/wp-init.ps1` with the corrected taxonomy (WF07–09 categories) and paste the IDs | output pasted into the PR / session note |
| T-28 | 🤖 | Record WF07–09 `wp_id` in `data/wp-taxonomy.json` and `category_id` in `07/08/09-*.json` (W11 flips from "skipped" to checked) | `check_wired` W11 PASS for 09/09 without "skipped"; pushed together with T-11 after the manual run |
| T-15 | 🧑 | Manual run WF01→02→05→06→03→04→07→08→09 in n8n cloud, confirm drafts + verdict metadata + category, then Activate | execution logs pasted; README Phase 1 = ✅ |
| T-16 | 🧑 | 30-day `report_only` review → `canary` (§22-3) with human signature (INV-R1) | signed note in requirements |

### Phase E / F — unchanged (T-17…T-23, see ROADMAP.md)

### Progress (formula `% = done / total`, rounded)

| Scope | Done | Total | % |
|---|---|---|---|
| Phase A | 6 | 6 | 100% |
| Phase B | 3 | 5 | 60% |
| Phase C | 1 | 4 | 25% |
| Phase D | 0 | 6 | 0% |
| Phase 1 definition (A–D) | 10 | 21 | 48% |
| Whole roadmap (A–F) | 10 | 28 | 36% |

Critical path: **T-25 → T-24 → T-27 → T-26 → (merge PR #10) → T-12 → T-13 → T-11 → T-14 → T-28 → T-15 → T-16**.

## 3. Spec deltas to commit FIRST (`docs:` commit, Claude Code, before any Codex call)

Paste-ready Japanese text for `docs/requirements.md` (the spec is Japanese). Version → 2.4.

### 3-1. §28-2 — add two rows / notes

```
| 認証 | `CLAIM_AUDITOR_TOKEN` が設定されている場合、`POST /audit` と `POST /embed-diagrams` は
  `Authorization: Bearer <token>` を要求する（不一致・欠落は `401 {"error":"unauthorized"}`、記憶層へは何も書かない）。
  `GET /health` は常に認証不要で、`"auth": true|false` を返す。未設定時は挙動を変えず、起動時に stderr へ
  「unauthenticated mode (sandbox only)」を1行出す。比較は `hmac.compare_digest`。トークンはログに出さない。 |
| ポート | `CLAIM_AUDITOR_PORT` → 無ければ `PORT`（Render / Fly.io 慣習）→ 無ければ 8090。 |
```

### 3-2. §28-3 — production row → hosting candidates (decision = T-12)

```
| 本番（n8n cloud） | T-26 の `Dockerfile` イメージを HTTPS で公開。候補: (a) Fly.io + 1GB volume（memory.db 永続・推奨候補）
  (b) Render Web Service（無料枠はディスク非永続 → memory.db がデプロイ毎に消える。§23 の30日集計に不適）
  (c) Cloudflare Tunnel でローカル compose を公開（費用ゼロだが操作者PCの常時稼働が前提）。
  費用・運用は操作者判断（T-12）。 | `CLAIM_AUDITOR_URL` / `CLAIM_AUDITOR_MODE` / `CLAIM_AUDITOR_TOKEN` は n8n cloud の
  **Variables（`$vars`）** に設定する（T-13）。Code ノードで `$env` が読めるかは T-13 で実測し本表に記録。ゲートは
  `$env` → `$vars` の順で解決する（T-11）。 |
```

### 3-3. §32-1 — add row D7 (decision deferred; not part of T-24)

```
| D7 | ⑤改変禁止の本来の意味（blockquote 内テキストが原文と ≥ 0.85 で一致していること） | §17-1 表 | 未実装 |
  D2 の `VERBATIM_COPY` は「blockquote **外**の本文が原文と ≥ 0.85 で一致 = 丸写し」の検出であり、⑤とは別物。
  ⑤（引用の改変検出）は `source_text` の対応箇所特定が必要で誤検出リスクが高いため、T-24 では実装せず本行で保留。 |
```

### 3-4. New §33 — gate portability (Windows)

```
## 33. ローカルゲートの可搬性（Windows cp932 環境・2026-09-13 実例）

### 33-1. 検出した事実
- `scripts/check_wired.py` / `run_eval.py` / `patch_workflows.py` / `build_eval_set.py` / `build_wf09.py` の
  `Path.read_text()` / `write_text()` が `encoding` 未指定 → Windows（cp932）で `UnicodeDecodeError`。
  `write_text` は例外を出さずに cp932 の JSON を書き、n8n 側で日本語ノード名が壊れる（読み込みより発見が遅い）。
- `.githooks/pre-push` は `python3` を呼ぶが、操作者の Windows では Store スタブに解決し、フックは実質未実行だった。
- これまでの「done」証拠は全て Linux（Codex / クラウドセッション）で取得されており、§D ゲートが操作者環境で
  動くことは検証されていなかった。

### 33-2. 規約
1. `scripts/` 配下のテキスト I/O は `encoding="utf-8"` を必ず明示する（バイナリモードは除外）。
2. `tests/test_encoding_guard.py` が `ast` で全 `scripts/*.py` を走査し、未指定の呼び出しを FAIL にする（センサー）。
3. `.githooks/pre-push` は `python3` が使えない場合 `py -3` にフォールバックする。
4. 「ゲート green」の報告には **操作者環境（Windows）での実行結果**を1回は含める（T-25 の完了条件）。
```

### 3-5. `CLAUDE.md` §C — append line 3 (repo-specific ratchet; A–E canonical blocks untouched)

```
3. `read_text()` / `write_text()` / `open()` に `encoding="utf-8"` を必ず明示 —
   Windows cp932 で `UnicodeDecodeError`、`write_text` は無言で cp932 を書く（2026-09-13 実例、要件§33）。
```

### 3-6. `docs/ROADMAP.md` — replace Phase B/C/D tables and Progress with §2 above; add "Roadmap v2 (2026-09-13)" pointer to this note.

Commit message body rule (CLAUDE.md §C-1): name only files that are in the diff.

## 4. Hosting options for T-12 (operator decision — no recommendation is a commitment)

| Option | HTTPS | `memory.db` persistence | Cost | Operator burden |
|---|---|---|---|---|
| Fly.io (Dockerfile + 1 GB volume) | built-in | yes (volume) | small monthly, operator to confirm | `fly launch` / `fly volumes create` / `fly secrets set CLAIM_AUDITOR_TOKEN=…` |
| Render Web Service | built-in | **no on free tier** (ephemeral) → §23 30-day aggregation lost on each deploy | free / paid disk | dashboard only |
| Cloudflare Tunnel → local `docker compose` | via tunnel | yes (local disk) | free | PC must stay on 24/7 |

Whichever is chosen: `CLAIM_AUDITOR_TOKEN` must be set on the host **and** in n8n Variables; never in any repo file.

## 5. Codex prompts (AGENT_WORKFLOW §9-3 — one prompt = one call, `git diff` after each)

Every call: `cwd: <absolute path of the ai-solution- checkout>`, `approval-policy: never`, `sandbox: workspace-write`.
Before starting: `git checkout claude/awesome-curie-mu3e69 && git pull origin claude/awesome-curie-mu3e69`, then commit the §3 docs first.

```
CONSTRAINTS (common, copy into every prompt):
- Python stdlib only (no pip deps). Tests are unittest.TestCase under tests/.
- Never write credentials; env var names only. Do not touch n8n/workflows/*.json unless the prompt says so.
- Code comments and identifiers in English. Do not edit docs/requirements.md (spec is frozen for the task).
- Do not commit; leave changes in the working tree for review.
- Do not reformat or reorder unrelated code; the diff must contain only what the prompt asks for.
```

### T-25 — gate portability (encoding + launcher + sensor)

```
GOAL: Make the CLAUDE.md §D local gates behave identically on Windows (cp932 locale) and Linux: every text file read/write in scripts/ becomes explicit UTF-8, a test fails if an implicit call is reintroduced, and the pre-push hook works where `python3` is the Windows Store stub.
FILES: scripts/check_wired.py, scripts/run_eval.py, scripts/patch_workflows.py, scripts/build_eval_set.py, scripts/build_wf09.py (edit); tests/test_encoding_guard.py (new); .githooks/pre-push (edit)
SPEC:
  1. In the five scripts, add encoding="utf-8" to every Path.read_text() / Path.write_text(...) / open(...) call that lacks an encoding= keyword. Binary-mode open() calls ("rb"/"wb") are exempt. No other behaviour or output changes.
  2. tests/test_encoding_guard.py: for every scripts/*.py, parse with `ast`; for each ast.Call whose func is an Attribute named read_text/write_text, or a Name `open`, require a keyword `encoding` unless the call has a positional/keyword mode argument containing "b". Collect violations as "path:line" and assert the list is empty (message lists them).
  3. .githooks/pre-push: pick the interpreter once at the top:
       PY=python3; "$PY" -c "pass" >/dev/null 2>&1 || PY="py -3"
     and use $PY for the four gate lines. Keep `set -euo pipefail`, the SKIP_GATES bypass and all messages unchanged.
ACCEPTANCE:
  python3 -m unittest discover -s tests -v     # exit 0, includes test_encoding_guard
  python3 scripts/check_wired.py               # Summary: 79 PASS, 0 FAIL (unchanged)
  python3 scripts/run_eval.py                  # RESULT: GREEN (FP=0, FN=0)
  bash .githooks/pre-push                      # ends with "all gates green — push allowed"
  git diff --stat                              # exactly the 7 files above
CONSTRAINTS: common.
```

Operator follow-up (part of T-25 done-when): in a Windows console **without** `PYTHONUTF8` set, run
`py -3 scripts/check_wired.py` and `py -3 -m unittest discover -s tests` → both exit 0. Paste the output into PR #10.

### T-24 — auditor spec/code parity (§32-1 D1, D2, D3, D5)

```
GOAL: Close the spec-vs-code drift recorded in docs/requirements.md §32-1 (rows D1, D2, D3, D5) in the LLM-free auditor, eval-set first, without changing any existing verdict. If the working tree already contains partial work for this task, keep it and reconcile it with this spec rather than starting over.
FILES: data/eval_set.json (edit: add cases), scripts/content_audit.py (edit), scripts/auditor_server.py (edit), tests/test_content_audit.py (new), tests/test_auditor_server.py (edit), n8n/skills/skill-base.md (edit: quote-ratio sentence only)
SPEC:
  D1 quote ratio (verdict-changing, so eval first):
    - Add to data/eval_set.json two labelled cases: blockquote share ≈ 35% of characters → expected "FAIL" (reason prefix FAIL:QUOTE_DOMINANCE); share ≈ 30% → expected "PASS" (must satisfy all other PASS conditions: ≥3 h2, attribution link, no hype, no unsourced numbers).
    - Then set QUOTE_DOMINANCE_RATIO = 0.34 (§17-1: quotes ≤ 1/3). Update skill-base.md's "≤ 30%" sentence to "≤ 1/3 (requirements §17-1)".
  D2 VERBATIM_COPY (WARN only, §32-2):
    - audit(content, source_urls, source_text=None, source_lang=None) — new optional keyword args; existing callers unchanged.
    - When source_text is given: strip blockquotes from content; slide a 200-char window over the remaining text (step 100); if difflib.SequenceMatcher(None, window, source_text).find_longest_match yields a block ≥ 120 chars OR ratio ≥ 0.85 against any 200-char window of source_text → append "WARN:VERBATIM_COPY" to reasons. Verdict unchanged.
  D3 MISSING_TRANSLATION_LABEL (WARN only):
    - When source_lang in {"en","zh"}: require ("本記事は" in content and "翻訳" in content and any(url in content for url in source_urls)); otherwise append "WARN:MISSING_TRANSLATION_LABEL". Verdict unchanged. source_lang None/"ja" → no check.
  D5 ALREADY_REJECTED (server side, WARN only):
    - In auditor_server POST /audit: compute sha256(content); before auditing, look up facts by content_hash (add memory_init.find_fact_by_hash(conn, content_hash) -> dict|None); if a row exists, append f"WARN:ALREADY_REJECTED:{fact_id}" to reasons. Verdict is still recomputed. Do not insert a second facts row for the same hash.
    - /audit accepts and forwards optional source_text and source_lang to audit().
  Ordering: FAIL/UNVERIFIABLE reasons first, WARN reasons last, so reasons[0] stays the category used for facts.fail_reason (§28-2).
  tests/test_content_audit.py: quote 35% → FAIL, 30% → PASS; VERBATIM_COPY appended when 300 chars are copied outside a blockquote, not appended for paraphrase; MISSING_TRANSLATION_LABEL for source_lang="en" without the label, absent when label + url present, absent for "ja".
  tests/test_auditor_server.py: same HYPE content posted twice → second response reasons contain "WARN:ALREADY_REJECTED:<id>" and facts count stays 1.
ACCEPTANCE:
  python3 scripts/run_eval.py                  # cases: 52 (or more), FP=0, FN=0, GREEN
  python3 -m unittest discover -s tests -v     # exit 0
  python3 scripts/check_wired.py               # 79 PASS, 0 FAIL
CONSTRAINTS: common + do not implement §32-1 D4 or D7; never let a WARN change the verdict.
```

### T-27 — shared-secret auth on write paths

```
GOAL: Protect the Auditor service's write paths with a shared secret so an internet-reachable deployment cannot poison data/memory.db, while the local sandbox stays zero-config.
FILES: scripts/auditor_server.py (edit), tests/test_auditor_server.py (edit), docker-compose.yml (edit), .env.example (edit)
SPEC:
  - Read CLAIM_AUDITOR_TOKEN at startup. If non-empty: POST /audit and POST /embed-diagrams require header "Authorization: Bearer <token>" compared with hmac.compare_digest; missing/mismatch → 401 {"error":"unauthorized"} with nothing written to the DB and a request-log line with status 401. GET /health never requires auth and gains "auth": true|false.
  - If empty: behaviour unchanged; print one stderr line at startup: "CLAIM_AUDITOR_TOKEN not set — unauthenticated mode (sandbox only)".
  - Port resolution in main(): CLAIM_AUDITOR_PORT, else PORT, else 8090.
  - make_server(bind, port, db_path, token="") so tests can pass a token.
  - docker-compose.yml: add CLAIM_AUDITOR_TOKEN=${CLAIM_AUDITOR_TOKEN:-} to both the auditor and n8n service environments. .env.example: commented "# Shared secret for the Auditor service write paths (requirements §28-2); leave empty for the local sandbox" + CLAIM_AUDITOR_TOKEN=.
  - Never log the token value.
  tests: token set + correct header → 200 and facts written on FAIL; wrong header → 401 and facts count unchanged; no header → 401; token unset → 200 and /health auth=false; /health with token set → 200 without header and auth=true.
ACCEPTANCE:
  python3 -m unittest discover -s tests -v     # exit 0
  python3 scripts/check_wired.py               # 79 PASS (W9 unchanged)
  python3 scripts/run_eval.py                  # GREEN
  docker compose config >/dev/null             # valid (say so if docker is absent)
CONSTRAINTS: common.
```

### T-26 — deployable image

```
GOAL: Make the Auditor service deployable as one container image on any HTTPS host reachable from n8n cloud (requirements §28-3 production row), with the memory DB on a mounted volume.
FILES: Dockerfile (new), .dockerignore (new), docker-compose.yml (edit)
SPEC:
  - Dockerfile: FROM python:3.11-slim; create non-root user "auditor"; WORKDIR /app; COPY scripts/ ./scripts/; RUN mkdir -p /app/data && chown -R auditor /app; USER auditor; ENV CLAIM_MEMORY_DB=/app/data/memory.db CLAIM_AUDITOR_PORT=8090 PYTHONUNBUFFERED=1; EXPOSE 8090; HEALTHCHECK --interval=30s --timeout=3s CMD python3 -c "import urllib.request,os;urllib.request.urlopen('http://127.0.0.1:%s/health'%os.environ.get('CLAIM_AUDITOR_PORT','8090'))"; CMD ["python3","scripts/auditor_server.py"]. No pip install.
  - .dockerignore: ignore everything except scripts/ (i.e. "*", "!scripts/", "!scripts/**").
  - docker-compose.yml auditor service: replace the image + ./scripts mount with `build: .`; keep the ./data:/app/data mount, environment, healthcheck, and the service name `auditor` (W9 depends on it).
ACCEPTANCE:
  docker build -t claim-auditor-gate . && docker run -d --rm -p 8090:8090 --name cag claim-auditor-gate && sleep 1 && curl -s localhost:8090/health && docker stop cag   # {"status":"ok",...} (if docker is absent, say so explicitly)
  docker compose config >/dev/null
  python3 scripts/check_wired.py               # 79 PASS, W9 still PASS
  python3 -m unittest discover -s tests        # OK
CONSTRAINTS: common.
```

### T-11 — workflow wiring (run ONLY after T-12/T-13 results are recorded in §28-3; one workflow file per Codex call)

```
GOAL: Wire the production Auditor service into workflow <NN> (n8n/workflows/<NN>-*.json): config fallback, auth header, diagram embedding — as one reviewable JSON change.
FILES: n8n/workflows/<NN>-*.json (edit, this file only)
SPEC:
  - "Auditor Gate (WF-<NN>)" jsCode: resolve config as
      const cfg = (k) => ($env && $env[k]) || ($vars && $vars[k]) || '';
      const auditorUrl = cfg('CLAIM_AUDITOR_URL'), mode = cfg('CLAIM_AUDITOR_MODE') || 'report_only', token = cfg('CLAIM_AUDITOR_TOKEN');
    add header Authorization: `Bearer ${token}` only when token is non-empty. (If §28-3 records that $env throws on n8n cloud, wrap the $env read in try/catch.) WF08 only: send source_lang: 'zh'.
  - New Code node "図解埋め込み (WF-<NN>)" connected between "WordPress投稿データ整形" and "Auditor Gate (WF-<NN>)": POST `${auditorUrl}/embed-diagrams` with {content} and the same auth header; on empty auditorUrl, non-200 or exception → return the input item unchanged (never block). Update `connections` accordingly.
  - Preserve category_id (§29), wp_status logic, prompt loading, and all node names.
ACCEPTANCE:
  python3 -c "import json;json.load(open('n8n/workflows/<NN>-....json',encoding='utf-8'))"
  python3 scripts/check_wired.py               # all PASS (W2/W3/W4/W7/W8/W11 for this file)
  git diff --stat                              # this one file only
CONSTRAINTS: common + DO NOT commit or push; the operator must first run this workflow manually in n8n cloud and confirm a WordPress draft with verdict metadata and a rendered Kroki image (CLAUDE.md §F).
```

Separate call for the prompt rule: `n8n/prompts/article-base.md` — allow at most one ```mermaid fence, only when explaining a flow/structure; acceptance `check_wired` W3/W5 PASS.

### T-28 — WF07–09 category IDs (after T-14 output is pasted)

```
GOAL: Record the WordPress category IDs issued for WF07–09 so W11 checks all nine workflows.
FILES: data/wp-taxonomy.json (edit), n8n/workflows/07-article-writer.json, 08-kimi-zh.json, 09-multi-source-research.json (edit, one file per call)
SPEC: add "wp_id": <id> to the three categories (howto-guide, overseas-ai, deep-dive) using the IDs from the T-14 output; in each workflow's "WordPress投稿データ整形" return object add category_id: <id>, and in "WordPressに下書き投稿" jsonBody add "categories": "={{ [$json.category_id] }}" exactly as WF01–06 do.
ACCEPTANCE: python3 scripts/check_wired.py → W11 PASS for all nine without "(skipped)"; JSON loads.
CONSTRAINTS: common + push together with T-11 after the manual run.
```

## 6. Operator runbook for Phase D (after PR #10 is merged)

1. **T-12**: pick a host (§4), deploy the T-26 image, set `CLAIM_AUDITOR_TOKEN` (generate: `python -c "import secrets;print(secrets.token_urlsafe(32))"`), attach a volume at `/app/data`. Check `curl https://<host>/health` → `"auth": true`.
2. **T-13**: n8n cloud → Settings → Variables: `CLAIM_AUDITOR_URL`, `CLAIM_AUDITOR_MODE=report_only`, `CLAIM_AUDITOR_TOKEN`. Create a throwaway workflow with one Code node: `return [{json:{vars: $vars.CLAIM_AUDITOR_URL, env: (()=>{try{return String($env.CLAIM_AUDITOR_URL)}catch(e){return 'ERR:'+e.message}})()}}]`; run it; paste the output into §28-3. Delete the throwaway workflow.
3. Hand T-11 prompts to Codex (one file per call, WF01 first). Import only WF01 via `scripts/n8n_deploy.ps1` or the UI, run it manually, confirm: WordPress draft exists, verdict metadata present, Kroki image renders in the WP editor. Then push, then proceed WF02→09.
4. **T-14 / T-28 / T-15 / T-16** as tabled in §2.

---

<details>
<summary>🇯🇵 日本語補足 / Japanese notes</summary>

- **検証結果**: PR #10 の主張（Phase A 完了・79 PASS・GREEN・18 tests）はこの環境で再現できた。fork 点も現在の main と一致し、§28〜§32 の採番衝突もない。
- **新たに判明した事実（F1〜F6）**: Windows cp932 での encoding 未指定（F1）と pre-push フックが Windows で未実行だった事実（F2）はローカルゲートの前提を崩すため **T-25 を最優先のブロッカー**にした。T-11 はサービスがクラウドから到達可能になるまで完了条件を満たせないため **T-12/T-13 の後**に移動（F3）。公開サービスに認証が無いと記憶層（ラチェットの入力）が汚染できるため **T-27 を T-12 の前**に追加（F4）。§32-1 D2 は「引用の改変検出」と「丸写し検出」を混同していたため D7 として分離・保留（F5）。クラウド配備にはイメージが必要なため **T-26 Dockerfile** を追加（F6）。
- **クリティカルパス**: T-25 → T-24 → T-27 → T-26 →（PR #10 マージ）→ T-12 → T-13 → T-11 → T-14 → T-28 → T-15 → T-16。
- **順序の原則**: 要件（§3 の差分）を `docs:` コミット → Codex 実装（§5 のプロンプト、1呼び出し1ファイル）→ `git diff` レビュー → ゲート → コミット。workflow JSON の変更（T-11/T-28）は操作者の n8n 手動実行の後にのみ push（CLAUDE.md §F）。
- **T-12 のホスティング判断は操作者のもの**（§4 の比較表）。memory.db の永続化が §23 の 30 日集計に必要な点だけは設計上の制約。

</details>

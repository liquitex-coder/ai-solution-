---
title: "ai-solution- roadmap session — Codex prompts"
date: 2026-09-12
tags: [ai-solution, roadmap, codex, claim-auditor, session-log]
branch: claude/awesome-curie-mu3e69
related: ["[[ROADMAP]]", "docs/requirements.md §26 §28 §30 §31 §31"]
---

# Session 2026-09-12 — Roadmap to Phase 1 + Codex implementation prompts

> Obsidian-compatible session note (user preference: chat content is managed in Obsidian).
> English primary; 🇯🇵 Japanese summary at the end.
> Role split (requirements §26): Claude Code orchestrates, **Codex implements**, operator runs production steps.

## How to run each prompt (operator, local machine — AGENT_WORKFLOW §9-3)

Every `codex` call carries: `cwd: <absolute path to ai-solution- checkout>`, `approval-policy: never`,
`sandbox: workspace-write`. One prompt = one sub-task. After each call: `git diff` → review → next.
Continue a task with `codex-reply` + the returned thread id, not a new session.
Before starting: `git checkout claude/awesome-curie-mu3e69 && git pull origin claude/awesome-curie-mu3e69`.

Common CONSTRAINTS for all prompts (copy into each):

```
CONSTRAINTS (common):
- Python stdlib only (no pip deps). Tests are unittest.TestCase (pytest-compatible), under tests/.
- Never write credentials; env var names only. Never touch n8n/workflows/*.json unless the prompt says so.
- Code comments and identifiers in English. Do not edit docs/requirements.md (spec is frozen for this task).
- Do not commit; leave changes in the working tree for review.
```

---

## T-02 — memory_init.py library API

```
GOAL: Expose the memory layer as importable functions so the Auditor HTTP service (T-03) can write facts without shelling out. CLI behaviour must stay identical.
FILES: scripts/memory_init.py (edit), tests/__init__.py (new, empty), tests/test_memory.py (new)
SPEC:
  - Add public functions in scripts/memory_init.py, each taking an open sqlite3.Connection as first arg:
      ensure_schema(conn) -> None                      # executescript(SCHEMA), idempotent
      insert_fact(conn, content, source_url="", confidence="LOW", verdict="", fail_reason="", skill_ref="", content_hash="") -> int
      insert_scene(conn, title, url, summary="") -> int
      find_duplicate(conn, title, summary="") -> dict   # same payload cmd_check_dup prints
  - Add column `content_hash TEXT DEFAULT ''` to facts in SCHEMA (CREATE TABLE IF NOT EXISTS) AND a migration
    that adds the column on existing DBs (ALTER TABLE ... if missing; check PRAGMA table_info). Add index on content_hash.
  - Refactor cmd_add_fact / cmd_add_scene / cmd_check_dup to call these functions. confidence validation stays.
  - tests/test_memory.py: uses a tempfile DB; covers ensure_schema idempotent (call twice), insert_fact returns id and row visible,
    insert_scene upsert on same url, find_duplicate returns duplicate=True for identical title and False for unrelated, migration adds content_hash to a DB created without it.
ACCEPTANCE:
  python3 -m unittest discover -s tests -v            # exit 0
  python3 scripts/memory_init.py --db /tmp/m.db init && python3 scripts/memory_init.py --db /tmp/m.db add-fact --content x --verdict FAIL --fail-reason FAIL:HYPE --skill-ref 01-github-trending && python3 scripts/memory_init.py --db /tmp/m.db stats   # facts: 1
  python3 scripts/ratchet_check.py --db /tmp/m.db     # exit 0
CONSTRAINTS: common + keep existing CLI subcommands, flags, and printed JSON keys unchanged.
```

## T-03 — scripts/auditor_server.py (POST /audit, GET /health)

```
GOAL: Implement the Auditor Gate HTTP service described in docs/requirements.md §28-2 so the nine n8n Auditor Gate nodes have a real callee.
FILES: scripts/auditor_server.py (new), tests/test_auditor_server.py (new)
SPEC (read docs/requirements.md §28 first; it is the contract):
  - http.server.ThreadingHTTPServer; bind CLAIM_AUDITOR_BIND (default 0.0.0.0), port CLAIM_AUDITOR_PORT (default 8090).
  - GET /health -> 200 {"status":"ok","service":"claim-auditor-gate","memory_db":<bool: db file openable>}
  - POST /audit body {content, source_urls?, skill_ref?, title?} -> 200 {"verdict","reasons","skill_ref","audited_at","fact_id"}.
    verdict/reasons come from content_audit.audit(content, source_urls) unchanged (import via sys.path like run_eval.py does).
    If verdict != PASS: memory_init.insert_fact(...) with fail_reason = category part of reasons[0]
    ("FAIL:HYPE:革命的" -> "FAIL:HYPE"; "UNVERIFIABLE:UNSOURCED_STATS" -> unchanged), content = content[:500],
    source_url = first url or "", confidence = "UNVERIFIABLE" if verdict == UNVERIFIABLE else "LOW",
    content_hash = sha256(content). DB path from CLAIM_MEMORY_DB (default data/memory.db); ensure_schema on startup.
    Any DB error -> log to stderr, respond normally with fact_id null (never block the gate).
  - Response keys must not collide with title/content/wp_status/source_url (the gate spreads the result).
  - 400 {"error": ...} for invalid JSON or missing/non-string content; 404 otherwise. Content-Type application/json; charset utf-8.
  - Request log: one JSON line to stdout {path, status, verdict, skill_ref, ms}; never log content.
  - `if __name__ == "__main__": main()`; expose `make_server(bind, port, db_path)` for tests.
  - Also register a route table so T-10 can add POST /embed-diagrams without touching /audit logic.
  - tests: start make_server("127.0.0.1", 0, tmp_db) in a thread; urllib requests for: health ok; PASS article (use a 3x<h2> article with <a href> link) -> PASS and facts count 0;
    HYPE article -> FAIL, facts count 1 with fail_reason "FAIL:HYPE" and skill_ref echoed; unsourced numeric article -> UNVERIFIABLE with confidence UNVERIFIABLE row;
    invalid JSON -> 400; db_path pointing into a non-writable location (e.g. "/proc/x/y.db") -> still 200 with fact_id null.
ACCEPTANCE:
  python3 -m unittest discover -s tests -v                              # exit 0
  (CLAIM_AUDITOR_PORT=8090 python3 scripts/auditor_server.py & sleep 1; curl -s localhost:8090/health; kill %1)   # {"status":"ok",...}
  python3 scripts/run_eval.py                                           # still GREEN (audit() untouched)
CONSTRAINTS: common + do not modify scripts/content_audit.py in this task.
```

## T-04 — docker-compose auditor service + env

```
GOAL: Wire the Auditor service into the local sandbox so n8n's Code nodes see CLAIM_AUDITOR_URL (requirements §28-3).
FILES: docker-compose.yml (edit), .env.example (edit)
SPEC:
  - Add service `auditor`: image python:3.11-slim, working_dir /app, volumes ./scripts:/app/scripts:ro and ./data:/app/data,
    environment CLAIM_MEMORY_DB=/app/data/memory.db, CLAIM_AUDITOR_PORT=8090, command ["python3","scripts/auditor_server.py"], expose 8090 (no host port needed), healthcheck via python3 -c urllib GET /health.
  - n8n service: add environment CLAIM_AUDITOR_URL=http://auditor:8090, CLAIM_AUDITOR_MODE=${CLAIM_AUDITOR_MODE:-report_only}, N8N_BLOCK_ENV_ACCESS_IN_NODE=false; depends_on auditor.
  - .env.example: add a commented block "# Claim-Auditor gate rollout mode (requirements §22-3): report_only | canary | full" and CLAIM_AUDITOR_MODE=report_only.
ACCEPTANCE:
  docker compose config >/dev/null      # valid (skip if docker absent, say so)
  grep -n "CLAIM_AUDITOR_URL=http://auditor:8090" docker-compose.yml
  python3 scripts/check_wired.py        # still green (W9 arrives in T-05)
CONSTRAINTS: common.
```

## T-05 — check_wired.py W8 / W9 / W10

```
GOAL: Extend the design-vs-wired gate per docs/requirements.md §30-1 so the "gate without a callee" and taxonomy drift can never recur.
FILES: scripts/check_wired.py (edit)
SPEC:
  - W8: for each workflow, extract skill_ref from the Auditor Gate jsCode (regex skill_ref:\s*'([^']+)'); FAIL if missing or not in ratchet_check.SKILL_PROMPTS (import ratchet_check via sys.path insert of scripts/).
  - W9: FAIL unless scripts/auditor_server.py exists AND docker-compose.yml contains a service named auditor AND the n8n service environment contains CLAIM_AUDITOR_URL. Parse docker-compose.yml with a minimal line-based scan (no PyYAML).
  - W10: load data/wp-taxonomy.json; FAIL if set(workflow_category_map) != {"WF-01".."WF-09"} or any mapped slug is not in categories[].slug or any categories[].source_workflow is outside WF-01..09.
  - W11: for each workflow, regex `category_id:\s*(\d+)` in the WP整形 jsCode; look up the category whose source_workflow matches the WF number; if that category has a numeric `wp_id`, FAIL unless equal; if no `wp_id` or no category_id in the workflow, print PASS with "(skipped: no wp_id)" and do not fail.
  - Keep output format ("  PASS  W8 ...") and Summary line; docstring lists W8-W10.
ACCEPTANCE:
  python3 scripts/check_wired.py ; echo exit=$?   # W10 must FAIL until T-07 lands; W9 must PASS if T-03/T-04 are in the tree. Report the exact FAIL lines.
CONSTRAINTS: common + no new LIBRARY_ONLY entries.
```

## T-06 — CI + pre-push + CLAUDE.md §D

```
GOAL: Make run_eval and the unittest suite mandatory gates locally and in CI (requirements §22-2, §28-4).
FILES: .github/workflows/wired-check.yml (edit), .githooks/pre-push (edit), CLAUDE.md (edit §D only)
SPEC:
  - CI job steps after check_wired: "Run content-audit eval set" python3 scripts/run_eval.py; "Run unit tests" python3 -m unittest discover -s tests -v. Keep pure stdlib, no pip.
  - pre-push: add python3 -m unittest discover -s tests after run_eval.
  - CLAUDE.md §D: add the unittest line with a one-line comment "unit tests（要件§28-4・§31-3）". Change nothing else in CLAUDE.md.
ACCEPTANCE:
  bash -n .githooks/pre-push && grep -n unittest .github/workflows/wired-check.yml .githooks/pre-push CLAUDE.md
CONSTRAINTS: common.
```

## T-07 — data/wp-taxonomy.json alignment

```
GOAL: Make data/wp-taxonomy.json match the canonical WF→category table in docs/requirements.md §30-2 (drop reporters-era WF-10..13).
FILES: data/wp-taxonomy.json (edit)
SPEC:
  - categories: keep WF-01..06 entries unchanged; replace WF-07 with {name:"使い方ガイド", slug:"howto-guide", description:"AIツール・自動化のステップバイステップ解説（手動トリガーの任意テーマ記事）", source_workflow:"WF-07"};
    WF-08 with {name:"海外AI動向", slug:"overseas-ai", description:"中国語圏などのAI情報源をKimi経由で翻訳・要約（翻訳ラベル付き）", source_workflow:"WF-08"};
    WF-09 with {name:"深掘り解説", slug:"deep-dive", description:"9媒体横断取材に基づく確度スコア付きの深掘り記事", source_workflow:"WF-09"}.
    Remove factcheck / hands-on-review / comparison / breaking-news / reader-qa / changelog-tracker and the WF-13 deep-dive entry.
  - Add `wp_id` (integer) to the six WF01–06 categories using the IDs in docs/requirements.md §29-2 (PR #9 table): github-trending 790464620, ai-official-news 790464621, youtube-summary 1564589, sns-pickup 790464623, note-creator 13765228, weekly-trend-report 130534926. WF07–09 get no wp_id yet (assigned after wp-init re-run, T-14).
  - workflow_category_map: exactly WF-01..WF-09 with the slugs above. tags unchanged. Update _comment to mention §30-2 and that wp_id is the single source of truth for W11.
ACCEPTANCE:
  python3 -c "import json;json.load(open('data/wp-taxonomy.json'))" && python3 scripts/check_wired.py | grep W10   # all PASS
CONSTRAINTS: common.
```

## T-08 — README refresh

```
GOAL: Remove stale statements from README.md and describe the pipeline as it exists on this branch (WF01–09, Auditor Gate + service, staged rollout).
FILES: README.md (edit)
SPEC:
  - Workflows table: rows 01–09 (07 article-writer manual trigger; 08 kimi-zh every 6h Kimi moonshot-v1-128k; 09 multi-source-research Fri 07:00 JST). Add a column "Category slug" from data/wp-taxonomy.json.
  - Architecture diagram: add Auditor Gate → scripts/auditor_server.py (/audit, report_only|canary|full) between Claude API and WordPress; mention memory layer (data/memory.db) written on FAIL.
  - Prompt Management: list all files in n8n/prompts/ (13) and note three LIBRARY_ONLY legacy variants (see scripts/check_wired.py).
  - Add "Local gates" section mirroring CLAUDE.md §D (check_wired, run_eval, unittest, ratchet_check).
  - Phase roadmap table: Phase 0 ✅, Phase 1 ⏳ (link docs/ROADMAP.md), keep Phase 2/3.
  - Environment variables table: add CLAIM_AUDITOR_MODE, KIMI_API_KEY, FAL_API_KEY, WP_BEARER_TOKEN/WP_SITE (production, §24).
  - Keep EN primary + the <details id="japanese"> block; mirror every change in the JA block.
ACCEPTANCE:
  grep -c "09-multi-source-research" README.md   # >= 1
  grep -n "auditor_server" README.md               # present
  ! grep -n "sonnet-5" README.md || true            # check model names against n8n/workflows/*.json and fix if they differ (report what you found)
CONSTRAINTS: common + do not invent features: every statement must match a file in the repo (cite path in your final message).
```

## T-09 — SETUP_GUIDE + n8n_deploy.ps1 stale fixes

```
GOAL: Bring n8n/SETUP_GUIDE.md and scripts/n8n_deploy.ps1 in line with current behaviour (Auditor Gate on all WFs, WF06 no longer auto-publishes, §25-4 resolved, §28 service).
FILES: n8n/SETUP_GUIDE.md (edit), scripts/n8n_deploy.ps1 (edit: final Write-Host reminder block only)
SPEC:
  - Step 6: delete the sentence saying WF06 publishes immediately; state that all WFs post drafts and the verdict/audit_mode fields are visible in the n8n execution output.
  - Workflow table: add 07/08/09 with schedule and required APIs (07 manual; 08 every 6h, Kimi; 09 Fri 07:00 JST, YouTube+GitHub optional).
  - New Step 4b "Claim-Auditor gate variables": CLAIM_AUDITOR_URL (public HTTPS of the §28 service; local sandbox uses http://auditor:8090 automatically), CLAIM_AUDITOR_MODE=report_only.
    Add an explicit verification step: run WF07 manually and check the execution output for verdict != "SKIP"; if $env is unavailable on n8n cloud, note that T-11 ($vars fallback) is required — do NOT assert either way.
  - Step 0-5 / 0-6: import 01–09 (not 01–06); add "docker compose ps shows auditor healthy" and "curl localhost:8090/health" is not exposed — use `docker compose exec auditor python3 -c ...` or check n8n execution output.
  - n8n_deploy.ps1: remove the last reminder bullet about the YouTube auth mismatch (resolved, §25-4); add a reminder to set CLAIM_AUDITOR_URL / CLAIM_AUDITOR_MODE.
ACCEPTANCE:
  ! grep -n "即公開" n8n/SETUP_GUIDE.md ; grep -n "CLAIM_AUDITOR_URL" n8n/SETUP_GUIDE.md scripts/n8n_deploy.ps1
CONSTRAINTS: common + Japanese prose is fine in SETUP_GUIDE (existing language); keep headings' numbering.
```

## T-10 — kroki_embed.py + POST /embed-diagrams

```
GOAL: Implement docs/requirements.md §31: convert ```mermaid fences into Kroki <img> figures, exposed on the §28 service as POST /embed-diagrams, without affecting verdicts.
FILES: scripts/kroki_embed.py (new), scripts/auditor_server.py (edit: register route only), tests/test_kroki_embed.py (new)
SPEC:
  - embed_diagrams(html: str, base_url: str | None = None) -> tuple[str, int]. base_url defaults to env KROKI_BASE_URL or "https://kroki.io".
    Fence regex: ```mermaid\n(.*?)``` (DOTALL, also tolerate <pre><code class="language-mermaid">…</code></pre>).
    Encoding: base64.urlsafe_b64encode(zlib.compress(src.encode("utf-8"), 9)).decode("ascii") (Kroki's documented Python example; keep padding).
    Replacement: <figure class="ai-navi-diagram"><img src="{base}/mermaid/svg/{enc}" alt="図解" loading="lazy"></figure>.
    If the full URL exceeds 4000 chars: leave the source as <pre class="mermaid-fallback">…escaped…</pre> and do not count it.
  - CLI: python3 scripts/kroki_embed.py --stdin | --content-file F  → prints converted HTML to stdout, count to stderr.
  - Route: POST /embed-diagrams {content} -> 200 {"content": html, "diagrams": n}; 400 on missing content. Implemented by importing kroki_embed; no change to /audit behaviour.
  - tests: one fence -> one <figure> and decode(base64url→zlib) == original source; no fence -> identical output and 0; oversized -> <pre> fallback and 0; endpoint round-trip via the test server from T-03.
ACCEPTANCE:
  python3 -m unittest discover -s tests -v && printf '<h2>a</h2>\n```mermaid\ngraph TD; A-->B\n```\n' | python3 scripts/kroki_embed.py --stdin | grep -c "kroki.io/mermaid/svg/"   # 1
CONSTRAINTS: common + no network calls anywhere in this module.
```

## T-24 — Auditor spec/code parity (§32-1), eval cases first

```
GOAL: Close the drift rows D1, D2, D3, D5 in docs/requirements.md §32-1 with an evaluation-set-first change; new checks are WARN-only until 30-day observation.
FILES: data/eval_set.json (edit: append cases), scripts/content_audit.py (edit), scripts/auditor_server.py (edit: pass-through of source_text/source_lang, ALREADY_REJECTED lookup), tests/test_content_audit.py (new)
SPEC (do steps in this order and keep run_eval GREEN after each):
  1. Append eval cases with ids q-ratio-30-pass (blockquote ≈30% of text, has link → expected PASS), q-ratio-35-fail (≈35% → expected FAIL). Then change QUOTE_DOMINANCE_RATIO to 0.34 (one third, §17-1). Update the comment to cite §17-1/§32-1 D1. Adjust any existing case that now flips ONLY if its label was wrong under §17-1; report each such case id.
  2. audit(content, source_urls=None, source_text=None, source_lang=None). D2: when source_text given and source_lang in (None,"ja"): for each blockquote, difflib.SequenceMatcher(None, quote, best-matching window of source_text).ratio() < 0.85 → append "WARN:VERBATIM_COPY" (WARN prefix: does NOT change verdict). D3: when source_lang in ("en","zh"): require ("本記事は" in text and "翻訳" in text and any(url in content for url in source_urls)) else append "WARN:MISSING_TRANSLATION_LABEL". Warnings are returned in a new key "warnings": [...] and never in "reasons".
  3. D5: auditor_server computes sha256(content); before auditing, if a facts row with that content_hash and verdict FAIL exists → respond verdict "FAIL", reasons ["FAIL:ALREADY_REJECTED"], do not insert a second row. Add tests.
  4. tests/test_content_audit.py: unit tests for each new branch incl. that warnings never change verdict.
ACCEPTANCE:
  python3 scripts/run_eval.py        # cases >= 52, FP=0, FN=0, GREEN
  python3 -m unittest discover -s tests -v
CONSTRAINTS: common + INV-R2: no LLM, no network; verdict precedence FAIL > UNVERIFIABLE > PASS unchanged; do not promote WARN to FAIL in this task.
```

---

## Operator checklist for T-11 (workflow JSON — manual n8n test before push)

After T-10 is merged, ask Codex to patch `n8n/workflows/*.json` (insert "図解埋め込み" Code node between WP整形 and Auditor Gate calling `${auditorUrl}/embed-diagrams`; add `const auditorUrl = $env.CLAIM_AUDITOR_URL || ($vars && $vars.CLAIM_AUDITOR_URL) || '';` fallback in every gate; allow one ```mermaid fence in `n8n/prompts/article-base.md`). Then **run WF07 manually in n8n**, confirm a WordPress draft with a Kroki image and a non-SKIP verdict, paste the execution log into the PR, and only then push (CLAUDE.md §F).

<details>
<summary>🇯🇵 日本語まとめ</summary>

- このノートは 2026-09-12 セッションの成果物。要件 §28〜§32 と `docs/ROADMAP.md` を先に確定し、実装は Codex に委譲する（§26）。
- 各プロンプトは GOAL / FILES / SPEC / ACCEPTANCE / CONSTRAINTS 形式。1回の `codex` 呼び出しで1タスク。毎回 `git diff` を確認してから次へ。
- 実行順: T-02 → T-03 → T-04 → T-05 → T-07（W10 を緑にする）→ T-06 → T-08 → T-09 → T-10 → T-24。T-11 以降の workflow JSON 変更は操作者の n8n 手動実行後にのみ push。
- 未検証事項（推測しない）: n8n cloud での `$env` 可用性、WordPress.com での Kroki 外部画像表示。どちらも T-11/T-13 の実機確認で確定する。

</details>

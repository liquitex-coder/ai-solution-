# ROADMAP — ai-solution- (AI Navi) to "Phase 1 in production"

> **Language / 言語:** English (primary) | 🇯🇵 日本語は各 Phase 末尾の `<details>`
>
> Source of truth for requirements: `docs/requirements.md` (§28–§31 added 2026-09-12).
> Task IDs (T-NN) are registered in the session task list and referenced from PR descriptions.
> Roles (requirements §26): **Claude Code = orchestrator** (spec, roadmap, review, gates),
> **Codex = implementer** (code diffs), **operator = production actions** (keys, hosting, n8n runs).

## Definition of "complete" for this roadmap

**Phase 1 core pipeline in production** (README "Phase 1"): WF01–09 imported into n8n cloud,
each Auditor Gate calling a *real* `/audit` service, all posts landing as WordPress drafts with a
recorded verdict (`CLAIM_AUDITOR_MODE=report_only`), and every code path covered by a local gate
(`check_wired`, `run_eval`, `unittest`) that CI also runs. Phase 2/3 items are listed for
sequencing but are not part of this definition.

## Evidence baseline (2026-09-12, branch `claude/awesome-curie-mu3e69` == `origin/main`)

| Gate | Result |
|---|---|
| `python3 scripts/check_wired.py` | 59 PASS, 0 FAIL |
| `python3 scripts/run_eval.py` | 50 cases, FP=0, FN=0 (GREEN) |
| `python3 scripts/ratchet_check.py` | "no memory db" (no production writer exists) |
| `tests/` | absent |

Gaps verified in code (details in requirements §28-1, §30, §31):

1. All nine Auditor Gate nodes `fetch("${CLAIM_AUDITOR_URL}/audit")`, but no process in the repo serves `/audit` → production verdict is always `SKIP`.
2. Nothing writes to `data/memory.db` → `ratchet_check.py` has no input.
3. No automated tests; CI runs only `check_wired.py`.
4. `data/wp-taxonomy.json` still carries reporters-era WF-10..13 and mismatched WF-07/08/09 mappings (contradicts §27).
5. README / SETUP_GUIDE / `n8n_deploy.ps1` contain stale statements (WF table 01–06 only, "WF06 publishes immediately", resolved §25-4 warning).
6. §7 Mermaid/Kroki, §8 EN SEO meta, yt-dlp captions: designed, not implemented.
7. Auditor spec ⇄ code drift (§32-1): three different quote-ratio thresholds; `VERBATIM_COPY`, `MISSING_TRANSLATION_LABEL`, `ALREADY_REJECTED` documented in `n8n/skills/20-auditor-gate.md` but absent from `scripts/content_audit.py`.

---

## Open-PR coordination (2026-09-12)

Three open PRs touch `docs/requirements.md` and all append new sections at the end, so they conflict pairwise
(trial merges of #8 and #9 into this branch both conflict on that file).

| PR | Content | Proposed handling |
|---|---|---|
| [#9](https://github.com/liquitex-coder/ai-solution-/pull/9) | §29 WordPress category IDs + `category_id` in WF01–06 JSON | **Merged 2026-09-12** (`fbf96ed`, operator decision). This branch merged `main` afterwards; §29 is its section, W11 / `wp_id` (T-05, T-07) build on it |
| [#8](https://github.com/liquitex-coder/ai-solution-/pull/8) | §13/§15 corrections + §28 completion roadmap | **Closed 2026-09-12 as superseded by this PR** (operator decision): verified facts ported into §13/§15 here; its §28 roadmap replaced by this file |
| [#10](https://github.com/liquitex-coder/ai-solution-/pull/10) (this) | §28 Auditor service, §30 W8–W11, §31 Kroki, §32 auditor drift | Renumbered on 2026-09-12 to avoid #9's §29; merge after #9 (merge `main` in, no rebase) |

Note on #9: its workflow JSON edits have not had the manual n8n run that CLAUDE.md §F requires; T-15 covers that run.

## Phase A — Make the Auditor Gate real (service + memory wiring)

| ID | Owner | Task | Done when |
|---|---|---|---|
| T-01 | Claude | Requirements §28–§31, §13/§15 refresh, this roadmap, session note with Codex prompts | standalone `docs:` commit pushed, draft PR open |
| T-02 ✅ | Codex | `scripts/memory_init.py`: extract `insert_fact()`, `insert_scene()`, `find_duplicate()` library functions (CLI unchanged) + `tests/test_memory.py` | done 2026-09-12 (`114bcb8`): unittest 5/5 OK on Linux; legacy-DB migration verified |
| T-03 ✅ | Codex | `scripts/auditor_server.py` per §28-2 (`GET /health`, `POST /audit`, facts write on FAIL/UNVERIFIABLE) + `tests/test_auditor_server.py` | done 2026-09-12 (`0763a20`): unittest 12/12 OK on Linux; live `/health`, PASS/FAIL/400/404 verified; facts row + ratchet read confirmed |
| T-04 ✅ | Codex | `docker-compose.yml` `auditor` service + n8n env `CLAIM_AUDITOR_URL`/`CLAIM_AUDITOR_MODE`; `.env.example` | done 2026-09-12 (`f2a9361`): `docker compose config` valid on Linux; healthcheck, depends_on service_healthy, env keys verified |
| T-05 ✅ | Codex | `scripts/check_wired.py` W8/W9/W10/W11 per §30-1 (W11 = workflow `category_id` ⇄ taxonomy `wp_id`) | done 2026-09-12 (`539d8d7`): 79 PASS; negative checks reproduced (wrong wp_id → W11 FAIL, renamed service / dropped URL → W9 FAIL, unknown skill_ref → W8 FAIL) |
| T-06 ✅ | Codex | CI `wired-check.yml` + `.githooks/pre-push` + `CLAUDE.md §D` run `check_wired`, `run_eval`, `unittest` | done 2026-09-12 (`54f7427`): pre-push hook ends "all gates green" locally; CI job 103544633368 green on `54f7427` with all three steps |

## Roadmap v2 (2026-09-13) — sequencing supersedes the 2026-09-12 order

Verified in code on 2026-09-13 (details and Codex prompts: `docs/sessions/2026-09-13-roadmap-v2-codex-prompts.md`):
F1 twenty `read_text/write_text` calls without `encoding=` in `scripts/` (gates break on Windows cp932);
F2 `.githooks/pre-push` calls `python3`, which is the Store stub on the operator's Windows;
F3 T-11 needs the service reachable from n8n cloud; F4 `auditor_server.py` has no auth (public `/audit` could poison `memory.db`);
F5 §32-1 D2 conflated ⑤改変禁止 with verbatim copying (now D7); F6 no Dockerfile for cloud hosting.

Critical path: **T-25 → T-24 → T-27 → T-26 → (merge PR #10) → T-12 → T-13 → T-11 → T-14 → T-28 → T-15 → T-16**.

## Phase B — Drift cleanup

| ID | Owner | Task | Done when |
|---|---|---|---|
| T-07 ✅ | Codex | `data/wp-taxonomy.json` → exactly WF-01..09 per §30-2, plus `wp_id` per category from §29-2 (WF01–06) | done 2026-09-12 (`4e275cd`): 9 categories, map == WF-01..09, six `wp_id` match §29-2 |
| T-08 ✅ | Codex | `README.md`: WF01–09 table, Auditor service in architecture, phase status, JA mirror | done 2026-09-12 (`90b7a1f`): model names, 13 prompts, slugs and JA block cross-checked against the repo |
| T-09 ✅ | Codex | `n8n/SETUP_GUIDE.md` (Step 6 fix, WF07–09, `CLAIM_AUDITOR_*` setup, n8n cloud `$env` check step) + `scripts/n8n_deploy.ps1` stale reminder removal | done 2026-09-12 (`8e786f3`) |
| T-25 ✅ | Codex | **Gate portability** (§33): explicit `encoding="utf-8"` on every text I/O in `scripts/`; `tests/test_encoding_guard.py` AST sensor; `.githooks/pre-push` falls back to `py -3` | done 2026-09-13 (`a6cd6ae`): unittest 29/29 incl. guard; `check_wired` 79 PASS; `py -3 scripts/check_wired.py` and `py -3 -m unittest` both exit 0 in a cp932 console without `PYTHONUTF8` (evidence on PR #10); also fixed `scripts/ratchet_check.py`'s em dash (found while verifying the full pre-push chain) |
| T-24 ✅ | Codex | Auditor spec/code parity per §32-1 D1/D2/D3/D5 (eval cases first; new checks are `WARN:` only per §32-2; D7 deferred) | done 2026-09-13 (`5012356`): `run_eval` 52 cases FP=0/FN=0; `tests/test_content_audit.py` green; §32-1 D1/D2/D3/D5 rows flipped to implemented; WARN entries live in `reasons` (single list, no separate field) |

## Phase C — Service hardening + visual layer

| ID | Owner | Task | Done when |
|---|---|---|---|
| T-10 ✅ | Codex | `scripts/kroki_embed.py` + `POST /embed-diagrams` + `tests/test_kroki_embed.py` | done 2026-09-12 (`10f2532`); endpoint unconsumed until T-11 |
| T-27 ✅ | Codex | `CLAIM_AUDITOR_TOKEN` shared secret on `POST /audit` and `POST /embed-diagrams` (§28-2); `/health` open with `auth` flag; sandbox zero-config | done 2026-09-13 (`3ad09b2`): unittest 36/36 incl. correct/wrong/missing token, `/health` auth=true|false; `check_wired` 79 PASS (W9 unchanged) |
| T-26 ✅ | Codex | `Dockerfile` + `.dockerignore`; compose builds the image; `$PORT` honoured; memory DB on a volume | done 2026-09-13 (`70510a6`): `docker compose config` valid, `check_wired`/unittest green; **`docker build`/`docker run` not verified this session — Docker Desktop daemon unavailable on the operator's machine** |
| T-11 | Codex + operator | **After T-13.** WF01–09 wiring, one file per Codex call: `$env`→`$vars` config fallback, `Authorization: Bearer` when token set, WF08 `source_lang:'zh'`, "図解埋め込み" node, `article-base.md` mermaid rule | push **only after** the operator's manual run shows a WP draft with verdict metadata and a rendered Kroki image (CLAUDE.md §F) |

## Phase D — Production rollout (operator)

| ID | Owner | Task | Done when |
|---|---|---|---|
| T-12 | operator | Choose hosting (Fly.io volume / Render / Cloudflare Tunnel, table in the v2 note) and deploy the T-26 image with `CLAIM_AUDITOR_TOKEN`; record host in §28-3 | `GET https://<host>/health` → `{"status":"ok","auth":true}` |
| T-13 | operator | n8n cloud Variables: `CLAIM_AUDITOR_URL`, `CLAIM_AUDITOR_MODE=report_only`, `CLAIM_AUDITOR_TOKEN`; throwaway Code node records whether `$env` is readable; result into §28-3 / §15 | one execution log shows the values readable via `$vars` |
| T-14 | operator | Re-run `scripts/wp-init.ps1` / `.sh` with the corrected taxonomy (WF07–09) | output pasted in PR / session note |
| T-28 | Codex | Record WF07–09 `wp_id` in `data/wp-taxonomy.json` and `category_id` in the 07/08/09 workflow JSON | W11 PASS for 9/9 without "skipped"; pushed together with T-11 after the manual run |
| T-15 | operator | Manual run WF01→02→05→06→03→04→07→08→09, confirm drafts + verdict metadata + category, then Activate | execution logs pasted; README Phase 1 = ✅ |
| T-16 | operator | 30-day `report_only` review → `canary` (§22-3) with human signature (INV-R1) | signed note in requirements |

## Phase E — Phase 2 features (after Phase 1 is live)

| ID | Owner | Task |
|---|---|---|
| T-17 | Codex + operator | Memory pre-query: `POST /check-dup` before generation, scene write after publish (§19-4, §19-7) |
| T-18 | Claude → Codex | WF03 yt-dlp captions sidecar (spec first; n8n cloud cannot run binaries) |
| T-19 | Codex + operator | EN SEO meta parallel generation (§8) |
| T-20 | Codex + operator | Flux.1 featured image via fal.ai (§7, 15%) |
| T-21 | Codex | Ratchet R1: proposals as draft PRs (§23-2) after 30-day R0 evaluation |
| T-22 | cross-repo | claim-crew / claim-evolve integration (§5, §18-4) |

## Phase F — Phase 3 (monetization, §13)

| ID | Task |
|---|---|
| T-23 | Build-process article series, Claim Platform badges, paid sources (X API), UGC prompts, EN full translations |

---

## Progress

Formula: `% = completed / total × 100` (rounded). Update at every task completion.

| Scope | Done | Total | % |
|---|---|---|---|
| Phase A | 6 | 6 | 100% |
| Phase B | 5 | 5 | 100% |
| Phase C | 3 | 4 | 75% |
| Phase D | 0 | 6 | 0% |
| Phase 1 definition (A–D) | 14 | 21 | 67% |
| Whole roadmap (A–F) | 14 | 28 | 50% |

<details>
<summary>🇯🇵 日本語補足 / Japanese notes</summary>

- **完成の定義**: README の Phase 1（コアパイプライン本番稼働）。WF01〜09 が n8n cloud で稼働し、Auditor Gate が実在する `/audit` を呼び、全記事が verdict 付きで WordPress 下書きになる（`report_only`）。加えて全コードパスがローカルゲート（`check_wired` / `run_eval` / `unittest`）と CI で検証される状態。
- **役割**: Claude Code は要件・ロードマップ・レビュー・ゲート確認。実装差分は Codex（プロンプトは `docs/sessions/2026-09-12-roadmap-codex-prompts.md`）。本番操作（鍵・ホスティング・n8n 手動実行）は操作者。
- **最重要ギャップ**: ゲートの呼び先サービスが無く、本番では全件 `SKIP`。Phase A で解消する。
- **workflow JSON の変更（T-11 / T-17 / T-19 / T-20）** は CLAUDE.md §F により、操作者の n8n 手動実行→WP 下書き確認の後にのみ push する。
- **未検証事項**: n8n cloud で Code ノードの `$env` が使えるか（docs.n8n.io が本セッションでは取得不可）。T-13 で確認し、不可なら T-11 の `$vars` フォールバックが必須になる。

</details>

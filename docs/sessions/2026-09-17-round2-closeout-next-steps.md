---
title: "Round-2 close-out and next steps — T-24/T-26 verified, T-12 in progress"
date: 2026-09-17
repo: ai-solution-
branch: claude/bold-heisenberg-4hwfbf
base: main @ b36ec28 (PR #13 merge)
session: https://claude.ai/code/session_013b6sG2N3tKaYuVxjS6LCJ3
tags: [claim-platform, ai-solution, auditor, roadmap, review, session-log]
related: ["[[ROADMAP]]", "[[2026-09-13-t24-t27-review]]", "[[2026-09-13-roadmap-v2-codex-prompts]]", "docs/requirements.md §28-3 §32-1"]
status: active
---

# Round-2 close-out and next steps (2026-09-17)

> English primary; 🇯🇵 Japanese summary at the end.
> Chat with the operator was in Japanese; this note is the Obsidian record.
> Question answered this session: "what comes next for ai-solution-?"

## 1. Evidence (Linux, head `b36ec28` == `origin/main`)

```
python3 scripts/check_wired.py            -> Summary: 79 PASS, 0 FAIL
python3 scripts/run_eval.py               -> cases: 52  exact-verdict match: 52/52  RESULT: GREEN (FP=0, FN=0)
python3 -m unittest discover -s tests     -> Ran 46 tests in 10.895s  OK
git rev-list --left-right --count origin/main...HEAD -> 0 0
```

Code checked for the round-2 acceptance items (file:line at `b36ec28`):

| Item | Where | Result |
|---|---|---|
| D7 rename `WARN:QUOTE_ALTERED` | `scripts/content_audit.py` L88–L104 | present, shares `SIMILARITY_THRESHOLD = 0.85` (L47) |
| Real D2 `WARN:VERBATIM_COPY` (body outside blockquotes, 200-char windows, step 100, longest match ≥ 120) | `scripts/content_audit.py` L106–L124 | present, at most one per audit |
| D5 non-PASS lookup | `scripts/auditor_server.py` L72–L85 `find_prior_fact`, SQL `verdict != 'PASS'` | present |
| Non-ASCII Bearer → 401 | `scripts/auditor_server.py` L110–L118 bytes `hmac.compare_digest` | present |
| `PORT` precedence | `scripts/auditor_server.py` L272 `resolve_port`; `Dockerfile` L11 ENV without `CLAIM_AUDITOR_PORT`, L16 HEALTHCHECK same order | present |

Operator evidence on PR #13 (2026-09-15, Docker 29.4.3): `docker build` OK; `-e PORT=10000` → `/health` 200
`{"memory_db": true, "auth": false}`; bind-mounted volume written (`memory.db` 65536 bytes) with
`auth: true` when a token is set. Caveat recorded there: Docker Desktop cannot reproduce Fly's
root-owned volume, so §28-3 (iii) stays a post-deploy check.

## 2. Verdicts

| Task | Verdict | Basis |
|---|---|---|
| T-24 round 2 | ✅ accepted | every ACCEPTANCE line of the 2026-09-13 prompt green; eval set unchanged (52 cases) |
| T-26 round 2 | ✅ accepted | unit tests + operator docker run; Fly volume ownership deferred to T-12 |
| T-12 | 🔄 in progress | hosting decided (PR #12); [PR #14](https://github.com/liquitex-coder/ai-solution-/pull/14) renames the Fly app to `ainavi-auditor-gate`; no deployment date or hostname in §28-3 yet |

## 3. Findings (auditor self-apply on the repo state)

- **F-1 docs drift (fixed in this PR)**: `docs/ROADMAP.md` still showed T-24/T-26 as 🔁 and the
  Progress table at 12/28 although PR #13 had merged; `docs/requirements.md` §32-1 D2 read
  「未実装（差し戻し）」and D5 carried a 残課題 that `9539897` resolved. Both now cite the
  commit and code lines above.
- **F-2 PR #14 wording (not fixed here — other branch)**: `FLY_DEPLOY.md` in PR #14 says
  "renamed from `ainavi-auditor-gate`"; the old name was `claim-auditor`. One-line fix before merge.
- **F-3 unverified**: whether the operator has already run `flyctl deploy`. Nothing in the repo
  records it; the PR #14 Test plan line for the deploy is unchecked. T-12 is not done until §28-3
  carries the hostname, the completion date and a `/health` response with `auth: true` and
  `memory_db: true`.

## 4. Next steps (critical path unchanged)

1. Merge PR #14 after the F-2 fix (operator).
2. **T-12** (operator): `flyctl deploy -c fly.toml --app ainavi-auditor-gate` → `/health` →
   record in §28-3. If `memory_db: false`, apply the `chown` remediation in `FLY_DEPLOY.md`.
3. **T-13** (operator): n8n cloud Variables + `$env` readability measurement → §28-3 / §15.
4. **T-11** (Codex + operator): WF01–09 wiring; push only after the manual run (CLAUDE.md §F).
5. T-14 → T-28 → T-15 → T-16 as in the ROADMAP.

## 5. Progress

```
✅ T-24 auditor spec/code parity round 2 — done (PR #13)
✅ T-26 deployable image round 2 — done (PR #13)
🔄 T-12 Fly.io deploy — in progress (PR #14 open)
📊 Phase B 5/5 (100%) · Phase C 3/4 (75%) · Phase D 0/6 (0%)
📊 Phase 1 scope (A–D) 14/21 (67%) · whole roadmap 14/28 (50%)
```

Session tasks (this note's PR): T-29 ROADMAP sync ✅ · T-30 §32-1 rows ✅ · T-31 this note ✅ ·
T-32 gates + push + draft PR — 📊 4/4 (100%) once the PR is open.

<details>
<summary>🇯🇵 日本語要約</summary>

- 質問「ai-solution- の次にやること」への回答: **Phase D の T-12（Fly.io へ Auditor Gate をデプロイ）**。
  その前提として、コードに追いついていなかった ROADMAP と要件 §32-1 を本 PR で同期した。
- T-24 / T-26 の第2ラウンドは PR #13 で main に入っており、本セッションで Linux 上のゲート
  （check_wired 79 PASS / eval 52 FP=0 FN=0 / unittest 46 OK）とコード行を再確認して ✅ とした。
- PR #14（Fly app 名の改名）は open。FLY_DEPLOY.md の「renamed from `ainavi-auditor-gate`」は
  `claim-auditor` の誤記なので、マージ前に修正が必要。
- 未検証: 操作者が `flyctl deploy` を実行済みかはリポジトリから判断できない。§28-3 にホスト名・
  完了日・`/health` 実測が入って T-12 完了。
- 次: PR #14 マージ → T-12 → T-13 → T-11（手動実行後にのみ push）→ T-14 → T-28 → T-15 → T-16。

</details>

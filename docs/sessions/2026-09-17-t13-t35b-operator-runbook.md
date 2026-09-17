# T-13 / T-35b Operator Runbook (requirements §32-1 D10, §34-9)

> Owner: operator. Claude Code cannot perform n8n cloud logins or manual workflow
> runs — this document exists so the operator can execute these steps without
> a live session, and hand the results back for the next automated step.

## 1. n8n cloud Variables (T-13)

In n8n.cloud → Settings → Variables, set:

```
AINAVI_GATE_URL   = https://ainavi-auditor-gate.fly.dev
AINAVI_GATE_MODE  = report_only
AINAVI_GATE_TOKEN = <value from C:\Users\user\.fly_ainavi_auditor_token.txt>
GITHUB_TOKEN      = <a GitHub PAT with repo:read on liquitex-coder/ai-solution->
```

## 2. Throwaway measurement Code node (T-13)

Create a new empty workflow, add one manual-trigger + one Code node, paste this
exactly, run it once, and paste the JSON output into `docs/requirements.md`
§28-3 (and report it back to the session):

```js
const out = {};
try { out.vars_gate_url_readable = !!($vars && $vars.AINAVI_GATE_URL); } catch (e) { out.vars_error = String(e.message); }
try { out.env_gate_url_readable = !!$env.AINAVI_GATE_URL; } catch (e) { out.env_error = String(e.message); }
try { const r = await fetch('https://ainavi-auditor-gate.fly.dev/health', { signal: AbortSignal.timeout(8000) }); out.fetch_status = r.status; out.health = await r.json(); } catch (e) { out.fetch_error = String(e.message); }
try { out.crypto_sha256_abc = require('crypto').createHash('sha256').update('abc').digest('hex'); } catch (e) { out.crypto_error = String(e.message); }
try { out.node_version = process.version; } catch (e) { out.process_error = String(e.message); }
return [{ json: out }];
```

Expected values (compare your run's output against these):

| Field | Expected |
|---|---|
| `vars_gate_url_readable` | `true` |
| `crypto_sha256_abc` | `ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad` |
| `fetch_status` | `200` |
| `health.auth` | `true` |
| `health.memory_db` | `true` |

`env_gate_url_readable` and `env_error` are recorded for information (requirements
§32-1 D10 expects n8n 2.x to throw here, i.e. `env_error` set and no
`env_gate_url_readable` key) — this is not a blocker either way, since all
generated Code nodes read config through `cfg()` (`$vars` first).

**Stop-and-report rule**: if `fetch_error` is set (the Code node cannot reach
the Fly service), stop here and report back to the session instead of
continuing to step 3 — that is a route-change-level finding (per
requirements §34-9's design notes, a `fetch()`-based probes/gate/verifier
redesign would be needed), not something to route around locally.

Delete the throwaway workflow once the output is recorded.

## 3. Wire WF01 (T-35b)

1. `py -3 scripts/patch_evidence_pack.py 01` (from the repo root) — this writes
   the patched JSON to `n8n/workflows/01-github-ai-trending-daily.json`.
2. Re-import into n8n cloud: either delete the existing WF01 workflow and
   re-run `scripts/n8n_deploy.ps1`, or use n8n's "Import from File" onto the
   existing workflow.
3. In the re-imported workflow, bind the **Fact-Check Verifier (WF-01)** node's
   credential to your existing "Claude API Key" credential (same one the
   article-writer node already uses).
4. Run the workflow manually once. For one processed item, capture from the
   execution log:
   - the **Evidence Probes (WF-01)** node's output (`probes`, `ground_truth`, `source_text`)
   - the **Fact-Check Verifier (WF-01)** node's HTTP status
   - the **Evidence Pack (WF-01)** node's `evidence.verifier.ok`
   - the **Auditor Gate (WF-01)** node's `verdict`, `reasons`, `evidence_summary`
   - the resulting WordPress draft's post id
5. Hand this log to the session. Only after that: commit the patched WF01 JSON
   together with `EVIDENCE_REQUIRED_WORKFLOWS = {"01-"}` in `scripts/check_wired.py`
   and the §34-9/ROADMAP completion notes (CLAUDE.md §F: never push workflow
   JSON without this manual-run evidence in hand first).

## 4. Wire WF02–09 (T-36b), after T-35b

Same loop, once per workflow, in the existing T-15 execution order
(WF01→02→05→06→03→04→07→08→09):

```
py -3 scripts/patch_evidence_pack.py 02   # ... through 09, or --all for the rest at once
```

WF08 has no existing Claude credential node (its writer uses the Kimi API) —
the re-import must add one for the new Fact-Check Verifier node. Repeat step
3-4-5 above per workflow, then update `EVIDENCE_REQUIRED_WORKFLOWS` to the
full set once all nine pass their manual run.

<details>
<summary>🇯🇵 日本語</summary>

T-13（n8n cloud Variables設定・実測）とT-35b（WF01実配線）の操作者向け手順書です。Claude Codeはn8n cloudへのログイン・手動実行ができないため、この文書を参照して操作者が実行し、結果をセッションに報告してください。

1. n8n cloud の Variables に `AINAVI_GATE_URL` / `AINAVI_GATE_MODE=report_only` / `AINAVI_GATE_TOKEN` / `GITHUB_TOKEN` を設定
2. 使い捨てのCodeノードで `$vars` 読み取り・`fetch`・`require('crypto')` の3点を実測（本文のコードをそのまま貼り付け）。`fetch_error` が出た場合は続行せず報告してください（設計変更が必要な可能性）
3. `py -3 scripts/patch_evidence_pack.py 01` でWF01のJSONを生成 → n8n cloudへ再取込 → Claude API Key credentialをFact-Check Verifierノードに設定 → 手動実行 → 実行ログをセッションに渡す → コミット
4. 同じ手順をWF02〜09にも適用（T-15と同じ実行順序）。WF08はKimi API使用のためClaude credentialの新規紐付けが必要

</details>

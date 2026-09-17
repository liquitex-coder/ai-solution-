#!/usr/bin/env python3
"""Idempotent Evidence Pack wiring patcher for n8n workflow JSON (requirements §34, T-35).

T-35a tooling only: do NOT run this against the committed n8n/workflows/*.json
files yet. Wiring a workflow for real happens in T-35b, after the operator's
manual n8n run (CLAUDE.md §F) -- this script only prepares the JSON.

Usage:
  python3 scripts/patch_evidence_pack.py 01 [--wf-dir DIR] [--check]
As a library: patch_workflow(num: str, wf_dir: Path) -> str
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
DEFAULT_WF_DIR = ROOT / "n8n" / "workflows"

# Shared config-resolution helper (requirements §32-1 D10): $vars first (n8n
# cloud Variables), then $env, each wrapped in try/catch since n8n 2.x throws
# on a blocked $env access rather than returning undefined.
CFG_JS = """function cfg(name) {
  try { const v = (typeof $vars !== 'undefined' && $vars) ? $vars[name] : ''; if (v) return String(v); } catch (e) {}
  try { const v = (typeof $env !== 'undefined' && $env) ? $env[name] : ''; if (v) return String(v); } catch (e) {}
  return '';
}"""

VERIFIER_SCHEMA = {
    "type": "object",
    "properties": {
        "claims": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "text": {"type": "string"},
                    "type": {"type": "string", "enum": ["FACT", "NUMBER", "TECHNIQUE", "OPINION"]},
                    "status": {"type": "string",
                               "enum": ["SUPPORTED", "CONTRADICTED", "NOT_IN_SOURCE", "UNCHECKABLE"]},
                    "evidence": {"type": ["string", "null"]},
                    "source_index": {"type": ["integer", "null"]},
                    "value": {"type": ["number", "null"]},
                    "gt_ref": {"type": ["string", "null"]},
                    "feasibility": {"type": ["string", "null"],
                                    "enum": ["PLAUSIBLE", "IMPLAUSIBLE", "UNKNOWN", None]},
                    "note": {"type": "string"},
                },
                "required": ["id", "text", "type", "status", "evidence", "source_index",
                             "value", "gt_ref", "feasibility", "note"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["claims"],
    "additionalProperties": False,
}

WF_CONFIG: dict[str, dict] = {
    "01": dict(
        file="01-github-ai-trending-daily.json",
        skill_ref="01-github-trending",
        prompt_node="プロンプト読込み (WF-01)",
        prompt_file="01-github-trending.md",
        item_node="上位5件を整形",
        format_node="WordPress投稿データ整形",
        gate_node="Auditor Gate (WF-01)",
        post_node="WordPressに下書き投稿",
        probes_name="Evidence Probes (WF-01)",
        verifier_name="Fact-Check Verifier (WF-01)",
        pack_name="Evidence Pack (WF-01)",
        source_lang_js="null",
        source_text_js=("`[S0] ${item.name}\\n${item.description || ''}\\n"
                         "stars: ${item.stars}\\nlanguage: ${item.language || ''}\\n"
                         "topics: ${item.topics || ''}\\nurl: ${item.url || ''}`"),
        ground_truth_js=("{ [item.name]: { stars: Number(item.stars) || 0, "
                          "forks: Number(item.forks) || 0, language: item.language || '' } }"),
        ids=dict(
            probes="ep01wf01-aa00-4001-8001-000000000011",
            verifier="fv01wf01-aa00-4001-8001-000000000012",
            pack="ek01wf01-aa00-4001-8001-000000000013",
        ),
        positions=dict(probes=[1780, 300], verifier=[2000, 300], pack=[2220, 300],
                        gate=[2440, 300], post=[2660, 300]),
    ),
}

# decide() is intentionally never touched by this patcher: it reads no
# environment configuration, and the T-35 spec requires it stay byte-identical
# so the report_only/canary/full staged-rollout logic (§22-3) is untouched.
DECIDE_JS = """function decide(verdict) {
  if (verdict !== 'PASS') return 'draft';
  if (mode === 'full') return 'publish';
  if (mode === 'canary') {
    const t = ($json.title || '') + String(content.length);
    let h = 0;
    for (let i = 0; i < t.length; i++) h = (h * 31 + t.charCodeAt(i)) >>> 0;
    return (h % 10 === 0) ? 'publish' : 'draft';
  }
  return 'draft'; // report_only: record verdict, never auto-publish
}"""


def extract_decide(js_code: str) -> str:
    start = js_code.index("function decide(verdict) {")
    depth = 0
    for i in range(start, len(js_code)):
        if js_code[i] == "{":
            depth += 1
        elif js_code[i] == "}":
            depth -= 1
            if depth == 0:
                return js_code[start:i + 1]
    raise ValueError("unbalanced decide() body")


def _probes_js(cfg: dict) -> str:
    template = """@@CFG_JS@@
// EVIDENCE_PROBES \u2014 Tier 0/1 evidence (requirements \u00a734-3), LLM-free
const item = $('@@ITEM_NODE@@').item.json;
const content = $json.content || '';
const source_text = @@SOURCE_TEXT_JS@@;
const ground_truth = @@GROUND_TRUTH_JS@@;
const source_lang = @@SOURCE_LANG_JS@@;
const GITHUB_TOKEN = cfg('GITHUB_TOKEN');
const UA = { 'User-Agent': 'n8n-ai-navi/1.0' };
const allUrls = [...new Set(content.match(/https?:\\/\\/[^\\s"'<>)]+/g) || [])];
const urls = allUrls.slice(0, 10);
const probes = [];
async function probeUrl(u) {
  try {
    let r = await fetch(u, { method: 'HEAD', redirect: 'follow', headers: UA, signal: AbortSignal.timeout(8000) });
    if (r.status === 405) r = await fetch(u, { method: 'GET', redirect: 'follow', headers: UA, signal: AbortSignal.timeout(8000) });
    if (r.status === 404 || r.status === 410) return { kind: 'URL', target: u, result: 'DEAD', detail: String(r.status) };
    if (r.ok) return { kind: 'URL', target: u, result: 'OK', detail: String(r.status) };
    return { kind: 'URL', target: u, result: 'TIMEOUT', detail: String(r.status) };
  } catch (e) { return { kind: 'URL', target: u, result: 'TIMEOUT', detail: String(e && e.message || e).slice(0, 80) }; }
}
for (const u of urls) probes.push(await probeUrl(u));
for (const u of allUrls.slice(10)) probes.push({ kind: 'URL', target: u, result: 'SKIPPED', detail: 'cap' });
const repos = [...new Set(allUrls.map(u => { const m = u.match(/^https?:\\/\\/github\\.com\\/([\\w.-]+)\\/([\\w.-]+)/); return m ? `${m[1]}/${m[2].replace(/\\.git$/, '')}` : ''; }).filter(Boolean))].slice(0, 10);
for (const repo of repos) {
  try {
    const h = { ...UA, 'Accept': 'application/vnd.github.v3+json' };
    if (GITHUB_TOKEN) h['Authorization'] = `token ${GITHUB_TOKEN}`;
    const r = await fetch(`https://api.github.com/repos/${repo}`, { headers: h, signal: AbortSignal.timeout(8000) });
    if (r.status === 404) probes.push({ kind: 'GITHUB_REPO', target: repo, result: 'NOT_FOUND', detail: '404' });
    else if (r.ok) { const d = await r.json(); probes.push({ kind: 'GITHUB_REPO', target: repo, result: 'OK', detail: { stars: d.stargazers_count } }); }
    else probes.push({ kind: 'GITHUB_REPO', target: repo, result: 'TIMEOUT', detail: String(r.status) });
  } catch (e) { probes.push({ kind: 'GITHUB_REPO', target: repo, result: 'TIMEOUT', detail: String(e && e.message || e).slice(0, 80) }); }
}
return [{ json: { ...$json, source_text, source_lang, ground_truth, probes } }];"""
    return (template
            .replace("@@CFG_JS@@", CFG_JS)
            .replace("@@ITEM_NODE@@", cfg["item_node"])
            .replace("@@SOURCE_TEXT_JS@@", cfg["source_text_js"])
            .replace("@@GROUND_TRUTH_JS@@", cfg["ground_truth_js"])
            .replace("@@SOURCE_LANG_JS@@", cfg["source_lang_js"]))


def _prompt_js(original_js: str, cfg: dict) -> str:
    if "fetchPrompt(" not in original_js:
        raise ValueError("prompt node js does not look like the expected loader")
    return original_js.replace(
        "const GITHUB_TOKEN = $env.GITHUB_TOKEN || '';",
        f"{CFG_JS}\nconst GITHUB_TOKEN = cfg('GITHUB_TOKEN');",
    ).replace(
        f"const [copyright, wfPrompt] = await Promise.all([\n  fetchPrompt('00-copyright-transform.md'),\n"
        f"  fetchPrompt('{cfg['prompt_file']}')\n]);\n"
        "return [{ json: { ...$json, promptContent: copyright + '\\n\\n---\\n\\n' + wfPrompt } }];",
        f"const [copyright, wfPrompt, factcheck] = await Promise.all([\n  fetchPrompt('00-copyright-transform.md'),\n"
        f"  fetchPrompt('{cfg['prompt_file']}'),\n  fetchPrompt('50-fact-check.md')\n]);\n"
        "let factcheckPromptSha256 = '';\n"
        "try { factcheckPromptSha256 = require('crypto').createHash('sha256')"
        ".update(factcheck, 'utf8').digest('hex'); } catch (e) {}\n"
        "return [{ json: { ...$json, promptContent: copyright + '\\n\\n---\\n\\n' + wfPrompt, "
        "factcheckPrompt: factcheck, factcheckPromptSha256 } }];",
    )


def _pack_js(cfg: dict) -> str:
    template = """const probesItem = $('@@PROBES_NAME@@').item.json;
const promptItem = $('@@PROMPT_NODE@@').item.json;
const resp = $json || {};
let ok = false, error = null, claims = [], usage = { input_tokens: 0, output_tokens: 0 };
try {
  if (resp.error) throw new Error(typeof resp.error === 'string' ? resp.error : (resp.error.message || JSON.stringify(resp.error)));
  if (resp.stop_reason && resp.stop_reason !== 'end_turn') throw new Error(`stop_reason ${resp.stop_reason}`);
  const text = (resp.content && resp.content[0] && resp.content[0].text) || '';
  const parsed = JSON.parse(text);
  if (!Array.isArray(parsed.claims)) throw new Error('claims not array');
  claims = parsed.claims; ok = true;
  if (resp.usage) usage = { input_tokens: resp.usage.input_tokens || 0, output_tokens: resp.usage.output_tokens || 0 };
} catch (e) { ok = false; error = String(e && e.message || e).slice(0, 200); claims = []; }
const evidence = { version: 1,
  verifier: { model: 'claude-haiku-4-5', prompt_ref: '50-fact-check.md', prompt_sha256: promptItem.factcheckPromptSha256 || '', ok, error, usage },
  claims, probes: probesItem.probes || [], ground_truth: probesItem.ground_truth || {} };
const { probes, ground_truth, ...rest } = probesItem;
return [{ json: { ...rest, source_text: probesItem.source_text || '', source_lang: probesItem.source_lang === undefined ? null : probesItem.source_lang, evidence } }];"""
    return (template
            .replace("@@PROBES_NAME@@", cfg["probes_name"])
            .replace("@@PROMPT_NODE@@", cfg["prompt_node"]))


def _gate_js(original_js: str, cfg: dict) -> str:
    decide_js = extract_decide(original_js)
    return f"""// Auditor Gate \u2014 staged rollout (requirements \u00a722-3, INV-R2)
// AINAVI_GATE_MODE: report_only (default) | canary (~10% publish) | full
{CFG_JS}
const auditorUrl = cfg('AINAVI_GATE_URL');
const mode = (cfg('AINAVI_GATE_MODE') || 'report_only').toLowerCase();
const token = cfg('AINAVI_GATE_TOKEN');
const content = $json.content || '';
const sourceUrl = $json.source_url || '';
{decide_js}
if (!auditorUrl) {{
  return [{{ json: {{ ...$json, verdict: 'SKIP', audit_mode: mode, wp_status: 'draft',
    audit_note: 'AINAVI_GATE_URL\u672a\u8a2d\u5b9a \u2192 \u4e0b\u66f8\u304d\u4fdd\u5b58' }} }}];
}}
try {{
  const body = {{ content, source_urls: sourceUrl ? [sourceUrl] : [], skill_ref: '{cfg["skill_ref"]}' }};
  if ($json.source_text) body.source_text = $json.source_text;
  if ($json.source_lang) body.source_lang = $json.source_lang;
  if ($json.evidence && typeof $json.evidence === 'object') body.evidence = $json.evidence;
  const res = await fetch(`${{auditorUrl}}/audit`, {{
    method: 'POST',
    headers: {{ 'Content-Type': 'application/json', ...(token ? {{ 'Authorization': `Bearer ${{token}}` }} : {{}}) }},
    body: JSON.stringify(body)
  }});
  if (!res.ok) {{
    return [{{ json: {{ ...$json, verdict: 'UNVERIFIABLE', audit_mode: mode, wp_status: 'draft',
      audit_note: `Auditor HTTP ${{res.status}}` }} }}];
  }}
  const result = await res.json();
  return [{{ json: {{ ...$json, ...result, audit_mode: mode,
    wp_status: decide(result.verdict) }} }}];
}} catch(e) {{
  return [{{ json: {{ ...$json, verdict: 'UNVERIFIABLE', audit_mode: mode, wp_status: 'draft',
    audit_note: e.message }} }}];
}}"""


def _find_node(wf: dict, name: str) -> dict:
    for node in wf.get("nodes", []):
        if node.get("name") == name:
            return node
    raise KeyError(f"node not found: {name}")


def _upsert_node(wf: dict, node_id: str, node: dict) -> None:
    nodes = wf.setdefault("nodes", [])
    for i, existing in enumerate(nodes):
        if existing.get("id") == node_id:
            nodes[i] = node
            return
    nodes.append(node)


def _connect(connections: dict, src: str, dst: str) -> None:
    connections[src] = {"main": [[{"node": dst, "type": "main", "index": 0}]]}


def patch_workflow(num: str, wf_dir: pathlib.Path = DEFAULT_WF_DIR) -> str:
    cfg = WF_CONFIG[num]
    path = wf_dir / cfg["file"]
    original_text = path.read_text(encoding="utf-8")
    wf = json.loads(original_text)

    prompt_node = _find_node(wf, cfg["prompt_node"])
    prompt_node["parameters"]["jsCode"] = _prompt_js(prompt_node["parameters"]["jsCode"], cfg)

    gate_node = _find_node(wf, cfg["gate_node"])
    gate_node["parameters"]["jsCode"] = _gate_js(gate_node["parameters"]["jsCode"], cfg)
    gate_node["position"] = list(cfg["positions"]["gate"])

    post_node = _find_node(wf, cfg["post_node"])
    post_node["position"] = list(cfg["positions"]["post"])

    _upsert_node(wf, cfg["ids"]["probes"], {
        "parameters": {"jsCode": _probes_js(cfg)},
        "id": cfg["ids"]["probes"], "name": cfg["probes_name"],
        "type": "n8n-nodes-base.code", "typeVersion": 2,
        "position": list(cfg["positions"]["probes"]),
    })

    _upsert_node(wf, cfg["ids"]["verifier"], {
        "parameters": {
            "method": "POST",
            "url": "https://api.anthropic.com/v1/messages",
            "authentication": "genericCredentialType",
            "genericAuthType": "httpHeaderAuth",
            "sendHeaders": True,
            "headerParameters": {"parameters": [
                {"name": "anthropic-version", "value": "2023-06-01"},
            ]},
            "options": {"timeout": 120000},
            "body": {
                "contentType": "json",
                "jsonBody": {
                    "model": "claude-haiku-4-5",
                    "max_tokens": 4096,
                    "system": f"={{{{ $('{cfg['prompt_node']}').item.json.factcheckPrompt }}}}",
                    "messages": [{
                        "role": "user",
                        "content": ("={{ '<ARTICLE>\\n' + ($json.content || '') + '\\n</ARTICLE>\\n\\n"
                                     "<SOURCES>\\n' + ($json.source_text || '') + '\\n</SOURCES>\\n\\n"
                                     "<GROUND_TRUTH>\\n' + JSON.stringify($json.ground_truth || {}) "
                                     "+ '\\n</GROUND_TRUTH>' }}"),
                    }],
                    "output_config": {"format": {"type": "json_schema", "schema": VERIFIER_SCHEMA}},
                },
            },
            "onError": "continueRegularOutput",
        },
        "id": cfg["ids"]["verifier"], "name": cfg["verifier_name"],
        "type": "n8n-nodes-base.httpRequest", "typeVersion": 4.2,
        "position": list(cfg["positions"]["verifier"]),
        "onError": "continueRegularOutput",
        "credentials": {"httpHeaderAuth": {"id": "CLAUDE_API_CRED_ID", "name": "Claude API Key"}},
    })

    _upsert_node(wf, cfg["ids"]["pack"], {
        "parameters": {"jsCode": _pack_js(cfg)},
        "id": cfg["ids"]["pack"], "name": cfg["pack_name"],
        "type": "n8n-nodes-base.code", "typeVersion": 2,
        "position": list(cfg["positions"]["pack"]),
    })

    connections = wf.setdefault("connections", {})
    _connect(connections, cfg["format_node"], cfg["probes_name"])
    _connect(connections, cfg["probes_name"], cfg["verifier_name"])
    _connect(connections, cfg["verifier_name"], cfg["pack_name"])
    _connect(connections, cfg["pack_name"], cfg["gate_node"])
    # connections[gate_node] -> post_node already exists and is untouched.

    dumped = json.dumps(wf, ensure_ascii=False, indent=2)
    if original_text.endswith("\n") and not dumped.endswith("\n"):
        dumped += "\n"
    return dumped


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("num", choices=sorted(WF_CONFIG))
    ap.add_argument("--wf-dir", type=pathlib.Path, default=DEFAULT_WF_DIR)
    ap.add_argument("--check", action="store_true",
                     help="exit 1 if the file on disk differs from the patched output")
    args = ap.parse_args()

    path = args.wf_dir / WF_CONFIG[args.num]["file"]
    patched = patch_workflow(args.num, args.wf_dir)
    if args.check:
        current = path.read_text(encoding="utf-8")
        if current != patched:
            print(f"{path.name}: not patched (run without --check to write)", file=sys.stderr)
            return 1
        print(f"{path.name}: already patched")
        return 0
    path.write_text(patched, encoding="utf-8")
    print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

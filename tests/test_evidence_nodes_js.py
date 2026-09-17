"""Execute the Evidence Pack Code-node JavaScript under real Node.js with
stubbed n8n globals (requirements §34, T-35a). This is a sensor against the
n8n runtime layer itself -- it does not touch any committed workflow JSON.

Skipped entirely when `node` is not on PATH.
"""

import json
import shutil
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path

from scripts.patch_evidence_pack import WF_CONFIG, _gate_js, _pack_js, _prompt_js, _probes_js

NODE = shutil.which("node")

CFG = WF_CONFIG["01"]

# $env is a Proxy that throws on any property access, emulating n8n 2.x's
# default N8N_BLOCK_ENV_ACCESS_IN_NODE=true behaviour (requirements §32-1 D10).
BLOCKED_ENV_JS = """
const $env = new Proxy({}, { get() { throw new Error('access to env vars denied'); } });
"""


def run_js(js_code: str, prelude: str) -> dict:
    """Run one Code node's jsCode under node with a stubbed n8n environment."""
    harness = prelude + "\n(async function(){\n" + js_code + "\n})()" \
        ".then(r => { process.stdout.write(JSON.stringify(r === undefined ? null : r)); })" \
        ".catch(e => { process.stderr.write(String(e && e.stack || e)); process.exit(1); });"
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "harness.js"
        path.write_text(harness, encoding="utf-8")
        result = subprocess.run([NODE, str(path)], capture_output=True, text=True,
                                encoding="utf-8", timeout=30)
    if result.returncode != 0:
        raise AssertionError(f"node harness failed: {result.stderr}")
    return json.loads(result.stdout)


def dollar_prelude(json_value: dict, vars_value: dict, nodes: dict, fetch_body: str) -> str:
    nodes_json = json.dumps(nodes, ensure_ascii=False)
    json_json = json.dumps(json_value, ensure_ascii=False)
    vars_json = json.dumps(vars_value, ensure_ascii=False)
    return textwrap.dedent(f"""
    const __nodes = {nodes_json};
    const $json = {json_json};
    const $vars = {vars_json};
    {BLOCKED_ENV_JS}
    function $(name) {{
      const data = __nodes[name];
      return {{ item: {{ json: data }}, first: () => ({{ json: data }}) }};
    }}
    {fetch_body}
    """)


@unittest.skipUnless(NODE, "node not installed")
class ProbesNodeJSTests(unittest.TestCase):
    def test_probes_url_and_github_scenarios(self):
        item = {"name": "acme/widget", "description": "A widget", "stars": 42,
                "language": "Python", "url": "https://github.com/acme/widget",
                "topics": "ai, tools", "forks": 3}
        urls = [f"https://example.com/extra{i}" for i in range(2)]
        content = ("見よ https://example.com/ok 良い記事 https://example.com/dead "
                   "https://example.com/throws https://github.com/acme/widget "
                   "https://github.com/acme/ghost " + " ".join(urls) +
                   " ".join(f"https://example.com/cap{i}" for i in range(6)))
        fetch_body = """
        async function fetch(url, opts) {
          if (url === 'https://example.com/ok') return { status: 200, ok: true };
          if (url === 'https://example.com/dead') return { status: 404, ok: false };
          if (url === 'https://example.com/throws') throw new Error('network down');
          if (url === 'https://api.github.com/repos/acme/widget') {
            if (!opts.headers['Authorization']) throw new Error('missing auth header');
            return { status: 200, ok: true, json: async () => ({ stargazers_count: 999 }) };
          }
          if (url === 'https://api.github.com/repos/acme/ghost') return { status: 404, ok: false };
          return { status: 200, ok: true };
        }
        """
        prelude = dollar_prelude(
            {"content": content}, {"GITHUB_TOKEN": "tok123"}, {CFG["item_node"]: item}, fetch_body)
        out = run_js(_probes_js(CFG), prelude)[0]["json"]

        self.assertTrue(out["source_text"].startswith("[S0] "))
        self.assertIsNone(out["source_lang"])
        self.assertEqual(out["ground_truth"], {"acme/widget": {"stars": 42, "forks": 3,
                                                                "language": "Python"}})
        probes = out["probes"]
        by_target = {(p["kind"], p["target"]): p for p in probes}
        self.assertEqual(by_target[("URL", "https://example.com/ok")]["result"], "OK")
        self.assertEqual(by_target[("URL", "https://example.com/dead")]["result"], "DEAD")
        self.assertEqual(by_target[("URL", "https://example.com/throws")]["result"], "TIMEOUT")
        self.assertEqual(by_target[("GITHUB_REPO", "acme/widget")]["result"], "OK")
        self.assertEqual(by_target[("GITHUB_REPO", "acme/widget")]["detail"]["stars"], 999)
        self.assertEqual(by_target[("GITHUB_REPO", "acme/ghost")]["result"], "NOT_FOUND")
        skipped = [p for p in probes if p["result"] == "SKIPPED"]
        self.assertTrue(len(skipped) >= 2)


@unittest.skipUnless(NODE, "node not installed")
class PromptNodeJSTests(unittest.TestCase):
    def test_prompt_node_fetches_three_files_and_hashes_factcheck(self):
        import hashlib
        factcheck_text = "FACTCHECK PROMPT BODY"
        expected_sha = hashlib.sha256(factcheck_text.encode("utf-8")).hexdigest()
        import base64
        fetch_body = f"""
        async function fetch(url, opts) {{
          if (!opts.headers['Authorization']) throw new Error('missing auth header');
          const map = {{
            '00-copyright-transform.md': {json.dumps(base64.b64encode(b"COPYRIGHT").decode())},
            '{CFG["prompt_file"]}': {json.dumps(base64.b64encode(b"WFPROMPT").decode())},
            '50-fact-check.md': {json.dumps(base64.b64encode(factcheck_text.encode()).decode())},
          }};
          for (const [suffix, content] of Object.entries(map)) {{
            if (url.endsWith(suffix)) return {{ ok: true, json: async () => ({{ content }}) }};
          }}
          return {{ ok: false }};
        }}
        """
        original_js = (
            "const GITHUB_TOKEN = $env.GITHUB_TOKEN || '';\n"
            "const BASE = 'https://api.github.com/repos/liquitex-coder/ai-solution-/contents/n8n/prompts/';\n"
            "const headers = { 'Accept': 'application/vnd.github.v3+json', 'User-Agent': 'n8n-ai-navi/1.0' };\n"
            "if (GITHUB_TOKEN) headers['Authorization'] = `token ${GITHUB_TOKEN}`;\n"
            "async function fetchPrompt(file) {\n"
            "  try {\n"
            "    const res = await fetch(BASE + file, { headers });\n"
            "    if (!res.ok) return '';\n"
            "    const data = await res.json();\n"
            "    return Buffer.from((data.content || '').replace(/\\n/g, ''), 'base64').toString('utf8');\n"
            "  } catch(e) { return ''; }\n"
            "}\n"
            "const [copyright, wfPrompt] = await Promise.all([\n"
            "  fetchPrompt('00-copyright-transform.md'),\n"
            f"  fetchPrompt('{CFG['prompt_file']}')\n"
            "]);\n"
            "return [{ json: { ...$json, promptContent: copyright + '\\n\\n---\\n\\n' + wfPrompt } }];"
        )
        js = _prompt_js(original_js, CFG)
        prelude = dollar_prelude({"x": 1}, {"GITHUB_TOKEN": "tok123"}, {}, fetch_body)
        out = run_js(js, prelude)
        item = out[0]["json"]
        self.assertEqual(item["factcheckPrompt"], factcheck_text)
        self.assertEqual(item["factcheckPromptSha256"], expected_sha)
        self.assertIn("COPYRIGHT", item["promptContent"])
        self.assertIn("WFPROMPT", item["promptContent"])


@unittest.skipUnless(NODE, "node not installed")
class EvidencePackNodeJSTests(unittest.TestCase):
    def _run(self, resp_json: dict, probes_item: dict) -> dict:
        prelude = dollar_prelude(
            resp_json, {}, {
                CFG["probes_name"]: probes_item,
                CFG["prompt_node"]: {"factcheckPromptSha256": "a" * 64},
            }, "async function fetch(){ throw new Error('should not be called'); }")
        out = run_js(_pack_js(CFG), prelude)
        return out[0]["json"]

    def test_valid_response_passes_through_claims(self):
        claims = [{"id": "c1", "text": "x"}]
        resp = {"content": [{"text": json.dumps({"claims": claims})}],
               "usage": {"input_tokens": 10, "output_tokens": 5}}
        probes_item = {"probes": [{"kind": "URL", "target": "u", "result": "OK"}],
                       "ground_truth": {"a": 1}, "source_text": "[S0] hi", "source_lang": "ja"}
        out = self._run(resp, probes_item)
        ev = out["evidence"]
        self.assertTrue(ev["verifier"]["ok"])
        self.assertEqual(ev["claims"], claims)
        self.assertEqual(ev["probes"], probes_item["probes"])
        self.assertEqual(ev["ground_truth"], probes_item["ground_truth"])
        self.assertEqual(ev["verifier"]["prompt_sha256"], "a" * 64)
        self.assertEqual(out["source_text"], "[S0] hi")
        self.assertEqual(out["source_lang"], "ja")

    def test_error_response_marks_not_ok(self):
        resp = {"error": {"message": "HTTP 529 overloaded"}}
        out = self._run(resp, {"probes": [], "ground_truth": {}, "source_text": ""})
        ev = out["evidence"]
        self.assertFalse(ev["verifier"]["ok"])
        self.assertIn("529", ev["verifier"]["error"])
        self.assertEqual(ev["claims"], [])

    def test_non_end_turn_stop_reason_marks_not_ok(self):
        resp = {"stop_reason": "max_tokens", "content": [{"text": "{}"}]}
        out = self._run(resp, {"probes": [], "ground_truth": {}, "source_text": ""})
        self.assertFalse(out["evidence"]["verifier"]["ok"])

    def test_unparsable_text_marks_not_ok(self):
        resp = {"content": [{"text": "not json"}]}
        out = self._run(resp, {"probes": [], "ground_truth": {}, "source_text": ""})
        self.assertFalse(out["evidence"]["verifier"]["ok"])

    def test_source_lang_undefined_becomes_null(self):
        resp = {"content": [{"text": json.dumps({"claims": []})}]}
        out = self._run(resp, {"probes": [], "ground_truth": {}, "source_text": ""})
        self.assertIsNone(out["source_lang"])


@unittest.skipUnless(NODE, "node not installed")
class GateNodeJSTests(unittest.TestCase):
    def _gate_js(self):
        original = (
            "const auditorUrl = $env.AINAVI_GATE_URL || '';\n"
            "const mode = ($env.AINAVI_GATE_MODE || 'report_only').toLowerCase();\n"
            "const content = $json.content || '';\n"
            "const sourceUrl = $json.source_url || '';\n"
            "function decide(verdict) {\n"
            "  if (verdict !== 'PASS') return 'draft';\n"
            "  if (mode === 'full') return 'publish';\n"
            "  if (mode === 'canary') {\n"
            "    const t = ($json.title || '') + String(content.length);\n"
            "    let h = 0;\n"
            "    for (let i = 0; i < t.length; i++) h = (h * 31 + t.charCodeAt(i)) >>> 0;\n"
            "    return (h % 10 === 0) ? 'publish' : 'draft';\n"
            "  }\n"
            "  return 'draft'; // report_only: record verdict, never auto-publish\n"
            "}\n"
            "if (!auditorUrl) { return [{ json: { verdict: 'SKIP' } }]; }\n"
        )
        return _gate_js(original, CFG)

    def test_full_request_includes_evidence_and_auth(self):
        seen = {}
        fetch_body = """
        async function fetch(url, opts) {
          __seen.url = url; __seen.opts = opts;
          return { ok: true, json: async () => ({ verdict: 'PASS', reasons: [],
                                                   evidence_summary: { claims: 1 } }) };
        }
        """
        prelude = ("const __seen = {};\n" +
                  dollar_prelude(
                      {"content": "hi", "source_text": "src", "source_lang": "ja",
                       "evidence": {"version": 1}, "source_url": "https://x"},
                      {"AINAVI_GATE_URL": "https://gate.test", "AINAVI_GATE_MODE": "report_only",
                       "AINAVI_GATE_TOKEN": "t"}, {}, fetch_body) +
                  "\nglobalThis.__seenExport = () => __seen;\n")
        js = self._gate_js() + "\n"
        # capture __seen via a second console print appended to the harness
        harness = prelude + "\n(async function(){\n" + js + "\n})()" \
            ".then(r => { process.stdout.write(JSON.stringify({result: r, seen: __seen})); })" \
            ".catch(e => { process.stderr.write(String(e && e.stack || e)); process.exit(1); });"
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "harness.js"
            path.write_text(harness, encoding="utf-8")
            result = subprocess.run([NODE, str(path)], capture_output=True, text=True,
                                    encoding="utf-8", timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        out = json.loads(result.stdout)
        body = json.loads(out["seen"]["opts"]["body"])
        self.assertEqual(body["source_text"], "src")
        self.assertEqual(body["evidence"], {"version": 1})
        self.assertEqual(out["seen"]["opts"]["headers"]["Authorization"], "Bearer t")
        self.assertEqual(out["result"][0]["json"]["wp_status"], "draft")

    def test_no_url_returns_skip_without_calling_fetch(self):
        fetch_body = "async function fetch(){ throw new Error('must not be called'); }"
        prelude = dollar_prelude(
            {"content": "hi"}, {}, {}, fetch_body)
        out = run_js(self._gate_js(), prelude)
        self.assertEqual(out[0]["json"]["verdict"], "SKIP")

    def test_no_token_omits_authorization_header(self):
        fetch_body = """
        async function fetch(url, opts) {
          if (opts.headers['Authorization']) throw new Error('should not have auth header');
          return { ok: true, json: async () => ({ verdict: 'PASS', reasons: [] }) };
        }
        """
        prelude = dollar_prelude(
            {"content": "hi"}, {"AINAVI_GATE_URL": "https://gate.test"}, {}, fetch_body)
        out = run_js(self._gate_js(), prelude)
        self.assertEqual(out[0]["json"]["wp_status"], "draft")


if __name__ == "__main__":
    unittest.main()

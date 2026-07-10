#!/usr/bin/env python3
"""Design-vs-wired gate (requirements §21) — prevents "designed but not running".

Pure stdlib, no network. Exit 0 = all PASS, exit 1 = any FAIL.

Checks:
  W1  every WF listed in requirements (WF01..WF09) has a workflow JSON
  W2  every workflow has an Auditor Gate node (CLAIM_AUDITOR_URL)
  W3  every workflow's prompt loading includes 00-copyright-transform.md
  W4  WordPress post status goes through wp_status (no hardcoded 'publish')
  W5  every prompt file is referenced by >=1 workflow (or LIBRARY_ONLY)
  W6  no credential-looking literals inside workflow JSONs
"""

from __future__ import annotations

import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
WF_DIR = ROOT / "n8n" / "workflows"
PROMPT_DIR = ROOT / "n8n" / "prompts"

# WF number -> expected workflow file prefix (requirements §WF table)
REQUIRED_WORKFLOWS = {
    "01": "01-", "02": "02-", "03": "03-", "04": "04-",
    "05": "05-", "06": "06-", "07": "07-", "08": "08-", "09": "09-",
}

# Intentionally unwired files, each with a reason. Anything else unwired = FAIL.
LIBRARY_ONLY_PROMPTS = {
    # superseded by 02-rss-monitor.md; kept for prompt-history comparison
    "02-rss-summary.md": "legacy variant, superseded by 02-rss-monitor.md",
    # superseded by 04-threads-influencer.md
    "04-threads-summary.md": "legacy variant, superseded by 04-threads-influencer.md",
    # superseded by 05-note-monitor.md
    "05-note-summary.md": "legacy variant, superseded by 05-note-monitor.md",
}

SECRET_PATTERNS = [
    re.compile(r"sk-ant-[A-Za-z0-9\-_]{10,}"),        # Anthropic key
    re.compile(r"sk-[A-Za-z0-9]{20,}"),                # generic sk- key
    re.compile(r"ghp_[A-Za-z0-9]{20,}"),               # GitHub PAT
    re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),                   # AWS access key
    # inline bearer token; YOUR_/PLACEHOLDER-style docs examples are fine
    re.compile(r"Bearer\s+(?!YOUR_|<|\{\{|\$)[A-Za-z0-9\-._~+/]{25,}"),
    re.compile(r'"(?:api_key|apikey|password|app_password|token)"\s*:\s*"(?!={{)[^"$][^"]{7,}"',
               re.IGNORECASE),
]

failures: list[str] = []
passes: list[str] = []


def ok(msg: str) -> None:
    passes.append(msg)
    print(f"  PASS  {msg}")


def fail(msg: str) -> None:
    failures.append(msg)
    print(f"  FAIL  {msg}")


def node_texts(wf: dict) -> list[tuple[str, str]]:
    """(node_name, jsCode-or-json-dump) per node."""
    out = []
    for node in wf.get("nodes", []):
        params = node.get("parameters", {})
        text = params.get("jsCode", "") or json.dumps(params, ensure_ascii=False)
        out.append((node.get("name", "?"), text))
    return out


def main() -> int:
    workflows: dict[str, dict] = {}
    for path in sorted(WF_DIR.glob("*.json")):
        try:
            workflows[path.name] = json.loads(path.read_text())
        except json.JSONDecodeError as e:
            fail(f"W0 {path.name}: invalid JSON ({e})")

    print("== W1: requirements WF table -> workflow JSON exists ==")
    for num, prefix in REQUIRED_WORKFLOWS.items():
        hits = [n for n in workflows if n.startswith(prefix)]
        if hits:
            ok(f"W1 WF{num} -> {', '.join(hits)}")
        else:
            fail(f"W1 WF{num}: no workflow JSON with prefix '{prefix}'")

    print("== W2: Auditor Gate node present ==")
    print("== W3: copyright prompt loaded ==")
    print("== W4: no hardcoded publish status ==")
    for name, wf in workflows.items():
        texts = node_texts(wf)
        blob = "\n".join(t for _, t in texts)

        if "CLAIM_AUDITOR_URL" in blob:
            ok(f"W2 {name}: Auditor Gate present")
        else:
            fail(f"W2 {name}: no Auditor Gate node (CLAIM_AUDITOR_URL not found)")

        if "00-copyright-transform.md" in blob:
            ok(f"W3 {name}: copyright prompt loaded")
        else:
            fail(f"W3 {name}: 00-copyright-transform.md not loaded")

        bad_nodes = []
        for node in wf.get("nodes", []):
            params = node.get("parameters", {})
            body = params.get("body", {})
            if isinstance(body, dict):
                status = (body.get("jsonBody") or {}).get("status", "")
                if status in ("publish", "'publish'"):
                    bad_nodes.append(node.get("name", "?"))
            js = params.get("jsCode", "")
            # WP-format nodes must emit wp_status; a literal status:'publish'
            # in code is the WF06 bug pattern
            if re.search(r"status:\s*'publish'", js):
                bad_nodes.append(node.get("name", "?"))
        if bad_nodes:
            fail(f"W4 {name}: hardcoded publish in {bad_nodes}")
        else:
            ok(f"W4 {name}: post status gate-controlled")

    print("== W5: every prompt referenced by a workflow ==")
    all_blob = "\n".join(
        json.dumps(wf, ensure_ascii=False) for wf in workflows.values())
    for prompt in sorted(PROMPT_DIR.glob("*.md")):
        if prompt.name in LIBRARY_ONLY_PROMPTS:
            ok(f"W5 {prompt.name}: LIBRARY_ONLY ({LIBRARY_ONLY_PROMPTS[prompt.name]})")
        elif prompt.name in all_blob:
            ok(f"W5 {prompt.name}: referenced")
        else:
            fail(f"W5 {prompt.name}: not referenced by any workflow "
                 f"(wire it or register LIBRARY_ONLY with a reason)")

    print("== W6: no credential literals in workflows ==")
    w6_bad = False
    for name, wf in workflows.items():
        raw = json.dumps(wf, ensure_ascii=False)
        for pat in SECRET_PATTERNS:
            m = pat.search(raw)
            if m:
                fail(f"W6 {name}: credential-looking literal: {m.group()[:12]}…")
                w6_bad = True
    if not w6_bad:
        ok("W6 all workflows: no credential literals")

    print()
    print(f"Summary: {len(passes)} PASS, {len(failures)} FAIL")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())

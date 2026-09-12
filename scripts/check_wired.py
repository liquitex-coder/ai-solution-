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
  W7  every Auditor Gate is CLAIM_AUDITOR_MODE aware (staged rollout)
  W8  every Auditor Gate skill_ref is registered for ratchet prompts
  W9  Auditor service and n8n CLAIM_AUDITOR_URL wiring exist
  W10 workflow/category taxonomy map and source_workflow values agree
  W11 workflow category_id values match taxonomy wp_id values
"""

from __future__ import annotations

import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import ratchet_check

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

        if "CLAIM_AUDITOR_MODE" in blob:
            ok(f"W7 {name}: gate is rollout-mode aware")
        else:
            fail(f"W7 {name}: Auditor Gate is not CLAIM_AUDITOR_MODE aware (§22-3)")

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

    print("== W8: Auditor Gate skill_ref registered for ratchet prompts ==")
    for name, wf in workflows.items():
        blob = "\n".join(t for _, t in node_texts(wf))
        match = re.search(r"skill_ref:\s*'([^']+)'", blob)
        if not match:
            fail(f"W8 {name}: no Auditor Gate skill_ref found")
        elif match.group(1) not in ratchet_check.SKILL_PROMPTS:
            fail(f"W8 {name}: unregistered skill_ref '{match.group(1)}'")
        else:
            ok(f"W8 {name}: skill_ref '{match.group(1)}' registered")

    print("== W9: Auditor service and n8n URL wiring exist ==")
    compose_path = ROOT / "docker-compose.yml"
    auditor_server = ROOT / "scripts" / "auditor_server.py"
    auditor_service = False
    n8n_auditor_url = False
    current_service = ""
    in_n8n_environment = False
    if compose_path.exists():
        for line in compose_path.read_text().splitlines():
            service = re.match(r"^  ([^ :]+):", line)
            if service:
                current_service = service.group(1)
                auditor_service = auditor_service or current_service == "auditor"
                in_n8n_environment = False
                continue
            if current_service == "n8n" and line.strip() == "environment:":
                in_n8n_environment = True
                continue
            if in_n8n_environment and re.match(r"^    [^ ]", line):
                in_n8n_environment = False
            if in_n8n_environment and "CLAIM_AUDITOR_URL" in line:
                n8n_auditor_url = True
    if not auditor_server.exists():
        fail("W9 scripts/auditor_server.py: missing")
    elif not auditor_service:
        fail("W9 docker-compose.yml: no auditor service")
    elif not n8n_auditor_url:
        fail("W9 docker-compose.yml: n8n environment lacks CLAIM_AUDITOR_URL")
    else:
        ok("W9 auditor service and n8n CLAIM_AUDITOR_URL wired")

    print("== W10: workflow/category taxonomy map agrees ==")
    taxonomy_path = ROOT / "data" / "wp-taxonomy.json"
    taxonomy = json.loads(taxonomy_path.read_text())
    categories = taxonomy.get("categories", [])
    workflow_category_map = taxonomy.get("workflow_category_map", {})
    required_wfs = {f"WF-{num}" for num in REQUIRED_WORKFLOWS}
    category_slugs = {category.get("slug") for category in categories}
    taxonomy_errors = []
    if set(workflow_category_map) != required_wfs:
        taxonomy_errors.append("workflow_category_map keys do not match WF-01..WF-09")
    if any(slug not in category_slugs for slug in workflow_category_map.values()):
        taxonomy_errors.append("workflow_category_map has unknown category slug")
    if any(category.get("source_workflow") is not None
           and category.get("source_workflow") not in required_wfs
           for category in categories):
        taxonomy_errors.append("category has out-of-range source_workflow")
    for wf_key, slug in workflow_category_map.items():
        if not any(category.get("source_workflow") == wf_key
                   and category.get("slug") == slug for category in categories):
            taxonomy_errors.append(f"{wf_key} map/source_workflow mismatch")
    if taxonomy_errors:
        fail(f"W10 taxonomy: {'; '.join(taxonomy_errors)}")
    else:
        ok("W10 taxonomy workflow/category map agrees")

    print("== W11: workflow category_id matches taxonomy wp_id ==")
    for name, wf in workflows.items():
        match = re.match(r"(\d{2})-", name)
        wf_key = f"WF-{match.group(1)}" if match else ""
        category = next((item for item in categories
                         if item.get("source_workflow") == wf_key), None)
        format_node = next((node for node in wf.get("nodes", [])
                            if node.get("name") == "WordPress投稿データ整形"), None)
        js_code = (format_node or {}).get("parameters", {}).get("jsCode", "")
        id_match = re.search(r"category_id:\s*(\d+)", js_code)
        category_id = int(id_match.group(1)) if id_match else None
        if not category:
            fail(f"W11 {name}: no taxonomy category for {wf_key or 'workflow'}")
        elif isinstance(category.get("wp_id"), int):
            if category_id is None:
                fail(f"W11 {name}: missing category_id for wp_id {category['wp_id']}")
            elif category_id != category["wp_id"]:
                fail(f"W11 {name}: category_id {category_id} != wp_id {category['wp_id']}")
            else:
                ok(f"W11 {name}: category_id matches wp_id {category_id}")
        elif category_id is not None:
            fail(f"W11 {name}: category_id {category_id} has no recorded wp_id")
        else:
            ok(f"W11 {name}: category check (skipped: no wp_id yet)")

    print()
    print(f"Summary: {len(passes)} PASS, {len(failures)} FAIL")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())

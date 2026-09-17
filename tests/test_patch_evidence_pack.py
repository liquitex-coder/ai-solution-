"""Tests for the idempotent Evidence Pack workflow patcher (requirements §34, T-35a).

These tests only ever touch a temp-directory copy of the workflow JSON --
never the committed n8n/workflows/*.json files.
"""

import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from scripts import check_wired
from scripts.patch_evidence_pack import WF_CONFIG, extract_decide, patch_workflow

ROOT = Path(__file__).resolve().parent.parent
REPO_WF01 = ROOT / "n8n" / "workflows" / "01-github-ai-trending-daily.json"


class PatchEvidencePackTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.wf_dir = Path(self.temp_dir.name)
        shutil.copy(REPO_WF01, self.wf_dir / REPO_WF01.name)
        self.repo_hash_before = hashlib.sha256(REPO_WF01.read_bytes()).hexdigest()

    def tearDown(self):
        self.temp_dir.cleanup()
        repo_hash_after = hashlib.sha256(REPO_WF01.read_bytes()).hexdigest()
        self.assertEqual(self.repo_hash_before, repo_hash_after,
                         "the repo's own WF01 file must never be touched by these tests")

    def _patched(self) -> dict:
        text = patch_workflow("01", self.wf_dir)
        (self.wf_dir / REPO_WF01.name).write_text(text, encoding="utf-8")
        return json.loads(text)

    def _original(self) -> dict:
        return json.loads(REPO_WF01.read_text(encoding="utf-8"))

    def _node(self, wf: dict, name: str) -> dict:
        return next(n for n in wf["nodes"] if n["name"] == name)

    def test_three_new_nodes_added(self):
        wf = self._patched()
        cfg = WF_CONFIG["01"]
        names = {n["name"] for n in wf["nodes"]}
        self.assertIn(cfg["probes_name"], names)
        self.assertIn(cfg["verifier_name"], names)
        self.assertIn(cfg["pack_name"], names)
        ids = {n["id"] for n in wf["nodes"]}
        self.assertIn(cfg["ids"]["probes"], ids)
        self.assertIn(cfg["ids"]["verifier"], ids)
        self.assertIn(cfg["ids"]["pack"], ids)

    def test_verifier_node_shape(self):
        wf = self._patched()
        cfg = WF_CONFIG["01"]
        verifier = self._node(wf, cfg["verifier_name"])
        self.assertEqual(verifier["onError"], "continueRegularOutput")
        self.assertEqual(verifier["credentials"]["httpHeaderAuth"]["name"], "Claude API Key")
        body = verifier["parameters"]["body"]["jsonBody"]
        self.assertEqual(body["model"], "claude-haiku-4-5")
        self.assertEqual(body["output_config"]["format"]["type"], "json_schema")
        self.assertIn(cfg["prompt_node"], body["system"])
        self.assertNotIn("thinking", body)
        self.assertNotIn("thinking", json.dumps(verifier))

    def test_connection_chain(self):
        wf = self._patched()
        cfg = WF_CONFIG["01"]
        conns = wf["connections"]

        def target(name):
            return conns[name]["main"][0][0]["node"]

        self.assertEqual(target(cfg["format_node"]), cfg["probes_name"])
        self.assertEqual(target(cfg["probes_name"]), cfg["verifier_name"])
        self.assertEqual(target(cfg["verifier_name"]), cfg["pack_name"])
        self.assertEqual(target(cfg["pack_name"]), cfg["gate_node"])
        self.assertEqual(target(cfg["gate_node"]), cfg["post_node"])

    def test_gate_jscode_contains_required_strings_and_decide_unchanged(self):
        original = self._original()
        cfg = WF_CONFIG["01"]
        original_gate_js = self._node(original, cfg["gate_node"])["parameters"]["jsCode"]
        original_decide = extract_decide(original_gate_js)

        wf = self._patched()
        gate_js = self._node(wf, cfg["gate_node"])["parameters"]["jsCode"]
        for needle in ("source_text", "evidence", "Authorization", "AINAVI_GATE_URL",
                       "AINAVI_GATE_MODE", "skill_ref: '01-github-trending'"):
            self.assertIn(needle, gate_js)
        self.assertEqual(extract_decide(gate_js), original_decide)

    def test_prompt_node_contains_factcheck_prompt_and_crypto(self):
        wf = self._patched()
        cfg = WF_CONFIG["01"]
        prompt_js = self._node(wf, cfg["prompt_node"])["parameters"]["jsCode"]
        self.assertIn("50-fact-check.md", prompt_js)
        self.assertIn("crypto", prompt_js)

    def test_probes_node_contains_marker(self):
        wf = self._patched()
        cfg = WF_CONFIG["01"]
        probes_js = self._node(wf, cfg["probes_name"])["parameters"]["jsCode"]
        self.assertIn("EVIDENCE_PROBES", probes_js)

    def test_untouched_nodes_are_deep_equal(self):
        original = self._original()
        wf = self._patched()
        cfg = WF_CONFIG["01"]
        touched = {cfg["prompt_node"], cfg["gate_node"], cfg["post_node"],
                  cfg["probes_name"], cfg["verifier_name"], cfg["pack_name"]}
        original_by_name = {n["name"]: n for n in original["nodes"]}
        for node in wf["nodes"]:
            if node["name"] in touched:
                continue
            self.assertEqual(node, original_by_name[node["name"]])

    def test_positions_as_specified(self):
        wf = self._patched()
        cfg = WF_CONFIG["01"]
        for key, name in (("probes", cfg["probes_name"]), ("verifier", cfg["verifier_name"]),
                          ("pack", cfg["pack_name"]), ("gate", cfg["gate_node"]),
                          ("post", cfg["post_node"])):
            self.assertEqual(self._node(wf, name)["position"], list(cfg["positions"][key]))

    def test_second_run_is_byte_identical(self):
        first = patch_workflow("01", self.wf_dir)
        (self.wf_dir / REPO_WF01.name).write_text(first, encoding="utf-8")
        second = patch_workflow("01", self.wf_dir)
        self.assertEqual(first, second)

    def test_evidence_wiring_errors_before_and_after(self):
        original = self._original()
        self.assertNotEqual(check_wired.evidence_wiring_errors(original), [])
        patched = self._patched()
        self.assertEqual(check_wired.evidence_wiring_errors(patched), [])


if __name__ == "__main__":
    unittest.main()

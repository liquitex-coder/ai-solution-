"""Tests for the idempotent Evidence Pack workflow patcher (requirements §34, T-35a/T-36a).

These tests only ever touch a temp-directory copy of the workflow JSON --
never the committed n8n/workflows/*.json files.
"""

import hashlib
import json
import re
import shutil
import tempfile
import unittest
from pathlib import Path

from scripts import check_wired
from scripts.patch_evidence_pack import WF_CONFIG, derive_positions, extract_decide, patch_workflow

ROOT = Path(__file__).resolve().parent.parent
WF_DIR = ROOT / "n8n" / "workflows"
REPO_FILES = {num: WF_DIR / cfg["file"] for num, cfg in WF_CONFIG.items()}


class PatchEvidencePackTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.wf_dir = Path(self.temp_dir.name)
        for path in REPO_FILES.values():
            shutil.copy(path, self.wf_dir / path.name)
        self.repo_hashes_before = {
            num: hashlib.sha256(path.read_bytes()).hexdigest() for num, path in REPO_FILES.items()
        }

    def tearDown(self):
        self.temp_dir.cleanup()
        for num, path in REPO_FILES.items():
            self.assertEqual(
                self.repo_hashes_before[num], hashlib.sha256(path.read_bytes()).hexdigest(),
                f"the repo's own WF{num} file must never be touched by these tests")

    def _patched(self, num: str) -> dict:
        text = patch_workflow(num, self.wf_dir)
        (self.wf_dir / WF_CONFIG[num]["file"]).write_text(text, encoding="utf-8")
        return json.loads(text)

    def _original(self, num: str) -> dict:
        return json.loads(REPO_FILES[num].read_text(encoding="utf-8"))

    def _node(self, wf: dict, name: str) -> dict:
        return next(n for n in wf["nodes"] if n["name"] == name)

    def test_three_new_nodes_added(self):
        for num, cfg in WF_CONFIG.items():
            with self.subTest(wf=num):
                wf = self._patched(num)
                names = {n["name"] for n in wf["nodes"]}
                ids = {n["id"] for n in wf["nodes"]}
                for key in ("probes", "verifier", "pack"):
                    self.assertIn(cfg[f"{key}_name"], names)
                    self.assertIn(cfg["ids"][key], ids)

    def test_verifier_node_shape(self):
        for num, cfg in WF_CONFIG.items():
            with self.subTest(wf=num):
                wf = self._patched(num)
                verifier = self._node(wf, cfg["verifier_name"])
                self.assertEqual(verifier["onError"], "continueRegularOutput")
                self.assertEqual(verifier["credentials"]["httpHeaderAuth"]["name"], "Claude API Key")
                p = verifier["parameters"]
                self.assertNotIn("body", p)
                self.assertNotIn("headers", p)
                self.assertTrue(p["sendBody"])
                self.assertEqual(p["specifyBody"], "json")
                self.assertTrue(p["sendHeaders"])
                tpl = p["jsonBody"]
                self.assertTrue(tpl.startswith("="))
                # every {{ }} must be a JSON.stringify(...) so the template stays valid JSON
                exprs = re.findall(r"\{\{(.*?)\}\}", tpl, flags=re.S)
                self.assertTrue(exprs)
                for e in exprs:
                    self.assertTrue(e.strip().startswith("JSON.stringify("), e)
                body = json.loads(re.sub(r"\{\{.*?\}\}", '"<expr>"', tpl[1:], flags=re.S))
                self.assertEqual(body["model"], "claude-haiku-4-5")
                self.assertEqual(body["output_config"]["format"]["type"], "json_schema")
                self.assertEqual(body["system"], "<expr>")
                self.assertIn(cfg["prompt_node"], tpl)
                self.assertNotIn("thinking", json.dumps(verifier))

    def test_connection_chain(self):
        for num, cfg in WF_CONFIG.items():
            with self.subTest(wf=num):
                wf = self._patched(num)
                conns = wf["connections"]

                def target(name):
                    return conns[name]["main"][0][0]["node"]

                self.assertEqual(target(cfg["format_node"]), cfg["probes_name"])
                self.assertEqual(target(cfg["probes_name"]), cfg["verifier_name"])
                self.assertEqual(target(cfg["verifier_name"]), cfg["pack_name"])
                self.assertEqual(target(cfg["pack_name"]), cfg["gate_node"])
                self.assertEqual(target(cfg["gate_node"]), cfg["post_node"])

    def test_gate_jscode_contains_required_strings_and_decide_unchanged(self):
        for num, cfg in WF_CONFIG.items():
            with self.subTest(wf=num):
                original = self._original(num)
                original_gate_js = self._node(original, cfg["gate_node"])["parameters"]["jsCode"]
                original_decide = extract_decide(original_gate_js)

                wf = self._patched(num)
                gate_js = self._node(wf, cfg["gate_node"])["parameters"]["jsCode"]
                for needle in ("source_text", "evidence", "Authorization", "AINAVI_GATE_URL",
                              "AINAVI_GATE_MODE", f"skill_ref: '{cfg['skill_ref']}'"):
                    self.assertIn(needle, gate_js)
                self.assertEqual(extract_decide(gate_js), original_decide)

    def test_prompt_node_contains_factcheck_prompt_and_crypto(self):
        for num, cfg in WF_CONFIG.items():
            with self.subTest(wf=num):
                wf = self._patched(num)
                prompt_js = self._node(wf, cfg["prompt_node"])["parameters"]["jsCode"]
                self.assertIn("50-fact-check.md", prompt_js)
                self.assertIn("crypto", prompt_js)

    def test_probes_node_contains_marker(self):
        for num, cfg in WF_CONFIG.items():
            with self.subTest(wf=num):
                wf = self._patched(num)
                probes_js = self._node(wf, cfg["probes_name"])["parameters"]["jsCode"]
                self.assertIn("EVIDENCE_PROBES", probes_js)

    def test_untouched_nodes_are_deep_equal(self):
        for num, cfg in WF_CONFIG.items():
            with self.subTest(wf=num):
                original = self._original(num)
                wf = self._patched(num)
                touched = {cfg["prompt_node"], cfg["gate_node"], cfg["post_node"],
                          cfg["probes_name"], cfg["verifier_name"], cfg["pack_name"]}
                original_by_name = {n["name"]: n for n in original["nodes"]}
                for node in wf["nodes"]:
                    if node["name"] in touched:
                        continue
                    self.assertEqual(node, original_by_name[node["name"]])

    def test_positions_derived_from_gate_and_wf01_matches_original_hardcoded_values(self):
        original = self._original("01")
        cfg = WF_CONFIG["01"]
        gate_position = self._node(original, cfg["gate_node"])["position"]
        expected = derive_positions(gate_position)
        self.assertEqual(expected["probes"], [1780, 300])
        self.assertEqual(expected["post"], [2660, 300])

        for num, cfg in WF_CONFIG.items():
            with self.subTest(wf=num):
                original = self._original(num)
                gate_position = self._node(original, cfg["gate_node"])["position"]
                expected = derive_positions(gate_position)
                wf = self._patched(num)
                for key, name in (("probes", cfg["probes_name"]), ("verifier", cfg["verifier_name"]),
                                  ("pack", cfg["pack_name"]), ("gate", cfg["gate_node"]),
                                  ("post", cfg["post_node"])):
                    self.assertEqual(self._node(wf, name)["position"], list(expected[key]))

    def test_second_run_is_byte_identical(self):
        for num in WF_CONFIG:
            with self.subTest(wf=num):
                first = patch_workflow(num, self.wf_dir)
                (self.wf_dir / WF_CONFIG[num]["file"]).write_text(first, encoding="utf-8")
                second = patch_workflow(num, self.wf_dir)
                self.assertEqual(first, second)

    def test_evidence_wiring_errors_before_and_after(self):
        for num in WF_CONFIG:
            with self.subTest(wf=num):
                original = self._original(num)
                self.assertNotEqual(check_wired.evidence_wiring_errors(original), [])
                patched = self._patched(num)
                self.assertEqual(check_wired.evidence_wiring_errors(patched), [])

    def test_check_flag_reports_drift_then_clean(self):
        from scripts.patch_evidence_pack import _patch_one
        for num in WF_CONFIG:
            with self.subTest(wf=num):
                self.assertEqual(_patch_one(num, self.wf_dir, check=True), 1)
                self.assertEqual(_patch_one(num, self.wf_dir, check=False), 0)
                self.assertEqual(_patch_one(num, self.wf_dir, check=True), 0)


if __name__ == "__main__":
    unittest.main()

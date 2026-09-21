"""Sensor: every HTTP Request node in n8n/workflows uses n8n's real v4.x
parameter schema (requirements §32-1 D11, CLAUDE.md §C-6).

The nested ``"headers": {...}`` / ``"body": {"jsonBody": {...}}`` form is not a
schema n8n knows; it imports silently and then sends empty requests.
"""

import json
import pathlib
import re
import unittest

from scripts.patch_evidence_pack import convert_http_node, json_body_template

ROOT = pathlib.Path(__file__).resolve().parent.parent
WF_DIR = ROOT / "n8n" / "workflows"


def http_nodes():
    for path in sorted(WF_DIR.glob("0*.json")):
        wf = json.loads(path.read_text(encoding="utf-8"))
        for node in wf["nodes"]:
            if node.get("type") == "n8n-nodes-base.httpRequest":
                yield path.name, node


class WorkflowHttpSchemaTests(unittest.TestCase):
    def test_no_nested_headers_or_body_objects(self):
        for name, node in http_nodes():
            with self.subTest(wf=name, node=node["name"]):
                p = node["parameters"]
                self.assertNotIsInstance(p.get("headers"), dict)
                self.assertNotIsInstance(p.get("body"), dict)

    def test_toggles_match_parameter_groups(self):
        for name, node in http_nodes():
            with self.subTest(wf=name, node=node["name"]):
                p = node["parameters"]
                if "queryParameters" in p:
                    self.assertTrue(p.get("sendQuery"))
                    self.assertEqual(p.get("specifyQuery"), "keypair")
                if "headerParameters" in p:
                    self.assertTrue(p.get("sendHeaders"))
                    self.assertEqual(p.get("specifyHeaders"), "keypair")
                if "jsonBody" in p:
                    self.assertTrue(p.get("sendBody"))
                    self.assertEqual(p.get("specifyBody"), "json")
                    self.assertEqual(p.get("contentType"), "json")

    def test_json_body_templates_are_valid_json_with_stringified_expressions(self):
        for name, node in http_nodes():
            tpl = node["parameters"].get("jsonBody")
            if tpl is None:
                continue
            with self.subTest(wf=name, node=node["name"]):
                self.assertIsInstance(tpl, str)
                self.assertTrue(tpl.startswith("="))
                for e in re.findall(r"\{\{(.*?)\}\}", tpl, flags=re.S):
                    self.assertTrue(e.strip().startswith("JSON.stringify("), e)
                json.loads(re.sub(r"\{\{.*?\}\}", '"<expr>"', tpl[1:], flags=re.S))

    def test_convert_http_node_is_idempotent_on_converted_nodes(self):
        for name, node in http_nodes():
            with self.subTest(wf=name, node=node["name"]):
                before = json.dumps(node, ensure_ascii=False, sort_keys=True)
                self.assertFalse(convert_http_node(json.loads(before)))


class JsonBodyTemplateTests(unittest.TestCase):
    def test_whole_expression_is_stringified(self):
        tpl = json_body_template({"a": "={{ $json.x }}", "n": 3, "s": "lit"})
        self.assertEqual(tpl, '={\n  "a": {{ JSON.stringify(($json.x)) }},\n  "n": 3,\n  "s": "lit"\n}')

    def test_inline_template_becomes_js_template_literal(self):
        tpl = json_body_template({"c": "=回答: 「{{ $json.label }}」`x` ${y}\n"})
        self.assertEqual(
            tpl,
            '={\n  "c": {{ JSON.stringify(`回答: 「${$json.label}」\\`x\\` \\${y}\\n`) }}\n}')

    def test_braces_without_equals_are_still_treated_as_expression(self):
        tpl = json_body_template({"c": "{{ $json.promptContent }}"})
        self.assertIn("JSON.stringify(($json.promptContent))", tpl)

    def test_nested_expression_inside_array(self):
        tpl = json_body_template({"messages": [{"role": "user", "content": "={{ $json.p }}"}]})
        body = json.loads(re.sub(r"\{\{.*?\}\}", '"<expr>"', tpl[1:], flags=re.S))
        self.assertEqual(body["messages"][0]["content"], "<expr>")


if __name__ == "__main__":
    unittest.main()

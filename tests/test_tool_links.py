"""Tests for deterministic tool-page links (requirements §35-13, rule R1)."""

import json
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.request import Request, urlopen

from scripts import tool_links
from scripts.auditor_server import make_server
from scripts.content_audit import audit

TOOLS = [
    {"slug": "chatgpt", "name": "ChatGPT"},
    {"slug": "claude", "name": "Claude"},
    {"slug": "n8n", "name": "n8n"},
    {"slug": "stable-diffusion", "name": "Stable Diffusion"},
]


def body(*paragraphs):
    return "".join(f"<h2>見出し{i}</h2><p>{p}</p>" for i, p in enumerate(paragraphs))


class LinkToolsTests(unittest.TestCase):
    def test_links_only_the_first_mention(self):
        html, linked = tool_links.link_tools(body("ChatGPTとChatGPT"), TOOLS)
        self.assertEqual(linked, ["chatgpt"])
        self.assertEqual(html.count('href="/tools/chatgpt/"'), 1)
        self.assertIn('<a href="/tools/chatgpt/">ChatGPT</a>とChatGPT', html)

    def test_skips_headings_existing_links_quotes_and_code(self):
        html = ('<h2>Claudeの話</h2><p><a href="https://x">Claude公式</a></p>'
                '<blockquote>Claude is</blockquote><p><code>Claude</code></p>'
                '<p><pre>Claude</pre></p>')
        out, linked = tool_links.link_tools(html, TOOLS)
        self.assertEqual(linked, [])
        self.assertEqual(out, html)

    def test_blockquote_text_is_never_altered(self):
        html = "<blockquote>ChatGPTの引用</blockquote><p>ChatGPTの本文</p>"
        out, _ = tool_links.link_tools(html, TOOLS)
        self.assertIn("<blockquote>ChatGPTの引用</blockquote>", out)
        self.assertIn('<p><a href="/tools/chatgpt/">ChatGPT</a>の本文</p>', out)

    def test_latin_name_does_not_match_inside_a_longer_word(self):
        out, linked = tool_links.link_tools("<p>n8nxとClaudeX</p>", TOOLS)
        self.assertEqual(linked, [])
        out, linked = tool_links.link_tools("<p>n8nで自動化</p>", TOOLS)
        self.assertEqual(linked, ["n8n"])

    def test_latin_name_does_not_match_after_a_letter_or_digit(self):
        out, linked = tool_links.link_tools("<p>xn8nとAClaudeと9ChatGPT</p>", TOOLS)
        self.assertEqual(linked, [])

    def test_longer_name_wins_and_is_not_relinked(self):
        out, linked = tool_links.link_tools("<p>Stable Diffusionを試す</p>", TOOLS)
        self.assertEqual(linked, ["stable-diffusion"])
        self.assertEqual(out.count("<a "), 1)

    def test_already_linked_tool_is_left_alone(self):
        html = '<p><a href="/tools/claude/">Claude</a>とClaude</p>'
        out, linked = tool_links.link_tools(html, TOOLS)
        self.assertEqual((out, linked), (html, []))

    def test_linking_is_idempotent(self):
        once, _ = tool_links.link_tools(body("ChatGPTとClaude"), TOOLS)
        twice, linked = tool_links.link_tools(once, TOOLS)
        self.assertEqual(twice, once)
        self.assertEqual(linked, [])

    def test_linked_article_still_passes_the_audit(self):
        html = body("ChatGPTの概要です。", "Claudeの概要です。", "まとめです。")
        linked, _ = tool_links.link_tools(html, TOOLS)
        result = audit(linked, tools=TOOLS)
        self.assertEqual(result["verdict"], "PASS")
        self.assertEqual(result["reasons"], [])


class MissingToolLinkTests(unittest.TestCase):
    def test_warn_when_mentioned_but_not_linked(self):
        result = audit(body("ChatGPTの話", "b", "c"), tools=TOOLS)
        self.assertEqual(result["verdict"], "PASS")
        self.assertEqual(result["reasons"], ["WARN:MISSING_TOOL_LINK:chatgpt"])

    def test_no_warn_for_mentions_only_in_headings_or_quotes(self):
        html = "<h2>ChatGPT</h2><p>本文</p><h2>b</h2><blockquote>Claude</blockquote><h2>c</h2><p>x</p>"
        self.assertEqual(tool_links.missing_tool_links(html, TOOLS), [])

    def test_no_check_without_catalog(self):
        self.assertEqual(audit(body("ChatGPTの話", "b", "c"))["reasons"], [])


class CatalogTests(unittest.TestCase):
    def test_repository_catalog_loads(self):
        tools = tool_links.load_catalog({})
        self.assertIsNotNone(tools)
        self.assertIn("claude", {t["slug"] for t in tools})

    def test_env_path_wins_and_bad_file_falls_through(self):
        with tempfile.TemporaryDirectory() as tmp:
            good = Path(tmp) / "tools.json"
            good.write_text(json.dumps({"tools": [{"slug": "x", "name": "X"}]}), encoding="utf-8")
            self.assertEqual(tool_links.load_catalog({"AINAVI_TOOLS_FILE": str(good)}),
                             [{"slug": "x", "name": "X"}])
            bad = Path(tmp) / "bad.json"
            bad.write_text("not json", encoding="utf-8")
            fallback = tool_links.load_catalog({"AINAVI_TOOLS_FILE": str(bad)})
            self.assertIsNotNone(fallback)  # falls back to data/tools.json

    def test_no_catalog_anywhere_returns_none(self):
        original = tool_links.CATALOG_CANDIDATES
        try:
            tool_links.CATALOG_CANDIDATES = (Path("/nonexistent/tools.json"),)
            self.assertIsNone(tool_links.load_catalog({}))
        finally:
            tool_links.CATALOG_CANDIDATES = original


class ServiceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.server = make_server("127.0.0.1", 0, Path(self.tmp.name) / "memory.db")
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_address[1]}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.tmp.cleanup()

    def post(self, path, payload):
        request = Request(self.base + path, data=json.dumps(payload).encode("utf-8"),
                          method="POST", headers={"Content-Type": "application/json"})
        with urlopen(request) as response:
            return json.loads(response.read())

    def test_health_reports_catalog(self):
        with urlopen(self.base + "/health") as response:
            self.assertTrue(json.loads(response.read())["tools_catalog"])

    def test_link_tools_route(self):
        result = self.post("/link-tools", {"content": "<p>Claudeを使う</p>"})
        self.assertEqual(result["links"], ["claude"])
        self.assertIn('href="/tools/claude/"', result["content"])

    def test_audit_route_reports_missing_link(self):
        result = self.post("/audit", {"content": body("Claudeの話", "b", "c"),
                                      "skill_ref": "01-github-trending"})
        self.assertIn("WARN:MISSING_TOOL_LINK:claude", result["reasons"])
        self.assertEqual(result["verdict"], "PASS")

    def test_link_tools_without_catalog_returns_content_unchanged(self):
        self.server.tools = None
        result = self.post("/link-tools", {"content": "<p>Claude</p>"})
        self.assertEqual(result, {"content": "<p>Claude</p>", "links": [], "catalog": False})


if __name__ == "__main__":
    unittest.main()

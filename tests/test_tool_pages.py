"""Tests for the tool DB, tool page generator and draft publisher (requirements §35-11, T-46)."""

import copy
import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from scripts import tool_pages
from scripts.content_audit import audit

TAGS = {"claude", "chatgpt"}
TOOL = {
    "slug": "claude", "name": "Claude", "vendor": "Anthropic",
    "official_url": "https://claude.ai/", "summary": "対話型のAIアシスタントです。",
    "pricing": [],
}
PRICE = {"plan": "Pro", "price": "$20/月", "source_url": "https://example.com/pricing",
         "retrieved_at": "2026-09-01"}
AFFILIATE = {"url": "https://px.a8.net/svt/ejp?a8mat=TEST", "program": "A8.net"}


def data(*tools):
    return {"tools": [copy.deepcopy(t) for t in tools]}


class RepositoryDataTests(unittest.TestCase):
    def test_repository_tools_json_is_valid_and_pages_pass(self):
        errors, pages = tool_pages.check()
        self.assertEqual(errors, [])
        self.assertEqual(pages[0]["slug"], "tools")
        self.assertGreaterEqual(len(pages), 2)

    def test_seed_has_no_unsourced_pricing_or_affiliate(self):
        seed = tool_pages.load_json(tool_pages.TOOLS_FILE)["tools"]
        for tool in seed:
            self.assertNotIn("affiliate", tool, tool["slug"])
            self.assertEqual(tool["pricing"], [], tool["slug"])


class ValidationTests(unittest.TestCase):
    def test_valid_tool(self):
        self.assertEqual(tool_pages.validate(data(TOOL), TAGS), [])

    def test_slug_must_be_a_tag(self):
        tool = {**TOOL, "slug": "unknown"}
        self.assertIn("unknown: not a tag in wp-taxonomy.json (R1/R2 need a tag)",
                      tool_pages.validate(data(tool), TAGS))

    def test_duplicate_and_reserved_slugs(self):
        errors = tool_pages.validate(data(TOOL, TOOL), TAGS)
        self.assertIn("claude: duplicate slug", errors)
        reserved = tool_pages.validate(data({**TOOL, "slug": "tools"}), TAGS | {"tools"})
        self.assertIn("tools: reserved for the index page", reserved)

    def test_missing_required_field(self):
        tool = {k: v for k, v in TOOL.items() if k != "vendor"}
        self.assertIn("claude: vendor is required", tool_pages.validate(data(tool), TAGS))

    def test_official_url_must_be_https(self):
        tool = {**TOOL, "official_url": "http://claude.ai/"}
        self.assertIn("claude: official_url must start with https://",
                      tool_pages.validate(data(tool), TAGS))

    def test_price_row_needs_source_and_date(self):
        tool = {**TOOL, "pricing": [{"plan": "Pro", "price": "$20"}]}
        errors = tool_pages.validate(data(tool), TAGS)
        self.assertIn("claude: pricing[0].source_url must start with https://", errors)
        self.assertIn("claude: pricing[0].retrieved_at must be YYYY-MM-DD", errors)

    def test_affiliate_needs_url_and_program(self):
        tool = {**TOOL, "affiliate": {"url": "https://px.a8.net/x"}}
        self.assertIn("claude: affiliate needs an https url and a program",
                      tool_pages.validate(data(tool), TAGS))


class RenderTests(unittest.TestCase):
    def test_plain_tool_page_passes_audit_without_signature(self):
        result = audit(tool_pages.render_tool(TOOL))
        self.assertEqual(result["verdict"], "PASS")
        self.assertFalse(result["requires_human_signature"])

    def test_tag_archive_link_for_r2(self):
        self.assertIn('<a href="/tag/claude/">', tool_pages.render_tool(TOOL))

    def test_priced_page_shows_source_and_date_and_passes_a4(self):
        html = tool_pages.render_tool({**TOOL, "pricing": [PRICE]})
        self.assertIn("2026-09-01 時点", html)
        self.assertEqual(audit(html)["reasons"], [])

    def test_affiliate_page_passes_a1_a2_and_needs_signature(self):
        html = tool_pages.render_tool({**TOOL, "affiliate": AFFILIATE})
        self.assertLess(html.index("【PR】"), html.index("<h2>"))
        self.assertIn('rel="sponsored nofollow"', html)
        result = audit(html)
        self.assertEqual(result["verdict"], "PASS")
        self.assertTrue(result["requires_human_signature"])

    def test_text_is_escaped(self):
        html = tool_pages.render_tool({**TOOL, "summary": "<script>x</script>"})
        self.assertNotIn("<script>", html)

    def test_index_lists_every_tool(self):
        html = tool_pages.render_index([TOOL, {**TOOL, "slug": "chatgpt", "name": "ChatGPT"}])
        self.assertIn('href="/tools/claude/"', html)
        self.assertIn('href="/tools/chatgpt/"', html)
        self.assertEqual(audit(html)["verdict"], "PASS")

    def test_hype_summary_is_caught_by_the_audit_gate(self):
        pages = tool_pages.build_pages(data({**TOOL, "summary": "革命的なAIです。"}))
        errors = tool_pages.audit_pages(pages)
        self.assertEqual(len(errors), 1)
        self.assertTrue(errors[0].startswith("claude: FAIL"))


class FakeWordPress:
    """In-memory /pages endpoint recording every write."""

    def __init__(self, existing=None):
        self.pages = {p["id"]: p for p in (existing or [])}
        self.writes = []
        self.next_id = 500

    def __call__(self, method, path, body):
        if method == "GET":
            slug = path.split("slug=")[1].split("&")[0]
            return [p for p in self.pages.values() if p["slug"] == slug]
        self.writes.append((path, json.loads(json.dumps(body))))
        if path == "/pages":
            page = {"id": self.next_id, "slug": body["slug"], "status": body["status"],
                    "content": {"raw": body["content"]}, "parent": body.get("parent", 0)}
            self.pages[page["id"]] = page
            self.next_id += 1
            return page
        page = self.pages[int(path.rsplit("/", 1)[1])]
        page.update(status=body["status"], content={"raw": body["content"]},
                    parent=body.get("parent", 0))
        return page


class PublishTests(unittest.TestCase):
    def setUp(self):
        self.pages = tool_pages.build_pages(data(TOOL))

    def test_creates_drafts_with_children_under_index(self):
        wp = FakeWordPress()
        log = tool_pages.publish(self.pages, wp)
        self.assertEqual([line.split()[0] for line in log], ["[CREATED]", "[CREATED]"])
        self.assertTrue(all(body["status"] == "draft" for _, body in wp.writes))
        self.assertEqual(wp.writes[1][1]["parent"], 500)  # id of the index page created first

    def test_second_run_is_idempotent(self):
        wp = FakeWordPress()
        tool_pages.publish(self.pages, wp)
        writes = len(wp.writes)
        log = tool_pages.publish(self.pages, wp)
        self.assertEqual(len(wp.writes), writes)
        self.assertTrue(all(line.startswith("[SKIP]") for line in log))

    def test_changed_draft_is_updated_as_draft(self):
        wp = FakeWordPress()
        tool_pages.publish(self.pages, wp)
        changed = tool_pages.build_pages(data({**TOOL, "summary": "更新した概要です。"}))
        log = tool_pages.publish(changed, wp)
        self.assertIn("[UPDATED] claude", log[1])
        self.assertEqual(wp.writes[-1][1]["status"], "draft")

    def test_changed_published_page_is_held_not_overwritten(self):
        wp = FakeWordPress()
        tool_pages.publish(self.pages, wp)
        for page in wp.pages.values():
            page["status"] = "publish"  # a human signed and published it
        changed = tool_pages.build_pages(data({**TOOL, "summary": "更新した概要です。"}))
        writes = len(wp.writes)
        log = tool_pages.publish(changed, wp)
        self.assertIn("[HOLD] claude", log[1])
        self.assertEqual(len(wp.writes), writes)


class WpTargetTests(unittest.TestCase):
    def test_bearer_uses_wordpress_com_api(self):
        base, auth = tool_pages.wp_target({"WP_BEARER_TOKEN": "t", "WP_SITE": "s.wordpress.com"})
        self.assertEqual(base, "https://public-api.wordpress.com/wp/v2/sites/s.wordpress.com")
        self.assertEqual(auth, "Bearer t")

    def test_basic_uses_self_hosted_api(self):
        base, auth = tool_pages.wp_target({"WP_URL": "http://localhost:8080/",
                                           "WP_USERNAME": "u", "WP_APP_PASSWORD": "p"})
        self.assertEqual(base, "http://localhost:8080/wp-json/wp/v2")
        self.assertTrue(auth.startswith("Basic "))

    def test_missing_credentials_stop(self):
        with self.assertRaises(SystemExit):
            tool_pages.wp_target({})
        with self.assertRaises(SystemExit):
            tool_pages.wp_target({"WP_BEARER_TOKEN": "t"})


class HttpTransportTests(unittest.TestCase):
    """publish() over real HTTP against a local fake WordPress pages endpoint."""

    def test_publish_over_http_sends_auth_and_creates_drafts(self):
        store = {"pages": [], "auth": []}

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, format, *args):  # noqa: A002
                pass

            def _send(self, body):
                data = json.dumps(body).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def do_GET(self):
                store["auth"].append(self.headers.get("Authorization"))
                slug = self.path.split("slug=")[1].split("&")[0]
                self._send([p for p in store["pages"] if p["slug"] == slug])

            def do_POST(self):
                store["auth"].append(self.headers.get("Authorization"))
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                page = {"id": 900 + len(store["pages"]), "slug": body["slug"],
                        "status": body["status"], "content": {"raw": body["content"]}}
                store["pages"].append(page)
                self._send(page)

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            base = f"http://127.0.0.1:{server.server_address[1]}/wp-json/wp/v2"
            send = tool_pages.http_transport(base, "Basic dGVzdDp0ZXN0")
            log = tool_pages.publish(tool_pages.build_pages(data(TOOL)), send)
        finally:
            server.shutdown()
            server.server_close()
            thread.join()
        self.assertEqual([line.split()[0] for line in log], ["[CREATED]", "[CREATED]"])
        self.assertEqual({p["status"] for p in store["pages"]}, {"draft"})
        self.assertEqual(set(store["auth"]), {"Basic dGVzdDp0ZXN0"})


if __name__ == "__main__":
    unittest.main()

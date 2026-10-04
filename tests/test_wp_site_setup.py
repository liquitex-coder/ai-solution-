"""Tests for the plugin-based site design setup (requirements §35-14, T-51)."""

import copy
import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from scripts import wp_site_setup as site
from scripts.tool_pages import http_transport

MANIFEST = site.load_manifest()


class FakeWordPress:
    """In-memory /plugins, /themes and /global-styles endpoints."""

    def __init__(self, plugins=None, theme="twentytwentyfive", styles_link=True, fail=()):
        self.plugins = {p["plugin"]: dict(p) for p in (plugins or [])}
        self.theme = theme
        self.styles_link = styles_link
        self.fail = set(fail)
        self.writes = []

    def __call__(self, method, path, body):
        if method == "GET" and path.startswith("/plugins"):
            return list(self.plugins.values())
        if method == "GET" and path.startswith("/themes"):
            links = ({"wp:user-global-styles": [{"href": "https://x/wp-json/wp/v2/global-styles/42"}]}
                     if self.styles_link else {})
            return [{"stylesheet": self.theme, "_links": links}]
        self.writes.append((path, json.loads(json.dumps(body))))
        if path == "/plugins":
            if body["slug"] in self.fail:
                raise RuntimeError("HTTP 500")
            key = f"{body['slug']}/{body['slug']}"
            self.plugins[key] = {"plugin": key, "status": body["status"]}
            return self.plugins[key]
        if path.startswith("/plugins/"):
            key = path[len("/plugins/"):]
            self.plugins[key]["status"] = body["status"]
            return self.plugins[key]
        return {"id": 42}


class ValidateTests(unittest.TestCase):
    def test_repository_manifest_is_valid(self):
        self.assertEqual(site.validate(MANIFEST), [])

    def test_forbidden_plugin_fails(self):
        data = copy.deepcopy(MANIFEST)
        data["plugins"].append({"slug": "classic-editor", "purpose": "x", "targets": ["wpcom"]})
        self.assertIn("classic-editor: forbidden plugin (§35-14)", site.validate(data))

    def test_missing_purpose_and_bad_target_fail(self):
        data = copy.deepcopy(MANIFEST)
        data["plugins"][0]["purpose"] = ""
        data["plugins"][1]["targets"] = ["mars"]
        errors = site.validate(data)
        self.assertIn("kadence-blocks: purpose is required", errors)
        self.assertTrue(any("wp-dark-mode: targets" in e for e in errors))

    def test_html_in_custom_css_fails(self):
        data = copy.deepcopy(MANIFEST)
        data["global_styles"]["styles"]["css"] = "body{color:red}</style><script>x</script>"
        self.assertIn("global_styles.styles.css must be plain CSS without HTML tags",
                      site.validate(data))

    def test_low_contrast_fails(self):
        data = copy.deepcopy(MANIFEST)
        for color in data["global_styles"]["settings"]["color"]["palette"]["theme"]:
            if color["slug"] == "accent-4":
                color["color"] = "#BBBBBB"
        errors = site.validate(data)
        self.assertTrue(any(e.startswith("contrast pair ['accent-4', 'base']") for e in errors))

    def test_contrast_ratio_matches_wcag_reference(self):
        self.assertAlmostEqual(site.contrast_ratio("#000000", "#FFFFFF"), 21.0, places=2)
        self.assertAlmostEqual(site.contrast_ratio("#FFFFFF", "#FFFFFF"), 1.0, places=2)


class SetupTests(unittest.TestCase):
    def test_plan_is_read_only(self):
        wp = FakeWordPress()
        log = site.setup(MANIFEST, wp, "wpcom", apply=False)
        self.assertEqual(wp.writes, [])
        self.assertIn("[PLAN] kadence-blocks: install+activate", log)
        self.assertIn("[PLAN] global styles 42: palette, fonts, card CSS", log)

    def test_apply_installs_activates_and_styles(self):
        wp = FakeWordPress(plugins=[
            {"plugin": "seo-by-rank-math/rank-math", "status": "inactive"},
            {"plugin": "wp-dark-mode/plugin", "status": "active"},
            {"plugin": "hello-dolly/hello", "status": "active"},
        ])
        log = site.setup(MANIFEST, wp, "wpcom", apply=True)
        self.assertIn("[DONE] kadence-blocks: install+activate", log)
        self.assertIn("[DONE] seo-by-rank-math: activate", log)
        self.assertIn("[SKIP] wp-dark-mode: already active", log)
        self.assertIn("[SKIP] wp-super-cache: not for wpcom", log)
        self.assertEqual(wp.writes[-1][0], "/global-styles/42")
        self.assertEqual(wp.writes[-1][1], MANIFEST["global_styles"])

    def test_additive_only(self):
        wp = FakeWordPress(plugins=[{"plugin": "hello-dolly/hello", "status": "active"}])
        site.setup(MANIFEST, wp, "self-hosted", apply=True)
        self.assertEqual(wp.plugins["hello-dolly/hello"]["status"], "active")
        self.assertTrue(all(body.get("status") in (None, "active") for _, body in wp.writes))

    def test_self_hosted_gets_page_cache(self):
        wp = FakeWordPress()
        log = site.setup(MANIFEST, wp, "self-hosted", apply=True)
        self.assertIn("[DONE] wp-super-cache: install+activate", log)

    def test_wrong_theme_stops_before_styles(self):
        wp = FakeWordPress(theme="twentytwentyfour")
        log = site.setup(MANIFEST, wp, "wpcom", apply=True)
        self.assertTrue(log[-1].startswith("[TODO] activate theme twentytwentyfive"))
        self.assertFalse(any(path.startswith("/global-styles") for path, _ in wp.writes))

    def test_missing_styles_link_is_a_todo(self):
        wp = FakeWordPress(styles_link=False)
        log = site.setup(MANIFEST, wp, "wpcom", apply=True)
        self.assertTrue(log[-1].startswith("[TODO] user global styles id not exposed"))

    def test_one_failing_plugin_does_not_stop_the_rest(self):
        wp = FakeWordPress(fail={"kadence-blocks"})
        log = site.setup(MANIFEST, wp, "wpcom", apply=True)
        self.assertTrue(any(line.startswith("[WARN] kadence-blocks") for line in log))
        self.assertIn("[DONE] wp-dark-mode: install+activate", log)

    def test_second_apply_is_idempotent(self):
        wp = FakeWordPress()
        site.setup(MANIFEST, wp, "wpcom", apply=True)
        plugin_writes = [w for w in wp.writes if w[0].startswith("/plugins")]
        site.setup(MANIFEST, wp, "wpcom", apply=True)
        self.assertEqual([w for w in wp.writes if w[0].startswith("/plugins")], plugin_writes)

    def test_target_selection(self):
        self.assertEqual(site.target_of({"WP_BEARER_TOKEN": "t"}), "wpcom")
        self.assertEqual(site.target_of({}), "self-hosted")


class HttpRoundTripTests(unittest.TestCase):
    """setup() over real HTTP against a local fake WordPress REST API."""

    def test_apply_over_http(self):
        wp = FakeWordPress()

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, format, *args):  # noqa: A002
                pass

            def _reply(self, payload):
                data = json.dumps(payload).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def _path(self):
                return self.path.split("/wp-json/wp/v2", 1)[1]

            def do_GET(self):
                self._reply(wp("GET", self._path(), None))

            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                self._reply(wp("POST", self._path(), body))

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            base = f"http://127.0.0.1:{server.server_address[1]}/wp-json/wp/v2"
            log = site.setup(MANIFEST, http_transport(base, "Basic dTpw"), "self-hosted", apply=True)
        finally:
            server.shutdown()
            server.server_close()
            thread.join()
        self.assertEqual(sum(line.startswith("[DONE]") for line in log), 6)


if __name__ == "__main__":
    unittest.main()

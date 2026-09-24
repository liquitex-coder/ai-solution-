"""Tests for the §35-3 taxonomy silo hierarchy: check_wired W13 and wp-init.sh parent pass."""

import json
import os
import shutil
import subprocess
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from scripts.check_wired import taxonomy_hierarchy_errors

ROOT = Path(__file__).resolve().parent.parent
TAXONOMY = json.loads((ROOT / "data" / "wp-taxonomy.json").read_text(encoding="utf-8"))


class HierarchyRuleTests(unittest.TestCase):
    def test_repository_taxonomy_is_valid(self):
        self.assertEqual(taxonomy_hierarchy_errors(TAXONOMY["categories"]), [])

    def test_every_wf_category_has_a_silo(self):
        for category in TAXONOMY["categories"]:
            if category.get("source_workflow"):
                self.assertIn(category.get("parent"), {"news", "tools", "compare"},
                              category["slug"])

    def test_wf_category_without_parent_fails(self):
        cats = [{"slug": "news"}, {"slug": "a", "source_workflow": "WF-01"}]
        self.assertEqual(taxonomy_hierarchy_errors(cats), ["a: WF category has no silo parent"])

    def test_unknown_parent_fails(self):
        cats = [{"slug": "a", "parent": "missing"}]
        self.assertEqual(taxonomy_hierarchy_errors(cats), ["a: unknown parent missing"])

    def test_self_parent_fails(self):
        cats = [{"slug": "a", "parent": "a"}]
        self.assertEqual(taxonomy_hierarchy_errors(cats), ["a: parent is itself"])

    def test_depth_three_fails(self):
        cats = [{"slug": "root"}, {"slug": "mid", "parent": "root"},
                {"slug": "leaf", "parent": "mid"}]
        self.assertEqual(taxonomy_hierarchy_errors(cats),
                         ["leaf: parent mid is not a silo root (depth > 2)"])


class FakeWordPress(BaseHTTPRequestHandler):
    """Minimal wp/v2 categories/tags/users endpoints backed by in-memory dicts."""

    state: dict = {}

    def log_message(self, format, *args):  # noqa: A002 - silence test output
        pass

    def _send(self, status, body):
        data = json.dumps(body).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _body(self):
        length = int(self.headers.get("Content-Length") or 0)
        return json.loads(self.rfile.read(length) or b"{}")

    def do_GET(self):
        url = urlparse(self.path)
        kind = url.path.rsplit("/", 1)[-1]
        if kind == "me":
            self._send(200, {"id": 1})
            return
        slug = parse_qs(url.query).get("slug", [""])[0]
        items = self.state[kind]
        self._send(200, [item for item in items.values() if item["slug"] == slug])

    def do_POST(self):
        parts = urlparse(self.path).path.rstrip("/").split("/")
        body = self._body()
        if parts[-1].isdigit():
            item = self.state["categories"][int(parts[-1])]
            item.update(body)
            self.state["updates"] += 1
            self._send(200, item)
            return
        kind = parts[-1]
        new_id = self.state["next_id"]
        self.state["next_id"] += 1
        item = {"id": new_id, "slug": body["slug"], "name": body["name"], "parent": 0}
        self.state[kind][new_id] = item
        self._send(201, item)


@unittest.skipUnless(shutil.which("bash") and shutil.which("jq") and shutil.which("curl"),
                     "wp-init.sh needs bash, jq and curl")
class WpInitParentPassTests(unittest.TestCase):
    def setUp(self):
        FakeWordPress.state = {"categories": {}, "tags": {}, "next_id": 100, "updates": 0}
        # a pre-existing flat category (production state before §35) must be re-parented
        FakeWordPress.state["categories"][7] = {
            "id": 7, "slug": "github-trending", "name": "GitHubトレンド", "parent": 0}
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), FakeWordPress)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()

    def _run(self):
        env = dict(os.environ)
        for key in ("WP_BEARER_TOKEN", "WP_SITE", "HTTP_PROXY", "HTTPS_PROXY",
                    "http_proxy", "https_proxy"):
            env.pop(key, None)
        env.update({"WP_URL": f"http://127.0.0.1:{self.server.server_port}",
                    "WP_APP_PASSWORD": "test-only", "NO_PROXY": "127.0.0.1",
                    "no_proxy": "127.0.0.1"})
        return subprocess.run(["bash", str(ROOT / "scripts" / "wp-init.sh")], env=env,
                              capture_output=True, text=True, encoding="utf-8",
                              timeout=120, check=True)

    def _by_slug(self):
        return {c["slug"]: c for c in FakeWordPress.state["categories"].values()}

    def test_children_are_attached_to_silo_roots(self):
        self._run()
        cats = self._by_slug()
        for category in TAXONOMY["categories"]:
            parent = category.get("parent")
            expected = cats[parent]["id"] if parent else 0
            self.assertEqual(cats[category["slug"]]["parent"], expected, category["slug"])

    def test_second_run_is_idempotent(self):
        self._run()
        updates = FakeWordPress.state["updates"]
        count = len(FakeWordPress.state["categories"])
        out = self._run().stdout
        self.assertEqual(FakeWordPress.state["updates"], updates)
        self.assertEqual(len(FakeWordPress.state["categories"]), count)
        self.assertIn("[SKIP] Parent already set: github-trending -> news", out)


if __name__ == "__main__":
    unittest.main()

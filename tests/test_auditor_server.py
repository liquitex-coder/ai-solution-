"""Integration tests for the Auditor Gate HTTP service."""

import hashlib
import json
import sqlite3
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from scripts import auditor_server
from scripts.auditor_server import make_server


class AuditorServerTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "memory.db"
        self.server = make_server("127.0.0.1", 0, self.db_path)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base_url = f"http://127.0.0.1:{self.server.server_address[1]}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.temp_dir.cleanup()

    def request(self, path, method="GET", body=None):
        data = None if body is None else json.dumps(body).encode("utf-8")
        request = Request(self.base_url + path, data=data, method=method)
        if data is not None:
            request.add_header("Content-Type", "application/json")
        with urlopen(request) as response:
            return response.status, json.loads(response.read().decode("utf-8"))

    def facts(self):
        conn = sqlite3.connect(self.db_path)
        try:
            return conn.execute("SELECT * FROM facts ORDER BY id").fetchall()
        finally:
            conn.close()

    def test_health_reports_available_memory_database(self):
        status, body = self.request("/health")
        self.assertEqual(status, 200)
        self.assertEqual(body, {"status": "ok", "service": "claim-auditor-gate", "memory_db": True})

    def test_pass_does_not_add_fact(self):
        content = '<h2>One</h2><h2>Two</h2><h2>Three</h2><a href="https://example.test">source</a>'
        status, body = self.request("/audit", "POST", {"content": content})
        self.assertEqual(status, 200)
        self.assertEqual(body["verdict"], "PASS")
        self.assertEqual(self.facts(), [])

    def test_hype_failure_is_stored_with_category_and_hash(self):
        content = "\u9769\u547d\u7684\u306a\u8a18\u4e8b"
        status, body = self.request("/audit", "POST", {
            "content": content,
            "skill_ref": "n8n/skills/20-auditor-gate.md",
        })
        self.assertEqual(status, 200)
        self.assertEqual(body["verdict"], "FAIL")
        row, = self.facts()
        self.assertEqual(row[5], "FAIL:HYPE")
        self.assertEqual(row[6], "n8n/skills/20-auditor-gate.md")
        self.assertEqual(row[7], hashlib.sha256(content.encode()).hexdigest())

    def test_unsourced_numeric_article_is_stored_as_unverifiable(self):
        content = "<h2>A</h2><h2>B</h2><h2>C</h2>\u5229\u7528\u8005\u304c300%\u5897\u52a0"
        status, body = self.request("/audit", "POST", {"content": content})
        self.assertEqual(status, 200)
        self.assertEqual(body["verdict"], "UNVERIFIABLE")
        row, = self.facts()
        self.assertEqual(row[3], "UNVERIFIABLE")

    def test_invalid_json_returns_400(self):
        request = Request(self.base_url + "/audit", data=b"{", method="POST")
        with self.assertRaises(HTTPError) as raised:
            urlopen(request)
        self.assertEqual(raised.exception.code, 400)

    def test_unknown_path_returns_404(self):
        with self.assertRaises(HTTPError) as raised:
            urlopen(self.base_url + "/missing")
        self.assertEqual(raised.exception.code, 404)

    def test_unavailable_database_does_not_block_audit(self):
        blocker = Path(self.temp_dir.name) / "not-a-directory"
        blocker.write_text("block")
        server = make_server("127.0.0.1", 0, blocker / "memory.db")
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base_url = f"http://127.0.0.1:{server.server_address[1]}"
        try:
            with urlopen(base_url + "/health") as response:
                self.assertFalse(json.loads(response.read())["memory_db"])
            request = Request(base_url + "/audit", data=json.dumps({
                "content": "\u9769\u547d\u7684\u306a\u8a18\u4e8b",
            }).encode(), method="POST")
            with urlopen(request) as response:
                body = json.loads(response.read())
            self.assertEqual(body["verdict"], "FAIL")
            self.assertIsNone(body["fact_id"])
        finally:
            server.shutdown()
            server.server_close()
            thread.join()

    def test_transient_write_failure_does_not_latch_memory_db(self):
        original_connect = auditor_server.memory_init.connect
        call_count = {"n": 0}

        def flaky_connect(path):
            call_count["n"] += 1
            if call_count["n"] == 1:
                raise sqlite3.OperationalError("database is locked")
            return original_connect(path)

        auditor_server.memory_init.connect = flaky_connect
        try:
            status, body = self.request("/audit", "POST", {
                "content": "革命的な記事",
            })
            self.assertEqual(status, 200)
            self.assertIsNone(body["fact_id"])

            # The latch must be gone: /health still reports the DB available,
            # and the very next write succeeds once the transient error clears.
            health_status, health_body = self.request("/health")
            self.assertEqual(health_status, 200)
            self.assertTrue(health_body["memory_db"])

            status2, body2 = self.request("/audit", "POST", {
                "content": "革命的な記事2",
            })
            self.assertEqual(status2, 200)
            self.assertIsNotNone(body2["fact_id"])
        finally:
            auditor_server.memory_init.connect = original_connect


if __name__ == "__main__":
    unittest.main()

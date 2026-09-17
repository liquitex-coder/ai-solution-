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
from scripts.auditor_server import make_server, resolve_port


class ResolvePortTests(unittest.TestCase):
    """§28-2 port row: AINAVI_GATE_PORT -> PORT (Render/Fly.io) -> 8090."""

    def test_ainavi_gate_port_wins_over_port(self):
        self.assertEqual(resolve_port({"AINAVI_GATE_PORT": "8091", "PORT": "10000"}), 8091)

    def test_port_used_when_ainavi_gate_port_unset(self):
        self.assertEqual(resolve_port({"PORT": "10000"}), 10000)

    def test_default_8090_when_neither_set(self):
        self.assertEqual(resolve_port({}), 8090)

    def test_empty_ainavi_gate_port_falls_through_to_port(self):
        self.assertEqual(resolve_port({"AINAVI_GATE_PORT": "", "PORT": "10000"}), 10000)


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

    def warnings(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            return [dict(r) for r in conn.execute("SELECT * FROM warnings ORDER BY id")]
        finally:
            conn.close()

    def test_health_reports_available_memory_database(self):
        status, body = self.request("/health")
        self.assertEqual(status, 200)
        self.assertEqual(body, {"status": "ok", "service": "ainavi-auditor-gate",
                                 "memory_db": True, "auth": False})

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
            # Call #1 is the find_prior_fact lookup (must succeed so the
            # audit proceeds); call #2 is the store_fact write we want to
            # fail transiently.
            if call_count["n"] == 2:
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

    def test_resubmitting_rejected_content_is_already_rejected(self):
        content = "革命的な記事の再提出テスト"
        status1, body1 = self.request("/audit", "POST", {"content": content})
        self.assertEqual(status1, 200)
        self.assertEqual(body1["verdict"], "FAIL")
        self.assertIsNotNone(body1["fact_id"])
        self.assertEqual(len(self.facts()), 1)

        status2, body2 = self.request("/audit", "POST", {"content": content})
        self.assertEqual(status2, 200)
        self.assertEqual(body2["verdict"], "FAIL")
        self.assertEqual(body2["reasons"], body1["reasons"] + [f"WARN:ALREADY_REJECTED:{body1['fact_id']}"])
        self.assertEqual(body2["fact_id"], body1["fact_id"])
        # no duplicate row was written for the resubmission
        self.assertEqual(len(self.facts()), 1)

    def test_resubmitting_unverifiable_content_is_already_rejected(self):
        # §32-1 D5 fix: find_prior_fact() must cover UNVERIFIABLE rows too, not only FAIL.
        content = "<h2>A</h2><h2>B</h2><h2>C</h2>利用者が300%増加"
        status1, body1 = self.request("/audit", "POST", {"content": content})
        self.assertEqual(status1, 200)
        self.assertEqual(body1["verdict"], "UNVERIFIABLE")
        self.assertIsNotNone(body1["fact_id"])
        self.assertEqual(len(self.facts()), 1)

        status2, body2 = self.request("/audit", "POST", {"content": content})
        self.assertEqual(status2, 200)
        self.assertEqual(body2["verdict"], "UNVERIFIABLE")
        self.assertIn(f"WARN:ALREADY_REJECTED:{body1['fact_id']}", body2["reasons"])
        # no duplicate row was written for the resubmission
        self.assertEqual(len(self.facts()), 1)

    def test_zh_without_translation_label_warns_but_keeps_verdict(self):
        content = "<h2>A</h2><h2>B</h2><h2>C</h2><p>本文には翻訳ラベルがありません。</p>"
        status, body = self.request("/audit", "POST", {
            "content": content,
            "source_urls": ["https://example.cn/article"],
            "source_lang": "zh",
        })
        self.assertEqual(status, 200)
        self.assertIn("WARN:MISSING_TRANSLATION_LABEL", body["reasons"])
        self.assertEqual(body["verdict"], "PASS")

    def _evidence_pack(self, claims):
        return {
            "version": 1,
            "verifier": {"model": "claude-haiku-4-5", "prompt_ref": "50-fact-check.md",
                        "prompt_sha256": "0" * 64, "ok": True, "error": None,
                        "usage": {"input_tokens": 0, "output_tokens": 0}},
            "claims": claims, "probes": [], "ground_truth": {},
        }

    def test_evidence_pack_persists_warning_row_and_summary(self):
        content = ('<h2>One</h2><h2>Two</h2><h2>Three</h2>'
                   '<a href="https://example.test">source</a>')
        evidence = self._evidence_pack([
            {"id": "c1", "text": "x", "type": "FACT", "status": "SUPPORTED",
             "evidence": "this exact span is not in the source at all",
             "source_index": 0, "value": None, "gt_ref": None,
             "feasibility": None, "note": ""},
        ])
        status, body = self.request("/audit", "POST", {
            "content": content, "source_text": "[S0] completely unrelated source text.",
            "evidence": evidence,
        })
        self.assertEqual(status, 200)
        self.assertEqual(body["verdict"], "PASS")
        self.assertEqual(body["evidence_summary"]["evidence_missing"], 1)
        self.assertEqual(self.facts(), [])
        rows = self.warnings()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["verdict"], "PASS")
        self.assertEqual(rows[0]["code"], "WARN:EVIDENCE_NOT_IN_SOURCE")
        self.assertEqual(rows[0]["detail"], "1")
        self.assertEqual(rows[0]["prompt_sha256"], "0" * 64)

    def test_no_evidence_no_summary_no_warnings_row(self):
        content = ('<h2>One</h2><h2>Two</h2><h2>Three</h2>'
                   '<a href="https://example.test">source</a>')
        status, body = self.request("/audit", "POST", {"content": content})
        self.assertEqual(status, 200)
        self.assertNotIn("evidence_summary", body)
        self.assertEqual(self.warnings(), [])

    def test_fail_hype_with_evidence_still_writes_fact_and_fails(self):
        content = "革命的な記事"
        evidence = self._evidence_pack([])
        status, body = self.request("/audit", "POST", {"content": content, "evidence": evidence})
        self.assertEqual(status, 200)
        self.assertEqual(body["verdict"], "FAIL")
        self.assertEqual(len(self.facts()), 1)

    def test_zh_missing_label_warning_is_also_persisted(self):
        content = "<h2>A</h2><h2>B</h2><h2>C</h2><p>本文には翻訳ラベルがありません。</p>"
        status, body = self.request("/audit", "POST", {
            "content": content,
            "source_urls": ["https://example.cn/article"],
            "source_lang": "zh",
        })
        self.assertEqual(status, 200)
        rows = self.warnings()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["code"], "WARN:MISSING_TRANSLATION_LABEL")

    def test_unavailable_database_does_not_block_warnings_either(self):
        blocker = Path(self.temp_dir.name) / "not-a-directory2"
        blocker.write_text("block")
        server = make_server("127.0.0.1", 0, blocker / "memory.db")
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base_url = f"http://127.0.0.1:{server.server_address[1]}"
        try:
            request = Request(base_url + "/audit", data=json.dumps({
                "content": "革命的な記事",
            }).encode(), method="POST")
            with urlopen(request) as response:
                body = json.loads(response.read())
            self.assertEqual(response.status, 200)
            self.assertEqual(body["verdict"], "FAIL")
        finally:
            server.shutdown()
            server.server_close()
            thread.join()


class AuditorServerAuthTests(unittest.TestCase):
    """§28-2 (v2.4) / T-27: AINAVI_GATE_TOKEN on the write paths."""

    TOKEN = "test-shared-secret"

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "memory.db"
        self.server = make_server("127.0.0.1", 0, self.db_path, self.TOKEN)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base_url = f"http://127.0.0.1:{self.server.server_address[1]}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.temp_dir.cleanup()

    def facts(self):
        conn = sqlite3.connect(self.db_path)
        try:
            return conn.execute("SELECT * FROM facts ORDER BY id").fetchall()
        finally:
            conn.close()

    def request(self, path, method="GET", body=None, token=None):
        data = None if body is None else json.dumps(body).encode("utf-8")
        request = Request(self.base_url + path, data=data, method=method)
        if data is not None:
            request.add_header("Content-Type", "application/json")
        if token is not None:
            request.add_header("Authorization", f"Bearer {token}")
        try:
            with urlopen(request) as response:
                return response.status, json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            return exc.code, json.loads(exc.read().decode("utf-8"))

    def test_health_never_requires_auth_and_reports_auth_true(self):
        status, body = self.request("/health")
        self.assertEqual(status, 200)
        self.assertEqual(body["auth"], True)

    def test_correct_token_allows_audit_and_writes_fact_on_fail(self):
        status, body = self.request("/audit", "POST", {"content": "革命的な記事"}, token=self.TOKEN)
        self.assertEqual(status, 200)
        self.assertEqual(body["verdict"], "FAIL")
        self.assertEqual(len(self.facts()), 1)

    def test_wrong_token_is_unauthorized_and_writes_nothing(self):
        status, body = self.request("/audit", "POST", {"content": "革命的な記事"}, token="wrong")
        self.assertEqual(status, 401)
        self.assertEqual(body, {"error": "unauthorized"})
        self.assertEqual(self.facts(), [])

    def test_missing_token_is_unauthorized(self):
        status, body = self.request("/audit", "POST", {"content": "革命的な記事"})
        self.assertEqual(status, 401)
        self.assertEqual(body, {"error": "unauthorized"})
        self.assertEqual(self.facts(), [])

    def test_non_ascii_bearer_token_is_unauthorized_not_400(self):
        status, body = self.request("/audit", "POST", {"content": "革命的な記事"}, token="tokén")
        self.assertEqual(status, 401)
        self.assertEqual(body, {"error": "unauthorized"})
        self.assertEqual(self.facts(), [])

    def test_embed_diagrams_also_requires_token(self):
        status, _ = self.request("/embed-diagrams", "POST", {"content": "<p>x</p>"})
        self.assertEqual(status, 401)
        status, _ = self.request("/embed-diagrams", "POST", {"content": "<p>x</p>"}, token=self.TOKEN)
        self.assertEqual(status, 200)


class AuditorServerNoTokenTests(unittest.TestCase):
    """Unset AINAVI_GATE_TOKEN: behaviour unchanged, /health reports auth=false."""

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

    def test_health_reports_auth_false_when_token_unset(self):
        with urlopen(self.base_url + "/health") as response:
            body = json.loads(response.read().decode("utf-8"))
        self.assertEqual(body["auth"], False)

    def test_audit_without_header_still_succeeds_when_token_unset(self):
        request = Request(self.base_url + "/audit",
                           data=json.dumps({"content": "普通の記事"}).encode("utf-8"),
                           method="POST", headers={"Content-Type": "application/json"})
        with urlopen(request) as response:
            status = response.status
        self.assertEqual(status, 200)


if __name__ == "__main__":
    unittest.main()

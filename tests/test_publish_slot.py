"""Tests for the daily publish-slot service (requirements §35-9, T-44)."""

import hashlib
import json
import sqlite3
import tempfile
import threading
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from scripts import auditor_server
from scripts.auditor_server import jst_today, make_server, resolve_news_daily_limit


def h(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class JstDayTests(unittest.TestCase):
    def test_utc_evening_is_next_jst_day(self):
        self.assertEqual(jst_today(datetime(2026, 9, 24, 15, 0, tzinfo=timezone.utc)),
                         "2026-09-25")

    def test_utc_before_1500_is_same_jst_day(self):
        self.assertEqual(jst_today(datetime(2026, 9, 24, 14, 59, tzinfo=timezone.utc)),
                         "2026-09-24")


class LimitConfigTests(unittest.TestCase):
    def test_default_is_three(self):
        self.assertEqual(resolve_news_daily_limit({}), 3)

    def test_env_override_and_floor_at_zero(self):
        self.assertEqual(resolve_news_daily_limit({"AINAVI_NEWS_DAILY_LIMIT": "5"}), 5)
        self.assertEqual(resolve_news_daily_limit({"AINAVI_NEWS_DAILY_LIMIT": "-1"}), 0)


class PublishSlotServiceTests(unittest.TestCase):
    LIMIT = 3

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "memory.db"
        self.start(self.db_path, token="")
        self.day = mock.patch.object(auditor_server, "jst_today", return_value="2026-09-24")
        self.day.start()

    def start(self, db_path, token):
        self.server = make_server("127.0.0.1", 0, db_path, token, self.LIMIT)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base_url = f"http://127.0.0.1:{self.server.server_address[1]}"

    def stop(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()

    def tearDown(self):
        self.day.stop()
        self.stop()
        self.temp_dir.cleanup()

    def slot(self, silo, content_hash, token=None):
        data = json.dumps({"silo": silo, "content_hash": content_hash}).encode("utf-8")
        request = Request(self.base_url + "/publish-slot", data=data, method="POST",
                          headers={"Content-Type": "application/json"})
        if token:
            request.add_header("Authorization", f"Bearer {token}")
        with urlopen(request) as response:
            return json.loads(response.read())

    def rows(self):
        conn = sqlite3.connect(self.db_path)
        try:
            return conn.execute("SELECT day, silo, content_hash FROM publish_slots").fetchall()
        finally:
            conn.close()

    def test_news_granted_up_to_limit_then_refused(self):
        results = [self.slot("news", h(f"a{i}")) for i in range(4)]
        self.assertEqual([r["granted"] for r in results], [True, True, True, False])
        self.assertEqual(results[-1]["reason"], "daily_limit_reached")
        self.assertEqual(results[-1]["used"], 3)
        self.assertEqual(results[-1]["limit"], 3)
        self.assertEqual(len(self.rows()), 3)

    def test_repeat_hash_does_not_consume_a_slot(self):
        for _ in range(3):
            self.assertTrue(self.slot("news", h("same"))["granted"])
        self.assertEqual(len(self.rows()), 1)
        self.assertTrue(self.slot("news", h("b"))["granted"])
        self.assertTrue(self.slot("news", h("c"))["granted"])
        self.assertFalse(self.slot("news", h("d"))["granted"])
        self.assertTrue(self.slot("news", h("same"))["granted"])  # still held after cap

    def test_new_jst_day_resets_the_count(self):
        for i in range(3):
            self.slot("news", h(f"a{i}"))
        self.assertFalse(self.slot("news", h("late"))["granted"])
        with mock.patch.object(auditor_server, "jst_today", return_value="2026-09-25"):
            result = self.slot("news", h("late"))
        self.assertTrue(result["granted"])
        self.assertEqual(result["day"], "2026-09-25")

    def test_tools_unlimited_and_unrecorded(self):
        results = [self.slot("tools", h(f"t{i}")) for i in range(5)]
        self.assertTrue(all(r["granted"] for r in results))
        self.assertEqual(self.rows(), [])

    def test_compare_never_granted(self):
        result = self.slot("compare", h("x"))
        self.assertFalse(result["granted"])
        self.assertEqual(result["reason"], "human_signature_required")
        self.assertEqual(self.rows(), [])

    def test_invalid_input_is_400(self):
        for body in ({"silo": "blog", "content_hash": h("x")},
                     {"silo": "news", "content_hash": "abc"},
                     {"silo": "news", "content_hash": h("x").upper()}):
            request = Request(self.base_url + "/publish-slot",
                              data=json.dumps(body).encode("utf-8"), method="POST",
                              headers={"Content-Type": "application/json"})
            with self.assertRaises(HTTPError) as ctx:
                urlopen(request)
            self.assertEqual(ctx.exception.code, 400)

    def test_concurrent_requests_never_exceed_limit(self):
        results = []
        lock = threading.Lock()

        def worker(i):
            r = self.slot("news", h(f"c{i}"))
            with lock:
                results.append(r["granted"])

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(12)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(results.count(True), 3)
        self.assertEqual(len(self.rows()), 3)

    def test_store_unavailable_fails_closed(self):
        self.stop()
        blocker = Path(self.temp_dir.name) / "not-a-dir"
        blocker.write_text("x", encoding="utf-8")
        self.start(blocker / "memory.db", token="")
        result = self.slot("news", h("x"))
        self.assertFalse(result["granted"])
        self.assertEqual(result["reason"], "slot_store_unavailable")

    def test_auth_required_when_token_set(self):
        self.stop()
        self.start(self.db_path, token="test-token")
        request = Request(self.base_url + "/publish-slot",
                          data=json.dumps({"silo": "news", "content_hash": h("x")}).encode(),
                          method="POST", headers={"Content-Type": "application/json"})
        with self.assertRaises(HTTPError) as ctx:
            urlopen(request)
        self.assertEqual(ctx.exception.code, 401)
        self.assertTrue(self.slot("news", h("x"), token="test-token")["granted"])


if __name__ == "__main__":
    unittest.main()

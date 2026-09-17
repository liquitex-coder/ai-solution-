"""Tests for the --warn 30-day observation report (requirements §34-6)."""

import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from scripts import memory_init
from scripts.ratchet_check import main


class WarnReportTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "memory.db"
        conn = memory_init.connect(self.db_path)
        try:
            memory_init.ensure_schema(conn)
            memory_init.insert_warning(conn, "hash1", "01-github-trending", "PASS",
                                       "WARN:EVIDENCE_NOT_IN_SOURCE", detail="1")
            memory_init.insert_warning(conn, "hash1", "01-github-trending", "PASS",
                                       "WARN:EVIDENCE_NOT_IN_SOURCE", detail="1")
            memory_init.insert_warning(conn, "hash2", "01-github-trending", "PASS",
                                       "WARN:EVIDENCE_NOT_IN_SOURCE", detail="1")
        finally:
            conn.close()

    def tearDown(self):
        self.temp_dir.cleanup()

    def _run(self, *args):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = main(["--db", str(self.db_path), *args])
        return code, buf.getvalue()

    def test_warn_report_aggregates_by_skill_and_code(self):
        code, out = self._run("--warn")
        self.assertEqual(code, 0)
        self.assertIn("01-github-trending - WARN:EVIDENCE_NOT_IN_SOURCE", out)
        self.assertIn("3 warnings / 2 articles", out)

    def test_warn_report_no_table(self):
        empty_db = Path(self.temp_dir.name) / "empty.db"
        conn = memory_init.connect(empty_db)
        conn.execute("CREATE TABLE facts (id INTEGER PRIMARY KEY)")
        conn.commit()
        conn.close()
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = main(["--db", str(empty_db), "--warn"])
        self.assertEqual(code, 0)
        self.assertIn("no warnings table", buf.getvalue())

    def test_without_warn_flag_uses_existing_ratchet_report(self):
        code, out = self._run()
        self.assertEqual(code, 0)
        self.assertIn("no proposals", out)


if __name__ == "__main__":
    unittest.main()

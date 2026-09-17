"""Tests for the importable SQLite memory layer."""

import sqlite3
import tempfile
import unittest
from pathlib import Path

from scripts.memory_init import (
    ensure_schema, find_duplicate, insert_fact, insert_scene, insert_warning,
)


class MemoryLayerTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.path = Path(self.temp_dir.name) / "memory.db"
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row

    def tearDown(self):
        self.conn.close()
        self.temp_dir.cleanup()

    def test_ensure_schema_is_idempotent(self):
        ensure_schema(self.conn)
        ensure_schema(self.conn)
        self.assertEqual(
            self.conn.execute("SELECT COUNT(*) FROM facts").fetchone()[0], 0)

    def test_insert_fact_returns_id(self):
        ensure_schema(self.conn)
        fact_id = insert_fact(self.conn, "A verified fact", content_hash="abc")
        row = self.conn.execute("SELECT content_hash FROM facts WHERE id=?", (fact_id,)).fetchone()
        self.assertEqual(row["content_hash"], "abc")

    def test_insert_scene_upserts_same_url(self):
        ensure_schema(self.conn)
        first_id = insert_scene(self.conn, "Original", "https://example.test/post", "old")
        second_id = insert_scene(self.conn, "Updated", "https://example.test/post", "new")
        row = self.conn.execute("SELECT title, summary FROM scenes WHERE id=?", (first_id,)).fetchone()
        self.assertEqual(first_id, second_id)
        self.assertEqual(dict(row), {"title": "Updated", "summary": "new"})

    def test_find_duplicate_reports_true_and_false(self):
        ensure_schema(self.conn)
        insert_scene(self.conn, "A distinct article title", "https://example.test/post")
        duplicate = find_duplicate(self.conn, "A distinct article title")
        unique = find_duplicate(self.conn, "An unrelated topic entirely")
        self.assertTrue(duplicate["duplicate"])
        self.assertFalse(unique["duplicate"])

    def test_migration_adds_content_hash(self):
        self.conn.execute(
            "CREATE TABLE facts (id INTEGER PRIMARY KEY, content TEXT NOT NULL, "
            "source_url TEXT DEFAULT '', confidence TEXT DEFAULT 'LOW', verdict TEXT DEFAULT '', "
            "fail_reason TEXT DEFAULT '', skill_ref TEXT DEFAULT '', created_at TEXT NOT NULL)"
        )
        self.conn.commit()
        ensure_schema(self.conn)
        columns = {row["name"] for row in self.conn.execute("PRAGMA table_info(facts)")}
        self.assertIn("content_hash", columns)

    def test_ensure_schema_adds_warnings_table_to_legacy_db(self):
        self.conn.execute(
            "CREATE TABLE facts (id INTEGER PRIMARY KEY, content TEXT NOT NULL, "
            "source_url TEXT DEFAULT '', confidence TEXT DEFAULT 'LOW', verdict TEXT DEFAULT '', "
            "fail_reason TEXT DEFAULT '', skill_ref TEXT DEFAULT '', created_at TEXT NOT NULL)"
        )
        self.conn.commit()
        ensure_schema(self.conn)
        columns = {row["name"] for row in self.conn.execute("PRAGMA table_info(warnings)")}
        self.assertEqual(
            columns,
            {"id", "content_hash", "skill_ref", "verdict", "code", "detail",
             "prompt_sha256", "created_at"},
        )

    def test_insert_warning_returns_id_and_reads_back(self):
        ensure_schema(self.conn)
        warning_id = insert_warning(
            self.conn, "hash123", "01-github-trending", "PASS",
            "WARN:EVIDENCE_NOT_IN_SOURCE", detail="1", prompt_sha256="a" * 64)
        self.assertIsInstance(warning_id, int)
        row = self.conn.execute(
            "SELECT content_hash, code, detail, prompt_sha256, created_at "
            "FROM warnings WHERE id=?", (warning_id,)).fetchone()
        self.assertEqual(row["content_hash"], "hash123")
        self.assertEqual(row["code"], "WARN:EVIDENCE_NOT_IN_SOURCE")
        self.assertEqual(row["detail"], "1")
        self.assertEqual(row["prompt_sha256"], "a" * 64)
        self.assertTrue(row["created_at"])

    def test_ensure_schema_twice_is_idempotent_for_warnings(self):
        ensure_schema(self.conn)
        insert_warning(self.conn, "h1", "01-github-trending", "PASS", "WARN:X")
        ensure_schema(self.conn)
        self.assertEqual(
            self.conn.execute("SELECT COUNT(*) FROM warnings").fetchone()[0], 1)


if __name__ == "__main__":
    unittest.main()

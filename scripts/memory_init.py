#!/usr/bin/env python3
"""Agent memory layer (docs/requirements.md §19) — SQLite 4-layer store.

Layers:
  conversation — current article brief / instructions (session-scoped)
  facts        — verified sources + Auditor FAIL history + confidence (persistent)
  scenes       — past article context for dedup (90-day retention)
  persona      — site tone / forbidden expressions (persistent, human-managed)

Search: FTS5 BM25 always; sqlite-vec vector search when the extension is
available; RRF fusion when both are present. No external dependencies —
degrades gracefully to BM25-only.

Usage:
  python3 scripts/memory_init.py init          [--db data/memory.db]
  python3 scripts/memory_init.py add-fact      --content TEXT [--source-url URL]
                                               [--confidence HIGH|MED|LOW|UNVERIFIABLE]
                                               [--skill-ref REF] [--verdict PASS|FAIL|...]
  python3 scripts/memory_init.py add-scene     --title T --url U [--summary S]
  python3 scripts/memory_init.py add-persona   --rule TEXT [--category tone|forbidden|style]
  python3 scripts/memory_init.py search        --query TEXT [--layer facts|scenes|all]
  python3 scripts/memory_init.py check-dup     --title T [--summary S]
  python3 scripts/memory_init.py prune         # expire scenes older than 90 days
  python3 scripts/memory_init.py stats
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_DB = Path(__file__).resolve().parent.parent / "data" / "memory.db"

SCENE_RETENTION_DAYS = 90       # §19-2
DUP_SIMILARITY_THRESHOLD = 0.85  # §19-4
RRF_K = 60                       # standard RRF constant

CONFIDENCE_LEVELS = ("HIGH", "MED", "LOW", "UNVERIFIABLE")  # §19-6

SCHEMA = """
CREATE TABLE IF NOT EXISTS conversation (
    id INTEGER PRIMARY KEY,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'brief',
    content TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS facts (
    id INTEGER PRIMARY KEY,
    content TEXT NOT NULL,
    source_url TEXT DEFAULT '',
    confidence TEXT NOT NULL DEFAULT 'LOW'
        CHECK (confidence IN ('HIGH','MED','LOW','UNVERIFIABLE')),
    verdict TEXT DEFAULT '',
    fail_reason TEXT DEFAULT '',
    skill_ref TEXT DEFAULT '',
    content_hash TEXT DEFAULT '',
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_facts_skill ON facts (skill_ref, created_at);

CREATE TABLE IF NOT EXISTS scenes (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    url TEXT NOT NULL,
    summary TEXT DEFAULT '',
    posted_at TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_scenes_url ON scenes (url);

CREATE TABLE IF NOT EXISTS persona (
    id INTEGER PRIMARY KEY,
    category TEXT NOT NULL DEFAULT 'tone'
        CHECK (category IN ('tone','forbidden','style')),
    rule TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE VIRTUAL TABLE IF NOT EXISTS facts_fts USING fts5(
    content, source_url, content='facts', content_rowid='id',
    tokenize='trigram'
);
CREATE VIRTUAL TABLE IF NOT EXISTS scenes_fts USING fts5(
    title, summary, content='scenes', content_rowid='id',
    tokenize='trigram'
);

CREATE TRIGGER IF NOT EXISTS facts_ai AFTER INSERT ON facts BEGIN
    INSERT INTO facts_fts(rowid, content, source_url)
    VALUES (new.id, new.content, new.source_url);
END;
CREATE TRIGGER IF NOT EXISTS facts_ad AFTER DELETE ON facts BEGIN
    INSERT INTO facts_fts(facts_fts, rowid, content, source_url)
    VALUES ('delete', old.id, old.content, old.source_url);
END;

CREATE TRIGGER IF NOT EXISTS scenes_ai AFTER INSERT ON scenes BEGIN
    INSERT INTO scenes_fts(rowid, title, summary)
    VALUES (new.id, new.title, new.summary);
END;
CREATE TRIGGER IF NOT EXISTS scenes_ad AFTER DELETE ON scenes BEGIN
    INSERT INTO scenes_fts(scenes_fts, rowid, title, summary)
    VALUES ('delete', old.id, old.title, old.summary);
END;
"""


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def ensure_schema(conn: sqlite3.Connection) -> None:
    """Create memory tables and apply lightweight migrations."""
    conn.executescript(SCHEMA)
    columns = {row[1] for row in conn.execute("PRAGMA table_info(facts)")}
    if "content_hash" not in columns:
        conn.execute("ALTER TABLE facts ADD COLUMN content_hash TEXT DEFAULT ''")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_facts_content_hash ON facts (content_hash)")
    conn.commit()


def insert_fact(conn: sqlite3.Connection, content: str, source_url: str = "",
                confidence: str = "LOW", verdict: str = "",
                fail_reason: str = "", skill_ref: str = "",
                content_hash: str = "") -> int:
    """Store a fact and return its database id."""
    if confidence not in CONFIDENCE_LEVELS:
        raise ValueError(f"confidence must be one of {CONFIDENCE_LEVELS}")
    cur = conn.execute(
        "INSERT INTO facts (content, source_url, confidence, verdict, fail_reason,"
        " skill_ref, content_hash, created_at) VALUES (?,?,?,?,?,?,?,?)",
        (content, source_url, confidence, verdict, fail_reason, skill_ref,
         content_hash, now_iso()),
    )
    conn.commit()
    return cur.lastrowid


def insert_scene(conn: sqlite3.Connection, title: str, url: str,
                 summary: str = "") -> int:
    """Insert or update a scene by URL and return its id."""
    conn.execute(
        "INSERT INTO scenes (title, url, summary, posted_at) VALUES (?,?,?,?) "
        "ON CONFLICT(url) DO UPDATE SET title=excluded.title, summary=excluded.summary",
        (title, url, summary, now_iso()),
    )
    row = conn.execute("SELECT id FROM scenes WHERE url=?", (url,)).fetchone()
    conn.commit()
    return row[0]


def try_load_vec(conn: sqlite3.Connection) -> bool:
    """Load sqlite-vec if installed; BM25-only otherwise (§19-5 graceful path)."""
    try:
        conn.enable_load_extension(True)
        conn.load_extension("vec0")
        return True
    except Exception:
        return False
    finally:
        try:
            conn.enable_load_extension(False)
        except Exception:
            pass


def cmd_init(conn: sqlite3.Connection, args: argparse.Namespace) -> None:
    ensure_schema(conn)
    has_vec = try_load_vec(conn)
    if has_vec:
        conn.execute(
            "CREATE VIRTUAL TABLE IF NOT EXISTS facts_vec USING vec0("
            "fact_id INTEGER PRIMARY KEY, embedding FLOAT[384])"
        )
        conn.execute(
            "CREATE VIRTUAL TABLE IF NOT EXISTS scenes_vec USING vec0("
            "scene_id INTEGER PRIMARY KEY, embedding FLOAT[384])"
        )
    conn.commit()
    tables = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type IN ('table','trigger') ORDER BY name")]
    print(json.dumps({
        "status": "initialized",
        "db": str(args.db),
        "vector_search": "sqlite-vec" if has_vec else "unavailable (BM25-only fallback)",
        "objects": tables,
    }, ensure_ascii=False, indent=2))


def cmd_add_fact(conn: sqlite3.Connection, args: argparse.Namespace) -> None:
    try:
        fact_id = insert_fact(conn, args.content, args.source_url, args.confidence,
                              args.verdict, args.fail_reason, args.skill_ref)
    except ValueError as exc:
        sys.exit(str(exc))
    print(json.dumps({"status": "ok", "layer": "facts", "id": fact_id},
                     ensure_ascii=False))


def cmd_add_scene(conn: sqlite3.Connection, args: argparse.Namespace) -> None:
    scene_id = insert_scene(conn, args.title, args.url, args.summary)
    print(json.dumps({"status": "ok", "layer": "scenes", "id": scene_id},
                     ensure_ascii=False))


def cmd_add_persona(conn: sqlite3.Connection, args: argparse.Namespace) -> None:
    cur = conn.execute(
        "INSERT INTO persona (category, rule, created_at) VALUES (?,?,?)",
        (args.category, args.rule, now_iso()),
    )
    conn.commit()
    print(json.dumps({"status": "ok", "layer": "persona", "id": cur.lastrowid},
                     ensure_ascii=False))


def bm25_search(conn: sqlite3.Connection, fts_table: str, query: str,
                limit: int = 10) -> list[tuple[int, float]]:
    """Return [(rowid, bm25_score)] — lower score = better in SQLite bm25()."""
    sql = (f"SELECT rowid, bm25({fts_table}) AS score FROM {fts_table} "
           f"WHERE {fts_table} MATCH ? ORDER BY score LIMIT ?")
    try:
        return [(r["rowid"], r["score"]) for r in conn.execute(sql, (query, limit))]
    except sqlite3.OperationalError:
        # fall back to LIKE for queries FTS5 cannot parse
        base = "facts" if fts_table == "facts_fts" else "scenes"
        col = "content" if base == "facts" else "title"
        rows = conn.execute(
            f"SELECT id FROM {base} WHERE {col} LIKE ? LIMIT ?",
            (f"%{query}%", limit))
        return [(r["id"], 0.0) for r in rows]


def rrf_fuse(*rankings: list[int]) -> list[int]:
    """Reciprocal Rank Fusion (§19-5) across ranked id lists."""
    scores: dict[int, float] = {}
    for ranking in rankings:
        for rank, doc_id in enumerate(ranking):
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (RRF_K + rank + 1)
    return [doc_id for doc_id, _ in
            sorted(scores.items(), key=lambda kv: kv[1], reverse=True)]


def cmd_search(conn: sqlite3.Connection, args: argparse.Namespace) -> None:
    """WideSearch (§19-7): BM25 (+vector when available) with RRF fusion."""
    results: dict[str, list[dict]] = {}
    layers = ["facts", "scenes"] if args.layer == "all" else [args.layer]
    for layer in layers:
        fts = f"{layer}_fts"
        ranked = [doc_id for doc_id, _ in bm25_search(conn, fts, args.query)]
        # vector ranking would be fused here when sqlite-vec + embeddings exist;
        # BM25-only today, so RRF over a single ranking preserves order
        fused = rrf_fuse(ranked)
        rows = []
        for doc_id in fused[:10]:
            if layer == "facts":
                r = conn.execute(
                    "SELECT id, content, source_url, confidence, verdict,"
                    " fail_reason, created_at FROM facts WHERE id=?",
                    (doc_id,)).fetchone()
            else:
                r = conn.execute(
                    "SELECT id, title, url, summary, posted_at FROM scenes WHERE id=?",
                    (doc_id,)).fetchone()
            if r:
                rows.append(dict(r))
        results[layer] = rows
    print(json.dumps({"query": args.query, "results": results},
                     ensure_ascii=False, indent=2))


def trigram_similarity(a: str, b: str) -> float:
    """Dependency-free similarity for dedup (§19-4)."""
    def grams(s: str) -> set[str]:
        s = s.lower()
        return {s[i:i + 3] for i in range(max(len(s) - 2, 1))}
    ga, gb = grams(a), grams(b)
    if not ga or not gb:
        return 0.0
    return len(ga & gb) / len(ga | gb)


def find_duplicate(conn: sqlite3.Connection, title: str,
                   summary: str = "") -> dict:
    """Return the duplicate-check payload used by the CLI."""
    probe = f"{title} {summary}".strip()
    best: dict | None = None
    best_sim = 0.0
    for row in conn.execute("SELECT id, title, url, summary FROM scenes"):
        sim = trigram_similarity(probe, f"{row[1]} {row[3]}".strip())
        if sim > best_sim:
            best_sim = sim
            best = {"id": row[0], "title": row[1], "url": row[2], "summary": row[3]}
    is_dup = best_sim > DUP_SIMILARITY_THRESHOLD
    action = ("REFRAME_OR_SKIP: 差分情報・新角度・アップデート記事としてリフレーム。"
              "全文重複なら生成スキップ" if is_dup else "PROCEED")
    return {
        "title": title,
        "max_similarity": round(best_sim, 3),
        "threshold": DUP_SIMILARITY_THRESHOLD,
        "duplicate": is_dup,
        "action": action,
        "closest": best,
    }


def cmd_check_dup(conn: sqlite3.Connection, args: argparse.Namespace) -> None:
    print(json.dumps(find_duplicate(conn, args.title, args.summary),
                     ensure_ascii=False, indent=2))


def cmd_prune(conn: sqlite3.Connection, args: argparse.Namespace) -> None:
    cur = conn.execute(
        "DELETE FROM scenes WHERE posted_at < datetime('now', ?)",
        (f"-{SCENE_RETENTION_DAYS} days",))
    conn.commit()
    print(json.dumps({"status": "ok", "pruned_scenes": cur.rowcount,
                      "retention_days": SCENE_RETENTION_DAYS}))


def cmd_stats(conn: sqlite3.Connection, args: argparse.Namespace) -> None:
    out = {}
    for table in ("conversation", "facts", "scenes", "persona"):
        out[table] = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    out["facts_by_confidence"] = {
        r["confidence"]: r["n"] for r in conn.execute(
            "SELECT confidence, COUNT(*) AS n FROM facts GROUP BY confidence")}
    out["recent_fail_reasons"] = [dict(r) for r in conn.execute(
        "SELECT fail_reason, COUNT(*) AS n FROM facts "
        "WHERE verdict='FAIL' AND created_at >= datetime('now','-30 days') "
        "GROUP BY fail_reason ORDER BY n DESC LIMIT 5")]
    print(json.dumps(out, ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("init")

    p = sub.add_parser("add-fact")
    p.add_argument("--content", required=True)
    p.add_argument("--source-url", default="")
    p.add_argument("--confidence", default="LOW")
    p.add_argument("--verdict", default="")
    p.add_argument("--fail-reason", default="")
    p.add_argument("--skill-ref", default="")

    p = sub.add_parser("add-scene")
    p.add_argument("--title", required=True)
    p.add_argument("--url", required=True)
    p.add_argument("--summary", default="")

    p = sub.add_parser("add-persona")
    p.add_argument("--rule", required=True)
    p.add_argument("--category", default="tone",
                   choices=["tone", "forbidden", "style"])

    p = sub.add_parser("search")
    p.add_argument("--query", required=True)
    p.add_argument("--layer", default="all", choices=["facts", "scenes", "all"])

    p = sub.add_parser("check-dup")
    p.add_argument("--title", required=True)
    p.add_argument("--summary", default="")

    sub.add_parser("prune")
    sub.add_parser("stats")

    args = parser.parse_args()
    conn = connect(args.db)
    try:
        if args.cmd != "init":
            # ensure schema exists for any command
            ensure_schema(conn)
        {
            "init": cmd_init,
            "add-fact": cmd_add_fact,
            "add-scene": cmd_add_scene,
            "add-persona": cmd_add_persona,
            "search": cmd_search,
            "check-dup": cmd_check_dup,
            "prune": cmd_prune,
            "stats": cmd_stats,
        }[args.cmd](conn, args)
    finally:
        conn.close()


if __name__ == "__main__":
    main()

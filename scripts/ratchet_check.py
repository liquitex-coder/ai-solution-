#!/usr/bin/env python3
"""Ratchet automation, Phase R0 - report-only proposer (requirements §23).

Reads the §19 memory layer, aggregates 30-day Auditor FAILs by
(skill_ref, fail_reason), and when the same combination hits the
threshold, prints a proposed CLAUDE.md §C ratchet line plus the prompt
file to review. Changes nothing (Report-Only).

Exit codes: 0 always in R0; with --strict, 3 when proposals exist
(reserved for the R1 CI promotion).

Usage:
  python3 scripts/ratchet_check.py [--db data/memory.db] [--threshold 3] [--strict]
"""

from __future__ import annotations

import argparse
import pathlib
import sqlite3
import sys

DEFAULT_DB = pathlib.Path(__file__).resolve().parent.parent / "data" / "memory.db"
PROMPT_DIR = pathlib.Path(__file__).resolve().parent.parent / "n8n" / "prompts"

# skill_ref (as sent by the workflow Auditor Gates) -> prompt file to review
SKILL_PROMPTS = {
    "01-github-trending": "01-github-trending.md",
    "02-rss-monitor": "02-rss-monitor.md",
    "03-youtube-summary": "03-youtube-summary.md",
    "04-threads-influencer": "04-threads-influencer.md",
    "05-note-monitor": "05-note-monitor.md",
    "06-weekly-report": "06-weekly-report.md",
    "07-article-writer": "article-base.md",
    "08-kimi-zh": "08-kimi-zh.md",
    "09-multi-source-research": "09-multi-source-research.md",
}


def _warn_report(db: pathlib.Path) -> int:
    """§34-6: 30-day WARN: observation report across all verdicts. Always Report-Only."""
    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    try:
        table = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='warnings'"
        ).fetchone()
        if not table:
            print(f"no warnings table at {db} - run the auditor service once (§34-6)")
            return 0

        groups = conn.execute(
            "SELECT skill_ref, code, COUNT(*) AS n, "
            "COUNT(DISTINCT content_hash) AS articles, MAX(created_at) AS last_seen "
            "FROM warnings WHERE created_at >= datetime('now','-30 days') "
            "GROUP BY skill_ref, code ORDER BY n DESC").fetchall()

        if not groups:
            print("no warnings in the last 30 days")
            return 0

        print("# Warning observation report (§34-6, last 30 days - report only)\n")
        for g in groups:
            details = [r["detail"] for r in conn.execute(
                "SELECT detail FROM warnings WHERE skill_ref=? AND code=? "
                "AND created_at >= datetime('now','-30 days') "
                "ORDER BY id DESC LIMIT 3", (g["skill_ref"], g["code"]))]
            print(f"## {g['skill_ref']} - {g['code']}: {g['n']} warnings / "
                  f"{g['articles']} articles (last: {g['last_seen']})")
            print(f"details: {details}")
            print()
        return 0
    finally:
        conn.close()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--db", type=pathlib.Path, default=DEFAULT_DB)
    ap.add_argument("--threshold", type=int, default=3)
    ap.add_argument("--strict", action="store_true",
                    help="exit 3 when proposals exist (R1 promotion switch)")
    ap.add_argument("--warn", action="store_true",
                    help="print the §34-6 30-day WARN: observation report instead (Report-Only)")
    args = ap.parse_args(argv)

    if not args.db.exists():
        print(f"no memory db at {args.db} - nothing to ratchet (run workflows first)")
        return 0

    if args.warn:
        return _warn_report(args.db)

    conn = sqlite3.connect(str(args.db))
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT skill_ref, fail_reason, COUNT(*) AS n, MAX(created_at) AS last_seen "
        "FROM facts WHERE verdict='FAIL' AND fail_reason != '' "
        "AND created_at >= datetime('now','-30 days') "
        "GROUP BY skill_ref, fail_reason "
        "HAVING n >= ? ORDER BY n DESC",
        (args.threshold,)).fetchall()
    conn.close()

    if not rows:
        print(f"no proposals (no (skill, reason) pair reached {args.threshold} "
              f"FAILs in 30 days)")
        return 0

    print("# Ratchet proposals (Phase R0 - report only, nothing was changed)\n")
    for r in rows:
        prompt = SKILL_PROMPTS.get(r["skill_ref"], "(unknown skill_ref)")
        prompt_path = PROMPT_DIR / prompt
        exists = "exists" if prompt_path.exists() else "MISSING"
        print(f"## {r['skill_ref']} - {r['fail_reason']} × {r['n']} (last: {r['last_seen']})")
        print()
        print("Proposed CLAUDE.md §C line:")
        print(f"> N. `{r['skill_ref']}` で `{r['fail_reason']}` が30日間に{r['n']}回発生 - "
              f"生成時にこの失敗様式を避けること（記憶層より自動起票）。")
        print()
        print(f"Prompt to review: `n8n/prompts/{prompt}` ({exists})")
        print()

    print(f"{len(rows)} proposal(s). Apply manually and record in CLAUDE.md §C "
          f"(R1 will open draft PRs instead).")
    return 3 if args.strict else 0


if __name__ == "__main__":
    sys.exit(main())

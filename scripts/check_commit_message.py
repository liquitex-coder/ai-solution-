#!/usr/bin/env python3
"""Commit-msg sensor for CLAUDE.md §C-1 (requirements: file mentions must be
in the diff they describe). Reject a commit whose body names a tracked file
that is not part of this commit's staged changes.

Usage (as a git commit-msg hook): scripts/check_commit_message.py <msg-file>
Bypass (emergency only): SKIP_COMMIT_MSG_CHECK=1 git commit ...
"""

from __future__ import annotations

import argparse
import os
import pathlib
import re
import subprocess
import sys

TOKEN_RE = re.compile(r"[A-Za-z0-9_./-]+\.(?:py|md|json|js|ps1|sh|yml|yaml|toml|txt)")
TRAILER_PREFIXES = ("Co-Authored-By:", "Claude-Session:")


def _git_lines(*args: str) -> set[str]:
    result = subprocess.run(["git", *args], capture_output=True, text=True, encoding="utf-8")
    return {line for line in result.stdout.splitlines() if line}


def _strip_trailers(message: str) -> str:
    return "\n".join(
        line for line in message.splitlines() if not line.startswith(TRAILER_PREFIXES))


def find_violations(message: str, staged: set[str], tracked: set[str]) -> list[str]:
    staged_basenames = {pathlib.PurePosixPath(p).name for p in staged}
    tracked_basenames = {pathlib.PurePosixPath(p).name for p in tracked}
    body = _strip_trailers(message)

    violations: list[str] = []
    seen: set[str] = set()
    for match in TOKEN_RE.finditer(body):
        token = match.group(0)
        if token in seen:
            continue
        seen.add(token)
        basename = pathlib.PurePosixPath(token).name
        is_tracked = token in tracked or basename in tracked_basenames
        if not is_tracked:
            continue  # not a real tracked file (version string, URL fragment, etc.)
        is_staged = token in staged or basename in staged_basenames
        if not is_staged:
            violations.append(token)
    return violations


def main(argv: list[str] | None = None) -> int:
    if os.environ.get("SKIP_COMMIT_MSG_CHECK") == "1":
        print("SKIP_COMMIT_MSG_CHECK=1 — commit-msg check bypassed", file=sys.stderr)
        return 0

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("msg_file")
    ap.add_argument("--staged-from", help="file listing staged paths, one per line (tests only)")
    ap.add_argument("--tracked-from", help="file listing tracked paths, one per line (tests only)")
    args = ap.parse_args(argv)

    message = pathlib.Path(args.msg_file).read_text(encoding="utf-8")

    if args.staged_from:
        staged = set(pathlib.Path(args.staged_from).read_text(encoding="utf-8").splitlines())
    else:
        staged = _git_lines("diff", "--cached", "--name-only")

    if args.tracked_from:
        tracked = set(pathlib.Path(args.tracked_from).read_text(encoding="utf-8").splitlines())
    else:
        tracked = _git_lines("ls-files")

    violations = find_violations(message, staged, tracked)
    if violations:
        for token in violations:
            print(f"CLAUDE.md §C-1: {token} is not in this commit's diff", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

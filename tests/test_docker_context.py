"""Every Dockerfile COPY source must survive .dockerignore (CLAUDE.md §C-8).

`.dockerignore` starts from `*` and re-includes paths with `!`; a COPY source it
does not re-include fails `docker build` / `fly deploy`, which no local gate runs.
"""

import fnmatch
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def included(path: str, patterns: list[str]) -> bool:
    """Docker semantics for our patterns: last matching rule wins."""
    keep = True
    for raw in patterns:
        negate = raw.startswith("!")
        pattern = raw[1:] if negate else raw
        pattern = pattern.rstrip("/")
        if fnmatch.fnmatch(path, pattern) or fnmatch.fnmatch(path, pattern + "/**") \
                or path.startswith(pattern + "/"):
            keep = negate
    return keep


class DockerContextTests(unittest.TestCase):
    def test_copy_sources_are_in_the_build_context(self):
        patterns = [line.strip() for line in
                    (ROOT / ".dockerignore").read_text(encoding="utf-8").splitlines()
                    if line.strip() and not line.startswith("#")]
        sources = []
        for line in (ROOT / "Dockerfile").read_text(encoding="utf-8").splitlines():
            parts = line.split()
            if parts and parts[0] == "COPY" and not any(p.startswith("--from") for p in parts):
                sources.extend(parts[1:-1])
        self.assertTrue(sources)
        for source in sources:
            source = source.rstrip("/")
            self.assertTrue((ROOT / source).exists(), f"{source} missing from repo")
            probe = source if (ROOT / source).is_file() else source + "/x.py"
            self.assertTrue(included(probe, patterns), f"{source} excluded by .dockerignore")

    def test_matcher_follows_last_rule_wins(self):
        self.assertFalse(included("data/tools.json", ["*", "!scripts/"]))
        self.assertTrue(included("data/tools.json", ["*", "!data/", "!data/tools.json"]))
        self.assertTrue(included("scripts/a.py", ["*", "!scripts/", "!scripts/**"]))


if __name__ == "__main__":
    unittest.main()

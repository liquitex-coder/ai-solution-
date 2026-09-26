"""CLAUDE.md §C-6: every tracked git hook must be committed executable (mode 100755)."""

import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


@unittest.skipUnless(shutil.which("git") and (ROOT / ".git").exists(), "needs a git checkout")
class GitHookModeTests(unittest.TestCase):
    def test_tracked_hooks_are_executable(self):
        out = subprocess.run(["git", "ls-files", "-s", ".githooks"], cwd=ROOT,
                             capture_output=True, text=True, encoding="utf-8",
                             check=True).stdout
        entries = [line.split(None, 3) for line in out.splitlines()]
        self.assertTrue(entries, "no hooks tracked under .githooks")
        for mode, _sha, _stage, path in entries:
            self.assertEqual(mode, "100755", f"{path} is not executable in git")


if __name__ == "__main__":
    unittest.main()

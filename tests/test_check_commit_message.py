"""Tests for the CLAUDE.md §C-1 commit-msg sensor (requirements, T-39)."""

import tempfile
import unittest
from pathlib import Path

from scripts.check_commit_message import main


class CheckCommitMessageTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.dir = Path(self.temp_dir.name)
        self.tracked_file = self.dir / "tracked.txt"
        self.tracked_file.write_text(
            "scripts/foo.py\nscripts/bar.py\ndocs/requirements.md\n", encoding="utf-8")

    def tearDown(self):
        self.temp_dir.cleanup()

    def _run(self, message: str, staged: list[str]) -> int:
        msg_file = self.dir / "msg.txt"
        msg_file.write_text(message, encoding="utf-8")
        staged_file = self.dir / "staged.txt"
        staged_file.write_text("\n".join(staged), encoding="utf-8")
        return main([str(msg_file), "--staged-from", str(staged_file),
                    "--tracked-from", str(self.tracked_file)])

    def test_naming_a_staged_file_passes(self):
        code = self._run("feat: update scripts/foo.py", ["scripts/foo.py"])
        self.assertEqual(code, 0)

    def test_naming_an_unstaged_tracked_file_fails(self):
        code = self._run("feat: also touches scripts/bar.py", ["scripts/foo.py"])
        self.assertEqual(code, 1)

    def test_naming_a_nonexistent_file_passes(self):
        code = self._run("feat: mentions nonexistent/ghost.py", ["scripts/foo.py"])
        self.assertEqual(code, 0)

    def test_trailer_lines_are_ignored(self):
        message = (
            "feat: update scripts/foo.py\n\n"
            "Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>\n"
            "Claude-Session: https://claude.ai/code/session_scripts/bar.py\n"
        )
        code = self._run(message, ["scripts/foo.py"])
        self.assertEqual(code, 0)

    def test_basename_match_across_directories(self):
        code = self._run("docs: sync requirements.md", ["docs/requirements.md"])
        self.assertEqual(code, 0)

    def test_skip_env_var_bypasses_check(self):
        import os
        msg_file = self.dir / "msg.txt"
        msg_file.write_text("feat: also touches scripts/bar.py", encoding="utf-8")
        os.environ["SKIP_COMMIT_MSG_CHECK"] = "1"
        try:
            code = main([str(msg_file)])
        finally:
            del os.environ["SKIP_COMMIT_MSG_CHECK"]
        self.assertEqual(code, 0)


if __name__ == "__main__":
    unittest.main()

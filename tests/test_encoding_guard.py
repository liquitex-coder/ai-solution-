"""Encoding sensor (requirements §33-2): scripts/ text I/O must be explicit UTF-8.

Prevents a Path.read_text()/write_text()/open() call from regressing to the
platform default encoding, which raises UnicodeDecodeError under Windows
cp932 (requirements §33-1, 2026-09-13 incident).
"""

from __future__ import annotations

import ast
import pathlib
import unittest

SCRIPTS_DIR = pathlib.Path(__file__).resolve().parent.parent / "scripts"
TARGET_ATTRS = {"read_text", "write_text"}


def _call_target(call: ast.Call) -> str | None:
    if isinstance(call.func, ast.Attribute) and call.func.attr in TARGET_ATTRS:
        return call.func.attr
    if isinstance(call.func, ast.Name) and call.func.id == "open":
        return "open"
    return None


def _str_contains_b(node: ast.expr) -> bool:
    return isinstance(node, ast.Constant) and isinstance(node.value, str) and "b" in node.value


def _has_binary_mode(call: ast.Call, target: str) -> bool:
    # For open(file, mode, ...) the mode is the second positional argument;
    # read_text/write_text have no mode argument at all, so only a keyword
    # "mode" (open only) can signal binary intent for them.
    positional = call.args[1:] if target == "open" else []
    if any(_str_contains_b(arg) for arg in positional):
        return True
    return any(kw.arg == "mode" and _str_contains_b(kw.value) for kw in call.keywords)


def _has_encoding_kw(call: ast.Call) -> bool:
    return any(kw.arg == "encoding" for kw in call.keywords)


def find_violations() -> list[str]:
    violations: list[str] = []
    for path in sorted(SCRIPTS_DIR.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        rel = path.relative_to(SCRIPTS_DIR.parent)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            target = _call_target(node)
            if target is None:
                continue
            if _has_binary_mode(node, target):
                continue
            if not _has_encoding_kw(node):
                violations.append(f"{rel}:{node.lineno} {target}() missing encoding=")
    return violations


class EncodingGuardTests(unittest.TestCase):
    def test_no_implicit_encoding_in_scripts(self):
        violations = find_violations()
        self.assertEqual(violations, [], msg="\n".join(violations))


if __name__ == "__main__":
    unittest.main()

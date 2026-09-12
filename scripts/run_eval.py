#!/usr/bin/env python3
"""Evaluate content_audit against the labeled eval set (requirements §22-2).

FP = expected PASS but auditor blocks (FAIL/UNVERIFIABLE) — must be 0.
FN = expected FAIL/UNVERIFIABLE but auditor says PASS — must be 0.
Exit 0 only when FP == 0 and FN == 0.
"""

from __future__ import annotations

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from content_audit import audit  # noqa: E402

EVAL_SET = pathlib.Path(__file__).resolve().parent.parent / "data" / "eval_set.json"


def main() -> int:
    cases = json.loads(EVAL_SET.read_text())
    fp, fn, mismatch, exact = [], [], [], 0
    for case in cases:
        result = audit(case["content"], case.get("source_urls", []))
        got, want = result["verdict"], case["expected"]
        blocked = got != "PASS"
        should_block = want != "PASS"
        if got == want:
            exact += 1
        else:
            mismatch.append((case["id"], want, got, result["reasons"][:2]))
        if not should_block and blocked:
            fp.append(case["id"])
        if should_block and not blocked:
            fn.append(case["id"])

    print(f"cases: {len(cases)}  exact-verdict match: {exact}/{len(cases)}")
    print(f"FP (PASS expected, blocked): {len(fp)} {fp}")
    print(f"FN (block expected, passed): {len(fn)} {fn}")
    if mismatch:
        print("verdict mismatches (id, expected, got, reasons):")
        for row in mismatch:
            print("  ", row)
    ok = not fp and not fn
    print("RESULT:", "GREEN (FP=0, FN=0)" if ok else "RED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

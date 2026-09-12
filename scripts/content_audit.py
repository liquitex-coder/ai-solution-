#!/usr/bin/env python3
"""Deterministic LLM-free content audit (requirements §22-1, INV-R2).

Verdict precedence: FAIL > UNVERIFIABLE > PASS.

Usage:
  python3 scripts/content_audit.py --content-file article.html [--source-url URL ...]
  echo '<h2>..</h2>' | python3 scripts/content_audit.py --stdin
As a library: audit(content, source_urls) -> {"verdict": ..., "reasons": [...]}
"""

from __future__ import annotations

import argparse
import json
import re
import sys

HYPE_PHRASES = [
    "革命的", "業界を震撼", "圧倒的No.1", "圧倒的ナンバーワン",
    "絶対に儲かる", "100%保証", "1000%", "誰でも必ず", "確実に稼げる",
    "世界を変える唯一", "他を圧倒する唯一",
]

QUOTE_DOMINANCE_RATIO = 0.40   # §22-1: blockquote chars / total text chars
UNMARKED_QUOTE_CHARS = 60      # 「」 runs longer than this outside blockquote
MIN_H2 = 3

TAG_RE = re.compile(r"<[^>]+>")
BLOCKQUOTE_RE = re.compile(r"<blockquote[^>]*>(.*?)</blockquote>", re.DOTALL | re.IGNORECASE)
H2_RE = re.compile(r"<h2[^>]*>", re.IGNORECASE)
LINK_RE = re.compile(r"<a\s[^>]*href=[\"']https?://[^\"']+[\"']", re.IGNORECASE)
KAGI_QUOTE_RE = re.compile(r"「([^」]*)」")
NUMERIC_CLAIM_RE = re.compile(
    r"\d[\d,.]*\s*(?:%|％|倍|億|兆|万人|万件|万ドル|億円|万円|pt|ポイント)")


def _text(html: str) -> str:
    return TAG_RE.sub("", html)


def audit(content: str, source_urls: list[str] | None = None) -> dict:
    source_urls = [u for u in (source_urls or []) if u]
    reasons: list[str] = []
    unverifiable: list[str] = []

    for phrase in HYPE_PHRASES:
        if phrase in content:
            reasons.append(f"FAIL:HYPE:{phrase}")

    total_chars = len(_text(content).strip())
    quotes = BLOCKQUOTE_RE.findall(content)
    quote_chars = sum(len(_text(q).strip()) for q in quotes)
    has_link = bool(LINK_RE.search(content))

    if total_chars and quote_chars / total_chars > QUOTE_DOMINANCE_RATIO:
        reasons.append(
            f"FAIL:QUOTE_DOMINANCE:{quote_chars}/{total_chars}"
            f"={quote_chars / total_chars:.2f}>{QUOTE_DOMINANCE_RATIO}")

    if quotes and not (has_link or source_urls):
        reasons.append("FAIL:NO_ATTRIBUTION:blockquote without any source link")

    outside = BLOCKQUOTE_RE.sub("", content)
    for m in KAGI_QUOTE_RE.finditer(_text(outside)):
        if len(m.group(1)) > UNMARKED_QUOTE_CHARS:
            reasons.append(
                f"FAIL:UNMARKED_QUOTE:{len(m.group(1))}chars outside blockquote")
            break

    h2_count = len(H2_RE.findall(content))
    if h2_count < MIN_H2:
        reasons.append(f"FAIL:STRUCTURE:h2={h2_count}<{MIN_H2}")

    if NUMERIC_CLAIM_RE.search(_text(content)) and not (has_link or source_urls):
        unverifiable.append("UNVERIFIABLE:UNSOURCED_STATS")

    if reasons:
        verdict = "FAIL"
    elif unverifiable:
        verdict = "UNVERIFIABLE"
        reasons = unverifiable
    else:
        verdict = "PASS"
    return {"verdict": verdict, "reasons": reasons}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--content-file")
    ap.add_argument("--stdin", action="store_true")
    ap.add_argument("--source-url", action="append", default=[])
    args = ap.parse_args()
    if args.stdin:
        content = sys.stdin.read()
    elif args.content_file:
        content = open(args.content_file, encoding="utf-8").read()
    else:
        ap.error("--content-file or --stdin required")
    result = audit(content, args.source_url)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["verdict"] == "PASS" else 2


if __name__ == "__main__":
    sys.exit(main())

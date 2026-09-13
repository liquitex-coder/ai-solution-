#!/usr/bin/env python3
"""Deterministic LLM-free content audit (requirements §22-1, INV-R2).

Verdict precedence: FAIL > UNVERIFIABLE > PASS.

Usage:
  python3 scripts/content_audit.py --content-file article.html [--source-url URL ...]
                                    [--source-text-file source.txt] [--source-lang ja|en|zh]
  echo '<h2>..</h2>' | python3 scripts/content_audit.py --stdin
As a library: audit(content, source_urls=None, source_text=None, source_lang=None)
              -> {"verdict": ..., "reasons": [...]}
              (WARN: entries are appended to reasons after any FAIL/UNVERIFIABLE
              ones and never change verdict — requirements §32-2)
"""

from __future__ import annotations

import argparse
import difflib
import json
import re
import sys

HYPE_PHRASES = [
    "革命的", "業界を震撼", "圧倒的No.1", "圧倒的ナンバーワン",
    "絶対に儲かる", "100%保証", "1000%", "誰でも必ず", "確実に稼げる",
    "世界を変える唯一", "他を圧倒する唯一",
]

QUOTE_DOMINANCE_RATIO = 0.34   # §17-1: generated/quoted > 2.0 => quote <= 1/3 (§32-1 D1)
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


VERBATIM_COPY_THRESHOLD = 0.85  # §17-1 (5): difflib ratio below this => possible alteration


def audit(content: str, source_urls: list[str] | None = None,
          source_text: str | None = None, source_lang: str | None = None) -> dict:
    source_urls = [u for u in (source_urls or []) if u]
    reasons: list[str] = []
    unverifiable: list[str] = []
    warnings: list[str] = []

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

    # D2 (§17-1 (5), §32-1): quotes must be verbatim in the source text.
    # WARN-only until the 30-day observation (§32-2) — never affects verdict.
    if source_text and source_lang in (None, "ja"):
        for q in quotes:
            qtext = _text(q).strip()
            if not qtext:
                continue
            qlen = len(qtext)
            step = max(1, qlen // 4)
            best_ratio = 0.0
            for start in range(0, max(1, len(source_text) - qlen + 1), step):
                window = source_text[start:start + qlen]
                ratio = difflib.SequenceMatcher(None, qtext, window).ratio()
                if ratio > best_ratio:
                    best_ratio = ratio
            if best_ratio < VERBATIM_COPY_THRESHOLD:
                warnings.append(f"WARN:VERBATIM_COPY:{best_ratio:.2f}")

    # D3 (§17-3, §32-1): translated articles must carry a translation label.
    if source_lang in ("en", "zh"):
        text_only = _text(content)
        has_label = ("本記事は" in text_only and "翻訳" in text_only
                     and any(u in content for u in source_urls))
        if not has_label:
            warnings.append("WARN:MISSING_TRANSLATION_LABEL")

    if reasons:
        verdict = "FAIL"
    elif unverifiable:
        verdict = "UNVERIFIABLE"
        reasons = unverifiable
    else:
        verdict = "PASS"
    return {"verdict": verdict, "reasons": reasons + warnings}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--content-file")
    ap.add_argument("--stdin", action="store_true")
    ap.add_argument("--source-url", action="append", default=[])
    ap.add_argument("--source-text-file")
    ap.add_argument("--source-lang", choices=["ja", "en", "zh"])
    args = ap.parse_args()
    if args.stdin:
        content = sys.stdin.read()
    elif args.content_file:
        content = open(args.content_file, encoding="utf-8").read()
    else:
        ap.error("--content-file or --stdin required")
    source_text = (open(args.source_text_file, encoding="utf-8").read()
                   if args.source_text_file else None)
    result = audit(content, args.source_url, source_text, args.source_lang)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["verdict"] == "PASS" else 2


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Deterministic LLM-free content audit (requirements §22-1, INV-R2).

Verdict precedence: FAIL > UNVERIFIABLE > PASS.

Usage:
  python3 scripts/content_audit.py --content-file article.html [--source-url URL ...]
                                    [--source-text-file source.txt] [--source-lang ja|en|zh]
  echo '<h2>..</h2>' | python3 scripts/content_audit.py --stdin
As a library: audit(content, source_urls=None, source_text=None, source_lang=None)
              -> {"verdict": ..., "reasons": [...], "requires_human_signature": bool}
              (WARN: entries are appended to reasons after any FAIL/UNVERIFIABLE
              ones and never change verdict — requirements §32-2)
"""

from __future__ import annotations

import argparse
import difflib
import json
import re
import sys
import unicodedata
from urllib.parse import urlparse

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


# Revenue rules (requirements §35-6). ASP redirect hosts; extend when a new ASP is adopted.
AFFILIATE_HOSTS = (
    "px.a8.net", "af.moshimo.com", "h.accesstrade.net", "ck.jp.ap.valuecommerce.com",
    "t.afi-b.com", "hb.afl.rakuten.co.jp",
)
ANCHOR_RE = re.compile(r"<a\s[^>]*>", re.IGNORECASE)
HREF_RE = re.compile(r"href=[\"']([^\"']+)[\"']", re.IGNORECASE)
REL_RE = re.compile(r"rel=[\"']([^\"']*)[\"']", re.IGNORECASE)
PR_LABEL_RE = re.compile(r"広告|プロモーション|アフィリエイト|(?<![A-Za-z])PR(?![A-Za-z])")
EXPERIENCE_PHRASES = ("使ってみた", "試してみた", "実際に使", "実際に試")
HANDS_ON_MARKER_RE = re.compile(r"data-ainavi-evidence=[\"']hands-on[\"']", re.IGNORECASE)
PRICE_RE = re.compile(r"\d[\d,]*\s*円|[¥￥]\s*\d|\$\s*\d|月額\s*\d")
PRICE_DATE_RE = re.compile(r"\d{4}年\d{1,2}月|\d{4}-\d{2}-\d{2}|時点")


def _text(html: str) -> str:
    return TAG_RE.sub("", html)


def _affiliate_links(content: str) -> list[tuple[bool, bool]]:
    """§35-6: (points at an ASP host, rel carries sponsored) per affiliate anchor."""
    links = []
    for tag in ANCHOR_RE.findall(content):
        href = HREF_RE.search(tag)
        rel = REL_RE.search(tag)
        host = (urlparse(href.group(1)).hostname or "") if href else ""
        is_asp = any(host == h or host.endswith("." + h) for h in AFFILIATE_HOSTS)
        sponsored = bool(rel) and "sponsored" in rel.group(1).lower().split()
        if is_asp or sponsored:
            links.append((is_asp, sponsored))
    return links


SIMILARITY_THRESHOLD = 0.85  # §17-1 (5): difflib ratio threshold shared by D7 and D2

# Evidence Pack (requirements §34-5)
EVIDENCE_MIN_CHARS = 10
EVIDENCE_MAX_CHARS = 300
MAX_CLAIMS = 40
MIN_CLAIMS_FOR_RATIO = 3
UNGROUNDED_RATIO = 0.5
NUMBER_TOLERANCE = 0.05
MAX_PROBE_WARNINGS = 5
CLAIM_TYPES = ("FACT", "NUMBER", "TECHNIQUE", "OPINION")
CLAIM_STATUSES = ("SUPPORTED", "CONTRADICTED", "NOT_IN_SOURCE", "UNCHECKABLE")
FEASIBILITIES = ("PLAUSIBLE", "IMPLAUSIBLE", "UNKNOWN")
CONSIDERED_TYPES = ("FACT", "NUMBER", "TECHNIQUE")


def _normalize(s: str) -> str:
    """NFKC-fold and collapse whitespace so full-width/half-width spans compare equal."""
    return " ".join(unicodedata.normalize("NFKC", s).split())


def _span_found(evidence_norm: str, source_norm: str) -> bool:
    """True if a normalized evidence span is verbatim (or near-verbatim) in the source."""
    if not evidence_norm or not source_norm:
        return False
    if evidence_norm in source_norm:
        return True
    qlen = len(evidence_norm)
    step = max(1, qlen // 4)
    for start in range(0, max(1, len(source_norm) - qlen + 1), step):
        window = source_norm[start:start + qlen]
        if difflib.SequenceMatcher(None, evidence_norm, window).ratio() >= SIMILARITY_THRESHOLD:
            return True
    return False


def _validate_claim(raw: object) -> dict | None:
    """Normalize one Evidence Pack claim, or return None if malformed (dropped)."""
    if not isinstance(raw, dict):
        return None
    cid, text = raw.get("id"), raw.get("text")
    ctype, status = raw.get("type"), raw.get("status")
    if not isinstance(cid, str) or not isinstance(text, str):
        return None
    if ctype not in CLAIM_TYPES or status not in CLAIM_STATUSES:
        return None
    evidence = raw.get("evidence")
    if evidence is not None and not isinstance(evidence, str):
        return None
    source_index = raw.get("source_index")
    if source_index is not None and (
            not isinstance(source_index, int) or isinstance(source_index, bool)):
        return None
    value = raw.get("value")
    if value is not None and (
            not isinstance(value, (int, float)) or isinstance(value, bool)):
        return None
    gt_ref = raw.get("gt_ref")
    if gt_ref is not None and not isinstance(gt_ref, str):
        return None
    feasibility = raw.get("feasibility")
    if feasibility is not None and feasibility not in FEASIBILITIES:
        return None
    note = raw.get("note", "")
    if not isinstance(note, str):
        return None
    claim = {
        "id": cid, "text": text, "type": ctype, "status": status,
        "evidence": evidence, "source_index": source_index,
        "value": value, "gt_ref": gt_ref, "feasibility": feasibility, "note": note,
    }
    if claim["type"] == "OPINION":
        claim["status"] = "UNCHECKABLE"
    if claim["type"] == "TECHNIQUE":
        if claim["feasibility"] is None:
            claim["feasibility"] = "UNKNOWN"
    else:
        claim["feasibility"] = None
    return claim


def _fmt_number(v: float) -> str:
    fv = float(v)
    return "%d" % fv if fv.is_integer() else repr(fv)


def evaluate_evidence(content: str, source_text: str | None, evidence: object) -> tuple[list[str], dict]:
    """Deterministic Evidence Pack rules (requirements §34-5). Returns (warnings, summary).

    Every returned warning starts with "WARN:" — this function never affects verdict
    directly (INV-R2a); callers only ever append its output to the existing warnings list.
    """
    warnings: list[str] = []
    summary = {
        "claims": 0, "considered": 0, "supported": 0, "contradicted": 0,
        "ungrounded": 0, "evidence_missing": 0, "implausible": 0,
        "probes_failed": 0, "dropped": 0,
    }

    if (not isinstance(evidence, dict) or evidence.get("version") != 1
            or not isinstance(evidence.get("claims"), list)):
        return (["WARN:FACTCHECK_UNAVAILABLE:schema"], summary)

    verifier = evidence.get("verifier")
    claims_ok = isinstance(verifier, dict) and verifier.get("ok") is True
    if not claims_ok:
        err = _normalize(str((verifier or {}).get("error") or "verifier"))[:40]
        warnings.append(f"WARN:FACTCHECK_UNAVAILABLE:{err}")

    source_norm = _normalize(source_text) if isinstance(source_text, str) else ""
    gt_raw = evidence.get("ground_truth")
    ground_truth = gt_raw if isinstance(gt_raw, dict) else {}
    text_nosep = _text(content).replace(",", "").replace("，", "").replace(" ", "")

    if claims_ok:
        raw_claims = evidence["claims"][:MAX_CLAIMS]
        summary["claims"] = len(raw_claims)
        claims: list[dict] = []
        dropped = 0
        for raw in raw_claims:
            claim = _validate_claim(raw)
            if claim is None:
                dropped += 1
            else:
                claims.append(claim)
        summary["dropped"] = dropped

        # Step 2: verbatim re-verification of SUPPORTED/CONTRADICTED evidence spans.
        for claim in claims:
            if claim["status"] in ("SUPPORTED", "CONTRADICTED"):
                ev = claim["evidence"]
                ev_norm = _normalize(ev) if isinstance(ev, str) else ""
                if (ev is None or not source_norm
                        or not (EVIDENCE_MIN_CHARS <= len(ev_norm) <= EVIDENCE_MAX_CHARS)
                        or not _span_found(ev_norm, source_norm)):
                    claim["status"] = "EVIDENCE_MISSING"

        # Step 3: NUMBER claims cross-checked against the article text and ground_truth.
        for claim in claims:
            if claim["type"] == "NUMBER" and claim["value"] is not None:
                if _fmt_number(claim["value"]) not in text_nosep:
                    claim["status"] = "EVIDENCE_MISSING"
                elif isinstance(claim["gt_ref"], str) and "." in claim["gt_ref"]:
                    key, field = claim["gt_ref"].rsplit(".", 1)
                    gt_entry = ground_truth.get(key)
                    gt_val = gt_entry.get(field) if isinstance(gt_entry, dict) else None
                    if isinstance(gt_val, (int, float)) and not isinstance(gt_val, bool):
                        if abs(claim["value"] - gt_val) > NUMBER_TOLERANCE * max(abs(gt_val), 1):
                            warnings.append(
                                f"WARN:NUMBER_MISMATCH:{_fmt_number(claim['value'])}/{_fmt_number(gt_val)}")

        # Step 4: ungrounded ratio (OPINION excluded — copyright prompt requires original analysis).
        considered = [c for c in claims if c["type"] in CONSIDERED_TYPES]
        n_considered = len(considered)
        ungrounded = sum(
            1 for c in considered if c["status"] in ("NOT_IN_SOURCE", "EVIDENCE_MISSING"))
        if n_considered >= MIN_CLAIMS_FOR_RATIO and ungrounded / n_considered > UNGROUNDED_RATIO:
            warnings.append(f"WARN:CLAIM_UNGROUNDED:{ungrounded}/{n_considered}")

        # Step 5: verified contradictions.
        n_contradicted = sum(1 for c in claims if c["status"] == "CONTRADICTED")
        if n_contradicted >= 1:
            warnings.append(f"WARN:CLAIM_CONTRADICTED:{n_contradicted}")

        # Step 6: implausible techniques.
        n_implausible = sum(
            1 for c in claims if c["type"] == "TECHNIQUE" and c["feasibility"] == "IMPLAUSIBLE")
        if n_implausible >= 1:
            warnings.append(f"WARN:TECHNIQUE_IMPLAUSIBLE:{n_implausible}")

        # Step 7: claims downgraded to EVIDENCE_MISSING (steps 2/3).
        n_missing = sum(1 for c in claims if c["status"] == "EVIDENCE_MISSING")
        if n_missing >= 1:
            warnings.append(f"WARN:EVIDENCE_NOT_IN_SOURCE:{n_missing}")

        summary["considered"] = n_considered
        summary["supported"] = sum(1 for c in claims if c["status"] == "SUPPORTED")
        summary["contradicted"] = n_contradicted
        summary["ungrounded"] = ungrounded
        summary["evidence_missing"] = n_missing
        summary["implausible"] = n_implausible

    # Step 8 (always): deterministic probes.
    probes_raw = evidence.get("probes")
    probes = probes_raw if isinstance(probes_raw, list) else []
    url_warned = repo_warned = probes_failed = 0
    for probe in probes:
        if not isinstance(probe, dict):
            continue
        kind, result, target = probe.get("kind"), probe.get("result"), probe.get("target")
        if kind == "URL" and result == "DEAD":
            probes_failed += 1
            if url_warned < MAX_PROBE_WARNINGS:
                warnings.append(f"WARN:URL_DEAD:{str(target)[:80]}")
                url_warned += 1
        elif kind == "GITHUB_REPO" and result == "NOT_FOUND":
            probes_failed += 1
            if repo_warned < MAX_PROBE_WARNINGS:
                warnings.append(f"WARN:REPO_NOT_FOUND:{str(target)[:80]}")
                repo_warned += 1
    summary["probes_failed"] = probes_failed

    # Step 9 (always): no source at all (WF07-style).
    if not source_norm and not ground_truth:
        warnings.append("WARN:NO_SOURCE_FOR_FACTCHECK")

    return (warnings, summary)


def audit(content: str, source_urls: list[str] | None = None,
          source_text: str | None = None, source_lang: str | None = None,
          evidence: dict | None = None) -> dict:
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

    # §35-6 A1/A2: affiliate links need a PR label before the first <h2> and rel=sponsored.
    affiliate = _affiliate_links(content)
    if affiliate:
        first_h2 = H2_RE.search(content)
        lead = _text(content[:first_h2.start()] if first_h2 else content)
        if not PR_LABEL_RE.search(lead):
            reasons.append("FAIL:NO_PR_LABEL:affiliate link without a PR label before the first h2")
        if any(is_asp and not sponsored for is_asp, sponsored in affiliate):
            reasons.append("FAIL:AFFILIATE_NOT_SPONSORED:ASP link without rel=sponsored")

    # §35-6 A3 (Report-Only): first-hand experience claims need a hands-on evidence block.
    text_all = _text(content)
    if (any(phrase in text_all for phrase in EXPERIENCE_PHRASES)
            and not HANDS_ON_MARKER_RE.search(content)):
        warnings.append("WARN:UNSUPPORTED_EXPERIENCE")

    # §35-6 A4: prices need a source (A4a) and a retrieval date (A4b, Report-Only).
    if PRICE_RE.search(text_all):
        if not (has_link or source_urls):
            unverifiable.append("UNVERIFIABLE:UNSOURCED_PRICE")
        if not PRICE_DATE_RE.search(text_all):
            warnings.append("WARN:PRICE_UNDATED")

    # D7 (§17-1 ⑤改変禁止, §32-1): blockquote text should be found verbatim in the source.
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
            if best_ratio < SIMILARITY_THRESHOLD:
                warnings.append(f"WARN:QUOTE_ALTERED:{best_ratio:.2f}")

    # D2 (§17-1 ①主従, §32-1): body outside blockquotes copied verbatim from the source.
    # WARN-only until the 30-day observation (§32-2) — never affects verdict.
    if source_text and source_lang in (None, "ja"):
        body = _text(BLOCKQUOTE_RE.sub("", content))
        for start in range(0, max(1, len(body) - 200 + 1), 100):
            window = body[start:start + 200]
            if len(window) < 120:
                continue
            m = difflib.SequenceMatcher(None, window, source_text).find_longest_match(
                0, len(window), 0, len(source_text))
            if m.size >= 120:
                warnings.append("WARN:VERBATIM_COPY:1.00")
                break
            best = max(
                difflib.SequenceMatcher(None, window, source_text[s:s + 200]).ratio()
                for s in range(0, max(1, len(source_text) - 200 + 1), 100))
            if best >= SIMILARITY_THRESHOLD:
                warnings.append(f"WARN:VERBATIM_COPY:{best:.2f}")
                break

    # D3 (§17-3, §32-1): translated articles must carry a translation label.
    if source_lang in ("en", "zh"):
        text_only = _text(content)
        has_label = ("本記事は" in text_only and "翻訳" in text_only
                     and any(u in content for u in source_urls))
        if not has_label:
            warnings.append("WARN:MISSING_TRANSLATION_LABEL")

    # Evidence Pack (requirements §34): LLM-supplied signals feed only WARN: entries
    # (INV-R2a) — never gated by source_lang (§34-11 item 5).
    ev_summary = None
    if evidence is not None:
        ev_warnings, ev_summary = evaluate_evidence(content, source_text, evidence)
        warnings.extend(ev_warnings)

    if reasons:
        verdict = "FAIL"
    elif unverifiable:
        verdict = "UNVERIFIABLE"
        reasons = unverifiable
    else:
        verdict = "PASS"
    # §35-6 A5: revenue content is published only on a human signature (INV-R1);
    # the flag never changes the verdict.
    result = {"verdict": verdict, "reasons": reasons + warnings,
              "requires_human_signature": bool(affiliate)}
    if ev_summary is not None:
        result["evidence_summary"] = ev_summary
    return result


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--content-file")
    ap.add_argument("--stdin", action="store_true")
    ap.add_argument("--source-url", action="append", default=[])
    ap.add_argument("--source-text-file")
    ap.add_argument("--source-lang", choices=["ja", "en", "zh"])
    ap.add_argument("--evidence-file")
    args = ap.parse_args()
    if args.stdin:
        content = sys.stdin.read()
    elif args.content_file:
        content = open(args.content_file, encoding="utf-8").read()
    else:
        ap.error("--content-file or --stdin required")
    source_text = (open(args.source_text_file, encoding="utf-8").read()
                   if args.source_text_file else None)
    evidence = (json.loads(open(args.evidence_file, encoding="utf-8").read())
                if args.evidence_file else None)
    result = audit(content, args.source_url, source_text, args.source_lang, evidence)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["verdict"] == "PASS" else 2


if __name__ == "__main__":
    sys.exit(main())

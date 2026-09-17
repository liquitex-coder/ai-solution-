"""Tests for the Evidence Pack deterministic rules (requirements §34-5)."""

import unittest

from scripts.content_audit import audit, evaluate_evidence

SRC_JA = ("[S0] Acme Labs は 2026年9月1日に Widget 2.0 を公開した。"
          "ストリーミング API が追加され、Python 3.8 のサポートは終了した。"
          "GitHub のスター数は 1,234 である。")

SRC_EN = ("[S0] Acme Labs released Widget 2.0 on 2026-09-01. The release "
          "adds a streaming API and drops support for Python 3.8. The "
          "repository has 1,234 stars on GitHub.")


def _article(extra=""):
    return (
        "<h2>概要</h2><p>Acme Labs が Widget 2.0 を公開した。"
        '<a href="https://example.com/source-article">公式発表</a>を参照。</p>'
        f"<h2>新機能</h2><p>ストリーミング API が追加された。{extra}</p>"
        "<h2>まとめ</h2><p>GitHub のスター数は 1,234 に達した。</p>"
    )


ARTICLE_E = _article("Python 3.8 のサポートは終了した。")
ARTICLE_E_CONTRA = _article("Python 3.8 のサポートは今も続いている。")
ARTICLE_E_HYPE = _article("これは業界を震撼させる革命的な発表だ。")


def _evidence(claims, ok=True, error=None, probes=None, ground_truth=None):
    return {
        "version": 1,
        "verifier": {
            "model": "claude-haiku-4-5", "prompt_ref": "50-fact-check.md",
            "prompt_sha256": "0" * 64, "ok": ok, "error": error,
            "usage": {"input_tokens": 0, "output_tokens": 0},
        },
        "claims": claims,
        "probes": probes or [],
        "ground_truth": ground_truth or {},
    }


def _claim(cid, text, ctype, status, evidence=None, source_index=0,
           value=None, gt_ref=None, feasibility=None, note=""):
    return {
        "id": cid, "text": text, "type": ctype, "status": status,
        "evidence": evidence, "source_index": source_index,
        "value": value, "gt_ref": gt_ref, "feasibility": feasibility, "note": note,
    }


class EvidencePackTests(unittest.TestCase):

    def test_no_evidence_key_unchanged_result(self):
        result = audit(ARTICLE_E, ["https://example.com/source-article"])
        self.assertNotIn("evidence_summary", result)

    def test_supported_with_real_span_no_warnings(self):
        ev = _evidence([
            _claim("c1", "ストリーミングAPI追加", "FACT", "SUPPORTED",
                   evidence="ストリーミング API が追加され"),
            _claim("c2", "スター数1234", "FACT", "SUPPORTED",
                   evidence="スター数は 1,234"),
            _claim("c3", "良い発表だ", "OPINION", "UNCHECKABLE"),
        ])
        result = audit(ARTICLE_E, ["https://example.com/source-article"],
                        source_text=SRC_JA, source_lang="ja", evidence=ev)
        self.assertEqual(result["evidence_summary"]["supported"], 2)
        self.assertFalse(any("EVIDENCE_NOT_IN_SOURCE" in r
                             or "CLAIM_UNGROUNDED" in r for r in result["reasons"]))

    def test_fabricated_span_downgrades_to_evidence_missing(self):
        ev = _evidence([
            _claim("c1", "無料提供", "FACT", "SUPPORTED",
                   evidence="Widget 2.0 は無料で提供される"),
            _claim("c2", "ストリーミングAPI追加", "FACT", "SUPPORTED",
                   evidence="ストリーミング API が追加され"),
            _claim("c3", "スター数1234", "FACT", "SUPPORTED",
                   evidence="スター数は 1,234"),
        ])
        warnings, summary = evaluate_evidence(ARTICLE_E, SRC_JA, ev)
        self.assertIn("WARN:EVIDENCE_NOT_IN_SOURCE:1", warnings)
        self.assertFalse(any("CLAIM_UNGROUNDED" in w for w in warnings))

    def test_verified_contradiction(self):
        ev = _evidence([
            _claim("c1", "Python 3.8 は今もサポート継続", "FACT", "CONTRADICTED",
                   evidence="Python 3.8 のサポートは終了した"),
        ])
        warnings, _ = evaluate_evidence(ARTICLE_E_CONTRA, SRC_JA, ev)
        self.assertIn("WARN:CLAIM_CONTRADICTED:1", warnings)
        self.assertFalse(any("EVIDENCE_NOT_IN_SOURCE" in w for w in warnings))

    def test_unverified_contradiction_downgrades(self):
        ev = _evidence([
            _claim("c1", "Python 3.8 は今もサポート継続", "FACT", "CONTRADICTED",
                   evidence="Python 3.8 は永久にサポートされる"),
        ])
        warnings, _ = evaluate_evidence(ARTICLE_E_CONTRA, SRC_JA, ev)
        self.assertIn("WARN:EVIDENCE_NOT_IN_SOURCE:1", warnings)
        self.assertFalse(any("CLAIM_CONTRADICTED" in w for w in warnings))

    def test_ungrounded_ratio_exceeded(self):
        ev = _evidence([
            _claim("c1", "ok", "FACT", "SUPPORTED", evidence="スター数は 1,234"),
            _claim("c2", "x", "FACT", "NOT_IN_SOURCE"),
            _claim("c3", "y", "FACT", "NOT_IN_SOURCE"),
            _claim("c4", "z", "FACT", "NOT_IN_SOURCE"),
        ])
        warnings, summary = evaluate_evidence(ARTICLE_E, SRC_JA, ev)
        self.assertIn("WARN:CLAIM_UNGROUNDED:3/4", warnings)
        self.assertEqual(summary["considered"], 4)

    def test_all_opinion_no_ratio_warning(self):
        ev = _evidence([
            _claim("c1", "a", "OPINION", "SUPPORTED"),
            _claim("c2", "b", "OPINION", "SUPPORTED"),
            _claim("c3", "c", "OPINION", "SUPPORTED"),
            _claim("c4", "d", "OPINION", "SUPPORTED"),
        ])
        warnings, summary = evaluate_evidence(ARTICLE_E, SRC_JA, ev)
        self.assertFalse(any("CLAIM_UNGROUNDED" in w for w in warnings))
        self.assertEqual(summary["considered"], 0)

    def test_below_min_claims_for_ratio_no_warning(self):
        ev = _evidence([
            _claim("c1", "x", "FACT", "NOT_IN_SOURCE"),
            _claim("c2", "y", "FACT", "NOT_IN_SOURCE"),
        ])
        warnings, _ = evaluate_evidence(ARTICLE_E, SRC_JA, ev)
        self.assertFalse(any("CLAIM_UNGROUNDED" in w for w in warnings))

    def test_number_mismatch(self):
        ev = _evidence(
            [_claim("c1", "star count", "NUMBER", "SUPPORTED",
                    evidence="スター数は 1,234", value=1234, gt_ref="acme/widget.stars")],
            ground_truth={"acme/widget": {"stars": 2000}})
        warnings, _ = evaluate_evidence(ARTICLE_E, SRC_JA, ev)
        self.assertIn("WARN:NUMBER_MISMATCH:1234/2000", warnings)

    def test_number_within_tolerance_no_warning(self):
        ev = _evidence(
            [_claim("c1", "star count", "NUMBER", "SUPPORTED",
                    evidence="スター数は 1,234", value=1234, gt_ref="acme/widget.stars")],
            ground_truth={"acme/widget": {"stars": 1260}})
        warnings, _ = evaluate_evidence(ARTICLE_E, SRC_JA, ev)
        self.assertFalse(any("NUMBER_MISMATCH" in w for w in warnings))

    def test_number_absent_from_article_becomes_evidence_missing(self):
        ev = _evidence(
            [_claim("c1", "star count", "NUMBER", "SUPPORTED",
                    evidence="スター数は 1,234", value=9999, gt_ref="acme/widget.stars")],
            ground_truth={"acme/widget": {"stars": 9999}})
        warnings, _ = evaluate_evidence(ARTICLE_E, SRC_JA, ev)
        self.assertIn("WARN:EVIDENCE_NOT_IN_SOURCE:1", warnings)
        self.assertFalse(any("NUMBER_MISMATCH" in w for w in warnings))

    def test_technique_implausible(self):
        ev = _evidence([
            _claim("c1", "curl trick", "TECHNIQUE", "SUPPORTED",
                   evidence="ストリーミング API が追加され", feasibility="IMPLAUSIBLE"),
        ])
        warnings, _ = evaluate_evidence(ARTICLE_E, SRC_JA, ev)
        self.assertIn("WARN:TECHNIQUE_IMPLAUSIBLE:1", warnings)

    def test_technique_missing_feasibility_coerced_to_unknown_no_warning(self):
        ev = _evidence([
            _claim("c1", "curl trick", "TECHNIQUE", "SUPPORTED",
                   evidence="ストリーミング API が追加され", feasibility=None),
        ])
        warnings, _ = evaluate_evidence(ARTICLE_E, SRC_JA, ev)
        self.assertFalse(any("TECHNIQUE_IMPLAUSIBLE" in w for w in warnings))

    def test_url_dead_probe(self):
        ev = _evidence([], probes=[
            {"kind": "URL", "target": "https://example.com/source-article", "result": "OK"},
            {"kind": "URL", "target": "https://example.com/gone", "result": "DEAD", "detail": "404"},
        ])
        warnings, summary = evaluate_evidence(ARTICLE_E, SRC_JA, ev)
        self.assertTrue(any(w.startswith("WARN:URL_DEAD:") for w in warnings))
        self.assertEqual(summary["probes_failed"], 1)

    def test_url_dead_capped_at_max_probe_warnings(self):
        probes = [{"kind": "URL", "target": f"https://example.com/{i}", "result": "DEAD"}
                  for i in range(7)]
        warnings, summary = evaluate_evidence(ARTICLE_E, SRC_JA, _evidence([], probes=probes))
        self.assertEqual(sum(1 for w in warnings if w.startswith("WARN:URL_DEAD:")), 5)
        self.assertEqual(summary["probes_failed"], 7)

    def test_repo_not_found_probe(self):
        ev = _evidence([], probes=[{"kind": "GITHUB_REPO", "target": "acme/ghost", "result": "NOT_FOUND"}])
        warnings, _ = evaluate_evidence(ARTICLE_E, SRC_JA, ev)
        self.assertTrue(any(w.startswith("WARN:REPO_NOT_FOUND:") for w in warnings))

    def test_url_timeout_produces_no_warning(self):
        ev = _evidence([], probes=[{"kind": "URL", "target": "https://example.com/slow", "result": "TIMEOUT"}])
        warnings, summary = evaluate_evidence(ARTICLE_E, SRC_JA, ev)
        self.assertEqual(warnings, [])
        self.assertEqual(summary["probes_failed"], 0)

    def test_verifier_not_ok_reports_unavailable_and_skips_claims(self):
        ev = _evidence(
            [_claim("c1", "x", "FACT", "SUPPORTED", evidence="スター数は 1,234")],
            ok=False, error="HTTP 529 overloaded",
            probes=[{"kind": "URL", "target": "https://example.com/gone", "result": "DEAD"}])
        warnings, summary = evaluate_evidence(ARTICLE_E, SRC_JA, ev)
        self.assertEqual(warnings[0], "WARN:FACTCHECK_UNAVAILABLE:HTTP 529 overloaded")
        self.assertTrue(any(w.startswith("WARN:URL_DEAD:") for w in warnings))
        self.assertEqual(summary["claims"], 0)

    def test_invalid_schema_returns_only_schema_warning(self):
        for bad in ({"version": 2, "claims": "oops"}, "x", None, {"version": 1}):
            with self.subTest(bad=bad):
                warnings, summary = evaluate_evidence(ARTICLE_E, SRC_JA, bad)
                self.assertEqual(warnings, ["WARN:FACTCHECK_UNAVAILABLE:schema"])
                self.assertEqual(summary["claims"], 0)

    def test_no_source_for_factcheck(self):
        warnings, _ = evaluate_evidence(ARTICLE_E, None,
                                         _evidence([_claim("c1", "x", "FACT", "NOT_IN_SOURCE")]))
        self.assertIn("WARN:NO_SOURCE_FOR_FACTCHECK", warnings)

        warnings2, _ = evaluate_evidence(
            ARTICLE_E, None,
            _evidence([_claim("c1", "x", "FACT", "NOT_IN_SOURCE")],
                      ground_truth={"acme/widget": {"stars": 100}}))
        self.assertFalse(any("NO_SOURCE_FOR_FACTCHECK" in w for w in warnings2))

    def test_fullwidth_normalization_matches(self):
        ev = _evidence([_claim("c1", "api", "FACT", "SUPPORTED",
                                evidence="ストリーミング　ＡＰＩ が追加され")])
        warnings, _ = evaluate_evidence(ARTICLE_E, SRC_JA, ev)
        self.assertFalse(any("EVIDENCE_NOT_IN_SOURCE" in w for w in warnings))

    def test_english_source_language_evidence_verified(self):
        ev = _evidence([_claim("c1", "streaming api", "FACT", "SUPPORTED",
                                evidence="adds  a streaming   API")])
        result = audit(ARTICLE_E, ["https://example.com/source-article"],
                        source_text=SRC_EN, source_lang="en", evidence=ev)
        self.assertFalse(any("EVIDENCE_NOT_IN_SOURCE" in r for r in result["reasons"]))

    def test_windowed_fallback_tolerates_one_char_diff(self):
        real_span = SRC_JA[5:65]
        mutated = real_span[:30] + ("X" if real_span[30] != "X" else "Y") + real_span[31:]
        ev = _evidence([_claim("c1", "x", "FACT", "SUPPORTED", evidence=mutated)])
        warnings, _ = evaluate_evidence(ARTICLE_E, SRC_JA, ev)
        self.assertFalse(any("EVIDENCE_NOT_IN_SOURCE" in w for w in warnings))

    def test_evidence_length_bounds(self):
        too_short = "abcdefghi"  # 9 chars
        too_long = SRC_JA[:5] + "a" * 296  # 301 chars, not a real span
        for ev_text in (too_short, too_long):
            with self.subTest(ev_text=len(ev_text)):
                ev = _evidence([_claim("c1", "x", "FACT", "SUPPORTED", evidence=ev_text)])
                warnings, _ = evaluate_evidence(ARTICLE_E, SRC_JA, ev)
                self.assertIn("WARN:EVIDENCE_NOT_IN_SOURCE:1", warnings)

    def test_max_claims_truncated_to_40(self):
        claims = [_claim(f"c{i}", "x", "OPINION", "UNCHECKABLE") for i in range(41)]
        _, summary = evaluate_evidence(ARTICLE_E, SRC_JA, _evidence(claims))
        self.assertEqual(summary["claims"], 40)

    def test_malformed_claim_is_dropped(self):
        claims = [
            _claim("c1", "ok", "OPINION", "UNCHECKABLE"),
            {"id": "c2", "text": "missing type field", "status": "UNCHECKABLE"},
        ]
        _, summary = evaluate_evidence(ARTICLE_E, SRC_JA, _evidence(claims))
        self.assertEqual(summary["dropped"], 1)

    def test_monotonicity_hype_verdict_unchanged_by_evidence(self):
        ev = _evidence([
            _claim("c1", "ok", "FACT", "SUPPORTED", evidence="ストリーミング API が追加され"),
            _claim("c2", "ok2", "FACT", "SUPPORTED", evidence="スター数は 1,234"),
        ])
        without = audit(ARTICLE_E_HYPE, ["https://example.com/source-article"])
        with_ev = audit(ARTICLE_E_HYPE, ["https://example.com/source-article"],
                         source_text=SRC_JA, source_lang="ja", evidence=ev)
        self.assertEqual(without["verdict"], "FAIL")
        self.assertEqual(with_ev["verdict"], "FAIL")

    def test_monotonicity_unverifiable_verdict_unchanged_by_evidence(self):
        content = "<h2>a</h2><h2>b</h2><h2>c</h2><p>売上は50%増加した。</p>"
        ev = _evidence([_claim("c1", "ok", "FACT", "SUPPORTED", evidence="スター数は 1,234")])
        without = audit(content)
        with_ev = audit(content, source_text=SRC_JA, source_lang="ja", evidence=ev)
        self.assertEqual(without["verdict"], "UNVERIFIABLE")
        self.assertEqual(with_ev["verdict"], "UNVERIFIABLE")

    def test_all_returned_warnings_are_warn_prefixed(self):
        ev = _evidence(
            [_claim("c1", "x", "FACT", "CONTRADICTED", evidence="Python 3.8 のサポートは終了した")],
            probes=[{"kind": "URL", "target": "https://example.com/gone", "result": "DEAD"}])
        warnings, _ = evaluate_evidence(ARTICLE_E, SRC_JA, ev)
        self.assertTrue(warnings)
        self.assertTrue(all(w.startswith("WARN:") for w in warnings))

    def test_warning_order_is_deterministic(self):
        # NO_SOURCE_FOR_FACTCHECK is mutually exclusive with NUMBER_MISMATCH (the
        # latter requires a non-empty ground_truth, which alone satisfies the
        # "not ground_truth" half of the former's condition) — omitted here.
        ev = _evidence([
            _claim("c1", "stars", "NUMBER", "SUPPORTED", evidence="スター数は 1,234",
                   value=1234, gt_ref="acme/widget.stars"),
            _claim("c2", "a", "FACT", "NOT_IN_SOURCE"),
            _claim("c3", "b", "FACT", "NOT_IN_SOURCE"),
            _claim("c4", "c", "FACT", "NOT_IN_SOURCE"),
            _claim("c5", "contra", "FACT", "CONTRADICTED",
                   evidence="Python 3.8 のサポートは終了した"),
            _claim("c6", "tech", "TECHNIQUE", "SUPPORTED",
                   evidence="ストリーミング API が追加され", feasibility="IMPLAUSIBLE"),
            _claim("c7", "fabricated", "FACT", "SUPPORTED", evidence="存在しない一節です"),
        ], ground_truth={"acme/widget": {"stars": 2000}},
           probes=[{"kind": "URL", "target": "https://example.com/gone", "result": "DEAD"}])
        expected_prefixes = [
            "WARN:NUMBER_MISMATCH", "WARN:CLAIM_UNGROUNDED", "WARN:CLAIM_CONTRADICTED",
            "WARN:TECHNIQUE_IMPLAUSIBLE", "WARN:EVIDENCE_NOT_IN_SOURCE", "WARN:URL_DEAD",
        ]
        warnings1, _ = evaluate_evidence(ARTICLE_E, SRC_JA, ev)
        warnings2, _ = evaluate_evidence(ARTICLE_E, SRC_JA, ev)
        self.assertEqual(warnings1, warnings2)
        self.assertEqual([w.split(":")[0] + ":" + w.split(":")[1] for w in warnings1],
                         expected_prefixes)


if __name__ == "__main__":
    unittest.main()

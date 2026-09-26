"""Tests for the revenue audit rules A1-A5 (requirements §35-6)."""

import json
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.request import Request, urlopen

from scripts.auditor_server import make_server
from scripts.content_audit import audit

BODY = ("AIツールの活用は業務の効率化に役立つ場面が増えています。"
        "導入の際は自社の課題を整理し、小さく試してから広げるのが安全です。")
SOURCE = '<a href="https://example.com/source-article">出典</a>'
ASP = "https://px.a8.net/svt/ejp?a8mat=TEST"


def article(lead="", extra="", cta=""):
    return (f"{lead}<h2>概要</h2><p>{BODY}{extra}</p>"
            f"<h2>ポイント</h2><p>{BODY}詳細は{SOURCE}を参照。</p>"
            f"<h2>まとめ</h2><p>{BODY}{cta}</p>")


def codes(result):
    return [":".join(r.split(":")[:2]) for r in result["reasons"]]


class AffiliateDisclosureTests(unittest.TestCase):
    LEAD = "<p>本記事はアフィリエイト広告を含みます。</p>"

    def test_labelled_sponsored_asp_link_passes(self):
        cta = f'<a href="{ASP}" rel="sponsored nofollow">公式</a>'
        self.assertEqual(audit(article(self.LEAD, cta=cta))["verdict"], "PASS")

    def test_missing_pr_label_fails_a1(self):
        cta = f'<a href="{ASP}" rel="sponsored">公式</a>'
        result = audit(article(cta=cta))
        self.assertEqual(result["verdict"], "FAIL")
        self.assertIn("FAIL:NO_PR_LABEL", codes(result))

    def test_asp_link_without_sponsored_fails_a2(self):
        cta = f'<a href="{ASP}" rel="nofollow">公式</a>'
        result = audit(article(self.LEAD, cta=cta))
        self.assertEqual(codes(result), ["FAIL:AFFILIATE_NOT_SPONSORED"])

    def test_asp_subdomain_counts_as_affiliate(self):
        cta = '<a href="https://www.px.a8.net/x">公式</a>'
        self.assertIn("FAIL:NO_PR_LABEL", codes(audit(article(cta=cta))))

    def test_pr_inside_latin_word_is_not_a_label(self):
        cta = f'<a href="{ASP}" rel="sponsored">公式</a>'
        result = audit(article("<p>PROプランとAPRILの話題です。</p>", cta=cta))
        self.assertIn("FAIL:NO_PR_LABEL", codes(result))

    def test_standalone_pr_is_a_label(self):
        cta = f'<a href="{ASP}" rel="sponsored">公式</a>'
        self.assertEqual(audit(article("<p>【PR】</p>", cta=cta))["verdict"], "PASS")

    def test_plain_links_do_not_trigger_revenue_rules(self):
        self.assertEqual(audit(article())["reasons"], [])


class ExperienceClaimTests(unittest.TestCase):
    CLAIM = "実際に試したところ数分で設定できました。"

    def test_claim_without_evidence_warns_only(self):
        result = audit(article(extra=self.CLAIM))
        self.assertEqual(result["verdict"], "PASS")
        self.assertEqual(result["reasons"], ["WARN:UNSUPPORTED_EXPERIENCE"])

    def test_claim_with_hands_on_block_is_clean(self):
        extra = self.CLAIM + '<pre data-ainavi-evidence="hands-on">$ tool --version</pre>'
        self.assertEqual(audit(article(extra=extra))["reasons"], [])


class PriceTests(unittest.TestCase):
    NO_LINK = ("<h2>料金</h2><p>{0}</p><h2>機能</h2><p>本文です。</p>"
               "<h2>まとめ</h2><p>本文です。</p>")

    def test_unsourced_price_is_unverifiable(self):
        result = audit(self.NO_LINK.format("月額3,000円（2026年9月時点）"))
        self.assertEqual(result["verdict"], "UNVERIFIABLE")
        self.assertEqual(codes(result), ["UNVERIFIABLE:UNSOURCED_PRICE"])

    def test_source_urls_satisfy_a4a(self):
        result = audit(self.NO_LINK.format("$20/月（2026-09-01 取得）"),
                       source_urls=["https://example.com/pricing"])
        self.assertEqual(result["reasons"], [])

    def test_undated_price_warns_only(self):
        result = audit(article(extra="有料版は¥980です。"))
        self.assertEqual(result["verdict"], "PASS")
        self.assertEqual(result["reasons"], ["WARN:PRICE_UNDATED"])


class HumanSignatureFlagTests(unittest.TestCase):
    """§35-6 A5: affiliate content carries requires_human_signature; verdict is unchanged."""

    LEAD = "<p>【PR】</p>"
    CTA = f'<a href="{ASP}" rel="sponsored">公式</a>'

    def test_affiliate_article_requires_signature_but_still_passes(self):
        result = audit(article(self.LEAD, cta=self.CTA))
        self.assertEqual(result["verdict"], "PASS")
        self.assertTrue(result["requires_human_signature"])

    def test_plain_article_does_not_require_signature(self):
        self.assertFalse(audit(article())["requires_human_signature"])

    def test_audit_endpoint_returns_the_flag(self):
        with tempfile.TemporaryDirectory() as tmp:
            server = make_server("127.0.0.1", 0, Path(tmp) / "memory.db")
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                url = f"http://127.0.0.1:{server.server_address[1]}/audit"
                flags = []
                for content in (article(self.LEAD, cta=self.CTA), article()):
                    body = json.dumps({"content": content, "skill_ref": "01-github-trending"})
                    request = Request(url, data=body.encode("utf-8"), method="POST",
                                      headers={"Content-Type": "application/json"})
                    with urlopen(request) as response:
                        flags.append(json.loads(response.read())["requires_human_signature"])
            finally:
                server.shutdown()
                server.server_close()
                thread.join()
        self.assertEqual(flags, [True, False])


if __name__ == "__main__":
    unittest.main()

"""Tests for the trust pages generator and publisher (requirements §35-12, T-47)."""

import copy
import unittest

from scripts import trust_pages
from scripts.content_audit import audit

READY = {"slug": "editorial-policy", "title": "編集方針", "status": "ready"}
PENDING = {"slug": "operator", "title": "運営者情報", "status": "pending",
           "pending_reason": "test"}
ALL_SLUGS = ["operator", "editorial-policy", "ad-policy", "claim-platform",
             "privacy", "contact"]


def full_set(**overrides):
    pages = []
    for slug in ALL_SLUGS:
        if slug in trust_pages.RENDER_READY or slug == "editorial-policy":
            pages.append({"slug": slug, "title": slug, "status": "ready"})
        else:
            pages.append({"slug": slug, "title": slug, "status": "pending",
                          "pending_reason": "test"})
    for slug, page in overrides.items():
        pages = [page if p["slug"] == slug else p for p in pages]
    return {"pages": pages}


class RepositoryDataTests(unittest.TestCase):
    def test_repository_trust_pages_json_is_valid(self):
        errors, pages = trust_pages.check()
        self.assertEqual(errors, [])
        self.assertEqual({p["slug"] for p in pages}, set(ALL_SLUGS))

    def test_ready_pages_have_a_renderer(self):
        data = trust_pages.load_json(trust_pages.TRUST_PAGES_FILE)
        for page in data["pages"]:
            if page["status"] == "ready":
                self.assertIn(page["slug"], trust_pages.RENDER_READY, page["slug"])

    def test_pending_pages_state_a_reason_not_shown_verbatim_on_page(self):
        data = trust_pages.load_json(trust_pages.TRUST_PAGES_FILE)
        for page in data["pages"]:
            if page["status"] == "pending":
                self.assertTrue(page["pending_reason"])
                rendered = trust_pages.render_page(page)
                self.assertNotIn(page["pending_reason"], rendered)


class ValidationTests(unittest.TestCase):
    def test_missing_required_page_fails(self):
        data = full_set()
        data["pages"] = [p for p in data["pages"] if p["slug"] != "contact"]
        errors = trust_pages.validate(data)
        self.assertIn("missing required pages: ['contact']", errors)

    def test_unexpected_page_fails(self):
        data = full_set()
        data["pages"].append({"slug": "extra", "title": "x", "status": "ready"})
        errors = trust_pages.validate(data)
        self.assertIn("unexpected pages: ['extra']", errors)

    def test_duplicate_slug_fails(self):
        data = full_set()
        data["pages"].append(copy.deepcopy(data["pages"][0]))
        self.assertIn("duplicate slug in pages", trust_pages.validate(data))

    def test_bad_status_fails(self):
        data = full_set(operator={"slug": "operator", "title": "x", "status": "draft"})
        errors = trust_pages.validate(data)
        self.assertTrue(any("status must be one of" in e for e in errors))

    def test_pending_without_reason_fails(self):
        data = full_set(operator={"slug": "operator", "title": "x", "status": "pending"})
        errors = trust_pages.validate(data)
        self.assertIn("operator: pending pages need pending_reason", errors)


class RenderTests(unittest.TestCase):
    def test_editorial_policy_passes_audit(self):
        result = audit(trust_pages.render_editorial_policy())
        self.assertEqual(result["verdict"], "PASS")

    def test_ad_policy_passes_audit(self):
        result = audit(trust_pages.render_ad_policy())
        self.assertEqual(result["verdict"], "PASS")

    def test_claim_platform_passes_audit(self):
        result = audit(trust_pages.render_claim_platform())
        self.assertEqual(result["verdict"], "PASS")

    def test_pending_placeholder_passes_audit(self):
        result = audit(trust_pages.render_pending("運営者情報"))
        self.assertEqual(result["verdict"], "PASS")

    def test_pending_placeholder_has_no_fabricated_specifics(self):
        html = trust_pages.render_pending("運営者情報")
        for forbidden in ("株式会社", "@", "TEL", "住所"):
            self.assertNotIn(forbidden, html)

    def test_render_page_dispatches_by_status(self):
        self.assertIn("準備中", trust_pages.render_page(PENDING))
        self.assertIn("Auditor Gate", trust_pages.render_page(READY))

    def test_unregistered_ready_slug_raises(self):
        with self.assertRaises(ValueError):
            trust_pages.render_page({"slug": "nope", "title": "x", "status": "ready"})


class AuditPagesTests(unittest.TestCase):
    def test_ready_failure_is_reported(self):
        pages = [{"slug": "a", "status": "ready", "content": "<p>革命的な話です。</p>"}]
        errors = trust_pages.audit_pages(pages)
        self.assertEqual(len(errors), 1)
        self.assertTrue(errors[0].startswith("a: FAIL"))

    def test_pending_failure_is_not_reported(self):
        pages = [{"slug": "a", "status": "pending", "content": "<p>革命的な話です。</p>"}]
        errors = trust_pages.audit_pages(pages)
        self.assertEqual(errors, [])
        self.assertEqual(pages[0]["audit_verdict"], "FAIL")


class PublishScopeTests(unittest.TestCase):
    """§35-12: pending pages are never sent as a draft, whatever wp-init does elsewhere."""

    def test_main_publish_only_sends_ready_pages(self):
        sent = []

        def fake_publish(pages, send):
            sent.extend(p["slug"] for p in pages)
            return []

        import unittest.mock as mock
        with mock.patch.object(trust_pages, "publish_pages", fake_publish), \
             mock.patch.object(trust_pages, "http_transport", lambda *a: None), \
             mock.patch.object(trust_pages, "wp_target", lambda env: ("", "")):
            trust_pages.main(["publish"])
        self.assertEqual(set(sent), {"editorial-policy", "ad-policy", "claim-platform"})
        self.assertNotIn("operator", sent)
        self.assertNotIn("privacy", sent)
        self.assertNotIn("contact", sent)


if __name__ == "__main__":
    unittest.main()

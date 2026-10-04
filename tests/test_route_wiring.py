"""Tests for check_wired W14: auditor POST routes vs. workflow callers (requirements §35-10)."""

import unittest

from scripts.check_wired import route_wiring_errors

GATE = "const res = await fetch(`${auditorUrl}/audit`, {"


class RouteWiringTests(unittest.TestCase):
    def test_called_route_passes(self):
        errors, notes = route_wiring_errors({"/audit"}, {"01.json": GATE}, {})
        self.assertEqual(errors, [])
        self.assertEqual(notes, ["/audit: called by 1 workflow(s)"])

    def test_unwired_unregistered_route_fails(self):
        errors, _ = route_wiring_errors({"/publish-slot"}, {"01.json": GATE}, {})
        self.assertEqual(len(errors), 1)
        self.assertIn("no workflow calls it", errors[0])

    def test_registered_route_passes_until_wired(self):
        registry = {"/publish-slot": "T-45"}
        errors, _ = route_wiring_errors({"/publish-slot"}, {"01.json": GATE}, registry)
        self.assertEqual(errors, [])
        wired = GATE + " fetch(`${auditorUrl}/publish-slot`)"
        errors, _ = route_wiring_errors({"/publish-slot"}, {"01.json": wired}, registry)
        self.assertIn("remove it from LIBRARY_ONLY_ROUTES", errors[0])

    def test_prefix_of_longer_path_is_not_a_caller(self):
        errors, _ = route_wiring_errors({"/audit"}, {"01.json": "`${u}/auditor-log`"}, {})
        self.assertIn("no workflow calls it", errors[0])

    def test_stale_registry_entry_fails(self):
        errors, _ = route_wiring_errors({"/audit"}, {"01.json": GATE}, {"/gone": "x"})
        self.assertEqual(errors, ["/gone: LIBRARY_ONLY_ROUTES entry for a route that does not exist"])


if __name__ == "__main__":
    unittest.main()

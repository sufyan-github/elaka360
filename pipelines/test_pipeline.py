"""Unit tests for the seed pipeline's trust policy and reconciliation helpers.
Run: python3 -m unittest pipelines/test_pipeline.py
"""
import os, sys, unittest
sys.path.insert(0, os.path.dirname(__file__))
from trust import check_row, eligible, nfc
from reconcile import latin_key, upazila_key, bn_key


class TrustPolicy(unittest.TestCase):
    def test_only_official_or_secondary_with_a_source_is_eligible(self):
        self.assertTrue(eligible("secondary", "WIKI_RAJ"))
        self.assertTrue(eligible("official", "LGD"))
        self.assertFalse(eligible("secondary", None))
        self.assertFalse(eligible("community", "NUHIL"))
        self.assertFalse(eligible("unverified", "UNVERIFIED"))
        self.assertFalse(eligible("secondary", "WIKI_RAJ", requested=False))

    def test_check_row_flags_violations(self):
        self.assertEqual(check_row(dict(evidence_level="secondary", production_eligible=True, evidence_source="X", verified=False)), [])
        self.assertTrue(check_row(dict(evidence_level="community", production_eligible=True, evidence_source="NUHIL", verified=False)))
        self.assertTrue(check_row(dict(evidence_level="secondary", production_eligible=False, evidence_source="X", verified=True)))
        self.assertTrue(check_row(dict(evidence_level="bogus", production_eligible=False, evidence_source=None, verified=False)))

    def test_nfc_makes_bangla_forms_equal(self):
        decomposed = "ড়"   # ড + nukta
        self.assertEqual(nfc(decomposed), nfc("ড়"))


class Reconcile(unittest.TestCase):
    def test_latin_key_matches_typescript_twin(self):
        self.assertEqual(latin_key("Rajshahi"), latin_key("rajsahi"))
        self.assertEqual(latin_key("Cox's Bazar"), latin_key("Coxs Bazar"))

    def test_upazila_aliases(self):
        self.assertEqual(upazila_key("Bogra Sadar"), upazila_key("Bogura Sadar"))
        self.assertEqual(upazila_key("Raigonj"), upazila_key("Raiganj"))

    def test_bn_key_ignores_spacing_and_punctuation(self):
        self.assertEqual(bn_key("নাটাই (উত্তর)"), bn_key("নাটাই উত্তর"))


if __name__ == "__main__":
    unittest.main()

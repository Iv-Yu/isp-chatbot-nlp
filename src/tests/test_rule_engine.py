import unittest

from chatbot.rule_engine import RuleEngine


class TestRuleEngineDetectWithStatus(unittest.TestCase):
    def setUp(self):
        # Use a conservative min_score to avoid accidental matches during test
        self.engine = RuleEngine(min_score=1)

    def test_greeting_status_auto(self):
        intent, response, status = self.engine.detect_with_status("halo kak")
        self.assertEqual(status, "AUTO_RESPONSE")
        self.assertIn(intent, ["greeting", "fallback"])  # greeting expected

    def test_kabel_putus_to_noc(self):
        intent, response, status = self.engine.detect_with_status("kabel putus di depan rumah")
        self.assertEqual(status, "TO_NOC")
        self.assertEqual(intent, "kabel_putus")

    def test_fallback_to_cs(self):
        intent, response, status = self.engine.detect_with_status("pertanyaan yang tidak jelas blablabla")
        self.assertEqual(status, "TO_CS")
        self.assertEqual(intent, "fallback")


if __name__ == "__main__":
    unittest.main()

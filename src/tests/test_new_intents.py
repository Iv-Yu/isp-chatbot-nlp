import unittest

from chatbot.rule_engine import RuleEngine


class TestNewIntents(unittest.TestCase):
    def setUp(self):
        # Keep min_score conservative to avoid accidental weak matches
        self.engine = RuleEngine(min_score=1)

    def test_pembayaran_intent(self):
        intent, response, status = self.engine.detect_with_status("kak pembayarannya gimana ya")
        self.assertEqual(intent, "pembayaran")
        self.assertEqual(status, "AUTO_RESPONSE")

    def test_gangguan_lemot_intent(self):
        intent, response, status = self.engine.detect_with_status("kak lemot")
        self.assertEqual(intent, "gangguan_lemot_umum")
        self.assertEqual(status, "TO_NOC")

    def test_cek_coverage_intent(self):
        intent, response, status = self.engine.detect_with_status("daerah Rejomulyo bisa dipasang kak?")
        self.assertEqual(intent, "cek_coverage")
        self.assertEqual(status, "TO_CS")

    def test_ganti_password_intent(self):
        intent, response, status = self.engine.detect_with_status("ganti password wifi gimana caranya")
        self.assertEqual(intent, "ganti_password_wifi")
        self.assertEqual(status, "TO_CS")

    def test_berhenti_langganan_intent(self):
        intent, response, status = self.engine.detect_with_status("saya mau berhenti langganan")
        self.assertEqual(intent, "berhenti_langganan")
        self.assertEqual(status, "TO_CS")


if __name__ == "__main__":
    unittest.main()

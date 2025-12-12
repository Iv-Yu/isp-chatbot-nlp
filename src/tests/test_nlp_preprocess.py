import unittest

from chatbot.nlp_preprocess import preprocess


class TestNLPPreprocess(unittest.TestCase):
    def test_preprocess_basic(self):
        text = "Saya mau komplain mengenai tagihan saya"
        tokens = preprocess(text)
        # Expected tokens (based on pipeline: tokenize -> remove stopwords -> stem)
        self.assertIsInstance(tokens, list)
        self.assertEqual(tokens, ["mau", "komplain", "kena", "tagih"])


if __name__ == "__main__":
    unittest.main()

import numpy as np
import joblib
import os
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline
from .rules import INTENT_RULES
from .nlp_preprocess import preprocess

class MLEngine:
    def __init__(self, model_path: str = "models/intent_classifier.joblib"):
        # Jika ada model hasil training yang lebih advanced, gunakan itu.
        # Jika tidak, baru fallback ke training sederhana dari rules.
        if os.path.exists(model_path):
            try:
                self.model = joblib.load(model_path)
                return
            except Exception:
                pass
        
        self.model = Pipeline([
            ('tfidf', TfidfVectorizer(tokenizer=lambda x: preprocess(x), token_pattern=None, ngram_range=(1, 2))),  # type: ignore
            ('clf', MultinomialNB(alpha=0.1))
        ])
        self._train_from_rules()

    def _train_from_rules(self):
        """Melatih model secara dinamis dari patterns di rules.py"""
        X = []
        y = []
        
        for rule in INTENT_RULES:
            for mapping in rule.get("mappings", []):
                X.append(mapping["pattern"])
                y.append(rule["name"])
        
        if X:
            self.model.fit(X, y)

    def predict(self, user_input: str, threshold_design: float = 0.4):
        """
        Prediksi intent menggunakan Multinomial Naive Bayes.
        Menggunakan predict_proba untuk mendapatkan nilai probabilitas (confidence) asli.
        """
        if not user_input.strip():
            return None, 0.0

        # Mendapatkan probabilitas untuk setiap kelas
        probs = self.model.predict_proba([user_input])[0]
        max_prob = np.max(probs)
        predicted_intent = self.model.predict([user_input])[0]

        if max_prob >= threshold_design:
            return predicted_intent, max_prob
        
        return "fallback", max_prob
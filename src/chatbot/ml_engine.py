import numpy as np
import joblib
import os
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import LinearSVC
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
            ('tfidf', TfidfVectorizer(tokenizer=lambda x: preprocess(x), token_pattern=None, ngram_range=(1, 2))),
            ('clf', LinearSVC(C=1.0, dual=True))
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
        Prediksi intent. LinearSVC tidak punya predict_proba secara default, 
        tapi kita bisa menggunakan decision_function untuk estimasi confidence.
        """
        if not user_input.strip():
            return None, 0.0

        # Mendapatkan skor keputusan
        decision_scores = self.model.decision_function([user_input])
        
        # Penanganan khusus jika output berupa array 1D (binary classification)
        if len(decision_scores.shape) == 1:
            probs = 1 / (1 + np.exp(-decision_scores))  # Sigmoid
            max_prob = probs[0] if probs[0] > 0.5 else 1 - probs[0]
        else:
            # Normalisasi skor sederhana ke rentang 0-1 (Softmax approximation)
            exp_scores = np.exp(decision_scores - np.max(decision_scores))
            probs = exp_scores / exp_scores.sum()
            max_prob = np.max(probs)
        
        predicted_intent = self.model.predict([user_input])[0]

        if max_prob >= threshold_design:
            return predicted_intent, max_prob
        
        return "fallback", max_prob
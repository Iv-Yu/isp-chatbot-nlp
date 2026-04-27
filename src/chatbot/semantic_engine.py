import torch
from sentence_transformers import SentenceTransformer, util
from .rules import INTENT_RULES
from typing import Optional, Tuple

class SemanticEngine:
    def __init__(self, model_name='paraphrase-multilingual-MiniLM-L12-v2'):
        # Model ini mendukung 50+ bahasa termasuk Indonesia
        self.model = SentenceTransformer(model_name)
        self.intent_labels = []
        self.reference_embeddings: Optional[torch.Tensor] = None
        self._prepare_references()

    def _prepare_references(self):
        """Menyiapkan representasi vektor (embeddings) dari semua pattern di rules.py"""
        sentences = []
        labels = []
        
        for rule in INTENT_RULES:
            for mapping in rule.get("mappings", []):
                sentences.append(mapping["pattern"])
                labels.append(rule["name"])
        
        self.intent_labels = labels
        # Encode semua pattern menjadi vektor
        self.reference_embeddings = self.model.encode(sentences, convert_to_tensor=True)

    def detect(self, user_input: str, threshold: float = 0.6) -> Tuple[Optional[str], float, Optional[str]]:
        """
        Mencari intent berdasarkan kemiripan makna (Cosine Similarity).
        """
        if not user_input.strip() or self.reference_embeddings is None:
            return None, 0.0, None

        # Encode input user
        query_embedding = self.model.encode(user_input, convert_to_tensor=True)
        
        # Hitung skor kemiripan dengan semua referensi
        # Pastikan kita memberitahu Pylance bahwa ini adalah Tensor yang bisa di-index
        scores_tensor = util.cos_sim(query_embedding, self.reference_embeddings)
        cosine_scores = scores_tensor[0]
        
        # Ambil skor tertinggi
        best_score_idx = int(torch.argmax(cosine_scores).item())
        best_score = float(cosine_scores[best_score_idx].item())
        
        if best_score >= threshold:
            intent_name = self.intent_labels[best_score_idx]
            # Cari respons default dari rules untuk intent ini
            response = self._get_default_response(intent_name)
            return intent_name, best_score, response
        
        return None, best_score, None

    def _get_default_response(self, intent_name):
        for rule in INTENT_RULES:
            if rule["name"] == intent_name:
                # Ambil respons pertama sebagai default dari semantic match
                return rule["mappings"][0]["response"]
        return None
import torch
from sentence_transformers import SentenceTransformer, util
from .rules import INTENT_RULES

class SemanticEngine:
    def __init__(self, model_name='paraphrase-multilingual-MiniLM-L12-v2'):
        # Model ini mendukung 50+ bahasa termasuk Indonesia
        self.model = SentenceTransformer(model_name)
        self.intent_labels = []
        self.reference_embeddings = None
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

    def detect(self, user_input: str, threshold: float = 0.6):
        """
        Mencari intent berdasarkan kemiripan makna (Cosine Similarity).
        """
        if not user_input.strip():
            return None, 0.0

        # Encode input user
        query_embedding = self.model.encode(user_input, convert_to_tensor=True)
        
        # Hitung skor kemiripan dengan semua referensi
        cosine_scores = util.cos_sim(query_embedding, self.reference_embeddings)[0]
        
        # Ambil skor tertinggi
        best_score_idx = torch.argmax(cosine_scores).item()
        best_score = cosine_scores[best_score_idx].item()
        
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
# chatbot/rule_engine.py (Final V3 - Logika yang Benar)

import os
import random
from typing import Optional, Tuple
from .rules import INTENT_RULES, FALLBACK_RESPONSES
from .response_router import route_intent
from .nlp_preprocess import preprocess


class RuleEngine:
    def __init__(self, min_score: int = 1) -> None:
        """Initialize the rule engine.

        Args:
            min_score: minimum token-match score required to consider an intent/pattern a match.
        """
        self.min_score = int(min_score)
        self.debug = os.getenv("INTENT_DEBUG", "0") in {"1", "true", "yes"}

    def _score_text(self, pattern_tokens: list[str], text_tokens: list[str]) -> int:
        """Memberikan skor berdasarkan jumlah token yang cocok."""
        if not pattern_tokens or not text_tokens:
            return 0
        
        # Cukup hitung jumlah kata yang sama
        return len(set(pattern_tokens) & set(text_tokens))

    def detect_with_response(self, user_input: str) -> Tuple[str, Optional[str], str]:
        """
        Mendeteksi intent dan respons dengan logika 2-langkah yang benar.
        1. Cari Intent dengan skor tertinggi.
        2. Di dalam Intent tersebut, cari Pola dengan skor tertinggi untuk mendapatkan Respons.
        """
        processed_tokens = preprocess(user_input)
        if not processed_tokens:
            return "fallback", random.choice(FALLBACK_RESPONSES), "TO_CS"

        if self.debug:
            print(f"[INTENT_DEBUG] user_input={user_input!r}")
            print(f"[INTENT_DEBUG] processed_tokens={processed_tokens}")

        # --- Langkah 1: Temukan Intent dengan Skor Tertinggi ---
        best_intent_rule = None
        highest_intent_score = 0

        for rule in INTENT_RULES:
            # Hitung skor total untuk satu intent dengan mencari skor pola terbaik di dalamnya
            max_score_in_rule = 0
            for mapping in rule.get("mappings", []):
                pattern_tokens = preprocess(mapping["pattern"])
                score = self._score_text(pattern_tokens, processed_tokens)
                if self.debug:
                    print(f"[INTENT_DEBUG] rule={rule.get('name')} pattern={mapping['pattern']!r} -> pattern_tokens={pattern_tokens} score={score}")
                if score > max_score_in_rule:
                    max_score_in_rule = score
            
            # Jika skor intent ini lebih tinggi dari yang terbaik sejauh ini
            if max_score_in_rule > highest_intent_score:
                highest_intent_score = max_score_in_rule
                best_intent_rule = rule

        # Jika tidak ada intent yang cocok sama sekali
        # Jika skor tertinggi tidak mencapai ambang minimal, fallback
        if self.debug:
            print(f"[INTENT_DEBUG] best_intent={getattr(best_intent_rule,'name', None) if best_intent_rule else best_intent_rule} highest_intent_score={highest_intent_score} min_score={self.min_score}")
        if highest_intent_score < self.min_score or not best_intent_rule:
            return "fallback", random.choice(FALLBACK_RESPONSES), "TO_CS"

        # --- Langkah 2: Di dalam Intent Terbaik, Temukan Respons Terbaik ---
        best_response = None
        highest_pattern_score = 0
        
        # Kita sekarang hanya mencari di dalam 'best_intent_rule' yang sudah kita menangkan
        for mapping in best_intent_rule.get("mappings", []):
            pattern_tokens = preprocess(mapping["pattern"])
            score = self._score_text(pattern_tokens, processed_tokens)

            if self.debug:
                print(f"[INTENT_DEBUG] checking mapping pattern={mapping['pattern']!r} -> pattern_tokens={pattern_tokens} score={score}")

            if score > highest_pattern_score:
                highest_pattern_score = score
                best_response = mapping["response"]
        
        # Jika karena suatu alasan tidak ada respons yang ditemukan (seharusnya tidak terjadi)
        if self.debug:
            print(f"[INTENT_DEBUG] best_response={best_response} highest_pattern_score={highest_pattern_score}")

        if not best_response or highest_pattern_score < self.min_score:
            return "fallback", random.choice(FALLBACK_RESPONSES), "TO_CS"

        # Dapatkan nama intent dan status routing
        final_intent_name = best_intent_rule["name"]
        status = route_intent(final_intent_name)

        return final_intent_name, best_response, status

    def detect_with_status(self, user_input: str) -> Tuple[str, Optional[str], str]:
        """Compatibility wrapper used by demos: calls `detect_with_response`.

        Kept for backward compatibility with existing demo scripts.
        """
        return self.detect_with_response(user_input)

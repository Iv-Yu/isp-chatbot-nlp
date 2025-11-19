import random
from typing import Optional, Tuple

from .nlp_processor import NLPProcessor
from .rules import INTENT_RULES, FALLBACK_RESPONSES
from .response_router import route_intent


class RuleEngine:
    def __init__(self, min_score: int = 1) -> None:
        """min_score: minimum total score required to accept a matched intent.
        If the best_score < min_score, engine returns fallback."""
        self.nlp = NLPProcessor()
        self.min_score = min_score

    def _score_pattern(self, pattern: str, text: str) -> int:
        pattern_norm = self.nlp.normalize(pattern)
        text_norm = text

        score = 0

        if pattern_norm in text_norm:
            score += 2

        for token in pattern_norm.split():
            if token in text_norm:
                score += 1

        return score

    def detect_intent(self, user_input: str) -> Tuple[str, str]:
        """Detect intent and return (intent_name, response_text).

        This method uses `min_score` to decide whether to accept the best match
        or return `fallback`.
        """
        norm_text = self.nlp.normalize(user_input)

        best_intent: Optional[str] = None
        best_response: Optional[str] = None
        best_score = 0

        for rule in INTENT_RULES:
            # Use the best single-pattern match for each rule instead of summing
            # across all patterns. Summing can inflate scores when many patterns
            # share common stopwords; using max(pattern_score) is more robust.
            pattern_scores = [self._score_pattern(p, norm_text) for p in rule["patterns"]]
            total_score = max(pattern_scores) if pattern_scores else 0

            if total_score > best_score:
                best_score = total_score
                best_intent = rule["name"]
                best_response = random.choice(rule["responses"])

        # Require a score strictly greater than `min_score` to accept a match.
        # This avoids accepting very weak matches (score == min_score) which
        # are often noisy. Tests create the engine with `min_score=1` and
        # expect ambiguous inputs to fall back.
        if best_intent is None or best_score <= self.min_score:
            return "fallback", random.choice(FALLBACK_RESPONSES)

        return best_intent, best_response

    def detect_with_score(self, user_input: str) -> Tuple[str, str, int]:
        """Return (intent_name, response_text, score) useful for analysis/debugging."""
        norm_text = self.nlp.normalize(user_input)

        best_intent: Optional[str] = None
        best_response: Optional[str] = None
        best_score = 0

        for rule in INTENT_RULES:
            pattern_scores = [self._score_pattern(p, norm_text) for p in rule["patterns"]]
            total_score = max(pattern_scores) if pattern_scores else 0

            if total_score > best_score:
                best_score = total_score
                best_intent = rule["name"]
                best_response = random.choice(rule["responses"])

        if best_intent is None or best_score <= self.min_score:
            return "fallback", random.choice(FALLBACK_RESPONSES), best_score

        return best_intent, best_response, best_score

    def detect_with_status(self, user_input: str):
        """
        Mengembalikan:
        - intent
        - response
        - status (AUTO_RESPONSE / TO_CS / TO_NOC)
        """
        intent, response = self.detect_intent(user_input)
        status = route_intent(intent)
        return intent, response, status

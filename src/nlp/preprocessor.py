import re
from typing import List

from Sastrawi.Stemmer.StemmerFactory import StemmerFactory
from Sastrawi.StopWordRemover.StopWordRemoverFactory import StopWordRemoverFactory


class IndoPreprocessor:
    """Case folding → cleaning → tokenizing → stopword removal → Sastrawi stemming."""

    _non_alnum = re.compile(r"[^0-9a-z\s]+")

    def __init__(self) -> None:
        self.stemmer = StemmerFactory().create_stemmer()
        self.stopword_remover = StopWordRemoverFactory().create_stop_word_remover()
        self.extra_stopwords = {
            "yg",
            "ya",
            "aja",
            "nih",
            "sih",
            "dong",
            "nya",
            "bang",
            "bro",
            "min",
            "gua",
            "gue",
            "gk",
            "ga",
            "gak",
            "kok",
            "lah",
            "deh",
        }
        self.custom_stem = {
            "mengeluhkan": "eluh",
            "keluhkan": "eluh",
            "pengeluhan": "eluh",
            "perbaikan": "baik",
        }

    def __call__(self, text: str) -> List[str]:
        if not isinstance(text, str):
            return []

        # 1. Case folding
        text = text.lower()
        # 2. Cleaning (hapus tanda baca/non alnum)
        text = self._non_alnum.sub(" ", text)
        text = re.sub(r"\s+", " ", text).strip()
        if not text:
            return []

        # 3. Tokenizing
        tokens = text.split()

        # 4. Stopword removal (Sastrawi + ekstra kata percakapan)
        filtered: List[str] = []
        for tok in tokens:
            if not self.stopword_remover.remove(tok).strip():
                continue
            if tok in self.extra_stopwords:
                continue
            filtered.append(tok)

        # 5. Stemming per token (Sastrawi) dengan mapping khusus
        processed: List[str] = []
        for token in filtered:
            stemmed = self.stemmer.stem(token)
            stemmed = self.custom_stem.get(token, self.custom_stem.get(stemmed, stemmed))
            if stemmed:
                processed.append(stemmed)
        return processed

import re
import unicodedata
from typing import List

from Sastrawi.Stemmer.StemmerFactory import StemmerFactory
from Sastrawi.StopWordRemover.StopWordRemoverFactory import StopWordRemoverFactory

# Initialize Sastrawi components once
_STEMMER = StemmerFactory().create_stemmer()
_STOPWORD_REMOVER = StopWordRemoverFactory().create_stop_word_remover()


_EXTRA_STOPWORDS = {
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

# Kata-kata yang harus dilindungi agar tidak dihapus oleh Sastrawi Stopword Remover
# karena merupakan pemicu utama intent (Greeting/Complaint)
_PROTECTED_TOKENS = {
    "assalamualaikum",
    "waalaikumsalam",
    "halo",
    "hai",
    "hello",
    "pagi", "siang", "sore", "malam",
    "ass", "wr", "wb",
    "bisa",
    "mati",
    "trouble",
    "rusak"
}

_CUSTOM_STEM = {
    "mengeluhkan": "eluh",
    "keluhkan": "eluh",
    "pengeluhan": "eluh",
    "perbaikan": "baik",
}


def normalize(text: str) -> str:
    if not isinstance(text, str):
        return ""
    text = text.lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[^a-z0-9\s]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def tokenize(text: str) -> List[str]:
    normalized = normalize(text)
    if not normalized:
        return []
    return normalized.split()


def remove_stopwords(tokens: List[str]) -> List[str]:
    filtered: List[str] = []
    for tok in tokens:
        # Jangan hapus jika kata tersebut ada dalam daftar proteksi
        if tok in _PROTECTED_TOKENS:
            filtered.append(tok)
            continue
        # Sastrawi stopword remover expects a string; if it returns empty, tok is stopword
        if not _STOPWORD_REMOVER.remove(tok).strip():
            continue
        if tok in _EXTRA_STOPWORDS:
            continue
        filtered.append(tok)
    return filtered


def stem_tokens(tokens: List[str]) -> List[str]:
    stemmed: List[str] = []
    for tok in tokens:
        s = _STEMMER.stem(tok)
        s = _CUSTOM_STEM.get(tok, _CUSTOM_STEM.get(s, s))
        if s:
            stemmed.append(s)
    return stemmed


def preprocess(text: str) -> List[str]:
    """Complete preprocessing pipeline: tokenize -> remove stopwords -> stem.

    Returns a list of final tokens (stemmed).
    """
    tokens = tokenize(text)
    tokens = remove_stopwords(tokens)
    tokens = stem_tokens(tokens)
    return tokens

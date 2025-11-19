import re
import unicodedata
import re
import unicodedata


class NLPProcessor:
    def normalize(self, text: str) -> str:
        if not isinstance(text, str):
            return ""

        text = text.lower()
        text = unicodedata.normalize("NFKD", text)
        text = "".join(ch for ch in text if not unicodedata.combining(ch))
        text = re.sub(r"[^a-z0-9\s]+", " ", text)
        text = re.sub(r"\s+", " ", text)
        return text.strip()


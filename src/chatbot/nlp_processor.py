from .nlp_preprocess import preprocess


class NLPProcessor:
    def __init__(self):
        # Keberadaan class ini mempertahankan API lama dan memungkinkan
        # ekstensi di masa depan. Saat ini ia hanya melapisi fungsi preprocess.
        pass

    def __call__(self, text: str) -> list[str]:
        return preprocess(text)
    def __init__(self):

        self.stemmer = _STEMMER


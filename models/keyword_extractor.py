# models/keyword_extractor.py
"""
Keyword extraction using KeyBERT (if available).
Fallback to a simple TF-IDF approach if KeyBERT not installed.
"""

try:
    from keybert import KeyBERT
except ImportError:
    KeyBERT = None

from sklearn.feature_extraction.text import TfidfVectorizer


class KeywordExtractor:
    def __init__(self, model_name: str = "distilbert-base-uncased"):
        if KeyBERT:
            try:
                self.kw_model = KeyBERT(model=model_name)
            except Exception as e:
                print(f"[WARN] Could not load KeyBERT with {model_name}: {e}")
                self.kw_model = None
        else:
            self.kw_model = None

    def extract(self, text: str, top_n: int = 10) -> list:
        """
        Extract keywords from text.
        Returns list of (keyword, score).
        """
        if self.kw_model:
            try:
                keywords = self.kw_model.extract_keywords(text, top_n=top_n)
                return keywords
            except Exception as e:
                print(f"[ERROR] KeyBERT extraction failed: {e}")

        # fallback: TF-IDF
        tfidf = TfidfVectorizer(stop_words="english", max_features=top_n)
        try:
            tfidf.fit([text])
            return [(word, 1.0) for word in tfidf.get_feature_names_out()]
        except Exception as e:
            print(f"[ERROR] TF-IDF extraction failed: {e}")
            return []

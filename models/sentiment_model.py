# models/sentiment_model.py
"""
Wrapper for HuggingFace sentiment analysis pipeline.
"""

from transformers import pipeline


class SentimentAnalyzer:
    def __init__(self, model_name: str = "distilbert-base-uncased-finetuned-sst-2-english"):
        try:
            self.pipeline = pipeline("sentiment-analysis", model=model_name)
        except Exception as e:
            print(f"[ERROR] Could not load sentiment model: {e}")
            self.pipeline = None

    def analyze(self, text: str) -> dict:
        """
        Run sentiment analysis on a given text.
        Returns dict: {label: str, score: float}
        """
        if not self.pipeline:
            return {"label": "UNKNOWN", "score": 0.0}

        result = self.pipeline(text)[0]
        return {"label": result["label"], "score": float(result["score"])}

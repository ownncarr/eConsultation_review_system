# models/summarizer_model.py
"""
Wrapper for HuggingFace summarization pipeline.
"""

from transformers import pipeline


class Summarizer:
    def __init__(self, model_name: str = "sshleifer/distilbart-cnn-12-6"):
        try:
            self.pipeline = pipeline("summarization", model=model_name)
        except Exception as e:
            print(f"[ERROR] Could not load summarizer model: {e}")
            self.pipeline = None

    def summarize(self, text: str, min_length: int = 25, max_length: int = 100) -> str:
        """
        Generate summary for input text.
        """
        if not self.pipeline:
            return text[:max_length]  # fallback: truncate

        try:
            result = self.pipeline(
                text, min_length=min_length, max_length=max_length, do_sample=False
            )
            return result[0]["summary_text"]
        except Exception as e:
            print(f"[ERROR] Summarization failed: {e}")
            return text[:max_length]

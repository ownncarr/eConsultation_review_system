# controllers/live_demo_controller.py
"""
Controller for Live Demo mode.

Responsibilities:
- Accept single text input from the UI
- Clean & chunk text for long inputs
- Run sentiment analysis, summarization (on chunks if needed), and keyword extraction
- Aggregate results into a single dict suitable for the UI
"""

from typing import Dict, Any, List
import logging
import yaml
from pathlib import Path

from models import SentimentAnalyzer, Summarizer, KeywordExtractor
from preprocessing import clean_text, chunk_text

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class LiveDemoController:
    def __init__(self, settings_path: str = "configs/settings.yaml"):
        self.settings = self._load_settings(settings_path)
        # instantiate models lazily
        self._sentiment = None
        self._summarizer = None
        self._keyword_extractor = None

    # ----- settings & lazy model loading -----
    def _load_settings(self, path: str) -> dict:
        try:
            with open(path, "r") as f:
                cfg = yaml.safe_load(f)
            return cfg or {}
        except Exception as e:
            logger.warning("Could not load settings.yaml (%s). Using defaults. Error: %s", path, e)
            return {}

    @property
    def sentiment(self) -> SentimentAnalyzer:
        if self._sentiment is None:
            model_name = self.settings.get("models", {}).get("sentiment_model", None)
            try:
                self._sentiment = SentimentAnalyzer(model_name) if model_name else SentimentAnalyzer()
            except Exception as e:
                logger.error("Failed loading SentimentAnalyzer: %s", e)
                self._sentiment = SentimentAnalyzer()
        return self._sentiment

    @property
    def summarizer(self) -> Summarizer:
        if self._summarizer is None:
            model_name = self.settings.get("models", {}).get("summarizer_model", None)
            try:
                self._summarizer = Summarizer(model_name) if model_name else Summarizer()
            except Exception as e:
                logger.error("Failed loading Summarizer: %s", e)
                self._summarizer = Summarizer()
        return self._summarizer

    @property
    def keyword_extractor(self) -> KeywordExtractor:
        if self._keyword_extractor is None:
            model_name = self.settings.get("models", {}).get("keyword_extractor", None)
            try:
                self._keyword_extractor = KeywordExtractor(model_name) if model_name else KeywordExtractor()
            except Exception as e:
                logger.warning("Failed loading KeywordExtractor: %s", e)
                self._keyword_extractor = KeywordExtractor()
        return self._keyword_extractor

    # ----- core processing -----
    def process_text(self, raw_text: str) -> Dict[str, Any]:
        """
        Process a single piece of text and produce:
          - cleaned text
          - sentiment {label, score}
          - summary
          - keywords [(kw, score), ...]
        """
        if not raw_text:
            return {"error": "Empty input"}

        # 1) Clean
        cleaned = clean_text(raw_text)

        # 2) Sentiment (single pass)
        try:
            sentiment_res = self.sentiment.analyze(cleaned)
        except Exception as e:
            logger.error("Sentiment analysis failed: %s", e)
            sentiment_res = {"label": "UNKNOWN", "score": 0.0}

        # 3) Summarization
        summary_cfg = self.settings.get("thresholds", {})
        min_len = summary_cfg.get("min_summary_length", 25)
        max_len = summary_cfg.get("max_summary_length", 100)

        # If text is long, chunk and summarize each chunk then join
        chunks = chunk_text(cleaned, max_words=300, overlap=60)
        if len(chunks) <= 1:
            try:
                summary = self.summarizer.summarize(cleaned, min_length=min_len, max_length=max_len)
            except Exception as e:
                logger.error("Summarization failed (single): %s", e)
                summary = cleaned[: max_len]
        else:
            # summarize each chunk and join them intelligently
            summaries: List[str] = []
            for c in chunks:
                try:
                    s = self.summarizer.summarize(c, min_length=min_len, max_length=max_len)
                except Exception as e:
                    logger.error("Summarization failed for chunk: %s", e)
                    s = c[: max_len]
                summaries.append(s.strip())
            # optionally summarize the concatenated chunk summaries if too long
            long_summary = " ".join(summaries)
            if len(long_summary.split()) > max_len:
                try:
                    summary = self.summarizer.summarize(long_summary, min_length=min_len, max_length=max_len)
                except Exception:
                    summary = long_summary[: max_len]
            else:
                summary = long_summary

        # 4) Keywords
        top_n = self.settings.get("thresholds", {}).get("top_keywords", 10)
        try:
            keywords = self.keyword_extractor.extract(cleaned, top_n=top_n)
        except Exception as e:
            logger.error("Keyword extraction failed: %s", e)
            keywords = []

        return {
            "cleaned_text": cleaned,
            "sentiment": sentiment_res,
            "summary": summary,
            "keywords": keywords,
        }

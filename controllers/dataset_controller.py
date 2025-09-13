# controllers/dataset_controller.py
"""
Controller for Dataset mode.

Responsibilities:
- Accept a dataset file (CSV or Excel).
- Read text column (user-specified or try to auto-detect common columns).
- Process each row (clean, sentiment, summary, keywords).
- Save results to `data/processed/` and/or return results to UI for display.

This class uses pandas to read datasets. If pandas is unavailable, it will raise
an informative error.
"""

from typing import List, Dict, Any, Optional
import logging
import os
import yaml
from pathlib import Path
import pandas as pd
from tqdm import tqdm

from models import SentimentAnalyzer, Summarizer, KeywordExtractor
from preprocessing import clean_text, chunk_text

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class DatasetController:
    SUPPORTED_EXT = [".csv", ".xls", ".xlsx"]

    def __init__(self, settings_path: str = "configs/settings.yaml"):
        self.settings = self._load_settings(settings_path)
        self.output_dir = Path(self.settings.get("paths", {}).get("data_dir", "data/processed/"))
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # lazy model instances
        self._sentiment = None
        self._summarizer = None
        self._keyword_extractor = None

    def _load_settings(self, path: str) -> dict:
        try:
            with open(path, "r") as f:
                cfg = yaml.safe_load(f)
            return cfg or {}
        except Exception as e:
            logger.warning("Could not load settings.yaml (%s). Using defaults. Error: %s", path, e)
            # fallback defaults
            return {
                "thresholds": {"min_summary_length": 25, "max_summary_length": 100, "top_keywords": 10},
                "paths": {"data_dir": "data/processed/"},
            }

    @property
    def sentiment(self) -> SentimentAnalyzer:
        if self._sentiment is None:
            model_name = self.settings.get("models", {}).get("sentiment_model", None)
            try:
                self._sentiment = SentimentAnalyzer(model_name) if model_name else SentimentAnalyzer()
            except Exception as e:
                logger.error("Failed to initialize SentimentAnalyzer: %s", e)
                self._sentiment = SentimentAnalyzer()
        return self._sentiment

    @property
    def summarizer(self) -> Summarizer:
        if self._summarizer is None:
            model_name = self.settings.get("models", {}).get("summarizer_model", None)
            try:
                self._summarizer = Summarizer(model_name) if model_name else Summarizer()
            except Exception as e:
                logger.error("Failed to initialize Summarizer: %s", e)
                self._summarizer = Summarizer()
        return self._summarizer

    @property
    def keyword_extractor(self) -> KeywordExtractor:
        if self._keyword_extractor is None:
            model_name = self.settings.get("models", {}).get("keyword_extractor", None)
            try:
                self._keyword_extractor = KeywordExtractor(model_name) if model_name else KeywordExtractor()
            except Exception as e:
                logger.warning("Failed to initialize KeywordExtractor: %s", e)
                self._keyword_extractor = KeywordExtractor()
        return self._keyword_extractor

    def _read_dataset(self, path: str) -> pd.DataFrame:
        ext = Path(path).suffix.lower()
        if ext not in self.SUPPORTED_EXT:
            raise ValueError(f"Unsupported file extension: {ext}. Supported: {self.SUPPORTED_EXT}")
        if ext == ".csv":
            df = pd.read_csv(path)
        else:
            df = pd.read_excel(path)
        return df

    def _guess_text_column(self, df: pd.DataFrame, preferred: Optional[str] = None) -> str:
        # If user provides preferred column and it's present, use it
        if preferred and preferred in df.columns:
            return preferred

        # common names to try
        candidates = ["comment", "text", "feedback", "review", "message", "content"]
        for c in candidates:
            if c in df.columns:
                return c

        # fallback: pick the first string-like column
        for col in df.columns:
            if pd.api.types.is_string_dtype(df[col]):
                return col

        # if nothing found, raise
        raise ValueError("No suitable text column found. Please specify which column contains text.")

    def process_dataset(
        self, file_path: str, text_column: Optional[str] = None, save_csv: bool = True
    ) -> Dict[str, Any]:
        """
        Process a dataset and return a dict with summary info + path to processed file.

        Returns:
            {
                "input_rows": int,
                "processed_rows": int,
                "output_path": "<path>",
                "errors": [ ... ],
                "preview": [ {row_id, original, cleaned, sentiment, summary, keywords}, ... ]
            }
        """
        df = self._read_dataset(file_path)
        input_rows = len(df)
        try:
            text_col = self._guess_text_column(df, text_column)
        except ValueError as e:
            logger.error("Could not determine text column: %s", e)
            return {"error": str(e)}

        results = []
        errors = []
        min_len = self.settings.get("thresholds", {}).get("min_summary_length", 25)
        max_len = self.settings.get("thresholds", {}).get("max_summary_length", 100)
        top_n = self.settings.get("thresholds", {}).get("top_keywords", 10)

        # iterate rows
        for idx, row in tqdm(df.iterrows(), total=input_rows, desc="Processing rows"):
            raw = row.get(text_col, "")
            if not isinstance(raw, str) or not raw.strip():
                errors.append({"row": int(idx), "error": "Empty or missing text"})
                continue

            try:
                cleaned = clean_text(raw)
                sentiment = self.sentiment.analyze(cleaned)
                # summarization with chunking like in live demo
                chunks = chunk_text(cleaned, max_words=300, overlap=60)
                if len(chunks) <= 1:
                    summary = self.summarizer.summarize(cleaned, min_length=min_len, max_length=max_len)
                else:
                    inner_summaries = []
                    for c in chunks:
                        try:
                            s = self.summarizer.summarize(c, min_length=min_len, max_length=max_len)
                        except Exception:
                            s = c[:max_len]
                        inner_summaries.append(s.strip())
                    long_summary = " ".join(inner_summaries)
                    if len(long_summary.split()) > max_len:
                        try:
                            summary = self.summarizer.summarize(long_summary, min_length=min_len, max_length=max_len)
                        except Exception:
                            summary = long_summary[: max_len]
                    else:
                        summary = long_summary

                keywords = self.keyword_extractor.extract(cleaned, top_n=top_n)

                results.append(
                    {
                        "row": int(idx),
                        "original": raw,
                        "cleaned": cleaned,
                        "sentiment_label": sentiment.get("label"),
                        "sentiment_score": sentiment.get("score"),
                        "summary": summary,
                        "keywords": keywords,
                    }
                )
            except Exception as e:
                logger.exception("Processing failed for row %s: %s", idx, e)
                errors.append({"row": int(idx), "error": str(e)})
                continue

        # convert results to DataFrame for saving/preview
        out_df = pd.DataFrame(results)
        out_name = Path(file_path).stem + "_processed.csv"
        out_path = self.output_dir.joinpath(out_name)

        if save_csv:
            try:
                out_df.to_csv(out_path, index=False)
                logger.info("Saved processed dataset to %s", out_path)
            except Exception as e:
                logger.error("Failed to save processed dataset: %s", e)

        preview = results[: min(50, len(results))]  # small preview for UI

        return {
            "input_rows": input_rows,
            "processed_rows": len(results),
            "output_path": str(out_path),
            "errors": errors,
            "preview": preview,
        }

# econsult_core/models.py
from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification
import logging
from typing import Tuple
import streamlit as st
# Internal (hidden) setting: confidence threshold for mapping to Neutral
_NEUTRAL_THRESHOLD = 0.70

logger = logging.getLogger(__name__)

@st.cache_resource
def load_pipelines():
    """
    Load summarizer + sentiment models once and cache them.
    """
    try:
        summarizer = pipeline("summarization", model="facebook/bart-large-cnn", device=-1)
    except Exception:
        summarizer = pipeline("summarization", model="t5-small", device=-1)

    try:
        sentiment = pipeline("sentiment-analysis", model="cardiffnlp/twitter-roberta-base-sentiment-latest", device=-1)
    except Exception:
        sentiment = pipeline("sentiment-analysis", model="distilbert-base-uncased-finetuned-sst-2-english", device=-1)

    return sentiment, summarizer

def map_sentiment(raw_label: str, score: float) -> Tuple[str, float]:
    """
    Map pipeline label and score into Positive/Neutral/Negative using internal threshold.
    """
    label = (raw_label or "").upper()
    if score < _NEUTRAL_THRESHOLD:
        return "Neutral", float(score)
    if label.startswith("POS") or "POS" in label:
        return "Positive", float(score)
    # handle star-rating style (like nlptown) mapping
    if label in {"1", "2"}:
        return "Negative", float(score)
    if label in {"4", "5"}:
        return "Positive", float(score)
    return "Negative", float(score)  # default fallback

# utils/visualization.py
"""
Simple visualization helpers:
- generate_wordcloud_image_bytes(text) -> PNG bytes (requires wordcloud + matplotlib)
- plot_sentiment_distribution(counts: dict) -> PNG bytes (uses matplotlib)
Both functions return raw PNG bytes which can be loaded into QPixmap in UI.
"""

from io import BytesIO
from typing import Dict, Any
from pathlib import Path

try:
    from wordcloud import WordCloud
    import matplotlib.pyplot as plt
    _VIS_AVAILABLE = True
except Exception:
    _VIS_AVAILABLE = False

def generate_wordcloud_image_bytes(text: str, width: int = 800, height: int = 400) -> bytes | None:
    """
    Generate a wordcloud PNG as bytes. Returns None if dependencies missing.
    """
    if not _VIS_AVAILABLE or not text:
        return None
    try:
        wc = WordCloud(width=width, height=height, background_color="white").generate(text)
        fig = plt.figure(figsize=(width / 100, height / 100), dpi=100)
        plt.imshow(wc, interpolation="bilinear")
        plt.axis("off")
        buf = BytesIO()
        fig.savefig(buf, format="png", bbox_inches="tight")
        plt.close(fig)
        buf.seek(0)
        return buf.getvalue()
    except Exception:
        return None

def plot_sentiment_distribution(counts: Dict[str, int], title: str = "Sentiment Distribution") -> bytes | None:
    """
    Create a simple bar chart for sentiment counts and return PNG bytes.
    counts: e.g. {"POSITIVE": 12, "NEGATIVE": 3, "NEUTRAL": 5}
    Returns PNG bytes or None if matplotlib missing.
    """
    if not _VIS_AVAILABLE:
        return None
    try:
        labels = list(counts.keys())
        values = [counts[k] for k in labels]
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.bar(labels, values)
        ax.set_title(title)
        ax.set_ylabel("Count")
        # avoid tight layout issues
        fig.tight_layout()
        buf = BytesIO()
        fig.savefig(buf, format="png", bbox_inches="tight")
        plt.close(fig)
        buf.seek(0)
        return buf.getvalue()
    except Exception:
        return None

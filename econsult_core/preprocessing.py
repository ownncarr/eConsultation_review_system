# econsult_core/preprocessing.py
import re
from typing import List
from math import ceil

def clean_text(text: str) -> str:
    if not isinstance(text, str):
        return ""
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def chunk_text(text: str, max_chars: int = 600) -> List[str]:
    """
    Simple chunker that tries to respect sentence boundaries.
    Larger chunk size used for heavier summarizers (BART can handle more).
    """
    text = text.strip()
    if len(text) <= max_chars:
        return [text]
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + max_chars, len(text))
        if end < len(text):
            # try to move to last sentence boundary inside the chunk
            last_dot = text.rfind(".", start, end)
            if last_dot > start + 30:
                end = last_dot + 1
        chunks.append(text[start:end].strip())
        start = end
    return chunks

def summarize_text(summarizer, text: str, max_chunk_chars: int = 600) -> str:
    text = clean_text(text)
    if not text:
        return ""
    chunks = chunk_text(text, max_chars=max_chunk_chars)
    summaries = []
    for c in chunks:
        try:
            out = summarizer(c, max_length=120, min_length=25, truncation=True)
            summaries.append(out[0]["summary_text"])
        except Exception:
            summaries.append((c[:250] + ("..." if len(c) > 250 else "")))
    if len(summaries) == 1:
        return summaries[0]
    # combine chunk summaries and compress once more
    combined = " ".join(summaries)
    try:
        out2 = summarizer(combined, max_length=180, min_length=40, truncation=True)
        return out2[0]["summary_text"]
    except Exception:
        return " ".join(summaries)

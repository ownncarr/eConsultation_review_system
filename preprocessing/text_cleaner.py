# preprocessing/text_cleaner.py
"""
Text cleaning utilities.

Features:
- Lowercasing (configurable)
- Removing extra whitespace
- Removing common control characters
- Removing URLs, emails, and simple HTML tags
- Optional basic contraction expansion (small list)
- Emoji removal (basic)
- Keeps punctuation useful for sentence splitting
"""

import re
from typing import Optional

# Small contraction map for common English contractions (extend as needed)
_CONTRACTIONS = {
    "can't": "cannot",
    "won't": "will not",
    "n't": " not",
    "'re": " are",
    "'s": " is",
    "'d": " would",
    "'ll": " will",
    "'ve": " have",
    "'m": " am",
}

# Basic emoji pattern (will remove many common emojis)
_EMOJI_PATTERN = re.compile(
    "[\U0001F600-\U0001F64F"  # emoticons
    "\U0001F300-\U0001F5FF"  # symbols & pictographs
    "\U0001F680-\U0001F6FF"  # transport & map symbols
    "\U0001F1E0-\U0001F1FF"  # flags (iOS)
    "]+",
    flags=re.UNICODE,
)


def _expand_contractions(text: str) -> str:
    # naive contraction expansion
    for contr, full in _CONTRACTIONS.items():
        # replace both case-sensitive and lower-case variants
        text = re.sub(re.escape(contr), full, text, flags=re.IGNORECASE)
    return text


def clean_text(text: str, lowercase: bool = True, expand_contractions: bool = True) -> str:
    """
    Clean and normalize raw text.

    Args:
        text: input string
        lowercase: whether to lowercase the text (default True)
        expand_contractions: whether to expand common contractions

    Returns:
        cleaned string
    """
    if not isinstance(text, str):
        text = str(text)

    # Normalize newlines and remove zero-width/control characters
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[\x00-\x1F\x7F]", " ", text)

    # Remove HTML tags
    text = re.sub(r"<[^>]+>", " ", text)

    # Remove URLs
    text = re.sub(
        r"(https?:\/\/(?:www\.|(?!www))[^\s]+|www\.[^\s]+)",
        " ",
        text,
        flags=re.IGNORECASE,
    )

    # Remove emails
    text = re.sub(r"\S+@\S+\.\S+", " ", text)

    # Remove emojis
    text = _EMOJI_PATTERN.sub(" ", text)

    # Expand contractions if requested
    if expand_contractions:
        text = _expand_contractions(text)

    # Replace multiple punctuation/newline sequences with single ones but keep sentence punctuation
    text = re.sub(r"\n+", "\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"(?<!\w)[—–-]+(?!\w)", "-", text)  # normalize dashes

    # Trim
    text = text.strip()

    if lowercase:
        text = text.lower()

    # Final collapse of repeated whitespace
    text = re.sub(r"\s+", " ", text).strip()

    return text

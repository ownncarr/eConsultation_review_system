# preprocessing/chunking.py
"""
Chunking utilities to split long text into smaller overlapping pieces.

Use-case:
- Summarizers and transformers often have token limits. For long feedback/comments
  we split by sentences (if available) and create overlapping chunks by word count.

Functions:
- chunk_text(text, max_words=250, overlap=50) -> list[str]
"""

from typing import List
import re

try:
    # sentence tokenizer improves chunk boundaries
    import nltk

    _NLTK_AVAILABLE = True
    try:
        nltk.data.find("tokenizers/punkt")
    except LookupError:
        # try to download punkt quietly (if internet & permission available)
        try:
            nltk.download("punkt", quiet=True)
        except Exception:
            pass
except Exception:
    _NLTK_AVAILABLE = False

_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")


def _sentences_from_text(text: str) -> List[str]:
    """Return a list of sentences using nltk if available, else a regex fallback."""
    if _NLTK_AVAILABLE:
        try:
            from nltk.tokenize import sent_tokenize

            return sent_tokenize(text)
        except Exception:
            pass

    # fallback: split on simple punctuation boundaries
    sentences = [s.strip() for s in _SENTENCE_SPLIT_RE.split(text) if s.strip()]
    return sentences


def _words_in_sentence(sentence: str) -> int:
    return len(sentence.split())


def chunk_text(text: str, max_words: int = 250, overlap: int = 50) -> List[str]:
    """
    Split text into chunks of up to `max_words` words with `overlap` words overlapping.

    Args:
        text: input text
        max_words: approximate max words per chunk (default 250)
        overlap: number of words to overlap between consecutive chunks (default 50)

    Returns:
        list of text chunks
    """
    if not text:
        return []

    sentences = _sentences_from_text(text)
    if not sentences:
        return []

    chunks: List[str] = []
    current_chunk: List[str] = []
    current_words = 0

    for sent in sentences:
        sent_words = _words_in_sentence(sent)
        # If single sentence longer than max_words, split by words
        if sent_words > max_words:
            words = sent.split()
            i = 0
            while i < len(words):
                end = min(i + max_words, len(words))
                chunk_words = words[i:end]
                chunk_text_piece = " ".join(chunk_words).strip()
                # append chunk
                if chunk_text_piece:
                    chunks.append(chunk_text_piece)
                # move with overlap
                i = end - overlap if end - overlap > i else end
            # continue to next sentence
            current_chunk = []
            current_words = 0
            continue

        # If adding the sentence would exceed max_words, finalize current chunk
        if current_words + sent_words > max_words:
            if current_chunk:
                chunks.append(" ".join(current_chunk).strip())
            # start new chunk — carry overlap from last chunk if possible
            if overlap > 0 and chunks:
                # take last `overlap` words from the last chunk as start
                last_chunk_words = chunks[-1].split()
                carry = last_chunk_words[-overlap:] if len(last_chunk_words) >= overlap else last_chunk_words
                current_chunk = carry.copy()
                current_words = len(current_chunk)
            else:
                current_chunk = []
                current_words = 0

        # add sentence to current chunk
        current_chunk.append(sent)
        current_words += sent_words

    # append any remaining chunk
    if current_chunk:
        chunks.append(" ".join(current_chunk).strip())

    # Final cleanup: strip and remove empty strings
    chunks = [c for c in (chunk.strip() for chunk in chunks) if c]

    return chunks

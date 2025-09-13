# preprocessing/__init__.py
"""
Preprocessing utilities for eConsult AI Reviewer.

Exports:
- clean_text: basic cleaning and normalization
- chunk_text: split long text into overlapping chunks suitable for summarizers
"""

from .text_cleaner import clean_text
from .chunking import chunk_text

__all__ = ["clean_text", "chunk_text"]

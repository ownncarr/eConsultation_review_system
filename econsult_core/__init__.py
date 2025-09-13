# econsult_core/__init__.py
"""
Core modules for eConsult AI Reviewer:
- models: load and run transformer pipelines
- preprocessing: clean, chunk, and summarize text
- reporting: generate wordclouds, keyword counts, and PDF reports
"""

from . import models, preprocessing, reporting

__all__ = ["models", "preprocessing", "reporting"]

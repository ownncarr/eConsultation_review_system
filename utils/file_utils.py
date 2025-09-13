# utils/file_utils.py
"""
File utilities: reading datasets (CSV/Excel) and saving dataframes as CSV.

This module prefers pandas if available, but falls back to csv / openpyxl-lite behaviors
with informative errors.
"""

from pathlib import Path
from typing import Optional
import csv
import os

try:
    import pandas as pd
    _PD_AVAILABLE = True
except Exception:
    _PD_AVAILABLE = False

def ensure_dir(path: str) -> Path:
    """
    Ensure a directory exists and return its Path.
    """
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p

def read_dataset(path: str, sample_n: Optional[int] = None):
    """
    Read a dataset from CSV or Excel. Returns a pandas.DataFrame if pandas is available,
    otherwise returns a list of dict rows (for CSV only).

    Args:
        path: path to .csv/.xls/.xlsx
        sample_n: if given, return only the first n rows (DataFrame or list)

    Raises:
        ValueError on unsupported extension or if pandas is required but missing for Excel.
    """
    p = Path(path)
    ext = p.suffix.lower()
    if ext == ".csv":
        if _PD_AVAILABLE:
            df = pd.read_csv(path)
            return df.head(sample_n) if sample_n else df
        # fallback: parse with csv module
        rows = []
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for i, r in enumerate(reader):
                rows.append(r)
                if sample_n and i + 1 >= sample_n:
                    break
        return rows
    elif ext in (".xls", ".xlsx"):
        if not _PD_AVAILABLE:
            raise ValueError("Reading Excel files requires pandas to be installed.")
        df = pd.read_excel(path)
        return df.head(sample_n) if sample_n else df
    else:
        raise ValueError(f"Unsupported dataset extension: {ext}")

def save_dataframe_csv(df, path: str):
    """
    Save a pandas DataFrame (or list-of-dicts) as CSV.

    Args:
        df: pandas.DataFrame or list[dict]
        path: output path
    Returns:
        Path to saved file.
    """
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    if _PD_AVAILABLE and hasattr(df, "to_csv"):
        df.to_csv(out, index=False, encoding="utf-8")
        return out
    # fallback for list-of-dicts
    if isinstance(df, (list, tuple)) and df:
        headers = sorted({k for row in df for k in row.keys()})
        with open(out, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            for row in df:
                writer.writerow([row.get(h, "") for h in headers])
        return out
    # last fallback: try writing str()
    with open(out, "w", encoding="utf-8") as f:
        f.write(str(df))
    return out

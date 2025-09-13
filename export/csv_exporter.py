# export/csv_exporter.py
"""
Export results to CSV using pandas.

This module expects a list of dicts (like the 'results' returned by DatasetController.process_dataset)
and saves them as a CSV in the reports directory (or data/processed if preferred).
"""

from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml
import datetime

try:
    import pandas as pd
    _PD_AVAILABLE = True
except Exception:
    _PD_AVAILABLE = False


def _load_reports_dir(default: str = "reports") -> Path:
    try:
        with open("configs/settings.yaml", "r") as f:
            cfg = yaml.safe_load(f) or {}
            path = cfg.get("paths", {}).get("reports_dir", default)
    except Exception:
        path = default
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def export_results_to_csv(items: List[Dict[str, Any]], filename: Optional[str] = None) -> Dict[str, Any]:
    """
    Export a list of dicts to a CSV file.

    Args:
        items: list of dictionaries (rows)
        filename: optional filename (without path), timestamped otherwise

    Returns:
        dict: {"ok": bool, "path": str, "error": Optional[str]}
    """
    reports_dir = _load_reports_dir()
    if filename is None:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"results_{timestamp}.csv"
    out_path = reports_dir / filename

    if not _PD_AVAILABLE:
        # simple fallback: write naive CSV
        try:
            if not items:
                with open(out_path, "w", encoding="utf-8") as f:
                    f.write("")
                return {"ok": True, "path": str(out_path), "error": None, "fallback": True}

            # infer headers
            headers = sorted({k for row in items for k in row.keys()})
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(",".join(headers) + "\n")
                for row in items:
                    values = []
                    for h in headers:
                        v = row.get(h, "")
                        # handle lists/tuples (keywords)
                        if isinstance(v, (list, tuple)):
                            if v and isinstance(v[0], (list, tuple)):
                                v = ";".join([str(x[0]) for x in v])
                            else:
                                v = ";".join([str(x) for x in v])
                        values.append('"' + str(v).replace('"', '""') + '"')
                    f.write(",".join(values) + "\n")
            return {"ok": True, "path": str(out_path), "error": None, "fallback": True}
        except Exception as e:
            return {"ok": False, "path": str(out_path), "error": str(e), "fallback": True}

    try:
        df = pd.DataFrame(items)
        df.to_csv(out_path, index=False)
        return {"ok": True, "path": str(out_path), "error": None, "fallback": False}
    except Exception as e:
        return {"ok": False, "path": str(out_path), "error": str(e), "fallback": False}

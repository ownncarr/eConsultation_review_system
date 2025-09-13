# export/pdf_generator.py
"""
Generate a simple PDF report summarizing analysis results.

Primary dependency: reportlab
Fallback: write a plain text .txt if reportlab is not installed.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml
import datetime

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.lib.units import mm
    _RL_AVAILABLE = True
except Exception:
    _RL_AVAILABLE = False


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


def generate_pdf_report(
    title: str,
    items: List[Dict[str, Any]],
    filename: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Generate a PDF report.

    Args:
        title: Title used on the report
        items: List of dicts describing analysis results. Each dict could be:
               {"row": 1, "original": "...", "summary": "...", "sentiment_label": "POSITIVE", ...}
        filename: Optional filename (without path). If None, a timestamped file will be created.

    Returns:
        dict: {"ok": bool, "path": str, "error": Optional[str]}
    """
    reports_dir = _load_reports_dir()
    if filename is None:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{title.replace(' ', '_')}_{timestamp}.pdf"
    out_path = reports_dir / filename

    if not _RL_AVAILABLE:
        # fallback: write as plain text file with .txt extension
        text_path = out_path.with_suffix(".txt")
        try:
            with open(text_path, "w", encoding="utf-8") as f:
                f.write(f"{title}\nGenerated: {datetime.datetime.now().isoformat()}\n\n")
                for item in items:
                    for k, v in item.items():
                        f.write(f"{k}: {v}\n")
                    f.write("\n" + ("-" * 60) + "\n\n")
            return {"ok": True, "path": str(text_path), "error": None, "fallback": True}
        except Exception as e:
            return {"ok": False, "path": str(text_path), "error": str(e), "fallback": True}

    # Using ReportLab to create a formatted PDF
    try:
        doc = SimpleDocTemplate(str(out_path), pagesize=A4, rightMargin=15*mm, leftMargin=15*mm, topMargin=15*mm, bottomMargin=15*mm)
        styles = getSampleStyleSheet()
        story = []
        story.append(Paragraph(f"<b>{title}</b>", styles["Title"]))
        story.append(Spacer(1, 6))

        story.append(Paragraph(f"Generated: {datetime.datetime.now().isoformat()}", styles["Normal"]))
        story.append(Spacer(1, 12))

        for i, item in enumerate(items, start=1):
            # Short header line for each item
            header = f"<b>Item {i} - Row: {item.get('row', 'n/a')}</b>"
            story.append(Paragraph(header, styles["Heading3"]))
            story.append(Spacer(1, 6))

            # main fields (original, summary, sentiment)
            if "original" in item:
                story.append(Paragraph(f"<b>Original:</b> {item.get('original')}", styles["BodyText"]))
                story.append(Spacer(1, 4))
            if "summary" in item:
                story.append(Paragraph(f"<b>Summary:</b> {item.get('summary')}", styles["BodyText"]))
                story.append(Spacer(1, 4))
            if "sentiment_label" in item or "sentiment_score" in item:
                sl = item.get("sentiment_label", "N/A")
                ss = item.get("sentiment_score", "")
                story.append(Paragraph(f"<b>Sentiment:</b> {sl} {f'({ss:.2f})' if isinstance(ss, (int,float)) else ss}", styles["BodyText"]))
                story.append(Spacer(1, 4))
            if "keywords" in item:
                # keywords could be list of tuples or strings
                kws = item.get("keywords") or []
                if kws:
                    if isinstance(kws[0], (list, tuple)):
                        kw_str = ", ".join([str(k[0]) for k in kws])
                    else:
                        kw_str = ", ".join([str(k) for k in kws])
                    story.append(Paragraph(f"<b>Keywords:</b> {kw_str}", styles["BodyText"]))
                    story.append(Spacer(1, 4))

            story.append(Spacer(1, 6))
            story.append(Paragraph("<br/>", styles["Normal"]))

        doc.build(story)
        return {"ok": True, "path": str(out_path), "error": None, "fallback": False}
    except Exception as e:
        return {"ok": False, "path": str(out_path), "error": str(e), "fallback": False}

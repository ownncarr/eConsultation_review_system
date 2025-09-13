# econsult_core/reporting.py
from typing import List, Tuple, Optional
from PIL import Image
from wordcloud import WordCloud
import re
import tempfile
import os
from fpdf import FPDF
from datetime import datetime
import pandas as pd
from io import BytesIO

def generate_wordcloud(texts: List[str], max_words: int = 150) -> Image.Image:
    combined = " ".join([t for t in texts if t])
    wc = WordCloud(width=900, height=450, background_color="white", max_words=max_words)
    arr = wc.generate(combined).to_array()
    img = Image.fromarray(arr)
    return img

def top_keywords(texts: List[str], top_n: int = 25) -> List[Tuple[str,int]]:
    combined = " ".join([t.lower() for t in texts if t])
    tokens = re.findall(r"\b[a-zA-Z]{3,}\b", combined)
    stop = set(["the","and","for","with","that","this","from","shall","may","will","not","are","have","were","been","paragraph","section","clause","proposed","draft","stakeholder","please","would","could"])
    freqs = {}
    for t in tokens:
        if t in stop: 
            continue
        freqs[t] = freqs.get(t, 0) + 1
    items = sorted(freqs.items(), key=lambda x: x[1], reverse=True)
    return items[:top_n]

def _save_pil_to_tempfile(img: Image.Image, suffix: str = ".png") -> str:
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    img.save(tmp.name)
    tmp.close()
    return tmp.name

def make_pdf_report(df: pd.DataFrame,
                    wordcloud_img: Image.Image,
                    title: str = "eConsultation Report",
                    project_logo_path: Optional[str] = None,
                    team_logo_path: Optional[str] = None) -> bytes:
    """
    Build a well-formatted PDF.
    - Inserts project_logo on top-left and team_logo on top-right if paths provided.
    - Wordcloud sits under the header.
    - Keywords and a table follow.
    - Table uses multi_cell for the summary column so it doesn't overflow the page.
    Returns PDF bytes.
    """
    pdf = FPDF(unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=12)
    pdf.add_page()

    # Header logos
    margin_left = 15
    current_y = 12
    logo_max_h = 20  # mm
    logo_max_w = 40  # mm

    # Project logo (left)
    if project_logo_path and os.path.exists(project_logo_path):
        try:
            pdf.image(project_logo_path, x=margin_left, y=10, w=logo_max_w)
        except Exception:
            pass

    # Team logo (right)
    if team_logo_path and os.path.exists(team_logo_path):
        try:
            # compute x to right margin
            page_w = pdf.w - 2 * pdf.l_margin
            x_right = pdf.w - pdf.r_margin - logo_max_w
            pdf.image(team_logo_path, x=x_right, y=10, w=logo_max_w)
        except Exception:
            pass

    # Title text (center-left, below logos)
    pdf.set_xy(margin_left, 10 + logo_max_h + 2)
    pdf.set_font("Arial", size=16, style="B")
    pdf.cell(0, 8, title, ln=True)

    pdf.set_font("Arial", size=10)
    pdf.cell(0, 6, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=True)
    pdf.ln(4)

    # Insert wordcloud image (centered)
    try:
        wc_path = _save_pil_to_tempfile(wordcloud_img, suffix=".png")
        # fit to page width (keep margins)
        usable_w = pdf.w - 2 * pdf.l_margin
        pdf.image(wc_path, x=pdf.l_margin, w=usable_w)
        # cleanup temp file
        try:
            os.unlink(wc_path)
        except Exception:
            pass
    except Exception:
        pass

    pdf.ln(6)

    # Keywords
    pdf.set_font("Arial", size=11, style="B")
    pdf.cell(0, 7, "Top Keywords:", ln=True)
    pdf.set_font("Arial", size=10)
    kws = top_keywords(df["clean_text"].tolist(), top_n=40) if "clean_text" in df.columns else []
    # write keywords as two columns per row
    colw = (pdf.w - 2 * pdf.l_margin) / 2
    for i in range(0, len(kws), 2):
        left = f"{kws[i][0]} ({kws[i][1]})" if i < len(kws) else ""
        right = f"{kws[i+1][0]} ({kws[i+1][1]})" if i+1 < len(kws) else ""
        pdf.cell(colw, 6, left, border=0)
        pdf.cell(colw, 6, right, border=0, ln=True)

    pdf.ln(6)

    # Table header - choose widths that fit within printable width
    pdf.set_font("Arial", size=11, style="B")
    # Column widths in mm (sum should be <= usable_w)
    id_w = 18
    sent_w = 30
    score_w = 20
    summary_w = pdf.w - pdf.l_margin - pdf.r_margin - (id_w + sent_w + score_w)  # remaining width

    # Header row
    pdf.cell(id_w, 7, "ID", border=1)
    pdf.cell(sent_w, 7, "Sentiment", border=1)
    pdf.cell(score_w, 7, "Score", border=1)
    pdf.cell(summary_w, 7, "Summary (truncated)", border=1, ln=True)

    pdf.set_font("Arial", size=10)
    # Rows: use multi_cell for the summary column to wrap text
    for _, row in df.iterrows():
        idcell = str(row.get("id",""))
        sentiment = str(row.get("sentiment",""))
        score_val = row.get("score", "")
        try:
            score_str = f"{score_val:.2f}" if score_val != "" else ""
        except Exception:
            score_str = str(score_val)

        summary = str(row.get("summary","")).replace("\n", " ")
        # If too long, truncate to reasonable length (helps PDF size)
        if len(summary) > 1000:
            summary = summary[:997] + "..."

        # Save current x/y to restore after multi_cell
        x_before = pdf.get_x()
        y_before = pdf.get_y()

        # ID, Sentiment, Score as normal cells
        pdf.cell(id_w, 7, idcell, border=1)
        pdf.cell(sent_w, 7, sentiment, border=1)
        pdf.cell(score_w, 7, score_str, border=1)

        # Summary: use multi_cell with border; multi_cell moves to next line automatically.
        # To ensure the top border aligns, we set x to current position
        pdf.multi_cell(summary_w, 7, summary, border=1)

        # FPDF after multi_cell moves cursor to start of next line; continue loop

    # Output bytes
    content = pdf.output(dest="S").encode("latin-1")
    return content

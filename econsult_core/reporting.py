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
import streamlit as st

@st.cache_data
def generate_wordcloud(texts, max_words=150):
    combined = " ".join([t for t in texts if t])
    wc = WordCloud(width=900, height=450, background_color="white", max_words=max_words)
    arr = wc.generate(combined).to_array()
    img = Image.fromarray(arr)
    return img

def top_keywords(texts: List[str], top_n: int = 25) -> List[Tuple[str,int]]:
    combined = " ".join([t.lower() for t in texts if t])
    tokens = re.findall(r"\b[a-zA-Z]{3,}\b", combined)
    stop = set([
        "the","and","for","with","that","this","from","shall","may","will","not","are","have",
        "were","been","paragraph","section","clause","proposed","draft","stakeholder","please","would","could"
    ])
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

class StyledPDF(FPDF):
    """
    Small subclass to provide a footer with page numbers and a nicer default margin.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # register page alias for total-page numbers
        self.alias_nb_pages()
    def footer(self):
        # position at 15 mm from bottom
        self.set_y(-15)
        self.set_font("Helvetica", size=9)
        self.set_text_color(100, 100, 100)
        # centered page number
        page_str = f"Page {self.page_no()} of {{nb}}"
        self.cell(0, 10, page_str, align="C")

def make_pdf_report(df: pd.DataFrame,
                    wordcloud_img: Image.Image,
                    title: str = "eConsultation Report",
                    project_logo_path: Optional[str] = None,
                    team_logo_path: Optional[str] = None) -> bytes:
    """
    Build a well-formatted PDF with improved typography and layout.
    - Title + timestamp
    - Optional project & team logos in header
    - Word cloud (full width)
    - Keyword section
    - Table with ID / Sentiment / Score / Summary (summary wraps)
    - Footer with page numbers
    Returns PDF bytes.
    """
    pdf = StyledPDF(unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=14)
    pdf.add_page()

    # ----- Header: logos -----
    left_margin = pdf.l_margin
    logo_max_w = 36  # mm
    logo_max_h = 18  # mm

    # left logo
    if project_logo_path and os.path.exists(project_logo_path):
        try:
            pdf.image(project_logo_path, x=left_margin, y=10, w=logo_max_w)
        except Exception:
            pass

    # right logo
    if team_logo_path and os.path.exists(team_logo_path):
        try:
            x_right = pdf.w - pdf.r_margin - logo_max_w
            pdf.image(team_logo_path, x=x_right, y=10, w=logo_max_w)
        except Exception:
            pass

    # ----- Title & meta -----
    # Move cursor below logos
    pdf.set_xy(left_margin, 10 + logo_max_h + 2)
    pdf.set_font("Helvetica", style="B", size=16)
    pdf.set_text_color(20, 20, 20)
    pdf.cell(0, 8, title, ln=True)

    pdf.set_font("Helvetica", size=10)
    pdf.set_text_color(90, 90, 90)
    pdf.cell(0, 6, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=True)
    pdf.ln(4)

    # ----- Wordcloud (fit to page width) -----
    try:
        wc_path = _save_pil_to_tempfile(wordcloud_img, suffix=".png")
        usable_w = pdf.w - pdf.l_margin - pdf.r_margin
        # keep some top padding
        pdf.image(wc_path, x=pdf.l_margin, w=usable_w)
        pdf.ln(6)
    except Exception:
        wc_path = None
    finally:
        if wc_path and os.path.exists(wc_path):
            try:
                os.unlink(wc_path)
            except Exception:
                pass

    # ----- Keywords -----
    pdf.set_font("Helvetica", style="B", size=11)
    pdf.set_text_color(30, 30, 30)
    pdf.cell(0, 7, "Top Keywords", ln=True)
    pdf.ln(2)
    pdf.set_font("Helvetica", size=10)
    kws = top_keywords(df["clean_text"].tolist(), top_n=40) if "clean_text" in df.columns else []
    # write keywords nicely (3 columns)
    col_w = (pdf.w - pdf.l_margin - pdf.r_margin) / 3
    for i in range(0, len(kws), 3):
        row_items = []
        for j in range(3):
            if i + j < len(kws):
                k, c = kws[i + j]
                row_items.append(f"{k} ({c})")
            else:
                row_items.append("")
        pdf.cell(col_w, 6, row_items[0], border=0)
        pdf.cell(col_w, 6, row_items[1], border=0)
        pdf.cell(col_w, 6, row_items[2], border=0, ln=True)
    pdf.ln(6)

    # ----- Results Table -----
    pdf.set_font("Helvetica", style="B", size=11)
    # define column widths that collectively fit the page
    id_w = 18
    sentiment_w = 34
    score_w = 20
    summary_w = pdf.w - pdf.l_margin - pdf.r_margin - (id_w + sentiment_w + score_w)

    # header styling
    pdf.set_fill_color(40, 116, 166)  # pleasant blue
    pdf.set_text_color(255, 255, 255)
    pdf.cell(id_w, 9, "ID", border=1, ln=0, align="C", fill=True)
    pdf.cell(sentiment_w, 9, "Sentiment", border=1, ln=0, align="C", fill=True)
    pdf.cell(score_w, 9, "Score", border=1, ln=0, align="C", fill=True)
    pdf.cell(summary_w, 9, "Summary (truncated)", border=1, ln=1, align="C", fill=True)

    # body rows
    pdf.set_font("Helvetica", size=10)
    pdf.set_text_color(20, 20, 20)
    row_h = 6  # base height for summary line; multi_cell will wrap as needed

    # iterate rows and write with multi_cell for summary
    for _, row in df.iterrows():
        idcell = str(row.get("id", ""))
        sentiment = str(row.get("sentiment", ""))
        score_val = row.get("score", "")
        try:
            score_str = f"{float(score_val):.2f}" if score_val != "" else ""
        except Exception:
            score_str = str(score_val)

        summary = str(row.get("summary", "")).replace("\n", " ")
        if len(summary) > 1200:
            summary = summary[:1197] + "..."

        # write fixed cells for ID, Sentiment, Score
        pdf.cell(id_w, row_h, idcell, border=1)
        pdf.cell(sentiment_w, row_h, sentiment, border=1)
        pdf.cell(score_w, row_h, score_str, border=1)

        # summary via multi_cell: create a cell with border and wrapped text.
        # Save current position to move to next line correctly after multi_cell
        x_before = pdf.get_x()
        y_before = pdf.get_y()

        # Make a multi_cell in the remaining width
        pdf.multi_cell(summary_w, row_h, summary, border=1)
        # after multi_cell, cursor is at start of next line; continue loop

    # Final output
    content = pdf.output(dest="S").encode("latin-1")
    return content

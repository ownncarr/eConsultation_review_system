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
    try:
        img.save(tmp.name)
    finally:
        tmp.close()
    return tmp.name

class StyledPDF(FPDF):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.alias_nb_pages()
    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", size=9)
        self.set_text_color(100, 100, 100)
        page_str = f"Page {self.page_no()} of {{nb}}"
        self.cell(0, 10, page_str, align="C")

def _draw_table_header(pdf: StyledPDF, id_w: float, sentiment_w: float, score_w: float, summary_w: float):
    pdf.set_font("Helvetica", style="B", size=11)
    pdf.set_fill_color(40, 116, 166)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(id_w, 9, "ID", border=1, ln=0, align="C", fill=True)
    pdf.cell(sentiment_w, 9, "Sentiment", border=1, ln=0, align="C", fill=True)
    pdf.cell(score_w, 9, "Score", border=1, ln=0, align="C", fill=True)
    pdf.cell(summary_w, 9, "Summary (truncated)", border=1, ln=1, align="C", fill=True)
    pdf.set_text_color(20, 20, 20)
    pdf.set_font("Helvetica", size=10)

def _wrap_text_to_width(pdf: StyledPDF, text: str, col_width: float) -> List[str]:
    if text is None:
        return [""]
    text = str(text).replace("\r", " ").replace("\n", " ")
    words = re.split(r'(\s+)', text)
    space_w = pdf.get_string_width(" ")
    lines: List[str] = []
    cur_line = ""
    cur_width = 0.0

    def flush_line():
        nonlocal cur_line, cur_width
        lines.append(cur_line.rstrip())
        cur_line = ""
        cur_width = 0.0

    for token in words:
        if token.isspace():
            if cur_line:
                cur_line += " "
                cur_width += space_w
            continue
        word = token
        word_w = pdf.get_string_width(word)
        if cur_line:
            if cur_width + space_w + word_w <= col_width:
                cur_line += word
                cur_width += space_w + word_w
            else:
                flush_line()
                if word_w <= col_width:
                    cur_line = word
                    cur_width = word_w
                else:
                    start = 0
                    while start < len(word):
                        end = start + 1
                        while end <= len(word) and pdf.get_string_width(word[start:end]) <= col_width:
                            end += 1
                        end -= 1
                        if end == start:
                            end = start + 1
                        chunk = word[start:end]
                        lines.append(chunk)
                        start = end
                    cur_line = ""
                    cur_width = 0.0
        else:
            if word_w <= col_width:
                cur_line = word
                cur_width = word_w
            else:
                start = 0
                while start < len(word):
                    end = start + 1
                    while end <= len(word) and pdf.get_string_width(word[start:end]) <= col_width:
                        end += 1
                    end -= 1
                    if end == start:
                        end = start + 1
                    chunk = word[start:end]
                    lines.append(chunk)
                    start = end
                cur_line = ""
                cur_width = 0.0

    if cur_line:
        lines.append(cur_line.rstrip())

    if not lines:
        return [""]
    return lines

def make_pdf_report(df: pd.DataFrame,
                    wordcloud_img: Optional[Image.Image],
                    title: str = "eConsultation Report",
                    project_logo_path: Optional[str] = None,
                    team_logo_path: Optional[str] = None,
                    max_summary_lines: int = 12) -> bytes:
    pdf = StyledPDF(unit="mm", format="A4")
    pdf.set_auto_page_break(auto=False)
    pdf.add_page()

    left_margin = pdf.l_margin
    logo_max_w = 36
    logo_max_h = 18

    if project_logo_path and os.path.exists(project_logo_path):
        try:
            pdf.image(project_logo_path, x=left_margin, y=10, w=logo_max_w)
        except Exception:
            pass

    if team_logo_path and os.path.exists(team_logo_path):
        try:
            x_right = pdf.w - pdf.r_margin - logo_max_w
            pdf.image(team_logo_path, x=x_right, y=10, w=logo_max_w)
        except Exception:
            pass

    pdf.set_xy(left_margin, 10 + logo_max_h + 2)
    pdf.set_font("Helvetica", style="B", size=16)
    pdf.set_text_color(20, 20, 20)
    pdf.cell(0, 8, title, ln=True)

    pdf.set_font("Helvetica", size=10)
    pdf.set_text_color(90, 90, 90)
    pdf.cell(0, 6, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=True)
    pdf.ln(4)

    wc_path = None
    try:
        if wordcloud_img is not None:
            wc_path = _save_pil_to_tempfile(wordcloud_img, suffix=".png")
            usable_w = pdf.w - pdf.l_margin - pdf.r_margin
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

    pdf.set_font("Helvetica", style="B", size=11)
    pdf.set_text_color(30, 30, 30)
    pdf.cell(0, 7, "Top Keywords", ln=True)
    pdf.ln(2)
    pdf.set_font("Helvetica", size=10)
    kws = top_keywords(df["clean_text"].tolist(), top_n=40) if "clean_text" in df.columns else []
    col_w = (pdf.w - pdf.l_margin - pdf.r_margin) / 3
    for i in range(0, len(kws), 3):
        vals = []
        for j in range(3):
            if i + j < len(kws):
                k, c = kws[i + j]
                vals.append(f"{k} ({c})")
            else:
                vals.append("")
        pdf.cell(col_w, 6, vals[0], border=0)
        pdf.cell(col_w, 6, vals[1], border=0)
        pdf.cell(col_w, 6, vals[2], border=0, ln=1)
    pdf.ln(6)

    id_w = 18
    sentiment_w = 34
    score_w = 20
    summary_w = pdf.w - pdf.l_margin - pdf.r_margin - (id_w + sentiment_w + score_w)

    _draw_table_header(pdf, id_w, sentiment_w, score_w, summary_w)

    row_h = 6
    bottom_limit = pdf.h - pdf.b_margin - 8

    pdf.set_font("Helvetica", size=10)
    pdf.set_text_color(20, 20, 20)

    for _, row in df.iterrows():
        idcell = str(row.get("id", ""))
        sentiment = str(row.get("sentiment", ""))
        score_val = row.get("score", "")
        try:
            score_str = f"{float(score_val):.2f}" if score_val != "" else ""
        except Exception:
            score_str = str(score_val)

        summary = str(row.get("summary", "")).replace("\n", " ")
        if len(summary) > 5000:
            summary = summary[:4997] + "..."

        # wrap into lines
        lines = _wrap_text_to_width(pdf, summary, summary_w - 1.0)
        if len(lines) > max_summary_lines:
            lines = lines[:max_summary_lines]
            if len(lines[-1]) > 10:
                lines[-1] = lines[-1].rstrip() + " ... (truncated)"
            else:
                lines[-1] = lines[-1] + " ... (truncated)"

        required_h = max(row_h, len(lines) * row_h)

        current_y = pdf.get_y()
        if current_y + required_h > bottom_limit:
            pdf.add_page()
            _draw_table_header(pdf, id_w, sentiment_w, score_w, summary_w)

        # starting x,y for this row
        x0 = pdf.get_x()
        y0 = pdf.get_y()

        # fixed cells
        pdf.cell(id_w, required_h, idcell, border=1)
        pdf.cell(sentiment_w, required_h, sentiment, border=1)
        pdf.cell(score_w, required_h, score_str, border=1)

        # summary area position
        x_summary = pdf.get_x()
        y_summary = y0

        # write summary text inside the cell without internal borders
        pdf.set_xy(x_summary, y_summary)
        # join lines with newline so multi_cell writes them in one call
        pdf.multi_cell(summary_w, row_h, "\n".join(lines), border=0)

        # draw a single rectangle border around the summary area so it matches other cells
        pdf.rect(x_summary, y_summary, summary_w, required_h)

        # move cursor to start of next row (left margin, y_summary + required_h)
        pdf.set_xy(pdf.l_margin, y_summary + required_h)

    # finalize
    output = pdf.output(dest="S")
    if isinstance(output, bytearray):
        content = bytes(output)
    elif isinstance(output, bytes):
        content = output
    elif isinstance(output, str):
        content = output.encode("latin-1")
    else:
        content = str(output).encode("latin-1")

    return content

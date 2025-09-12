# app_pyqt.py
"""
PyQt5 desktop app for eConsult AI Reviewer.
Features: Live input, CSV upload, analyze (sentiment + summary), word cloud preview, export PDF.
Developer constants at top for tuning.
"""

import sys, os, re, tempfile
from datetime import datetime
from typing import List, Tuple

from PyQt5 import QtCore, QtWidgets, QtGui
import pandas as pd
from transformers import pipeline
from wordcloud import WordCloud
from fpdf import FPDF
from PIL import Image

# ----------------- DEVELOPER-CONFIG (developer-only) -----------------
NEUTRAL_THRESHOLD = 0.70
SENTIMENT_MODEL = "distilbert-base-uncased-finetuned-sst-2-english"
SUMMARIZER_MODEL = "t5-small"
MAX_CHUNK_CHARS = 400
# -------------------------------------------------------------------

def clean_text(text: str) -> str:
    if not isinstance(text, str): return ""
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def chunk_text(text: str, max_chars: int = MAX_CHUNK_CHARS):
    text = text.strip()
    if len(text) <= max_chars: return [text]
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + max_chars, len(text))
        if end < len(text):
            next_dot = text.rfind(".", start, end)
            if next_dot > start + 20:
                end = next_dot + 1
        chunks.append(text[start:end].strip())
        start = end
    return chunks

def summarize_text(summarizer, text: str) -> str:
    text = clean_text(text)
    if not text:
        return ""
    chunks = chunk_text(text)
    summaries = []
    for c in chunks:
        try:
            out = summarizer(c, max_length=60, min_length=15, truncation=True)
            summaries.append(out[0]['summary_text'])
        except Exception:
            summaries.append((c[:200] + ("..." if len(c) > 200 else "")))
    if len(summaries) == 1:
        return summaries[0]
    combined = " ".join(summaries)
    try:
        out2 = summarizer(combined, max_length=80, min_length=20, truncation=True)
        return out2[0]['summary_text']
    except Exception:
        return " ".join(summaries)

def map_sentiment(raw_label: str, score: float, neutral_threshold: float = NEUTRAL_THRESHOLD) -> Tuple[str, float]:
    label = raw_label.upper()
    if score < neutral_threshold:
        return "Neutral", float(score)
    return ("Positive", float(score)) if label.startswith("POS") else ("Negative", float(score))

def generate_wordcloud_image(texts: List[str], path: str):
    combined = " ".join(texts)
    wc = WordCloud(width=900, height=450, background_color="white", max_words=150)
    wc.generate(combined)
    wc.to_file(path)

def make_pdf_report(df: pd.DataFrame, wc_path: str, title: str = "eConsultation Report"):
    pdf = FPDF(unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=12)
    pdf.add_page()
    pdf.set_font("Arial", size=14, style="B")
    pdf.cell(0, 8, title, ln=True)
    pdf.set_font("Arial", size=10)
    pdf.cell(0, 6, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=True)
    pdf.ln(4)
    pdf.image(wc_path, x=15, w=180)
    pdf.ln(6)
    pdf.set_font("Arial", size=11, style="B")
    pdf.cell(30, 7, "ID", border=1)
    pdf.cell(35, 7, "Sentiment", border=1)
    pdf.cell(120, 7, "Summary (truncated)", border=1, ln=True)
    pdf.set_font("Arial", size=10)
    for _, row in df.iterrows():
        idcell = str(row.get("id", ""))
        sentiment = str(row.get("sentiment", ""))
        summary = str(row.get("summary", "")).replace("\n", " ")
        if len(summary) > 150: summary = summary[:147] + "..."
        pdf.cell(30, 7, idcell, border=1)
        pdf.cell(35, 7, sentiment, border=1)
        pdf.cell(120, 7, summary, border=1, ln=True)
    return pdf.output(dest='S').encode('latin-1')

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("eConsultation AI Reviewer — Desktop")
        self.resize(1100, 700)
        # Central widget
        container = QtWidgets.QWidget()
        self.setCentralWidget(container)
        layout = QtWidgets.QVBoxLayout(container)

        # Top panel: mode tabs
        tabs = QtWidgets.QTabWidget()
        layout.addWidget(tabs)

        # Live tab
        live_tab = QtWidgets.QWidget()
        live_layout = QtWidgets.QVBoxLayout(live_tab)
        self.live_text = QtWidgets.QPlainTextEdit()
        self.live_text.setPlaceholderText("Type/paste comments. Separate comments by a blank line.")
        live_layout.addWidget(self.live_text)
        self.btn_analyze_live = QtWidgets.QPushButton("Analyze Live Input")
        self.btn_analyze_live.clicked.connect(self.analyze_live)
        live_layout.addWidget(self.btn_analyze_live)
        tabs.addTab(live_tab, "Live Demo")

        # Dataset tab
        data_tab = QtWidgets.QWidget()
        data_layout = QtWidgets.QVBoxLayout(data_tab)
        h = QtWidgets.QHBoxLayout()
        self.btn_load_csv = QtWidgets.QPushButton("Load CSV/Excel")
        self.btn_load_csv.clicked.connect(self.load_csv)
        h.addWidget(self.btn_load_csv)
        self.lbl_file = QtWidgets.QLabel("No file loaded")
        h.addWidget(self.lbl_file)
        h.addStretch()
        data_layout.addLayout(h)
        self.btn_analyze_file = QtWidgets.QPushButton("Analyze Dataset")
        self.btn_analyze_file.clicked.connect(self.analyze_file)
        data_layout.addWidget(self.btn_analyze_file)
        tabs.addTab(data_tab, "Dataset Mode")

        # Results split: left table, right wordcloud + keywords
        split = QtWidgets.QSplitter()
        layout.addWidget(split)
        # left: table
        left_widget = QtWidgets.QWidget()
        left_layout = QtWidgets.QVBoxLayout(left_widget)
        self.table = QtWidgets.QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["ID", "Comment", "Sentiment", "Summary"])
        self.table.horizontalHeader().setStretchLastSection(True)
        left_layout.addWidget(self.table)
        self.btn_export_csv = QtWidgets.QPushButton("Export Results CSV")
        self.btn_export_csv.clicked.connect(self.export_csv)
        left_layout.addWidget(self.btn_export_csv)
        split.addWidget(left_widget)

        # right: wordcloud image and keywords
        right_widget = QtWidgets.QWidget()
        right_layout = QtWidgets.QVBoxLayout(right_widget)
        self.lbl_wc = QtWidgets.QLabel()
        self.lbl_wc.setFixedHeight(300)
        self.lbl_wc.setAlignment(QtCore.Qt.AlignCenter)
        right_layout.addWidget(self.lbl_wc)
        self.lst_keywords = QtWidgets.QListWidget()
        right_layout.addWidget(self.lst_keywords)
        self.btn_export_pdf = QtWidgets.QPushButton("Export PDF Report")
        self.btn_export_pdf.clicked.connect(self.export_pdf)
        right_layout.addWidget(self.btn_export_pdf)
        split.addWidget(right_widget)
        split.setStretchFactor(0, 3)
        split.setStretchFactor(1, 2)

        # status bar
        self.status = QtWidgets.QStatusBar()
        self.setStatusBar(self.status)

        # model placeholders
        self.sentiment_pipe = None
        self.summarizer = None
        self.loaded_df = None
        self.results_df = None
        self.wc_path = None

        self._load_models_async()

    def _load_models_async(self):
        self.status.showMessage("Loading models — please wait (first run may take a while)...")
        QtCore.QTimer.singleShot(100, self._load_models)

    def _load_models(self):
        self.sentiment_pipe = pipeline("sentiment-analysis", model=SENTIMENT_MODEL)
        self.summarizer = pipeline("summarization", model=SUMMARIZER_MODEL, tokenizer=SUMMARIZER_MODEL)
        self.status.showMessage("Models loaded. Ready.")

    def analyze_live(self):
        text = self.live_text.toPlainText().strip()
        if not text:
            QtWidgets.QMessageBox.warning(self, "No input", "Please enter at least one comment.")
            return
        comments = [c.strip() for c in re.split(r"\n{1,}", text) if c.strip()]
        self._run_analysis(comments, ids=[str(i+1) for i in range(len(comments))])

    def load_csv(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Open CSV/Excel", filter="CSV (*.csv);;Excel (*.xlsx);;All Files (*)")
        if not path: return
        self.lbl_file.setText(path)
        try:
            if path.lower().endswith(".xlsx"):
                self.loaded_df = pd.read_excel(path)
            else:
                self.loaded_df = pd.read_csv(path)
            self.status.showMessage(f"Loaded {len(self.loaded_df)} rows.")
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Read error", str(e))
            self.loaded_df = None

    def analyze_file(self):
        if self.loaded_df is None:
            QtWidgets.QMessageBox.warning(self, "No file", "Please load a dataset first.")
            return
        if "submission_text" not in self.loaded_df.columns:
            QtWidgets.QMessageBox.critical(self, "Invalid file", "CSV must contain a 'submission_text' column.")
            return
        comments = self.loaded_df['submission_text'].astype(str).tolist()
        ids = self.loaded_df['id'].astype(str).tolist() if 'id' in self.loaded_df.columns else [str(i+1) for i in range(len(comments))]
        self._run_analysis(comments, ids=ids)

    def _run_analysis(self, comments: List[str], ids: List[str]):
        self.status.showMessage("Analyzing — please wait...")
        QtWidgets.QApplication.processEvents()
        processed = []
        cleaned_texts = []
        for cid, txt in zip(ids, comments):
            ct = clean_text(txt)
            cleaned_texts.append(ct)
            try:
                sraw = self.sentiment_pipe(ct[:512])[0]
                sentiment_label, score = map_sentiment(sraw['label'], float(sraw['score']))
            except Exception:
                sentiment_label, score = "Neutral", 0.0
            summary = summarize_text(self.summarizer, ct)
            processed.append({"id": cid, "submission_text": txt, "clean_text": ct, "sentiment": sentiment_label, "score": score, "summary": summary})
        self.results_df = pd.DataFrame(processed)
        # populate table
        self.table.setRowCount(0)
        for i, row in self.results_df.iterrows():
            r = self.table.rowCount()
            self.table.insertRow(r)
            self.table.setItem(r, 0, QtWidgets.QTableWidgetItem(str(row['id'])))
            self.table.setItem(r, 1, QtWidgets.QTableWidgetItem(str(row['submission_text'])))
            self.table.setItem(r, 2, QtWidgets.QTableWidgetItem(str(row['sentiment'])))
            self.table.setItem(r, 3, QtWidgets.QTableWidgetItem(str(row['summary'])))
        # wordcloud
        tmp_wc = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
        generate_wordcloud_image(cleaned_texts, tmp_wc.name)
        self.wc_path = tmp_wc.name
        pix = QtGui.QPixmap(self.wc_path)
        scaled = pix.scaled(self.lbl_wc.width(), self.lbl_wc.height(), QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
        self.lbl_wc.setPixmap(scaled)
        # top keywords
        self.lst_keywords.clear()
        # derive keywords (simple)
        combined = " ".join(cleaned_texts).lower()
        tokens = re.findall(r"\b[a-zA-Z]{3,}\b", combined)
        stop = set(["the","and","for","with","that","this","from","shall","may","will","not","are","have","were","been","paragraph","section","clause","proposed","draft","stakeholder"])
        freqs = {}
        for t in tokens:
            if t in stop: continue
            freqs[t] = freqs.get(t, 0) + 1
        items = sorted(freqs.items(), key=lambda x: x[1], reverse=True)[:25]
        for k,v in items:
            self.lst_keywords.addItem(f"{k} — {v}")
        self.status.showMessage("Analysis complete.")

    def export_csv(self):
        if self.results_df is None:
            QtWidgets.QMessageBox.warning(self, "No results", "No results to export.")
            return
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save results CSV", filter="CSV (*.csv)")
        if not path: return
        self.results_df.to_csv(path, index=False)
        QtWidgets.QMessageBox.information(self, "Saved", f"Results saved to {path}")

    def export_pdf(self):
        if self.results_df is None or self.wc_path is None:
            QtWidgets.QMessageBox.warning(self, "No data", "Run analysis first.")
            return
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save PDF report", filter="PDF (*.pdf)")
        if not path: return
        pdf_bytes = make_pdf_report(self.results_df, self.wc_path, title="eConsultation Report")
        with open(path, "wb") as f:
            f.write(pdf_bytes)
        QtWidgets.QMessageBox.information(self, "Saved", f"PDF report saved to {path}")

def main():
    app = QtWidgets.QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()

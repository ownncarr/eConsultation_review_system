# app.py
import io
import os
import math
from typing import List, Tuple
from pathlib import Path
from datetime import datetime
import tempfile

import streamlit as st
import pandas as pd
from transformers import pipeline
from wordcloud import WordCloud
from fpdf import FPDF
from PIL import Image
import matplotlib.pyplot as plt
import numpy as np
import re

st.set_page_config(page_title="eConsult AI Reviewer — MVP", layout="wide", page_icon="📝")

# -----------------------
# Helper functions
# -----------------------
@st.cache_resource
def load_models():
    """Load transformer pipelines (cached). Choose compact models for speed on CPU."""
    sentiment_pipe = pipeline("sentiment-analysis", model="distilbert-base-uncased-finetuned-sst-2-english")
    # Use t5-small for faster summaries (if you have GPU swap to larger model)
    summarizer = pipeline("summarization", model="t5-small", tokenizer="t5-small")
    return sentiment_pipe, summarizer

def clean_text(text: str) -> str:
    if not isinstance(text, str):
        return ""
    # remove HTML, multiple whitespace
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def chunk_text(text: str, max_chars: int = 400):
    # naive chunk by chars to avoid excessive tokens; keep splits on sentence-like boundaries if possible
    text = text.strip()
    if len(text) <= max_chars:
        return [text]
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + max_chars, len(text))
        # try to expand end until punctuation if possible (to keep sentences intact)
        if end < len(text):
            next_dot = text.rfind(".", start, end)
            if next_dot > start + 20:  # a reasonable boundary
                end = next_dot + 1
        chunks.append(text[start:end].strip())
        start = end
    return chunks

def summarize_text(summarizer, text: str) -> str:
    text = clean_text(text)
    if not text:
        return ""
    chunks = chunk_text(text, max_chars=400)
    # summarize each chunk then combine (if multiple)
    summaries = []
    for c in chunks:
        try:
            out = summarizer(c, max_length=60, min_length=15, truncation=True)
            summaries.append(out[0]['summary_text'])
        except Exception as e:
            # fallback to short slice if summarizer fails
            summaries.append((c[:200] + ("..." if len(c) > 200 else "")))
    if len(summaries) == 1:
        return summaries[0]
    # combine and summarize again if multiple
    combined = " ".join(summaries)
    try:
        out2 = summarizer(combined, max_length=80, min_length=20, truncation=True)
        return out2[0]['summary_text']
    except Exception:
        # join chunk-summaries
        return " ".join(summaries)

def map_sentiment(raw_label: str, score: float, neutral_threshold: float = 0.7) -> Tuple[str, float]:
    """
    Map pipeline label into Positive / Neutral / Negative.
    If model confidence < neutral_threshold -> Neutral
    """
    label = raw_label.upper()
    if score < neutral_threshold:
        return "Neutral", float(score)
    if label.startswith("POS"):
        return "Positive", float(score)
    else:
        return "Negative", float(score)

def generate_wordcloud(texts: List[str], max_words: int = 150) -> Image.Image:
    combined = " ".join(texts)
    wc = WordCloud(width=900, height=450, background_color="white", max_words=max_words)
    arr = wc.generate(combined).to_array()
    img = Image.fromarray(arr)
    return img

def top_keywords(texts: List[str], top_n: int = 25):
    combined = " ".join(texts).lower()
    # simple tokenization
    tokens = re.findall(r"\b[a-zA-Z]{3,}\b", combined)
    # remove common stopwords (small list; extend if needed)
    stop = set([
        "the","and","for","with","that","this","from","shall","may","will","not","are","have",
        "were","been","paragraph","section","clause","shall","proposed","draft","stakeholder",
    ])
    freqs = {}
    for t in tokens:
        if t in stop: 
            continue
        freqs[t] = freqs.get(t, 0) + 1
    items = sorted(freqs.items(), key=lambda x: x[1], reverse=True)
    return items[:top_n]

def make_pdf_report(df: pd.DataFrame, wordcloud_img: Image.Image, title: str = "eConsultation Report"):
    # Prepare a PDF with FPDF
    pdf = FPDF(unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=12)
    pdf.add_page()
    pdf.set_font("Arial", size=14, style="B")
    pdf.cell(0, 8, title, ln=True)
    pdf.set_font("Arial", size=10)
    pdf.cell(0, 6, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=True)
    pdf.ln(4)
    # Insert wordcloud (save temporary)
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    wordcloud_img.save(tmp.name)
    pdf.image(tmp.name, x=15, w=180)
    pdf.ln(6)

    # Add a table-like section: id, sentiment, summary (truncate)
    pdf.set_font("Arial", size=11, style="B")
    pdf.cell(30, 7, "ID", border=1)
    pdf.cell(35, 7, "Sentiment", border=1)
    pdf.cell(120, 7, "Summary (truncated)", border=1, ln=True)
    pdf.set_font("Arial", size=10)
    for _, row in df.iterrows():
        idcell = str(row.get("id", ""))
        sentiment = str(row.get("sentiment", ""))
        summary = str(row.get("summary", "")).replace("\n", " ")
        if len(summary) > 150:
            summary = summary[:147] + "..."
        pdf.cell(30, 7, idcell, border=1)
        pdf.cell(35, 7, sentiment, border=1)
        pdf.cell(120, 7, summary, border=1, ln=True)
        # limit rows per PDF for demo; can add multiple pages
    # cleanup
    tmp.close()
    content = pdf.output(dest='S').encode('latin-1')
    try:
        os.unlink(tmp.name)
    except Exception:
        pass
    return content

# -----------------------
# App layout
# -----------------------
st.title("📝 eConsult AI Reviewer — MVP")
st.markdown(
    """
A minimal Streamlit demo that analyzes stakeholder comments (sentiment, 1–2 line summary, and word cloud).
Two modes: **Live Demo** (type/paste comments interactively) and **Dataset Mode** (upload CSV).
PDF report is downloadable.
"""
)

models_load_state = st.info("Loading models (this may take 10-30s on first run)...")
sentiment_pipe, summarizer = load_models()
models_load_state.empty()

# Sidebar controls
st.sidebar.header("Options")
mode = st.sidebar.selectbox("Mode", ["Live Demo", "Dataset Mode"])
neutral_threshold = st.sidebar.slider("Neutral confidence threshold", min_value=0.5, max_value=0.95, value=0.70, step=0.05)
max_preview_rows = st.sidebar.slider("Max rows to show in preview", 5, 200, 50)

# Main work area
if mode == "Live Demo":
    st.subheader("Live Demo — add a single comment or multiple (one per line)")
    user_text = st.text_area("Paste or type comments (one per line). Use SHIFT+ENTER for new line within a comment.", height=180)
    if st.button("Analyze Live Input"):
        if not user_text.strip():
            st.warning("Please enter at least one comment.")
        else:
            # split by blank line or newline as separate comments (keep non-empty)
            raw_comments = [c.strip() for c in re.split(r"\n{1,}", user_text) if c.strip()]
            df = pd.DataFrame({"id": list(range(1, len(raw_comments)+1)), "submission_text": raw_comments})
            with st.spinner("Analyzing comments..."):
                processed = []
                cleaned_texts = []
                for i, txt in enumerate(df['submission_text'].tolist()):
                    ct = clean_text(txt)
                    cleaned_texts.append(ct)
                    # sentiment
                    try:
                        sraw = sentiment_pipe(ct[:512])[0]
                        sentiment_label, score = map_sentiment(sraw['label'], float(sraw['score']), neutral_threshold)
                    except Exception as e:
                        sentiment_label, score = "Neutral", 0.0
                    # summary
                    summary = summarize_text(summarizer, ct)
                    processed.append({"id": df.loc[i, "id"], "submission_text": txt, "clean_text": ct, "sentiment": sentiment_label, "score": score, "summary": summary})
                out_df = pd.DataFrame(processed)
                # Wordcloud and keywords
                wc_img = generate_wordcloud(cleaned_texts)
                kws = top_keywords(cleaned_texts, top_n=25)
            # Show results
            st.success(f"Analyzed {len(out_df)} comments.")
            col1, col2 = st.columns([2,1])
            with col1:
                st.dataframe(out_df[["id","submission_text","sentiment","score","summary"]].rename(columns={"submission_text":"comment"}).head(max_preview_rows))
                st.download_button("Download results CSV", data=out_df.to_csv(index=False).encode('utf-8'), file_name="analysis_results.csv", mime="text/csv")
            with col2:
                st.image(wc_img, use_column_width=True, caption="Word Cloud")
                st.write("Top keywords:")
                st.table(pd.DataFrame(kws, columns=["keyword","count"]).head(15))
            # PDF download
            pdf_bytes = make_pdf_report(out_df, wc_img, title="eConsultation Live Demo Report")
            st.download_button("Download PDF report", data=pdf_bytes, file_name="econsult_report_live.pdf", mime="application/pdf")

elif mode == "Dataset Mode":
    st.subheader("Dataset Mode — upload CSV (columns: id (optional), submission_text, stakeholder_type (optional))")
    uploaded = st.file_uploader("Upload CSV file", type=["csv","txt","xlsx"])
    show_sample = st.checkbox("See sample CSV format")
    if show_sample:
        st.markdown("**Sample CSV content**")
        st.code(
"""id,submission_text,stakeholder_type
1,"We support the amendment but suggest clarifying clause 3.",Industry
2,"This will hurt MSMEs — strongly oppose.",SME
3,"Neutral: looks fine but add timeline.",Citizen
"""
        )
    if uploaded is not None:
        # read file
        try:
            if uploaded.name.lower().endswith(".xlsx"):
                df_in = pd.read_excel(uploaded)
            else:
                df_in = pd.read_csv(uploaded)
        except Exception as e:
            st.error(f"Could not read file: {e}")
            st.stop()
        if "submission_text" not in df_in.columns:
            st.error("CSV must contain a 'submission_text' column.")
            st.stop()
        # preview
        st.write(f"Uploaded {len(df_in)} rows.")
        st.dataframe(df_in.head(max_preview_rows))
        if st.button("Analyze dataset"):
            with st.spinner("Processing dataset (this may take a while depending on size)..."):
                comments = df_in['submission_text'].astype(str).tolist()
                ids = df_in['id'].astype(str).tolist() if 'id' in df_in.columns else [str(i+1) for i in range(len(comments))]
                processed = []
                cleaned_texts = []
                for i, (cid, txt) in enumerate(zip(ids, comments)):
                    ct = clean_text(txt)
                    cleaned_texts.append(ct)
                    try:
                        sraw = sentiment_pipe(ct[:512])[0]
                        sentiment_label, score = map_sentiment(sraw['label'], float(sraw['score']), neutral_threshold)
                    except Exception as e:
                        sentiment_label, score = "Neutral", 0.0
                    summary = summarize_text(summarizer, ct)
                    processed.append({"id": cid, "submission_text": txt, "clean_text": ct, "sentiment": sentiment_label, "score": score, "summary": summary})
                out_df = pd.DataFrame(processed)
                wc_img = generate_wordcloud(cleaned_texts)
                kws = top_keywords(cleaned_texts, top_n=30)
            st.success("Analysis complete.")
            # show sentiment distribution
            st.markdown("### Sentiment distribution")
            dist = out_df['sentiment'].value_counts().reindex(["Positive","Neutral","Negative"]).fillna(0)
            st.bar_chart(dist)
            # results table
            st.subheader("Results")
            st.dataframe(out_df[["id","submission_text","sentiment","score","summary"]].rename(columns={"submission_text":"comment"}).head(max_preview_rows))
            # full download
            st.download_button("Download results CSV", data=out_df.to_csv(index=False).encode('utf-8'), file_name="analysis_results.csv", mime="text/csv")
            st.image(wc_img, use_column_width=True, caption="Word Cloud")
            st.write("Top keywords:")
            st.table(pd.DataFrame(kws, columns=["keyword","count"]).head(20))
            # PDF
            pdf_bytes = make_pdf_report(out_df, wc_img, title="eConsultation Dataset Report")
            st.download_button("Download PDF report", data=pdf_bytes, file_name="econsult_report_dataset.pdf", mime="application/pdf")

# Footer notes
st.markdown("---")
st.caption("MVP note: models are general-purpose transformers. Domain fine-tuning and multilingual support can be added next. For large datasets or production, run inference in background workers and use GPU for faster summarization.")

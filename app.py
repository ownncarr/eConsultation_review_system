# app.py
import io
import re
from io import BytesIO
from typing import List
from datetime import datetime
import os

import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt

from econsult_core import models, preprocessing, reporting
from PIL import Image

st.set_page_config(page_title="eConsult AI Reviewer — MVP", layout="wide", page_icon="📝")

# -----------------------
# Header / Branding (left-aligned logo + name)
# -----------------------
assets_dir = "assets"
project_logo_path = os.path.join(assets_dir, "project_logo.png")  # your project logo (top-left)
team_logo_path = os.path.join(assets_dir, "team_logo.png")        # your team logo (top-right)

col_logo, col_title, col_right = st.columns([1, 8, 1])
with col_logo:
    if os.path.exists(project_logo_path):
        try:
            logo_img = Image.open(project_logo_path)
            st.image(logo_img, width=92)  # adjust size as needed
        except Exception:
            st.write("")  # fallback
    st.markdown("**eConsult AI Reviewer — MVP**")

with col_title:
    st.write("")  # keep title compact (logo + name are shown left)

with col_right:
    if os.path.exists(team_logo_path):
        try:
            tlogo = Image.open(team_logo_path)
            st.image(tlogo, width=86)
        except Exception:
            st.write("")

st.markdown("---")

# -----------------------
# Load models (cached)
# -----------------------
@st.cache_resource
def load_pipelines():
    return models.load_pipelines()

sentiment_pipe, summarizer = load_pipelines()

# -----------------------
# Utility helpers & analysis (unchanged)
# -----------------------
def analyze_texts(texts: List[str], progress_callback=None):
    processed = []
    cleaned_texts = []
    total = len(texts)
    for i, txt in enumerate(texts):
        ct = preprocessing.clean_text(str(txt))
        cleaned_texts.append(ct)
        try:
            sraw = sentiment_pipe(ct[:512])[0]
            label = sraw.get("label") or ""
            score = float(sraw.get("score", 0.0))
        except Exception:
            label, score = "Neutral", 0.0
        sentiment_label, mapped_score = models.map_sentiment(label, score)
        summary = preprocessing.summarize_text(summarizer, ct)
        processed.append({
            "id": str(i+1),
            "submission_text": txt,
            "clean_text": ct,
            "sentiment": sentiment_label,
            "score": mapped_score,
            "summary": summary
        })
        if progress_callback:
            progress_callback(i + 1, total)
    return processed, cleaned_texts

def sentiment_color_label(s):
    if s == "Positive":
        return "🟢 Positive"
    if s == "Neutral":
        return "🟡 Neutral"
    if s == "Negative":
        return "🔴 Negative"
    return s

# -----------------------
# Main UI using Tabs (Live / Dataset / About)
# -----------------------
tabs = st.tabs(["Live Demo", "Dataset Mode", "About / Notes"])

with tabs[0]:
    st.header("Live Demo — quick single-run analysis")
    st.markdown("Paste multiple comments separated by a blank line. Each paragraph becomes a comment.")
    user_text = st.text_area("Comments (separate by a blank line)", height=220, placeholder="Write or paste comments here...")
    analyze_btn = st.button("🔎 Analyze")

    if analyze_btn:
        if not user_text or not user_text.strip():
            st.warning("Please enter at least one comment.")
        else:
            raw_comments = [c.strip() for c in re.split(r"\n\s*\n", user_text) if c.strip()]
            total = len(raw_comments)
            progress_text = st.empty()
            progress_bar = st.progress(0)
            def _progress_cb(done, tot):
                pct = int(done / tot * 100)
                progress_text.info(f"Processing {done}/{tot} — {pct}%")
                progress_bar.progress(pct)
            processed, cleaned_texts = analyze_texts(raw_comments, progress_callback=_progress_cb)
            progress_text.success("Analysis complete.")
            progress_bar.empty()

            out_df = pd.DataFrame(processed)

            # Metrics
            pos = (out_df['sentiment'] == "Positive").sum()
            neu = (out_df['sentiment'] == "Neutral").sum()
            neg = (out_df['sentiment'] == "Negative").sum()
            total = len(out_df)
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Total comments", total)
            col2.metric("Positive", f"{pos} ({pos/total*100:.0f}%)")
            col3.metric("Neutral", f"{neu} ({neu/total*100:.0f}%)")
            col4.metric("Negative", f"{neg} ({neg/total*100:.0f}%)")

            left, right = st.columns([2,1])
            with left:
                st.subheader("Results")
                sentiment_filter = st.selectbox("Filter sentiment", options=["All","Positive","Neutral","Negative"], index=0)
                search_q = st.text_input("Search comments (text)")
                df_show = out_df.copy()
                if sentiment_filter != "All":
                    df_show = df_show[df_show['sentiment'] == sentiment_filter]
                if search_q:
                    df_show = df_show[df_show['submission_text'].str.contains(search_q, case=False, na=False)]
                df_display = df_show[["id","submission_text","sentiment","score","summary"]].rename(columns={"submission_text":"comment"})
                df_display["sentiment_badge"] = df_display["sentiment"].apply(sentiment_color_label)
                st.dataframe(df_display.drop(columns=["sentiment"]).rename(columns={"sentiment_badge":"sentiment"}), use_container_width=True)

            with right:
                st.subheader("Word Cloud")
                wc_img = reporting.generate_wordcloud(cleaned_texts)
                st.image(wc_img, use_column_width=True)
                st.subheader("Top Keywords")
                kws = reporting.top_keywords(cleaned_texts, top_n=25)
                st.table(pd.DataFrame(kws, columns=["keyword","count"]).head(20))

            # PDF file name includes date/time
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            pdf_bytes = reporting.make_pdf_report(out_df, wc_img,
                                                  title="eConsultation Live Demo Report",
                                                  project_logo_path=project_logo_path if os.path.exists(project_logo_path) else None,
                                                  team_logo_path=team_logo_path if os.path.exists(team_logo_path) else None)
            filename = f"econsult_report_{timestamp}.pdf"
            st.download_button("Download PDF report", data=pdf_bytes, file_name=filename, mime="application/pdf")

with tabs[1]:
    st.header("Dataset Mode — upload CSV / XLSX")
    st.markdown("CSV must contain a `submission_text` column. Optional: `id`, `stakeholder_type`.")
    uploaded = st.file_uploader("Upload CSV / XLSX file", type=["csv","xlsx","txt"])

    if uploaded is not None:
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

        st.write(f"Uploaded {len(df_in)} rows.")
        st.dataframe(df_in.head(10))

        analyze_dataset = st.button("🔎 Analyze dataset")
        if analyze_dataset:
            comments = df_in['submission_text'].astype(str).tolist()
            total = len(comments)
            progress_text = st.empty()
            progress_bar = st.progress(0)
            def _progress_cb(done, tot):
                pct = int(done / tot * 100)
                progress_text.info(f"Processing {done}/{tot} — {pct}%")
                progress_bar.progress(pct)
            processed, cleaned_texts = analyze_texts(comments, progress_callback=_progress_cb)
            progress_text.success("Analysis complete.")
            progress_bar.empty()

            out_df = pd.DataFrame(processed)
            pos = (out_df['sentiment'] == "Positive").sum()
            neu = (out_df['sentiment'] == "Neutral").sum()
            neg = (out_df['sentiment'] == "Negative").sum()
            total = len(out_df)
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Total rows", total)
            c2.metric("Positive", f"{pos} ({pos/total*100:.0f}%)")
            c3.metric("Neutral", f"{neu} ({neu/total*100:.0f}%)")
            c4.metric("Negative", f"{neg} ({neg/total*100:.0f}%)")

            st.subheader("Sentiment distribution")
            fig1, ax1 = plt.subplots()
            labels = ["Positive","Neutral","Negative"]
            sizes = [pos, neu, neg]
            if sum(sizes) == 0:
                sizes = [1,1,1]
            ax1.pie(sizes, labels=labels, autopct="%1.1f%%", startangle=90)
            ax1.axis('equal')
            st.pyplot(fig1)

            st.subheader("Results")
            sentiment_filter = st.selectbox("Filter by sentiment", options=["All","Positive","Neutral","Negative"], index=0)
            search_q = st.text_input("Search text")
            df_show = out_df.copy()
            if sentiment_filter != "All":
                df_show = df_show[df_show['sentiment'] == sentiment_filter]
            if search_q:
                df_show = df_show[df_show['submission_text'].str.contains(search_q, case=False, na=False)]
            df_display = df_show[["id","submission_text","sentiment","score","summary"]].rename(columns={"submission_text":"comment"})
            df_display["sentiment_badge"] = df_display["sentiment"].apply(sentiment_color_label)
            st.dataframe(df_display.drop(columns=["sentiment"]).rename(columns={"sentiment_badge":"sentiment"}), use_container_width=True)

            left, right = st.columns([2,1])
            with right:
                st.subheader("Word Cloud")
                wc_img = reporting.generate_wordcloud(cleaned_texts)
                st.image(wc_img, use_column_width=True)
                st.subheader("Top Keywords")
                kws = reporting.top_keywords(cleaned_texts, top_n=40)
                st.table(pd.DataFrame(kws, columns=["keyword","count"]).head(25))
            with left:
                top_k = pd.DataFrame(kws, columns=["keyword","count"]).head(15)
                if not top_k.empty:
                    fig2, ax2 = plt.subplots(figsize=(8,4))
                    ax2.barh(top_k["keyword"][::-1], top_k["count"][::-1])
                    ax2.set_xlabel("Count")
                    ax2.set_title("Top keywords")
                    st.pyplot(fig2)

            # PDF with timestamped filename and logos
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            pdf_bytes = reporting.make_pdf_report(out_df, wc_img,
                                                  title="eConsultation Dataset Report",
                                                  project_logo_path=project_logo_path if os.path.exists(project_logo_path) else None,
                                                  team_logo_path=team_logo_path if os.path.exists(team_logo_path) else None)
            filename = f"econsult_report_{timestamp}.pdf"
            st.download_button("Download PDF report", data=pdf_bytes, file_name=filename, mime="application/pdf")

with tabs[2]:
    st.header("About / Notes")
    st.markdown("""
- Uses transformer summarization and sentiment models (heavier models by default with safe fallbacks).  
- PDF includes project and team logos (if present in `assets/`).  
- The app produces: sentiment analysis, a concise summary, a word cloud, and a word frequency list — available in both Live Demo and Dataset modes.  
""")

st.markdown("---")
st.caption("MVP note: for production, add auth, background workers, better logging and monitoring.")

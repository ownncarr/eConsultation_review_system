import io
import re
from io import BytesIO
from typing import List
from datetime import datetime
import os

import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
from PIL import Image
from econsult_core import models, preprocessing, reporting
from streamlit_option_menu import option_menu

# -----------------------
# Page config
# -----------------------
st.set_page_config(page_title="eConsult AI Reviewer — MVP", layout="wide", page_icon="📝")

# -----------------------
# Sidebar
# -----------------------
assets_dir = "assets"
project_logo_path = os.path.join(assets_dir, "project_logo.png")
team_logo_path = os.path.join(assets_dir, "team_logo.png")

with st.sidebar:
    # Only the logo container, nothing above
    if os.path.exists(project_logo_path):
        try:
            logo_img = Image.open(project_logo_path)
            st.markdown(
                """
                <div style="
                    background: linear-gradient(135deg, #f5e9da 0%, #e9dbc7 100%);
                    border-radius: 24px;
                    padding: 32px 16px 24px 16px;
                    margin-bottom: 18px;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    box-shadow: 0 4px 16px rgba(200, 182, 166, 0.08);
                ">
                """,
                unsafe_allow_html=True
            )
            st.image(logo_img, use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)
        except Exception as e:
            st.write("")
    st.markdown("---")
    # Sidebar Option Menu with modern light brown colors
    selected_tab = option_menu(
        menu_title=None,
        options=["Live Demo", "Dataset Mode", "About / Notes"],
        icons=["box-arrow-up-right", "file-earmark-spreadsheet", "info-circle"],
        menu_icon="cast",
        default_index=0,
        orientation="vertical",
        styles={
            "container": {
                "padding": "0px",
                "background": "linear-gradient(135deg, #f5e9da 0%, #e9dbc7 100%)",
                "border-radius": "16px",
                "box-shadow": "0 2px 8px rgba(200,182,166,0.06)"
            },
            "nav-link": {
                "font-size": "18px",
                "font-weight": "500",
                "text-align": "left",
                "margin": "0px",
                "color": "#6e5849",
                "hover-color": "#c8b6a6",
                "border-radius": "8px"
            },
            "nav-link-selected": {
                "background": "linear-gradient(90deg, #c8b6a6 0%, #e9dbc7 100%)",
                "color": "#fff",
                "font-weight": "700"
            },
        }
    )

# -----------------------
# Load models (cached)
# -----------------------
@st.cache_resource
def load_pipelines():
    return models.load_pipelines()

def get_pipelines():
    return load_pipelines()

# -----------------------
# Utility helpers & analysis
# -----------------------
def analyze_texts(texts: List[str], progress_callback=None):
    sentiment_pipe, summarizer = get_pipelines()
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
    if s == "Positive": return "🟢 Positive"
    if s == "Neutral": return "🟡 Neutral"
    if s == "Negative": return "🔴 Negative"
    return s

# -----------------------
# Main content (right side)
# -----------------------
if selected_tab == "Live Demo":
    # Modern main container with light brown gradient
    st.markdown("""
        <div style="
            background: linear-gradient(135deg, #f5e9da 0%, #e9dbc7 100%);
            border-radius: 28px;
            padding: 48px 48px 32px 48px;
            margin-top: 24px;
            box-shadow: 0 6px 24px rgba(200,182,166,0.10);
        ">
            <h1 style="font-family: 'Segoe UI', Arial Black, sans-serif; color: #6e5849; font-size: 2.8rem; font-weight: 800; margin-bottom: 12px;">
                Live Demo — quick single-run analysis
            </h1>
            <p style="color: #8d735b; font-size: 1.2rem; margin-bottom: 24px;">
                Paste multiple comments separated by a blank line. Each paragraph becomes a comment.
            </p>
        </div>
    """, unsafe_allow_html=True)

    # Gap between header and textarea
    st.markdown("<div style='height:32px'></div>", unsafe_allow_html=True)

    user_text = st.text_area(
        "Comments (separate by a blank line)",
        height=220,
        placeholder="Write or paste comments here...",
        label_visibility="collapsed"
    )

    # Gap between textarea and button
    st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)

    analyze_btn = st.button("Analyze")

    # Gap after button
    st.markdown("<div style='height:32px'></div>", unsafe_allow_html=True)

    if analyze_btn:
        if not user_text.strip():
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
            pos = (out_df['sentiment'] == "Positive").sum()
            neu = (out_df['sentiment'] == "Neutral").sum()
            neg = (out_df['sentiment'] == "Negative").sum()
            total = len(out_df)

            # Gap before metrics
            st.markdown("<div style='height:32px'></div>", unsafe_allow_html=True)

            st.markdown("""
                <div style="background-color: #fff8f0; border-radius: 12px; padding: 18px; margin-top: 16px; box-shadow: 0 1px 6px rgba(200,182,166,0.04);">
            """, unsafe_allow_html=True)
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Total comments", total)
            col2.metric("Positive", f"{pos} ({pos/total*100:.0f}%)")
            col3.metric("Neutral", f"{neu} ({neu/total*100:.0f}%)")
            col4.metric("Negative", f"{neg} ({neg/total*100:.0f}%)")
            st.markdown("</div>", unsafe_allow_html=True)

            # Gap before results
            st.markdown("<div style='height:32px'></div>", unsafe_allow_html=True)

            left, right = st.columns([2, 1])
            with left:
                st.subheader("Results")
                st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
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
                st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
                wc_img = reporting.generate_wordcloud(cleaned_texts)
                st.image(wc_img, use_container_width=True)
                st.subheader("Top Keywords")
                st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
                kws = reporting.top_keywords(cleaned_texts, top_n=25)
                st.table(pd.DataFrame(kws, columns=["keyword","count"]).head(20))

            # PDF report
            st.markdown("<div style='height:32px'></div>", unsafe_allow_html=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            pdf_bytes = reporting.make_pdf_report(
                out_df, wc_img, title="eConsultation Live Demo Report",
                project_logo_path=project_logo_path if os.path.exists(project_logo_path) else None,
                team_logo_path=team_logo_path if os.path.exists(team_logo_path) else None
            )
            filename = f"econsult_report_{timestamp}.pdf"
            st.download_button("Download PDF report", data=pdf_bytes, file_name=filename, mime="application/pdf")

elif selected_tab == "Dataset Mode":
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
                st.image(wc_img, use_container_width=True)
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

elif selected_tab == "About / Notes":
    st.header("About / Notes")
    st.markdown("""
- Uses transformer summarization and sentiment models (heavier models by default with safe fallbacks).  
- PDF includes project and team logos (if present in `assets/`).  
- The app produces: sentiment analysis, a concise summary, a word cloud, and a word frequency list — available in both Live Demo and Dataset modes.  
""")

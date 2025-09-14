# eConsult AI Reviewer — MVP

**eConsult AI Reviewer — MVP** is a modular Streamlit application that analyzes stakeholder comments and generates a professional PDF report. The application performs sentiment analysis, concise summarization, word-cloud generation, and keyword frequency extraction. It is designed as a minimal, maintainable MVP suitable for demonstrations, hackathons, and early-stage evaluation.

---

## Features

* Sentiment classification mapped to `Positive` / `Neutral` / `Negative` (internal confidence threshold).
* Concise summarization for each comment (uses a higher-quality summarizer with fallback).
* Word cloud generation and top-keywords extraction.
* Clean, timestamped PDF report that includes optional project and team logos, word cloud, keywords, and a wrapped results table with page numbers.
* Two UI modes:

  * **Live Demo** — paste comments interactively.
  * **Dataset Mode** — upload CSV / XLSX for batch analysis.
* Modular codebase for easier testing, tuning and extension.

---

## Repository structure

```
econsult-ai-reviewer/
│
├── app.py                        # Streamlit entrypoint (UI + glue)
├── requirements.txt              # Python dependencies
├── README.md
├── assets/                       # optional: logos, fonts
│   ├── project_logo.png
│   └── team_logo.png
└── econsult_core/                # core modules
    ├── __init__.py
    ├── models.py                 # model loading and sentiment mapping
    ├── preprocessing.py          # cleaning, chunking, summarization helpers
    └── reporting.py              # wordcloud, keywords, PDF report builder
```

---

## Quick start (local)

These instructions assume a Unix-like shell. Adjust commands for Windows where necessary.

1. Clone the repository and change directory:

```bash
git clone <repository-url>
cd econsult-ai-reviewer
```

2. Create and activate a Python virtual environment (Python 3.10+ recommended):

```bash
python -m venv .venv
source .venv/bin/activate         # macOS / Linux
.venv\Scripts\activate            # Windows (PowerShell)
```

3. Install dependencies:

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

4. (Optional) Add branding assets:

Create an `assets/` directory at repository root and add optional images:

* `assets/project_logo.png` — project logo (used in header and PDF)
* `assets/team_logo.png` — team/institution logo (used in header and PDF)

Recommended: PNG images (\~300×300 px). The app will resize images to fit the UI and PDF.

5. Run the Streamlit app:

```bash
streamlit run app.py
```

Open the URL printed by Streamlit (typically `http://localhost:8501`).

---

## Input format (Dataset Mode)

The dataset must contain a `submission_text` column. Optional columns such as `id` and `stakeholder_type` are supported and will be included in the output.

Sample CSV:

```csv
id,submission_text,stakeholder_type
1,"We support the amendment but suggest clarifying clause 3.",Industry
2,"This will hurt MSMEs — strongly oppose.",SME
3,"Neutral: looks fine but add timeline.",Citizen
```

---

## PDF output

* Filenames are generated using a timestamp pattern: `econsult_report_YYYYMMDD_HHMMSS.pdf`.
* The PDF includes:

  * Project title and generation timestamp.
  * Optional project and team logos in the header (if provided in `assets/`).
  * Word cloud (full width).
  * Top keywords section.
  * Results table with columns: `ID`, `Sentiment`, `Score`, `Summary`. Summary text wraps using `multi_cell` so table content does not overflow the page.
  * Footer with page numbers.
* The PDF generation function signature remains:

  ```py
  make_pdf_report(df: pandas.DataFrame, wordcloud_img: PIL.Image, title: str = ..., project_logo_path: Optional[str] = None, team_logo_path: Optional[str] = None) -> bytes
  ```

---

## Configuration & tuning

* **Model selection and threshold**:

  * Summarizer default: `facebook/bart-large-cnn` (fallback to `t5-small`).
  * Sentiment default: `cardiffnlp/twitter-roberta-base-sentiment-latest` (fallback to `distilbert-base-uncased-finetuned-sst-2-english`).
  * Internal neutral threshold for mapping model confidence to `Neutral` is defined inside `econsult_core/models.py`. Change that constant to tune sensitivity (not exposed in the UI).
* **Performance**:

  * Heavier models are slow on CPU. For faster inference, run with a GPU-enabled machine and the appropriate `torch` installation.
  * For large datasets, add batching, background workers (Celery/RQ), or stream processing to avoid blocking the UI.

---

## Recommended improvements (next steps)

* Add batching for model inference to improve throughput and reduce latency.
* Add a background job queue for dataset analysis (Celery + Redis, RQ, or similar).
* Add authentication/authorization for multi-user deployments.
* Fine-tune models on domain-specific data for improved summarization and sentiment accuracy.
* Optionally add interactive table editing with `st-aggrid` and an administrative dashboard for audits.

---

## Troubleshooting

* **Transformer model download fails**: ensure outbound internet access or pre-cache models in the `TRANSFORMERS_CACHE` directory.
* **Out of memory or slow performance**: switch to smaller models (edit `econsult_core/models.py`) or run on a machine with more RAM/GPU.
* **PDF encoding**: default PDF encoding uses `latin-1`. For full Unicode support, register a TTF font in `reporting.py` using `pdf.add_font()` and switch the font usage accordingly.

---

## Development

* Keep concerns separated:

  * `econsult_core/models.py` — change model names or mapping logic.
  * `econsult_core/preprocessing.py` — modify text cleaning, chunking, or summarization orchestration.
  * `econsult_core/reporting.py` — adjust PDF layout, fonts, or export behavior.
* Unit tests are recommended for the preprocessing and reporting modules before productionization.

---

## Contributing

Contributions are welcome. Suggested workflow:

1. Fork the repository.
2. Create a feature branch: `git checkout -b feature/your-feature`.
3. Implement changes and add tests when applicable.
4. Open a pull request describing the changes and rationale.

Include sample input files and brief reproduction steps for any bug fixes.

---

## Authors and credits

* Project: eConsult AI Reviewer — MVP
* Built for: SIH 2025 (Smart India Hackathon)
* Team: GitLit



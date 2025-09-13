# eConsult AI Reviewer — MVP

A lightweight PyQt5 desktop app that analyzes user comments / feedback using transformer models.  
Features: sentiment analysis, summarization, keyword extraction, dataset batch processing, and export (PDF/PPTX/CSV).

---

## Quick start

### 1) Prerequisites
- Python **3.10+**
- ~8–16 GB free RAM (more recommended for transformer models)
- Optional GPU for faster inference (install CUDA & GPU-enabled `torch` if available)

### 2) Create & activate a virtual environment
Linux / macOS:
```bash
python3 -m venv venv
source venv/bin/activate
```

Windows (PowerShell):
```powershell
python -m venv venv
.env\Scripts\Activate.ps1
```

### 3) Install dependencies
```bash
pip install -r requirements.txt
```

> Note: Installing `transformers`, `torch`, `sentence-transformers` and `keybert` will download model weights at first run. This requires internet and may take time and disk space.

### 4) Run the app
From the project root:
```bash
python main.py
```

The main window will open. Use the **Live Demo** tab to paste a comment and run analysis, or the **Dataset** tab to upload a CSV/XLSX with a comment/text column.

---

## Project layout (key files)

```
econsult-ai-reviewer/
├── main.py
├── configs/settings.yaml
├── models/                 # Sentiment, summarizer, keyword extractor (transformer-based)
├── preprocessing/          # text cleaning & chunking
├── controllers/            # UI ↔ models glue (live and dataset)
├── ui/                     # PyQt5 UI (main window + tabs + components)
├── export/                 # PDF/PPTX/CSV exporters
├── utils/                  # file utils, visualization, logger
├── assets/                 # icons, styles.qss, sample_comments.csv
├── data/                   # uploaded/ processed (runtime)
├── requirements.txt
└── README.md
```

---

## Configuration

Edit `configs/settings.yaml` to change model names (HuggingFace IDs), thresholds, paths, and UI settings. Example keys:

```yaml
models:
  sentiment_model: "distilbert-base-uncased-finetuned-sst-2-english"
  summarizer_model: "sshleifer/distilbart-cnn-12-6"
  keyword_extractor: "distilbert-base-uncased"

thresholds:
  sentiment_positive: 0.6
  sentiment_negative: 0.4
  max_summary_length: 100
  min_summary_length: 25
  top_keywords: 10

paths:
  assets_dir: "assets/"
  reports_dir: "reports/"
```

If you change the model IDs to larger / better models, expect slower startup and larger downloads.

---

## How it works (high level)

- **LiveDemoController**: cleans text, runs sentiment, chunks & summarizes (if long), extracts keywords, returns a result dict for the UI.
- **DatasetController**: loads CSV/XLSX, auto-detects text column (or use the input box), processes rows in sequence, saves a processed CSV in `data/processed/`.
- **Models**: wrappers around HuggingFace `pipeline` for sentiment and summarization; KeyBERT (or TF-IDF fallback) for keywords.
- **Export**: `export/` provides PDF, PPTX, and CSV export; each has graceful fallbacks if optional libs are missing.

---

## Performance & tips

- Transformer models load weights on first run — expect several hundred MBs downloaded and 10–60+ seconds to load depending on disk/connection and model size.
- For batch processing of large datasets, run on a machine with enough RAM; consider enabling GPU and using a GPU-compatible `torch`.
- To speed up local demos, swap heavy models in `configs/settings.yaml` for lighter ones (e.g., DistilBART, DistilBERT models).
- For responsive UI under heavy work, convert synchronous processing to `QThread` / `QRunnable` (the UI currently runs tasks synchronously for MVP).

---

## Optional features & extending

- Swap PyQt5 → PyQt6 (requires API adjustments)
- Add `QThreads` to offload heavy model inference
- Add caching of model outputs in `data/processed/` to avoid repeated work
- Add a settings dialog in UI to change `configs/settings.yaml` values
- Replace KeyBERT with an embedding store (e.g., FAISS) for similarity / semantic search

---

## Troubleshooting

- **Model loading fails**: ensure internet access for first-run downloads. Check console/log file `logs/app.log` for stack traces.
- **ImportError for optional libs**: install missing packages from `requirements.txt` (e.g., `pip install reportlab python-pptx`).
- **Large memory usage / crashes**: try lighter models or run on a machine with more RAM; use CPU-only `torch` or GPU-accelerated `torch` if GPU & drivers available.
- **No UI or QPA errors**: ensure PyQt5 installed and proper display drivers are present (on headless servers you’ll need an X server or run with `xvfb`).

---

## Files to look at during development

- `ui/main_window.py` — main app wiring
- `controllers/live_demo_controller.py` — main processing pipeline for live input
- `models/sentiment_model.py` / `models/summarizer_model.py` — where HF pipelines are created
- `configs/settings.yaml` — to configure model IDs and paths

---

## License & credits

- Project: MIT-style permissive use for the MVP. (Add a LICENSE file if you want to be explicit.)
- Models & libraries: Follow respective licenses (HuggingFace model licenses, PyTorch, PyQt, etc.). Make sure to review model usage terms if using in production.

---

## Contact / Next steps

If you want, I can:
- Wire in `QThread` workers so the UI never blocks,
- Add a settings dialog to change models from the UI,
- Create a packaged executable (PyInstaller spec) for Windows/macOS,
- Or generate a short demo screencast script / checklist for judges.

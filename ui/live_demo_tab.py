# ui/live_demo_tab.py
"""
Live Demo tab UI.
Allows user to paste text, run analysis, and view results.
"""

from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QTextEdit,
    QPushButton,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QProgressBar,
)
from PyQt5.QtCore import Qt

from controllers import LiveDemoController
from .components.sentiment_badge import SentimentBadge
from .components.results_table import ResultsTable


class LiveDemoTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.controller = LiveDemoController()
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)

        hint = QLabel("Paste a comment/feedback below and click Analyze")
        layout.addWidget(hint)

        self.text_input = QTextEdit()
        self.text_input.setPlaceholderText("Type or paste feedback here...")
        layout.addWidget(self.text_input, 2)

        controls = QHBoxLayout()
        self.analyze_btn = QPushButton("Analyze")
        self.analyze_btn.clicked.connect(self.run_analysis)
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.clicked.connect(self.text_input.clear)
        controls.addWidget(self.analyze_btn)
        controls.addWidget(self.clear_btn)
        controls.addStretch()
        layout.addLayout(controls)

        # progress and outputs
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

        # outputs: sentiment badge, summary, keywords, cleaned text
        out_layout = QHBoxLayout()

        left_col = QVBoxLayout()
        self.sentiment_badge = SentimentBadge()
        left_col.addWidget(QLabel("Sentiment"))
        left_col.addWidget(self.sentiment_badge)
        left_col.addStretch()
        out_layout.addLayout(left_col, 1)

        middle_col = QVBoxLayout()
        middle_col.addWidget(QLabel("Summary"))
        self.summary_label = QLabel("")
        self.summary_label.setWordWrap(True)
        self.summary_label.setAlignment(Qt.AlignTop)
        middle_col.addWidget(self.summary_label)
        out_layout.addLayout(middle_col, 2)

        right_col = QVBoxLayout()
        right_col.addWidget(QLabel("Keywords"))
        self.keywords_list = QListWidget()
        right_col.addWidget(self.keywords_list)
        out_layout.addLayout(right_col, 1)

        layout.addLayout(out_layout, 3)

        # bottom: cleaned text and raw preview table
        layout.addWidget(QLabel("Cleaned Text"))
        self.cleaned_preview = QTextEdit()
        self.cleaned_preview.setReadOnly(True)
        layout.addWidget(self.cleaned_preview, 1)

        self.results_table = ResultsTable(headers=["Field", "Value"])
        layout.addWidget(self.results_table, 1)

    def run_analysis(self):
        text = self.text_input.toPlainText().strip()
        if not text:
            return
        self.progress.setVisible(True)
        self.progress.setRange(0, 0)  # indefinite
        self.analyze_btn.setEnabled(False)

        # perform processing synchronously (OK for MVP; later move to worker thread)
        result = self.controller.process_text(text)

        # update UI
        sentiment = result.get("sentiment", {})
        label = sentiment.get("label", "UNKNOWN")
        score = sentiment.get("score", 0.0)
        self.sentiment_badge.set_sentiment(label, score)

        summary = result.get("summary", "")
        self.summary_label.setText(summary)

        keywords = result.get("keywords", []) or []
        self.keywords_list.clear()
        # keywords may be (kw, score) or strings
        for kw in keywords:
            if isinstance(kw, (list, tuple)):
                item = f"{kw[0]} ({kw[1]:.2f})"
            else:
                item = str(kw)
            self.keywords_list.addItem(QListWidgetItem(item))

        cleaned = result.get("cleaned_text", "")
        self.cleaned_preview.setPlainText(cleaned)

        # also populate results table
        self.results_table.clear_rows()
        self.results_table.add_row(["Sentiment", f"{label} ({score:.2f})"])
        self.results_table.add_row(["Summary", summary])
        self.results_table.add_row(["Keywords", ", ".join([str(k[0] if isinstance(k, (list, tuple)) else k) for k in keywords])])

        self.progress.setVisible(False)
        self.analyze_btn.setEnabled(True)

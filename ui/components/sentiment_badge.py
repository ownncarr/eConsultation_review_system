# ui/components/sentiment_badge.py
"""
A small widget that displays sentiment label and a colored badge.
"""

from PyQt5.QtWidgets import QWidget, QLabel, QHBoxLayout
from PyQt5.QtGui import QColor, QPalette
from PyQt5.QtCore import Qt


class SentimentBadge(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout()
        self.setLayout(layout)
        self.label = QLabel("N/A")
        self.score = QLabel("")
        layout.addWidget(self.label)
        layout.addWidget(self.score)
        layout.addStretch()
        self._apply_style("neutral")

    def _apply_style(self, mood: str):
        # simple palette-based color
        pal = self.palette()
        if mood == "POSITIVE":
            pal.setColor(QPalette.Window, QColor("#e6ffed"))
            pal.setColor(QPalette.WindowText, QColor("#1b7a2f"))
        elif mood == "NEGATIVE":
            pal.setColor(QPalette.Window, QColor("#ffe6e6"))
            pal.setColor(QPalette.WindowText, QColor("#a12a2a"))
        else:
            pal.setColor(QPalette.Window, QColor("#f0f0f0"))
            pal.setColor(QPalette.WindowText, QColor("#333333"))
        self.setAutoFillBackground(True)
        self.setPalette(pal)

    def set_sentiment(self, label: str, score: float):
        label_str = str(label).upper()
        self.label.setText(label_str)
        self.score.setText(f"{score:.2f}")
        self._apply_style(label_str)

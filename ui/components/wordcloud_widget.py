# ui/components/wordcloud_widget.py
"""
A small widget that can render a wordcloud image (requires wordcloud & matplotlib).
If dependencies are missing, the widget shows a helpful message.
"""

from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout
from PyQt5.QtGui import QPixmap
from io import BytesIO

try:
    from wordcloud import WordCloud
    import matplotlib.pyplot as plt
    _WC_AVAILABLE = True
except Exception:
    _WC_AVAILABLE = False


class WordCloudWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout()
        self.setLayout(layout)
        self.image_label = QLabel("WordCloud unavailable")
        layout.addWidget(self.image_label)

    def render(self, text: str):
        if not _WC_AVAILABLE:
            self.image_label.setText("Install 'wordcloud' and 'matplotlib' to enable wordcloud.")
            return
        wc = WordCloud(width=600, height=400, background_color="white").generate(text)
        fig = plt.figure(figsize=(6, 4))
        plt.imshow(wc, interpolation="bilinear")
        plt.axis("off")
        buf = BytesIO()
        fig.savefig(buf, format="png", bbox_inches="tight")
        plt.close(fig)
        buf.seek(0)
        pix = QPixmap()
        pix.loadFromData(buf.getvalue())
        self.image_label.setPixmap(pix)

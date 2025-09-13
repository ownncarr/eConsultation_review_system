# ui/report_tab.py
"""
Reports tab - light UI to show exported reports and provide export triggers.
Currently minimal for MVP; hooks into export/pdf/pptx generators later.
"""

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QFileDialog, QMessageBox
from pathlib import Path


class ReportTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)

        layout.addWidget(QLabel("Reports / Export"))

        self.export_pdf_btn = QPushButton("Export current preview to PDF (not implemented)")
        self.export_pdf_btn.clicked.connect(self._not_impl)
        layout.addWidget(self.export_pdf_btn)

        self.open_reports_btn = QPushButton("Open reports folder")
        self.open_reports_btn.clicked.connect(self._open_reports)
        layout.addWidget(self.open_reports_btn)

    def _not_impl(self):
        QMessageBox.information(self, "Not implemented", "PDF export will be implemented in export module.")

    def _open_reports(self):
        reports_dir = Path("reports")
        if not reports_dir.exists():
            QMessageBox.information(self, "Reports", "No reports folder found yet.")
            return
        QFileDialog.getOpenFileName(self, "Open report", str(reports_dir), "PDF Files (*.pdf);;PowerPoint (*.pptx);;All Files (*)")

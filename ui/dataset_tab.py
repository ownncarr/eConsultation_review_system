# ui/dataset_tab.py
"""
Dataset tab UI.
Upload CSV/XLSX files, configure options, run batch processing, view preview.
"""

from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QFileDialog,
    QHBoxLayout,
    QLineEdit,
    QMessageBox,
    QTableWidget,
    QTableWidgetItem,
    QProgressBar,
)
from PyQt5.QtCore import Qt
from controllers import DatasetController


class DatasetTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.controller = DatasetController()
        self.current_file = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)

        instructions = QLabel("Upload a CSV / Excel file with a column containing feedback text.")
        layout.addWidget(instructions)

        file_layout = QHBoxLayout()
        self.file_input = QLineEdit()
        self.file_input.setPlaceholderText("Select dataset file...")
        file_layout.addWidget(self.file_input)
        browse_btn = QPushButton("Browse")
        browse_btn.clicked.connect(self.browse_file)
        file_layout.addWidget(browse_btn)
        load_btn = QPushButton("Load & Preview")
        load_btn.clicked.connect(self.load_and_preview)
        file_layout.addWidget(load_btn)
        layout.addLayout(file_layout)

        col_layout = QHBoxLayout()
        self.column_input = QLineEdit()
        self.column_input.setPlaceholderText("Text column name (optional, will auto-detect)")
        col_layout.addWidget(self.column_input)
        run_btn = QPushButton("Process Dataset")
        run_btn.clicked.connect(self.process_dataset)
        col_layout.addWidget(run_btn)
        layout.addLayout(col_layout)

        self.progress = QProgressBar()
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

        layout.addWidget(QLabel("Preview (first 50 rows of processed output):"))
        self.preview_table = QTableWidget()
        self.preview_table.setColumnCount(5)
        self.preview_table.setHorizontalHeaderLabels(["Row", "Sentiment", "Score", "Summary", "Keywords"])
        layout.addWidget(self.preview_table)

    def browse_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open dataset", "", "Datasets (*.csv *.xls *.xlsx)")
        if path:
            self.file_input.setText(path)
            self.current_file = path

    def load_and_preview(self):
        path = self.file_input.text().strip()
        if not path:
            QMessageBox.warning(self, "No file", "Please select a dataset file first.")
            return
        self.load_file(path)

    def load_file(self, path: str):
        # just set the file and attempt to preview basic info via controller read
        try:
            info = self.controller._read_dataset(path)  # returns DataFrame
        except Exception as e:
            QMessageBox.critical(self, "Load failed", f"Could not load dataset: {e}")
            return
        self.current_file = path
        self.file_input.setText(path)
        QMessageBox.information(self, "Loaded", f"Loaded dataset with {len(info)} rows. You can now Process Dataset.")

    def process_dataset(self):
        if not self.current_file:
            QMessageBox.warning(self, "No file", "Please select or load a dataset file first.")
            return
        text_col = self.column_input.text().strip() or None
        self.progress.setVisible(True)
        self.progress.setRange(0, 0)
        # synchronous processing (ok for MVP)
        result = self.controller.process_dataset(self.current_file, text_column=text_col, save_csv=True)
        self.progress.setVisible(False)

        if result.get("error"):
            QMessageBox.critical(self, "Processing failed", result["error"])
            return

        preview = result.get("preview", [])
        self._populate_preview(preview)
        QMessageBox.information(self, "Done", f"Processed {result.get('processed_rows')} rows. Saved to {result.get('output_path')}")

    def _populate_preview(self, rows):
        self.preview_table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            sent = row.get("sentiment_label", "")
            score = row.get("sentiment_score", 0.0)
            summary = (row.get("summary") or "")[:200]
            keywords = ", ".join([k[0] if isinstance(k, (list, tuple)) else str(k) for k in (row.get("keywords") or [])])
            self.preview_table.setItem(i, 0, QTableWidgetItem(str(row.get("row", i))))
            self.preview_table.setItem(i, 1, QTableWidgetItem(sent))
            self.preview_table.setItem(i, 2, QTableWidgetItem(f"{score:.2f}"))
            self.preview_table.setItem(i, 3, QTableWidgetItem(summary))
            self.preview_table.setItem(i, 4, QTableWidgetItem(keywords))
        self.preview_table.resizeColumnsToContents()

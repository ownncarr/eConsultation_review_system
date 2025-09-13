# ui/main_window.py
"""
Main application window. Contains a tab widget with:
- Live Demo
- Dataset
- Report
"""

from PyQt5.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QTabWidget,
    QLabel,
    QHBoxLayout,
    QAction,
    QFileDialog,
    QMessageBox,
)
from PyQt5.QtGui import QIcon
from pathlib import Path

from .live_demo_tab import LiveDemoTab
from .dataset_tab import DatasetTab
from .report_tab import ReportTab


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("eConsult AI Reviewer — MVP")
        self.setMinimumSize(900, 640)
        self._build_ui()
        self._create_menu()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout()
        central.setLayout(layout)

        # header
        header_layout = QHBoxLayout()
        title = QLabel("<h2>eConsult AI Reviewer</h2>")
        subtitle = QLabel("Analyze comments with sentiment, summary, and keywords")
        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(subtitle)
        layout.addLayout(header_layout)

        # tabs
        self.tabs = QTabWidget()
        self.live_demo_tab = LiveDemoTab()
        self.dataset_tab = DatasetTab()
        self.report_tab = ReportTab()

        self.tabs.addTab(self.live_demo_tab, "Live Demo")
        self.tabs.addTab(self.dataset_tab, "Dataset")
        self.tabs.addTab(self.report_tab, "Reports")

        layout.addWidget(self.tabs)

    def _create_menu(self):
        menubar = self.menuBar()
        file_menu = menubar.addMenu("&File")

        load_action = QAction(QIcon(), "Load sample dataset", self)
        load_action.triggered.connect(self._load_sample)
        file_menu.addAction(load_action)

        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

    def _load_sample(self):
        # attempt to find assets/sample_comments.csv relative to project root
        sample = Path("assets/sample_comments.csv")
        if not sample.exists():
            QMessageBox.warning(self, "Sample dataset", f"Sample dataset not found at {sample}")
            return
        # open dataset tab and prefill path
        self.tabs.setCurrentWidget(self.dataset_tab)
        self.dataset_tab.load_file(str(sample))

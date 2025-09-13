# main.py
"""
Entry point for the eConsult AI Reviewer application.
Initializes the PyQt5 application, applies styles, and loads the main window.
"""

import sys
from PyQt5.QtWidgets import QApplication
from ui.main_window import MainWindow


def load_stylesheet(path: str) -> str:
    """Read the QSS stylesheet file."""
    try:
        with open(path, "r") as f:
            return f.read()
    except Exception as e:
        print(f"[WARN] Could not load stylesheet {path}: {e}")
        return ""


def main():
    app = QApplication(sys.argv)

    # Apply stylesheet if available
    stylesheet = load_stylesheet("assets/styles.qss")
    if stylesheet:
        app.setStyleSheet(stylesheet)

    # Launch main window
    window = MainWindow()
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()

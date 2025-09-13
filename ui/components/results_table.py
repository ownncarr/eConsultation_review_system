# ui/components/results_table.py
"""
A small key-value table widget used in Live Demo to show quick fields.
"""

from PyQt5.QtWidgets import QWidget, QTableWidget, QVBoxLayout, QTableWidgetItem


class ResultsTable(QWidget):
    def __init__(self, headers=None, parent=None):
        super().__init__(parent)
        headers = headers or ["Key", "Value"]
        layout = QVBoxLayout()
        self.setLayout(layout)
        self.table = QTableWidget(0, len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        layout.addWidget(self.table)

    def add_row(self, row):
        r = self.table.rowCount()
        self.table.insertRow(r)
        for c, val in enumerate(row):
            item = QTableWidgetItem(str(val))
            self.table.setItem(r, c, item)

    def clear_rows(self):
        self.table.setRowCount(0)

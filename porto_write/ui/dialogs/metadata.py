import os
import logging
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
    QLabel, QLineEdit, QFormLayout, QSpinBox, QMessageBox, 
    QFileDialog, QTextEdit, QTableWidget, QTableWidgetItem, QHeaderView
)
from PySide6.QtGui import QColor
from PySide6.QtCore import Qt

logger = logging.getLogger(__name__)

class MetadataDialog(QDialog):
    """Dialog to edit project-wide metadata including title, author, and cover."""

    def __init__(self, doc, cover_rel_path, parent=None):
        super().__init__(parent)
        self.doc = doc
        self.setWindowTitle("Project Metadata")
        self.setMinimumWidth(500)
        self.setMinimumHeight(600)
        self.new_cover_path = None
        
        layout = QVBoxLayout(self)
        form = QFormLayout()
        
        self.title_edit = QLineEdit(self.doc.title)
        form.addRow("Novel Title:", self.title_edit)

        self.subtitle_edit = QLineEdit(self.doc.subtitle)
        form.addRow("Subtitle:", self.subtitle_edit)
        
        self.author_edit = QLineEdit(self.doc.author)
        form.addRow("Author:", self.author_edit)

        series_layout = QHBoxLayout()
        self.series_name_edit = QLineEdit(self.doc.series_name)
        self.series_number_spin = QSpinBox()
        self.series_number_spin.setRange(0, 999)
        self.series_number_spin.setValue(self.doc.series_number)
        series_layout.addWidget(self.series_name_edit, 3)
        series_layout.addWidget(QLabel("#"), 0)
        series_layout.addWidget(self.series_number_spin, 1)
        form.addRow("Series:", series_layout)

        self.publisher_edit = QLineEdit(self.doc.publisher)
        form.addRow("Publisher:", self.publisher_edit)

        self.isbn_edit = QLineEdit(self.doc.isbn)
        form.addRow("ISBN:", self.isbn_edit)

        self.keywords_edit = QLineEdit(", ".join(self.doc.keywords))
        form.addRow("Keywords:", self.keywords_edit)
        
        self.description_edit = QTextEdit()
        self.description_edit.setPlainText(self.doc.description)
        self.description_edit.setMaximumHeight(100)
        form.addRow("Description:", self.description_edit)
        
        cover_layout = QHBoxLayout()
        self.cover_label = QLabel(cover_rel_path or "None")
        self.cover_label.setStyleSheet("color: #666; font-style: italic;")
        cover_layout.addWidget(self.cover_label)
        
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._on_browse)
        cover_layout.addWidget(browse_btn)
        
        form.addRow("Cover Image:", cover_layout)
        
        layout.addLayout(form)
        
        # Action buttons
        btns = QHBoxLayout()
        ok_btn = QPushButton("Save")
        ok_btn.clicked.connect(self.accept)
        ok_btn.setDefault(True)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        
        btns.addStretch()
        btns.addWidget(ok_btn)
        btns.addWidget(cancel_btn)
        layout.addLayout(btns)

    def _on_browse(self):
        filters = "Images (*.jpg *.jpeg *.png)"
        path, _ = QFileDialog.getOpenFileName(self, "Select Cover Image", "", filters)
        if path:
            self.new_cover_path = path
            self.cover_label.setText(os.path.basename(path) + " (Selected)")
            self.cover_label.setStyleSheet("color: #27ae60; font-weight: bold; font-style: normal;")

    def get_data(self):
        keywords = [k.strip() for k in self.keywords_edit.text().split(",") if k.strip()]
        return {
            "title": self.title_edit.text().strip(),
            "subtitle": self.subtitle_edit.text().strip(),
            "author": self.author_edit.text().strip(),
            "series_name": self.series_name_edit.text().strip(),
            "series_number": self.series_number_spin.value(),
            "publisher": self.publisher_edit.text().strip(),
            "isbn": self.isbn_edit.text().strip(),
            "keywords": keywords,
            "description": self.description_edit.toPlainText().strip(),
            "new_cover_path": self.new_cover_path
        }


class TocEditorDialog(QDialog):
    """Dialog to view and edit the Table of Contents."""

    def __init__(self, doc, parent=None):
        super().__init__(parent)
        self.doc = doc
        self.setWindowTitle("Table of Contents Editor")
        self.setMinimumSize(600, 500)
        self._setup_ui()
        self._populate_table()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        layout.addWidget(QLabel("<b>Generated Table of Contents</b>"))
        layout.addWidget(QLabel("Authors can rename entries for the published book. Changes here do not affect the main text."))
        
        # Table
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Level", "Original Text", "TOC Display Text"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table)
        
        # Buttons
        btns = QHBoxLayout()
        
        refresh_btn = QPushButton("Regenerate from Headings")
        refresh_btn.setToolTip("Rescan document for chapters and heading styles. Warning: This will overwrite manual renames.")
        refresh_btn.clicked.connect(self._on_regenerate)
        btns.addWidget(refresh_btn)
        
        btns.addStretch()
        
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self._on_save)
        save_btn.setDefault(True)
        btns.addWidget(save_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btns.addWidget(cancel_btn)
        layout.addLayout(btns)

    def _populate_table(self):
        self.table.setRowCount(0)
        for i, entry in enumerate(self.doc.toc):
            self.table.insertRow(i)
            
            # Level (Read-only)
            level_item = QTableWidgetItem(str(entry.level))
            level_item.setFlags(level_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            level_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(i, 0, level_item)
            
            # Original Text (Read-only)
            orig_item = QTableWidgetItem(entry.text)
            orig_item.setFlags(orig_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            orig_item.setForeground(QColor("#777"))
            self.table.setItem(i, 1, orig_item)
            
            # Display Text (Editable)
            display_item = QTableWidgetItem(entry.text)
            self.table.setItem(i, 2, display_item)

    def _on_regenerate(self):
        res = QMessageBox.question(
            self, "Regenerate TOC",
            "This will rescan your document for all headings. Any manual renames in this table will be lost.\n\nContinue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if res == QMessageBox.StandardButton.Yes:
            self.doc.refresh_toc()
            self._populate_table()

    def _on_save(self):
        # Update doc.toc from table
        for i in range(self.table.rowCount()):
            new_text = self.table.item(i, 2).text().strip()
            if i < len(self.doc.toc):
                self.doc.toc[i].text = new_text
        
        self.accept()

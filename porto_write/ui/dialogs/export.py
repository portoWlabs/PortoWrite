import os
import logging
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
    QListWidget, QListWidgetItem, QLabel, QFormLayout, 
    QMessageBox, QFileDialog, QComboBox
)
from PySide6.QtGui import QColor
from porto_write.epub_validator import ValidationResult

logger = logging.getLogger(__name__)

class ExportOptionsDialog(QDialog):
    """Dialog to select export platform and options."""
    def __init__(self, file_path: str, default_platform: str = "kindle", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Export Options")
        self.setFixedSize(400, 180)
        
        layout = QVBoxLayout(self)
        
        form = QFormLayout()
        self.path_label = QLabel(os.path.basename(file_path))
        self.path_label.setToolTip(file_path)
        form.addRow("Destination:", self.path_label)
        
        self.platform_combo = QComboBox()
        self.platform_combo.addItem("Kindle (Standard)", "kindle")
        self.platform_combo.addItem("Kobo", "kobo")
        self.platform_combo.addItem("Apple Books", "apple_books")
        
        idx = self.platform_combo.findData(default_platform)
        if idx >= 0:
            self.platform_combo.setCurrentIndex(idx)
            
        form.addRow("Target Platform:", self.platform_combo)
        
        layout.addLayout(form)
        layout.addStretch()
        
        btns = QHBoxLayout()
        export_btn = QPushButton("Export")
        export_btn.setDefault(True)
        export_btn.clicked.connect(self.accept)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        
        btns.addStretch()
        btns.addWidget(cancel_btn)
        btns.addWidget(export_btn)
        layout.addLayout(btns)

    def get_platform(self) -> str:
        return self.platform_combo.currentData()


class ValidationResultDialog(QDialog):
    """Dialog to display EPUB validation results."""

    def __init__(self, result: ValidationResult, file_path: str, parent=None):
        super().__init__(parent)
        self.result = result
        self.file_path = file_path
        self.setWindowTitle("EPUB Validation Report")
        self.setMinimumSize(500, 400)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Status Header
        status_layout = QHBoxLayout()
        icon_label = QLabel()
        if self.result.is_valid:
            icon_label.setText("✅")
            status_text = "<b>Validation PASSED</b>"
            status_color = "#27ae60"
        else:
            icon_label.setText("❌")
            status_text = "<b>Validation FAILED</b>"
            status_color = "#c0392b"
            
        status_label = QLabel(status_text)
        status_label.setStyleSheet(f"color: {status_color}; font-size: 16px;")
        status_layout.addWidget(icon_label)
        status_layout.addWidget(status_label)
        status_layout.addStretch()
        layout.addLayout(status_layout)
        
        layout.addWidget(QLabel(f"File: {os.path.basename(self.file_path)}"))
        
        # Summary
        summary = f"Errors: {len(self.result.errors)} | Warnings: {len(self.result.warnings)}"
        layout.addWidget(QLabel(summary))
        
        # Results List
        self.list_widget = QListWidget()
        for err in self.result.errors:
            item = QListWidgetItem(f"ERROR: {err}")
            item.setForeground(QColor("#c0392b"))
            self.list_widget.addItem(item)
            
        for warn in self.result.warnings:
            item = QListWidgetItem(f"WARNING: {warn}")
            item.setForeground(QColor("#f39c12"))
            self.list_widget.addItem(item)
            
        if not self.result.errors and not self.result.warnings:
            self.list_widget.addItem("No issues found. Your EPUB is compliant.")
            
        layout.addWidget(self.list_widget)
        
        # Buttons
        btns = QHBoxLayout()
        
        save_btn = QPushButton("Save Report...")
        save_btn.clicked.connect(self._on_save_report)
        btns.addWidget(save_btn)
        
        btns.addStretch()
        
        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self.accept)
        ok_btn.setDefault(True)
        btns.addWidget(ok_btn)
        
        layout.addLayout(btns)

    def _on_save_report(self):
        report_path, _ = QFileDialog.getSaveFileName(
            self, "Save Validation Report", 
            os.path.splitext(self.file_path)[0] + "_validation.txt",
            "Text Files (*.txt)"
        )
        if report_path:
            try:
                with open(report_path, "w", encoding="utf-8") as f:
                    f.write(f"EPUB Validation Report for: {self.file_path}\n")
                    f.write(f"Result: {'PASS' if self.result.is_valid else 'FAIL'}\n")
                    f.write("-" * 40 + "\n\n")

                    f.write(f"ERRORS ({len(self.result.errors)}):\n")
                    for err in self.result.errors:
                        f.write(f"  - {err}\n")

                    f.write(f"\nWARNINGS ({len(self.result.warnings)}):\n")
                    for warn in self.result.warnings:
                        f.write(f"  - {warn}\n")

                QMessageBox.information(self, "Success", f"Report saved to: {os.path.basename(report_path)}")

            except Exception as e:
                logger.error("Failed to save report: %s", e)
                QMessageBox.critical(self, "Error", f"Failed to save report: {e}")

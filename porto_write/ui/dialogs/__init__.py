import os
import sys
import logging
from datetime import datetime
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
    QListWidget, QListWidgetItem, QLabel, QLineEdit, QFormLayout, 
    QSpinBox, QMessageBox, QFileDialog, QComboBox, 
    QFontComboBox, QColorDialog, QCheckBox, QDoubleSpinBox, QDialogButtonBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QTextEdit,
    QTabWidget, QTextBrowser
)
from PySide6.QtGui import QColor, QPalette, QFontDatabase, QFont, QDesktopServices, QCloseEvent
from PySide6.QtCore import Qt, QUrl
from porto_write.constants import KINDLE_FONTS, APP_NAME, APP_VERSION
from porto_write.project import ProjectManager, NovelProject
from porto_write.settings import AppSettings
from porto_write.styles import StyleDefinition
from porto_write.epub_validator import ValidationResult
from porto_write.toc import TocEntry
from porto_write.licensing import get_edition_label

logger = logging.getLogger(__name__)

class BetaWarningDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("PortoWrite Beta — Important Notice")
        self.setFixedSize(550, 420)
        # Non-closeable via standard buttons
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.CustomizeWindowHint | Qt.WindowType.WindowTitleHint)
        
        layout = QVBoxLayout(self)
        
        text = (
            f"PortoWrite v{APP_VERSION} — IMPORTANT NOTICE\n\n"
            "This software is a BETA release. It may contain bugs, errors, or incomplete features "
            "that could result in unexpected behavior, data corruption, or loss of work.\n\n"
            "PLEASE BACK UP ALL YOUR WORK BEFORE USING THIS PROGRAM.\n\n"
            "THIS SOFTWARE IS PROVIDED \"AS IS\", WITHOUT WARRANTY OF ANY KIND. THE DEVELOPER(S) "
            "OF PORTOWRITE SHALL NOT BE HELD RESPONSIBLE OR LIABLE FOR ANY LOSS OF DATA, CORRUPTION "
            "OF FILES, OR ANY OTHER DAMAGES ARISING FROM THE USE OF THIS SOFTWARE. USE AT YOUR OWN RISK.\n\n"
            "By clicking OK, you acknowledge that you have read and understood this disclaimer."
        )
        
        label = QLabel(text)
        label.setWordWrap(True)
        label.setStyleSheet("font-size: 13px; line-height: 1.4;")
        layout.addWidget(label)
        
        layout.addStretch()
        
        btn_layout = QHBoxLayout()
        exit_btn = QPushButton("Exit Application")
        exit_btn.clicked.connect(lambda: sys.exit(0))
        btn_layout.addWidget(exit_btn)
        
        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self.accept)
        ok_btn.setDefault(True)
        btn_layout.addWidget(ok_btn)
        
        layout.addLayout(btn_layout)

    def closeEvent(self, event: QCloseEvent):
        # Prevent closing via Alt+F4 or other system methods
        event.ignore()

class BetaInitialsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Disable Beta Warning — Confirm")
        self.setFixedSize(400, 180)
        
        layout = QVBoxLayout(self)
        
        layout.addWidget(QLabel(
            "Type your initials below to confirm you have read and accepted the beta disclaimer. "
            "The warning will no longer appear at startup."
        ))
        
        self.initials_edit = QLineEdit()
        self.initials_edit.setMaxLength(5)
        self.initials_edit.setPlaceholderText("YOUR INITIALS")
        self.initials_edit.textChanged.connect(self._on_text_changed)
        layout.addWidget(self.initials_edit)
        
        layout.addStretch()
        
        btns = QHBoxLayout()
        self.confirm_btn = QPushButton("Confirm")
        self.confirm_btn.setEnabled(False)
        self.confirm_btn.clicked.connect(self.accept)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        
        btns.addStretch()
        btns.addWidget(cancel_btn)
        btns.addWidget(self.confirm_btn)
        layout.addLayout(btns)

    def _on_text_changed(self, text):
        # Force uppercase
        self.initials_edit.blockSignals(True)
        self.initials_edit.setText(text.upper())
        self.initials_edit.blockSignals(False)
        self.confirm_btn.setEnabled(len(text.strip()) > 0)

    def get_initials(self) -> str:
        return self.initials_edit.text().strip().upper()

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

class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"About {APP_NAME}")
        self.setFixedSize(300, 180)
        
        layout = QVBoxLayout(self)
        
        title_label = QLabel(f"<b>{APP_NAME} v{APP_VERSION}</b>")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)
        
        edition_label = QLabel(f"Edition: {get_edition_label()}")
        edition_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(edition_label)
        
        copy_label = QLabel("© 2026 William Porto. All rights reserved.")
        copy_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(copy_label)
        
        link_label = QLabel("<a href='https://github.com'>See TIERS.md for licensing info</a>")
        link_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        link_label.setOpenExternalLinks(True)
        layout.addWidget(link_label)
        
        layout.addStretch()
        
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

class UpgradeDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Upgrade PortoWrite")
        self.setFixedSize(350, 250)
        
        layout = QVBoxLayout(self)
        
        edition_label = QLabel(f"Current Edition: <b>{get_edition_label()}</b>")
        layout.addWidget(edition_label)
        
        info_label = QLabel("<b>Upgrade to Pro to unlock:</b>")
        layout.addWidget(info_label)
        
        features_list = QLabel(
            "• DOCX & Markdown Export\n"
            "• Custom Styles (Create/Edit/Delete)\n"
            "• Future: Footnotes & Hyperlinks\n"
            "• Future: Track Changes\n"
            "• Priority Support"
        )
        layout.addWidget(features_list)
        
        layout.addStretch()
        
        btn_layout = QHBoxLayout()
        donate_btn = QPushButton("Donate $25")
        donate_btn.clicked.connect(self._on_donate)
        donate_btn.setStyleSheet("background-color: #2e8b57; color: white; font-weight: bold; padding: 6px;")
        btn_layout.addWidget(donate_btn)
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.reject)
        btn_layout.addWidget(close_btn)
        
        layout.addLayout(btn_layout)
        
    def _on_donate(self):
        QDesktopServices.openUrl(QUrl("https://portowrite.dev/donate"))
        self.accept()


class ParagraphSpacingDialog(QDialog):
    """Minimal dialog to set space-before and space-after for selected paragraphs."""

    def __init__(self, parent=None, space_before: int = 0, space_after: int = 6):
        super().__init__(parent)
        self.setWindowTitle("Paragraph Spacing")
        self.setFixedSize(280, 130)
        layout = QFormLayout(self)
        self._before = QSpinBox()
        self._before.setRange(0, 200)
        self._before.setSuffix(" pt")
        self._before.setValue(space_before)
        self._after = QSpinBox()
        self._after.setRange(0, 200)
        self._after.setSuffix(" pt")
        self._after.setValue(space_after)
        layout.addRow("Space before:", self._before)
        layout.addRow("Space after:", self._after)
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addRow(btns)

    def get_values(self) -> tuple[int, int]:
        return self._before.value(), self._after.value()


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

class DisplayPreferencesDialog(QDialog):
    """Dialog for customizing editor font and colors."""

    def __init__(self, parent, current_font, current_font_size, current_text_color, current_bg_color, 
                 current_m_left, current_m_right, dynamic_enabled, max_width_chars,
                 show_beta_warning, beta_warning_initials, projects_dir, tooltips_enabled):
        super().__init__(parent)
        self.setWindowTitle("Display Preferences")
        self.setMinimumWidth(450)
        
        self.font_name = current_font
        self.font_size = current_font_size
        self.text_color = QColor(current_text_color)
        self.bg_color = QColor(current_bg_color)
        self.m_left = current_m_left
        self.m_right = current_m_right
        self.dynamic_enabled = dynamic_enabled
        self.max_width_chars = max_width_chars
        self.show_beta_warning = show_beta_warning
        self.beta_initials = beta_warning_initials
        self.projects_dir = projects_dir
        self.tooltips_enabled = tooltips_enabled
        
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()
        
        # 0. Projects Folder
        proj_layout = QHBoxLayout()
        self.projects_dir_label = QLabel(self.projects_dir)
        self.projects_dir_label.setStyleSheet("color: #666; font-size: 11px;")
        proj_layout.addWidget(self.projects_dir_label, 1)
        
        browse_proj_btn = QPushButton("Browse...")
        browse_proj_btn.setToolTip("Click to choose a different folder on your computer where projects will be stored.")
        browse_proj_btn.clicked.connect(self._on_browse_projects_dir)
        proj_layout.addWidget(browse_proj_btn)
        form.addRow("Projects Root Folder:", proj_layout)

        # 1. Font
        self.font_combo = QComboBox()
        self.font_combo.setToolTip("Choose the font used while writing. Kindle-native fonts are recommended for accurate previewing.")
        # Add Kindle fonts first
        self.font_combo.addItem("--- Kindle Native Fonts ---")
        self.font_combo.model().item(0).setEnabled(False)
        for f in KINDLE_FONTS:
            self.font_combo.addItem(f)
            
        self.font_combo.addItem("--- System Fonts ---")
        self.font_combo.model().item(len(KINDLE_FONTS) + 1).setEnabled(False)
        
        # Add all system fonts using the stable QFontDatabase
        font_db = QFontDatabase()
        all_fonts = font_db.families()
        for family in all_fonts:
            self.font_combo.addItem(family)
            
        idx = self.font_combo.findText(self.font_name)
        if idx >= 0:
            self.font_combo.setCurrentIndex(idx)
        form.addRow("Editor Font:", self.font_combo)

        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(8, 72)
        self.font_size_spin.setSuffix(" pt")
        self.font_size_spin.setValue(self.font_size)
        self.font_size_spin.setToolTip("Set the base font size for the editor display.")
        form.addRow("Base Font Size:", self.font_size_spin)
        
        # 2. Text Color
        self.text_color_btn = QPushButton()
        self.text_color_btn.setToolTip("Click to choose the color of the text in the editor.")
        self._update_color_button(self.text_color_btn, self.text_color)
        self.text_color_btn.clicked.connect(self._pick_text_color)
        form.addRow("Text Color:", self.text_color_btn)
        
        # 3. Background Color
        self.bg_color_btn = QPushButton()
        self.bg_color_btn.setToolTip("Click to choose the background color of the editor.")
        self._update_color_button(self.bg_color_btn, self.bg_color)
        self.bg_color_btn.clicked.connect(self._pick_bg_color)
        form.addRow("Background Color:", self.bg_color_btn)
        
        # 4. Margins
        self.m_left_spin = QSpinBox()
        self.m_left_spin.setRange(0, 500)
        self.m_left_spin.setValue(self.m_left)
        self.m_left_spin.setToolTip("Set the fixed padding (in pixels) on the left side of the editor.")
        form.addRow("Min Left Margin (px):", self.m_left_spin)
        
        self.m_right_spin = QSpinBox()
        self.m_right_spin.setRange(0, 500)
        self.m_right_spin.setValue(self.m_right)
        self.m_right_spin.setToolTip("Set the fixed padding (in pixels) on the right side of the editor.")
        form.addRow("Min Right Margin (px):", self.m_right_spin)
        
        # 5. Dynamic Centering
        self.dynamic_cb = QCheckBox("Enable Dynamic Centering (Kindle style)")
        self.dynamic_cb.setChecked(self.dynamic_enabled)
        self.dynamic_cb.setToolTip("Automatically center the text when the window is wide, simulating an e-reader screen.")
        form.addRow(self.dynamic_cb)
        
        self.max_width_spin = QSpinBox()
        self.max_width_spin.setRange(20, 200)
        self.max_width_spin.setValue(self.max_width_chars)
        self.max_width_spin.setEnabled(self.dynamic_enabled)
        self.max_width_spin.setToolTip("The maximum number of characters per line when Dynamic Centering is enabled.")
        self.dynamic_cb.toggled.connect(self.max_width_spin.setEnabled)
        form.addRow("Max Content Width (chars):", self.max_width_spin)

        # 6. Beta Warning
        self.beta_cb = QCheckBox("Show beta warning at startup")
        self.beta_cb.setChecked(self.show_beta_warning)
        self.beta_cb.setToolTip("Display the feedback reminder splash screen on startup.")
        self.beta_cb.toggled.connect(self._on_beta_toggled)
        form.addRow(self.beta_cb)

        # 7. UI Tooltips
        self.tooltips_cb = QCheckBox("Enable UI Tooltips")
        self.tooltips_cb.setChecked(self.tooltips_enabled)
        self.tooltips_cb.setToolTip("Show helpful explanations when hovering over menus and buttons.")
        form.addRow(self.tooltips_cb)
        
        layout.addLayout(form)
        
        # Buttons
        btns = QHBoxLayout()
        ok_btn = QPushButton("Save")
        ok_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btns.addStretch()
        btns.addWidget(ok_btn)
        btns.addWidget(cancel_btn)
        layout.addLayout(btns)

    def _on_beta_toggled(self, checked: bool):
        if not checked:
            # User is trying to disable the warning
            dlg = BetaInitialsDialog(self)
            if dlg.exec() == QDialog.Accepted:
                self.beta_initials = dlg.get_initials()
                self.show_beta_warning = False
            else:
                # Cancelled, revert checkbox
                self.beta_cb.blockSignals(True)
                self.beta_cb.setChecked(True)
                self.beta_cb.blockSignals(False)
        else:
            self.show_beta_warning = True
            self.beta_initials = ""

    def _update_color_button(self, btn, color):
        btn.setStyleSheet(f"background-color: {color.name()}; border: 1px solid #888;")
        btn.setText(color.name())

    def _pick_text_color(self):
        color = QColorDialog.getColor(self.text_color, self, "Select Text Color")
        if color.isValid():
            self.text_color = color
            self._update_color_button(self.text_color_btn, color)

    def _pick_bg_color(self):
        color = QColorDialog.getColor(self.bg_color, self, "Select Background Color")
        if color.isValid():
            self.bg_color = color
            self._update_color_button(self.bg_color_btn, color)

    def _on_browse_projects_dir(self):
        path = QFileDialog.getExistingDirectory(self, "Select Projects Root Folder", self.projects_dir)
        if path:
            self.projects_dir = path
            self.projects_dir_label.setText(path)

    def get_data(self):
        return {
            "font": self.font_combo.currentText(),
            "font_size": self.font_size_spin.value(),
            "text_color": self.text_color.name(),
            "bg_color": self.bg_color.name(),
            "m_left": self.m_left_spin.value(),
            "m_right": self.m_right_spin.value(),
            "dynamic_margins": self.dynamic_cb.isChecked(),
            "max_content_width": self.max_width_spin.value(),
            "show_beta_warning": self.show_beta_warning,
            "beta_warning_initials": self.beta_initials,
            "projects_dir": self.projects_dir,
            "tooltips_enabled": self.tooltips_cb.isChecked()
        }

class ProjectPickerDialog(QDialog):
    """Dialog to pick an existing project or create a new one on startup."""

    def __init__(self, settings: AppSettings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.manager = ProjectManager(self.settings.projects_dir)
        self.selected_project: NovelProject | None = None
        
        self.setWindowTitle("PortoWrite — Project Picker")
        self.setMinimumSize(400, 300)
        
        self._setup_ui()
        self._refresh_list()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        layout.addWidget(QLabel("Select a project to open:"))
        
        self.project_list = QListWidget()
        self.project_list.itemDoubleClicked.connect(self._on_open_selected)
        layout.addWidget(self.project_list)
        
        btn_layout = QHBoxLayout()
        
        new_btn = QPushButton("New Project...")
        new_btn.clicked.connect(self._on_new_project)
        btn_layout.addWidget(new_btn)
        
        open_disk_btn = QPushButton("Open from Disk...")
        open_disk_btn.clicked.connect(self._on_open_from_disk)
        btn_layout.addWidget(open_disk_btn)
        
        layout.addLayout(btn_layout)
        
        # Action buttons
        actions = QHBoxLayout()
        self.open_btn = QPushButton("Open")
        self.open_btn.clicked.connect(self._on_open_selected)
        self.open_btn.setDefault(True)
        
        cancel_btn = QPushButton("Exit")
        cancel_btn.clicked.connect(self.reject)
        
        actions.addStretch()
        actions.addWidget(cancel_btn)
        actions.addWidget(self.open_btn)
        layout.addLayout(actions)

    def _refresh_list(self):
        self.project_list.clear()
        projects = self.manager.list_projects()
        for p in projects:
            self.project_list.addItem(p)
        
        if self.project_list.count() > 0:
            self.project_list.setCurrentRow(0)
            self.open_btn.setEnabled(True)
        else:
            self.open_btn.setEnabled(False)

    def _on_open_selected(self):
        item = self.project_list.currentItem()
        if not item:
            return
        
        name = item.text()
        try:
            self.selected_project = self.manager.open_project(name)
            self.accept()
        except Exception as e:
            logger.error("Failed to open project %s: %s", name, e)
            QMessageBox.critical(self, "Error", f"Could not open project: {e}")

    def _on_new_project(self):
        dlg = NewProjectDialog(self.settings, self)
        if dlg.exec() == QDialog.Accepted:
            data = dlg.get_data()
            try:
                self.selected_project = self.manager.create_project(
                    title=data["title"],
                    author=data["author"],
                    max_backups=data["max_backups"]
                )
                self.accept()
            except Exception as e:
                logger.error("Failed to create project: %s", e)
                QMessageBox.critical(self, "Error", f"Could not create project: {e}")

    def _on_open_from_disk(self):
        path = QFileDialog.getExistingDirectory(self, "Select Project Folder", self.settings.projects_dir)
        if path:
            try:
                self.selected_project = self.manager.open_project_by_path(path)
                self.accept()
            except Exception as e:
                logger.error("Failed to open project from %s: %s", path, e)
                QMessageBox.critical(self, "Error", f"That folder does not appear to be a valid PortoWrite project.\n\n({e})")


class NewProjectDialog(QDialog):
    """Small dialog to prompt for new project details."""

    def __init__(self, settings: AppSettings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.setWindowTitle("Create New Project")
        self.setMinimumSize(600, 500)
        
        layout = QVBoxLayout(self)
        form = QFormLayout()
        
        # 1. Title
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("e.g. My Great Novel")
        self.title_edit.setToolTip(
            "The name of your book. Used as the project folder name and in exported files.\n"
            "You can rename it later via File → Save As."
        )
        form.addRow("Novel Title:", self.title_edit)
        
        title_hint = QLabel("You can rename the project later from File > Save As")
        title_hint.setStyleSheet("color: #777; font-size: 10px; margin-top: -5px; margin-bottom: 10px;")
        form.addRow("", title_hint)
        
        # 2. Author
        self.author_edit = QLineEdit()
        self.author_edit.setPlaceholderText("e.g. Jane Smith")
        self.author_edit.setToolTip(
            "Your name as the author. Appears on the title page and in exported EPUB/DOCX metadata."
        )
        form.addRow("Author:", self.author_edit)
        
        # 3. Backups
        self.backups_spin = QSpinBox()
        self.backups_spin.setRange(0, 100)
        self.backups_spin.setValue(10)
        self.backups_spin.setToolTip(
            "PortoWrite saves a backup copy every time you save your project.\n"
            "This sets the maximum number of backups to keep — the oldest are deleted automatically\n"
            "when the limit is reached. Set to 0 to keep all backups forever."
        )
        form.addRow("Max Backups:", self.backups_spin)
        
        backups_hint = QLabel("(0 = unlimited) — oldest backups are deleted automatically when this limit is reached")
        backups_hint.setStyleSheet("color: #777; font-size: 10px; margin-top: -5px; margin-bottom: 10px;")
        form.addRow("", backups_hint)

        # 4. Location Display
        location_header = QLabel("Project Location:")
        location_header.setStyleSheet("font-weight: bold; margin-top: 10px;")
        form.addRow(location_header)
        
        loc_row = QHBoxLayout()
        self.root_label = QLabel(self.settings.projects_dir)
        self.root_label.setStyleSheet("color: #444; font-size: 11px;")
        self.root_label.setToolTip(
            "The main folder where all your PortoWrite projects are stored.\n"
            "Each project gets its own subfolder inside here."
        )
        loc_row.addWidget(self.root_label, 1)

        browse_btn = QPushButton("Change...")
        browse_btn.setToolTip(
            "Click to choose a different folder on your computer where projects will be stored.\n"
            "All future projects will be saved here by default."
        )
        browse_btn.clicked.connect(self._on_browse_location)
        loc_row.addWidget(browse_btn)
        form.addRow("Root Folder:", loc_row)

        self.path_label = QLabel()
        self.path_label.setWordWrap(True)
        self.path_label.setStyleSheet("color: #666; font-family: monospace; font-size: 11px; background-color: #f8f8f8; padding: 5px; border: 1px solid #ddd;")
        self.path_label.setToolTip(
            "The exact location on your computer where this project's files will be created.\n"
            "This folder is created automatically when you click Create Project."
        )
        form.addRow("Full Path:", self.path_label)
        
        path_hint = QLabel("Each project is stored in its own subfolder within the root.")
        path_hint.setStyleSheet("color: #777; font-size: 10px; margin-top: 2px;")
        form.addRow("", path_hint)
        
        layout.addLayout(form)
        layout.addStretch()
        
        # Buttons
        btns = QHBoxLayout()
        ok_btn = QPushButton("Create Project")
        ok_btn.clicked.connect(self._try_accept)
        ok_btn.setDefault(True)
        ok_btn.setMinimumHeight(35)
        ok_btn.setStyleSheet("font-weight: bold;")
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setMinimumHeight(35)
        
        btns.addStretch()
        btns.addWidget(cancel_btn)
        btns.addWidget(ok_btn)
        layout.addLayout(btns)

        # Signals
        self.title_edit.textChanged.connect(self._update_path_preview)
        self._update_path_preview()

    def _on_browse_location(self):
        path = QFileDialog.getExistingDirectory(self, "Select Projects Root Folder", self.settings.projects_dir)
        if path:
            self.settings.projects_dir = path
            self.settings.save()
            self.root_label.setText(path)
            self._update_path_preview()

    def _try_accept(self):
        if not self.title_edit.text().strip():
            QMessageBox.warning(self, "Title Required",
                                "Please enter a novel title before creating the project.")
            self.title_edit.setFocus()
            return
        self.accept()

    def _update_path_preview(self):
        title = self.title_edit.text().strip() or "Untitled"
        from porto_write.project import _safe_folder_name
        folder_name = _safe_folder_name(title)
        full_path = os.path.join(self.settings.projects_dir, folder_name)
        self.path_label.setText(full_path)

    def get_data(self):
        return {
            "title": self.title_edit.text().strip() or "Untitled",
            "author": self.author_edit.text().strip(),
            "max_backups": self.backups_spin.value()
        }


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


class StyleEditorDialog(QDialog):
    """Dialog for editing a single style definition."""

    def __init__(self, style: StyleDefinition, is_builtin: bool, parent=None):
        super().__init__(parent)
        self.style = style
        self.is_builtin = is_builtin
        self.setWindowTitle(f"Edit Style: {style.name}")
        self.setMinimumWidth(450)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        # 1. Name
        self.name_edit = QLineEdit(self.style.name)
        self.name_edit.setEnabled(not self.is_builtin)
        form.addRow("Style Name:", self.name_edit)

        # 2. Font
        self.font_combo = QFontComboBox()
        self.font_combo.setCurrentFont(self.style.font_family)
        form.addRow("Font Family:", self.font_combo)

        self.size_spin = QSpinBox()
        self.size_spin.setRange(8, 72)
        self.size_spin.setValue(int(self.style.font_size))
        form.addRow("Font Size (pt):", self.size_spin)

        # 3. Attributes
        checks = QHBoxLayout()
        self.bold_cb = QCheckBox("Bold")
        self.bold_cb.setChecked(self.style.bold)
        self.italic_cb = QCheckBox("Italic")
        self.italic_cb.setChecked(self.style.italic)
        self.underline_cb = QCheckBox("Underline")
        self.underline_cb.setChecked(self.style.underline)
        checks.addWidget(self.bold_cb)
        checks.addWidget(self.italic_cb)
        checks.addWidget(self.underline_cb)
        form.addRow("Style:", checks)

        # 4. Alignment
        self.align_combo = QComboBox()
        self.align_combo.addItems(["Left", "Center", "Right", "Justify"])
        idx = self.align_combo.findText(self.style.alignment.capitalize())
        if idx >= 0:
            self.align_combo.setCurrentIndex(idx)
        form.addRow("Alignment:", self.align_combo)

        # 5. Line Height
        self.lh_spin = QDoubleSpinBox()
        self.lh_spin.setRange(1.0, 3.0)
        self.lh_spin.setSingleStep(0.1)
        self.lh_spin.setValue(self.style.line_height)
        form.addRow("Line Height:", self.lh_spin)

        # 6. Spacing
        self.before_spin = QSpinBox()
        self.before_spin.setRange(0, 100)
        self.before_spin.setSuffix(" pt")
        self.before_spin.setValue(int(self.style.space_before))
        form.addRow("Space Before:", self.before_spin)

        self.after_spin = QSpinBox()
        self.after_spin.setRange(0, 100)
        self.after_spin.setSuffix(" pt")
        self.after_spin.setValue(int(self.style.space_after))
        form.addRow("Space After:", self.after_spin)

        # 7. Page Breaks
        pb_layout = QHBoxLayout()
        self.pb_before_cb = QCheckBox("Before")
        self.pb_before_cb.setChecked(self.style.page_break_before)
        self.pb_after_cb = QCheckBox("After")
        self.pb_after_cb.setChecked(self.style.page_break_after)
        pb_layout.addWidget(self.pb_before_cb)
        pb_layout.addWidget(self.pb_after_cb)
        form.addRow("Page Break:", pb_layout)

        layout.addLayout(form)

        # Buttons
        btns = QHBoxLayout()
        ok_btn = QPushButton("Apply")
        ok_btn.clicked.connect(self.accept)
        ok_btn.setDefault(True)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btns.addStretch()
        btns.addWidget(ok_btn)
        btns.addWidget(cancel_btn)
        layout.addLayout(btns)

    def get_data(self) -> dict:
        # Converting points from UI back to internal pixels
        # Formula: px = pt * (96 / 72) -> px = pt * 1.333...
        return {
            "name": self.name_edit.text().strip(),
            "font_family": self.font_combo.currentFont().family(),
            "font_size": self.size_spin.value(),
            "bold": self.bold_cb.isChecked(),
            "italic": self.italic_cb.isChecked(),
            "underline": self.underline_cb.isChecked(),
            "alignment": self.align_combo.currentText().lower(),
            "line_height": self.lh_spin.value(),
            "space_before": self.before_spin.value(),
            "space_after": self.after_spin.value(),
            "page_break_before": self.pb_before_cb.isChecked(),
            "page_break_after": self.pb_after_cb.isChecked(),
        }

class FindReplaceDialog(QDialog):
    def __init__(self, editor, parent=None):
        super().__init__(parent)
        self._editor = editor
        self.setWindowTitle("Find & Replace")
        self.setMinimumWidth(420)

        main_layout = QVBoxLayout()
        form_layout = QFormLayout()

        self.find_field = QLineEdit()
        self.replace_field = QLineEdit()
        form_layout.addRow("Find:", self.find_field)
        form_layout.addRow("Replace:", self.replace_field)
        main_layout.addLayout(form_layout)

        options_layout = QHBoxLayout()
        self.case_sensitive_checkbox = QCheckBox("Case sensitive")
        self.whole_word_checkbox = QCheckBox("Whole word")
        self.regex_checkbox = QCheckBox("Regex")
        options_layout.addWidget(self.case_sensitive_checkbox)
        options_layout.addWidget(self.whole_word_checkbox)
        options_layout.addWidget(self.regex_checkbox)
        main_layout.addLayout(options_layout)

        buttons_layout = QHBoxLayout()
        self.find_next_button = QPushButton("Find Next")
        self.find_prev_button = QPushButton("Find Prev")
        self.replace_button = QPushButton("Replace")
        self.replace_all_button = QPushButton("Replace All")
        buttons_layout.addWidget(self.find_next_button)
        buttons_layout.addWidget(self.find_prev_button)
        buttons_layout.addWidget(self.replace_button)
        buttons_layout.addWidget(self.replace_all_button)
        main_layout.addLayout(buttons_layout)

        self.status_label = QLabel()
        main_layout.addWidget(self.status_label)

        close_button = QPushButton("Close")
        close_button.clicked.connect(self.close)
        main_layout.addWidget(close_button)

        self.setLayout(main_layout)

        self.find_next_button.clicked.connect(self._on_find_next)
        self.find_prev_button.clicked.connect(self._on_find_prev)
        self.replace_button.clicked.connect(self._on_replace)
        self.replace_all_button.clicked.connect(self._on_replace_all)
        self.find_field.returnPressed.connect(self._on_find_next)

    def showEvent(self, event):
        super().showEvent(event)
        self.find_field.setFocus()

    def _opts(self):
        return (
            self.case_sensitive_checkbox.isChecked(),
            self.whole_word_checkbox.isChecked(),
            self.regex_checkbox.isChecked(),
        )

    def _on_find_next(self):
        if not self._editor.find_next(self.find_field.text(), *self._opts()):
            self.status_label.setText("Not found")
        else:
            self.status_label.clear()

    def _on_find_prev(self):
        if not self._editor.find_prev(self.find_field.text(), *self._opts()):
            self.status_label.setText("Not found")
        else:
            self.status_label.clear()

    def _on_replace(self):
        # replace_current replaces current match (if any) and advances to next
        self._editor.replace_current(
            self.find_field.text(), self.replace_field.text(), *self._opts()
        )
        self.status_label.clear()

    def _on_replace_all(self):
        count = self._editor.replace_all(
            self.find_field.text(), self.replace_field.text(), *self._opts()
        )
        self.status_label.setText(f"{count} replacement{'s' if count != 1 else ''} made")

class RestoreBackupDialog(QDialog):
    def __init__(self, project: NovelProject, parent=None):
        super().__init__(parent)
        self.project = project
        self.setWindowTitle("Restore from Backup")
        self.setFixedSize(500, 350)
        
        main_layout = QVBoxLayout(self)
        
        content_layout = QHBoxLayout()
        main_layout.addLayout(content_layout)
        
        # Left: List
        self.list_widget = QListWidget()
        content_layout.addWidget(self.list_widget, 1)
        
        # Right: Preview
        preview_group = QVBoxLayout()
        content_layout.addLayout(preview_group, 1)
        
        self.title_label = QLabel("<b>Select a backup</b>")
        self.title_label.setWordWrap(True)
        preview_group.addWidget(self.title_label)
        
        self.info_label = QLabel("")
        self.info_label.setWordWrap(True)
        preview_group.addWidget(self.info_label)
        preview_group.addStretch()
        
        # Buttons
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.button(QDialogButtonBox.StandardButton.Ok).setText("Restore")
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        main_layout.addWidget(self.button_box)
        
        self.list_widget.currentItemChanged.connect(self._on_selection_changed)
        self._populate()
        
    def _populate(self):
        backups = self.project.list_backups()
        for b in backups:
            self.list_widget.addItem(b)
        if not backups:
            self.title_label.setText("No backups found.")
            self.button_box.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)

    def _on_selection_changed(self, current, previous):
        if not current:
            return
        filename = current.text()
        try:
            doc = self.project.load_backup(filename)
            self.title_label.setText(f"<b>{doc.title}</b>")
            
            word_count = sum(len(b.text.split()) for ch in doc.chapters for b in ch.blocks)
            
            info = f"Author: {doc.author}\n"
            info += f"Chapters: {len(doc.chapters)}\n"
            info += f"Words: {word_count:,}\n\n"
            info += f"File: {filename}"
            
            self.info_label.setText(info)
        except Exception as e:
            self.title_label.setText("Error loading backup")
            self.info_label.setText(str(e))

    def get_selected_backup(self) -> str:
        item = self.list_widget.currentItem()
        return item.text() if item else ""

class SaveSnapshotDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Save Snapshot")
        self.setFixedSize(400, 250)
        
        layout = QVBoxLayout(self)
        form = QFormLayout()
        
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("e.g. End of Chapter 5")
        form.addRow("Snapshot Name:", self.name_edit)
        
        self.desc_edit = QTextEdit()
        self.desc_edit.setPlaceholderText("Optional details about this version...")
        self.desc_edit.setMaximumHeight(80)
        form.addRow("Description:", self.desc_edit)
        
        layout.addLayout(form)
        
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.button(QDialogButtonBox.StandardButton.Ok).setText("Save Snapshot")
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

    def get_data(self) -> tuple[str, str]:
        return self.name_edit.text().strip(), self.desc_edit.toPlainText().strip()

class VersionHistoryDialog(QDialog):
    def __init__(self, project: NovelProject, parent=None):
        super().__init__(parent)
        self.project = project
        self.setWindowTitle("Version History")
        self.setMinimumSize(650, 450)
        
        main_layout = QVBoxLayout(self)
        
        content_layout = QHBoxLayout()
        main_layout.addLayout(content_layout)
        
        # Left: List
        self.list_widget = QListWidget()
        content_layout.addWidget(self.list_widget, 2)
        
        # Right: Details
        details_group = QVBoxLayout()
        content_layout.addLayout(details_group, 3)
        
        self.name_label = QLabel("<b>Select a version</b>")
        self.name_label.setWordWrap(True)
        self.name_label.setStyleSheet("font-size: 14px;")
        details_group.addWidget(self.name_label)
        
        self.info_label = QLabel("")
        self.info_label.setWordWrap(True)
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        details_group.addWidget(self.info_label)
        details_group.addStretch()
        
        # Bottom Buttons
        btn_layout = QHBoxLayout()
        
        self.restore_btn = QPushButton("Restore Selected")
        self.restore_btn.setEnabled(False)
        self.restore_btn.clicked.connect(self.accept)
        self.restore_btn.setStyleSheet("font-weight: bold; padding: 5px;")
        btn_layout.addWidget(self.restore_btn)
        
        self.delete_btn = QPushButton("Delete")
        self.delete_btn.setEnabled(False)
        self.delete_btn.clicked.connect(self._on_delete)
        btn_layout.addWidget(self.delete_btn)
        
        btn_layout.addStretch()
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.reject)
        btn_layout.addWidget(close_btn)
        
        main_layout.addLayout(btn_layout)
        
        self.list_widget.currentItemChanged.connect(self._on_selection_changed)
        self._populate()
        
    def _populate(self):
        self.list_widget.clear()
        self.snapshots = self.project.list_snapshots()
        for s in self.snapshots:
            # Display name and short date
            display_text = f"{s['name']} ({s['date'][:10]})"
            item = QListWidgetItem(display_text)
            item.setData(Qt.ItemDataRole.UserRole, s)
            self.list_widget.addItem(item)
            
        if not self.snapshots:
            self.name_label.setText("No snapshots found.")
            self.info_label.setText("Use 'Save Snapshot' from the File menu to create permanent versions of your project.")
            self.restore_btn.setEnabled(False)
            self.delete_btn.setEnabled(False)

    def _on_selection_changed(self, current, previous):
        if not current:
            return
            
        s = current.data(Qt.ItemDataRole.UserRole)
        self.name_label.setText(f"<b>{s['name']}</b>")
        
        try:
            dt = datetime.fromisoformat(s['date'])
            date_str = dt.strftime('%Y-%m-%d %H:%M')
        except:
            date_str = s['date']
            
        info = f"Date: {date_str}\n"
        info += f"Words: {s.get('word_count', 0):,}\n\n"
        
        desc = s.get('description', '')
        if desc:
            info += f"Description:\n{desc}"
            
        self.info_label.setText(info)
        self.restore_btn.setEnabled(True)
        self.delete_btn.setEnabled(True)

    def _on_delete(self):
        item = self.list_widget.currentItem()
        if not item:
            return
            
        s = item.data(Qt.ItemDataRole.UserRole)
        res = QMessageBox.question(
            self, "Delete Snapshot",
            f"Are you sure you want to permanently delete the snapshot '{s['name']}'?\n\nThis cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if res == QMessageBox.StandardButton.Yes:
            try:
                self.project.delete_snapshot(s['filename'])
                self._populate()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not delete snapshot: {e}")

    def get_selected_filename(self) -> str:
        item = self.list_widget.currentItem()
        if item:
            s = item.data(Qt.ItemDataRole.UserRole)
            return s['filename']
        return ""

class HelpUserGuideDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("PortoWrite User Guide")
        self.resize(650, 550)
        
        layout = QVBoxLayout(self)
        
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        
        self._add_tab("Getting Started", self._get_started_html())
        self._add_tab("Writing", self._get_writing_html())
        self._add_tab("Styles", self._get_styles_html())
        self._add_tab("Exporting", self._get_export_html())
        self._add_tab("Backups & Versions", self._get_backup_html())
        
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _add_tab(self, title, html):
        browser = QTextBrowser()
        browser.setHtml(html)
        browser.setOpenExternalLinks(True)
        self.tabs.addTab(browser, title)

    def _get_started_html(self):
        return """
        <h2>Welcome to PortoWrite</h2>
        <p>PortoWrite is a specialized editor designed for novelists. It focuses on clean writing and seamless EPUB generation.</p>
        <h3>Core Workflows:</h3>
        <ul>
            <li><b>New Project:</b> File > New Project. Every novel lives in its own folder.</li>
            <li><b>Open Project:</b> File > Open Project or double-click a project.json.</li>
            <li><b>Project Metadata:</b> File > Project Metadata. Set your Title, Author, and Cover image here.</li>
        </ul>
        """

    def _get_writing_html(self):
        return """
        <h2>The Writing Experience</h2>
        <p>Use the main editor for your manuscript. PortoWrite handles chapters and subheadings via Styles.</p>
        <ul>
            <li><b>Chapters:</b> Use the 'Chapter Header' style for new chapters. They appear automatically in the Sidebar.</li>
            <li><b>Scene Breaks:</b> Insert > Scene Break (Ctrl+Shift+Enter) to insert ⚬ ⚬ ⚬.</li>
            <li><b>Page Breaks:</b> Insert > Page Break (Ctrl+Enter) to force a new page in the exported book.</li>
            <li><b>Spelling:</b> Misspelled words are underlined in red. Right-click for suggestions.</li>
        </ul>
        """

    def _get_styles_html(self):
        return """
        <h2>Mastering Styles</h2>
        <p>Styles control how your book looks. Use the Style Panel (right side) to apply and edit styles.</p>
        <ul>
            <li><b>Applying Styles:</b> Select text and click a style in the panel or use the toolbar dropdown.</li>
            <li><b>Editing Styles:</b> Right-click a style in the panel > Edit Style. Changes apply instantly to all text using that style.</li>
            <li><b>Built-in Styles:</b> 'Body', 'Chapter Header', and 'Sub Header' are default. You can create custom styles in the Pro edition.</li>
        </ul>
        """

    def _get_export_html(self):
        return """
        <h2>Exporting your Book</h2>
        <p>Convert your manuscript into a publishable format via File > Export As.</p>
        <ul>
            <li><b>EPUB:</b> The primary format for Kindle, Kobo, and Apple Books.</li>
            <li><b>Validation:</b> PortoWrite automatically validates your EPUB against industry standards.</li>
            <li><b>Platform Profiles:</b> Select 'Kindle' or 'Standard' profiles to optimize formatting for specific devices.</li>
            <li><b>TOC:</b> Use File > Table of Contents to review or rename entries before exporting.</li>
        </ul>
        """

    def _get_backup_html(self):
        return """
        <h2>Data Protection</h2>
        <p>Your work is precious. PortoWrite provides multiple layers of protection.</p>
        <ul>
            <li><b>Auto-Save:</b> Saves a recovery copy every 5 minutes (configurable in Preferences).</li>
            <li><b>Automatic Backups:</b> A full project backup is created every time you click 'Save'.</li>
            <li><b>Restore from Backup:</b> File > Restore from Backup. View previews and word counts before rolling back.</li>
            <li><b>Snapshots:</b> File > Save Snapshot. Use these for permanent 'milestone' versions (e.g., 'First Draft Complete').</li>
        </ul>
        """

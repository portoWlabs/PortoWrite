import logging
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
    QLabel, QFormLayout, QSpinBox, QFileDialog, QComboBox, 
    QFontComboBox, QColorDialog, QCheckBox
)
from PySide6.QtGui import QColor, QFontDatabase
from PySide6.QtCore import Qt
from porto_write.constants import KINDLE_FONTS
from porto_write.ui.dialogs.project import BetaInitialsDialog

logger = logging.getLogger(__name__)

class DisplayPreferencesDialog(QDialog):
    """Dialog for customizing editor font and colors."""

    def __init__(self, parent, current_font, current_font_size, current_text_color, current_bg_color,
                 current_m_left, current_m_right, text_margin_chars, dynamic_enabled, max_width_chars,
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
        self.text_margin_chars = text_margin_chars
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

        self.text_margin_chars_spin = QSpinBox()
        self.text_margin_chars_spin.setRange(0, 10)
        self.text_margin_chars_spin.setValue(self.text_margin_chars)
        self.text_margin_chars_spin.setToolTip("Set text padding from left and right edges in character widths (0 = disabled).")
        form.addRow("Text Margin (characters):", self.text_margin_chars_spin)

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
            "text_margin_chars": self.text_margin_chars_spin.value(),
            "dynamic_margins": self.dynamic_cb.isChecked(),
            "max_content_width": self.max_width_spin.value(),
            "show_beta_warning": self.show_beta_warning,
            "beta_warning_initials": self.beta_initials,
            "projects_dir": self.projects_dir,
            "tooltips_enabled": self.tooltips_cb.isChecked()
        }

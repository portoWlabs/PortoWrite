import logging
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QLineEdit, QFormLayout, QSpinBox, QCheckBox,
    QFontComboBox, QComboBox, QDoubleSpinBox, QDialogButtonBox
)
from PySide6.QtCore import Qt
from porto_write.styles import StyleDefinition

logger = logging.getLogger(__name__)

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

import logging
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from porto_write.constants import STYLE_NAME_PROPERTY
from porto_write.styles import StyleDefinition

logger = logging.getLogger(__name__)

class StyleMixin:
    """Mixin for style management and toolbar synchronization in MainWindow."""

    def _on_style_added(self, data: dict):
        from porto_write.styles import StyleDefinition
        new_style = StyleDefinition(**data)
        self.project.doc.add_style(new_style)
        self.style_panel.refresh(self.project.doc.styles)
        self.toolbar.refresh_styles(self.project.doc.styles.names())
        self.is_dirty = True
        self._update_title()

    def _on_style_updated(self, old_name: str, data: dict):
        new_name = data["name"]
        style = self.project.doc.styles.get(old_name)
        if not style: return

        # Update properties
        for k, v in data.items():
            setattr(style, k, v)

        if old_name != new_name:
            self.project.doc.rename_style(old_name, new_name)
        
        # Refresh UI
        self.style_panel.refresh(self.project.doc.styles)
        self.toolbar.refresh_styles(self.project.doc.styles.names())
        self.editor.refresh_styling()
        self._update_preview()
        
        self.is_dirty = True
        self._update_title()

    def _on_style_deleted(self, name: str):
        # First, revert blocks in the document model
        for chapter in self.project.doc.chapters:
            for block in chapter.blocks:
                if block.style_name == name:
                    block.style_name = "Body"
        
        # Remove from registry
        self.project.doc.remove_style(name)
        
        # Refresh UI
        self.style_panel.refresh(self.project.doc.styles)
        self.toolbar.refresh_styles(self.project.doc.styles.names())
        self.editor.refresh_styling()
        self._update_preview()
        
        self.is_dirty = True
        self._update_title()

    def _on_toolbar_style_selected(self, index: int):
        style_name = self.toolbar.style_combo.currentText()
        style = self.project.doc.styles.get(style_name)
        if style:
            self.editor.apply_style(style)
            # The editor will emit cursorPositionChanged, triggering _update_toolbar_states

    def _on_style_hotkey(self, style_name: str):
        style = self.project.doc.styles.get(style_name)
        if style:
            self.editor.apply_style(style)
            # The editor will emit cursorPositionChanged, triggering _update_toolbar_states

    def _update_toolbar_states(self):
        """Update Bold/Italic/Underline button checked state and style indicators based on current cursor format."""
        cursor = self.editor.textCursor()
        char_fmt = cursor.charFormat()
        block_fmt = cursor.blockFormat()
        
        # 1. Basic Formatting
        self.toolbar.bold_action.setChecked(char_fmt.fontWeight() == QFont.Weight.Bold)
        self.toolbar.italic_action.setChecked(char_fmt.fontItalic())
        self.toolbar.underline_action.setChecked(char_fmt.fontUnderline())

        # 1.1 Alignment Formatting
        align = block_fmt.alignment()
        self.toolbar.align_left_action.setChecked(bool(align & Qt.AlignmentFlag.AlignLeft))
        self.toolbar.align_center_action.setChecked(bool(align & Qt.AlignmentFlag.AlignHCenter))
        self.toolbar.align_right_action.setChecked(bool(align & Qt.AlignmentFlag.AlignRight))
        self.toolbar.align_justify_action.setChecked(bool(align & Qt.AlignmentFlag.AlignJustify))
        
        # 2. Style Synchronization
        style_name = block_fmt.property(STYLE_NAME_PROPERTY)
        if style_name:
            # Map internal names to visible aliases for UI selection (B2)
            _ALIASES = {
                "ChapterHeader": "Heading1",
                "SubHeader": "Heading2",
            }
            lookup = _ALIASES.get(style_name, style_name)

            # Update Toolbar Dropdown
            self.toolbar.style_combo.blockSignals(True)
            idx = self.toolbar.style_combo.findText(lookup)
            if idx >= 0:
                self.toolbar.style_combo.setCurrentIndex(idx)
            else:
                self.toolbar.style_combo.setCurrentIndex(-1)
            self.toolbar.style_combo.blockSignals(False)
            
            # Update Style Panel
            self.style_panel.blockSignals(True)
            self.style_panel.select_style(lookup)
            self.style_panel.blockSignals(False)

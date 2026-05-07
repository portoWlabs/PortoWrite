import json
import logging
import re
from typing import Optional
from PySide6.QtWidgets import QTextEdit, QMenu, QApplication
from PySide6.QtGui import (
    QTextCursor, QTextBlockFormat, QTextCharFormat,
    QFont, QAction, QKeySequence,
    QTextFrameFormat, QTextDocument
)
from PySide6.QtCore import Signal, Qt, QRegularExpression, QMimeData, QTimer
from porto_write.constants import STYLE_NAME_PROPERTY, DROP_CAP_PROPERTY
from porto_write.document import PortoDocument, TextBlock, Chapter
from porto_write.styles import StyleDefinition
from porto_write.ui.spell_highlighter import SpellCheckHighlighter
from porto_write.ui.find_replace_mixin import FindReplaceMixin

logger = logging.getLogger(__name__)

class EditorWidget(FindReplaceMixin, QTextEdit):
    """WYSIWYG editor for PortoWrite documents."""
    
    style_hotkey_triggered = Signal(str)
    active_chapter_changed = Signal(int)
    zoom_changed = Signal(float)
    stats_changed = Signal(int, int) 
    structure_changed = Signal() 
    current_style_changed = Signal(str)
    style_updated = Signal(str, dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptRichText(True)
        self._zoom_steps = 0
        self._zoom_factor = 1.0  # Base scale multiplier
        self._user_margin_left = 0
        self._user_margin_right = 0
        self._text_margin_chars = 0  # Character-width based margin (0 = disabled)
        self._max_content_width = None
        self.spell_checker = None
        self._chapter_positions = []
        self._current_doc_ref = None
        self._ebook_mode = False # S20.1
        self._suppress_refresh = False
        self.highlighter = None  # S20.4
        self._display_font_override: Optional[str] = None
        self._display_line_height_override: Optional[float] = None
        self._setup_shortcuts()
        self._stats_timer = QTimer(self)
        self._stats_timer.setSingleShot(True)
        self._stats_timer.setInterval(400)
        self._stats_timer.timeout.connect(self._update_stats)
        self.textChanged.connect(self._stats_timer.start)

        self._layout_timer = QTimer(self)
        self._layout_timer.setSingleShot(True)
        self._layout_timer.setInterval(150)
        self._layout_timer.timeout.connect(self._update_layout)

        self._style_timer = QTimer(self)
        self._style_timer.setSingleShot(True)
        self._style_timer.setInterval(200)
        self._style_timer.timeout.connect(self.refresh_styling)

        self.cursorPositionChanged.connect(self._check_active_chapter)

    def set_spell_checker(self, spell_checker):
        self.spell_checker = spell_checker

    def set_highlighter(self, highlighter):
        self.highlighter = highlighter

    def set_display_font_override(self, font_name: Optional[str]):
        """Set a render-time font override (None = use style-defined fonts)."""
        self._display_font_override = font_name
        self.refresh_styling()

    def set_display_line_height_override(self, value: Optional[float]):
        """Set a temporary line-height multiplier for ebook mode; None restores normal spacing."""
        self._display_line_height_override = value
        self.refresh_styling()

    def _check_active_chapter(self):
        """Emit active_chapter_changed signal if the cursor has moved into a different chapter."""
        idx = self.current_chapter_index()
        if hasattr(self, "_last_active_chapter") and self._last_active_chapter == idx:
            return
        self._last_active_chapter = idx
        self.active_chapter_changed.emit(idx)

    def current_chapter_index(self) -> int:
        """Return the index of the chapter containing the cursor, or -1."""
        current_block = self.textCursor().blockNumber()
        idx = -1
        for i, block_num in enumerate(self._chapter_positions):
            if block_num <= current_block:
                idx = i
            else:
                break
        return idx

    def top_visible_block_ids(self) -> tuple | None:
        """Return (chap_idx, block_idx) for the topmost block visible in the viewport."""
        from PySide6.QtCore import QPoint
        cursor = self.cursorForPosition(QPoint(0, 0))
        block_num = cursor.block().blockNumber()
        chap_idx = -1
        for i, start in enumerate(self._chapter_positions):
            if start <= block_num:
                chap_idx = i
            else:
                break
        if chap_idx < 0:
            return None
        block_idx = block_num - self._chapter_positions[chap_idx]
        return (chap_idx, block_idx)

    def contextMenuEvent(self, event):
        menu = self.createStandardContextMenu()
        cursor = self.cursorForPosition(event.pos())
        cursor.select(QTextCursor.SelectionType.WordUnderCursor)
        word = cursor.selectedText().strip()
        if word and self.spell_checker and not self.spell_checker.check(word):
            suggestions = self.spell_checker.suggest(word)
            if suggestions:
                first_action = menu.actions()[0]
                for sugg in reversed(suggestions[:5]):
                    action = QAction(sugg, menu)
                    action.triggered.connect(lambda checked=False, s=sugg, c=cursor: self._replace_word(c, s))
                    menu.insertAction(first_action, action)
                menu.insertSeparator(first_action)
            add_dict_action = QAction(f"Add '{word}' to Dictionary", menu)
            add_dict_action.triggered.connect(lambda checked=False, w=word: self._add_to_dictionary(w))
            menu.insertAction(menu.actions()[0], add_dict_action)
            menu.insertSeparator(menu.actions()[1])

        menu.addSeparator()

        spacing_action = QAction("Paragraph Spacing...", menu)
        spacing_action.triggered.connect(self._open_paragraph_spacing_dialog)
        menu.addAction(spacing_action)

        if self._current_doc_ref:
            style_menu = QMenu("Apply Style", menu)
            for style in self._current_doc_ref.styles.all():
                act = QAction(style.name, style_menu)
                act.triggered.connect(lambda checked=False, s=style: self.apply_style(s))
                style_menu.addAction(act)
            menu.addMenu(style_menu)

            # Drop Cap Toggle
            style_name = cursor.block().blockFormat().property(STYLE_NAME_PROPERTY)
            if style_name == "Body":
                menu.addSeparator()
                is_drop_cap = bool(cursor.block().blockFormat().property(DROP_CAP_PROPERTY))
                drop_cap_action = QAction("Remove Drop Cap" if is_drop_cap else "Add Drop Cap", menu)
                drop_cap_action.triggered.connect(self.toggle_drop_cap)
                menu.addAction(drop_cap_action)

            # Update Style to Match
            if style_name not in ("PageBreak", "SceneBreak"):
                menu.addSeparator()
                update_style_action = QAction(f"Update Style '{style_name}' to Match", menu)
                update_style_action.triggered.connect(self.update_style_to_match)
                menu.addAction(update_style_action)

        if self.textCursor().hasSelection():
            menu.addSeparator()
            copy_fmt_action = QAction("Copy with Format", menu)
            copy_fmt_action.triggered.connect(self.copy_with_format)
            menu.addAction(copy_fmt_action)

        menu.exec(event.globalPos())

    def update_style_to_match(self):
        if not self._current_doc_ref:
            return
            
        cursor = self.textCursor()
        block = cursor.block()
        block_fmt = block.blockFormat()
        char_fmt = block.charFormat()
        
        style_name = block_fmt.property(STYLE_NAME_PROPERTY) or "Body"
        
        # Mapping alignment
        align = block_fmt.alignment()
        if align & Qt.AlignmentFlag.AlignCenter:
            alignment = "center"
        elif align & Qt.AlignmentFlag.AlignRight:
            alignment = "right"
        elif align & Qt.AlignmentFlag.AlignJustify:
            alignment = "justify"
        else:
            alignment = "left"
            
        dpi_scale = self.logicalDpiY() / 72.0
        
        data = {
            "name": style_name,
            "font_family": char_fmt.fontFamily(),
            "font_size": int(char_fmt.fontPointSize() / self._zoom_factor),
            "bold": char_fmt.fontWeight() == QFont.Weight.Bold,
            "italic": char_fmt.fontItalic(),
            "underline": char_fmt.fontUnderline(),
            "alignment": alignment,
            "space_before": int(block_fmt.topMargin() / dpi_scale),
            "space_after": int(block_fmt.bottomMargin() / dpi_scale)
        }
        
        self.style_updated.emit(style_name, data)

    def copy_with_format(self):
        """Copies the selected text along with style metadata to the clipboard."""
        cursor = self.textCursor()
        if not cursor.hasSelection():
            return
            
        plain_text = cursor.selectedText()
        # Replace paragraph separator with newline
        plain_text = plain_text.replace('\u2029', '\n')
        
        # Use the format at the start of the selection for metadata
        char_fmt = cursor.charFormat()
        block_fmt = cursor.block().blockFormat()
        
        style_name = block_fmt.property(STYLE_NAME_PROPERTY) or "Body"
        
        metadata = {
            "style_name": style_name,
            "font_family": char_fmt.fontFamily(),
            "font_size": char_fmt.fontPointSize() / self._zoom_factor,
            "bold": char_fmt.fontWeight() == QFont.Weight.Bold,
            "italic": char_fmt.fontItalic(),
            "underline": char_fmt.fontUnderline(),
        }
        
        mime_data = QMimeData()
        mime_data.setText(plain_text)
        mime_data.setData("application/x-portowrite-block", json.dumps(metadata).encode('utf-8'))
        
        QApplication.clipboard().setMimeData(mime_data)
        logger.debug("Copied with format: %s", style_name)

    def _open_paragraph_spacing_dialog(self):
        from porto_write.ui.dialogs import ParagraphSpacingDialog
        dlg = ParagraphSpacingDialog(self)
        if dlg.exec():
            before, after = dlg.get_values()
            self.apply_paragraph_spacing(before, after)

    def apply_paragraph_spacing(self, before: int, after: int):
        """Apply spacing (in points) to selected blocks without changing their style definition."""
        dpi_scale = self.logicalDpiY() / 72.0
        cursor = self.textCursor()
        start_block = self.document().findBlock(cursor.selectionStart()).blockNumber()
        end_block = self.document().findBlock(cursor.selectionEnd()).blockNumber()
        cursor.beginEditBlock()
        for i in range(start_block, end_block + 1):
            block = self.document().findBlockByNumber(i)
            if block.isValid():
                fmt = block.blockFormat()
                fmt.setTopMargin(before * dpi_scale)
                fmt.setBottomMargin(after * dpi_scale)
                temp = QTextCursor(block)
                temp.setBlockFormat(fmt)
        cursor.endEditBlock()

    def insert_page_break(self):
        """Insert a PageBreak marker paragraph at the current cursor position."""
        from porto_write.styles import StyleDefinition
        style = None
        if self._current_doc_ref:
            style = self._current_doc_ref.styles.get("PageBreak")
        if style is None:
            style = StyleDefinition(
                name="PageBreak", font_family="Georgia", font_size=10,
                italic=True, alignment="center", space_before=8, space_after=8,
                page_break_before=True,
            )
        cursor = self.textCursor()
        prev_style_name = cursor.block().blockFormat().property(STYLE_NAME_PROPERTY)
        cursor.beginEditBlock()
        cursor.insertBlock()
        cursor.insertText("── Page Break ──")
        block_fmt = self._style_to_block_format(style, prev_style_name)
        char_fmt = self._style_to_char_format(style)
        cursor.setBlockFormat(block_fmt)
        cursor.setBlockCharFormat(char_fmt)
        
        # Insert a new block after the break and set it to Body with no indent
        cursor.insertBlock()
        body_style = self._current_doc_ref.styles.get("Body") if self._current_doc_ref else None
        if body_style:
            cursor.setBlockFormat(self._style_to_block_format(body_style, "PageBreak"))
            cursor.setCharFormat(self._style_to_char_format(body_style))
        
        cursor.endEditBlock()
        self.setTextCursor(cursor)

    def insert_scene_break(self):
        """Insert a SceneBreak marker paragraph at the current cursor position."""
        from porto_write.styles import StyleDefinition
        style = None
        if self._current_doc_ref:
            style = self._current_doc_ref.styles.get("SceneBreak")
        if style is None:
            style = StyleDefinition(
                name="SceneBreak", font_family="Georgia", font_size=11,
                italic=False, alignment="center", space_before=12, space_after=12,
                page_break_before=False,
            )
        cursor = self.textCursor()
        prev_style_name = cursor.block().blockFormat().property(STYLE_NAME_PROPERTY)
        cursor.beginEditBlock()
        cursor.insertBlock()
        cursor.insertText("⚬ ⚬ ⚬")
        block_fmt = self._style_to_block_format(style, prev_style_name)
        char_fmt = self._style_to_char_format(style)
        cursor.setBlockFormat(block_fmt)
        cursor.setBlockCharFormat(char_fmt)
        
        # Insert a new block after the break and set it to Body with no indent
        cursor.insertBlock()
        body_style = self._current_doc_ref.styles.get("Body") if self._current_doc_ref else None
        if body_style:
            cursor.setBlockFormat(self._style_to_block_format(body_style, "SceneBreak"))
            cursor.setCharFormat(self._style_to_char_format(body_style))

        cursor.endEditBlock()
        self.setTextCursor(cursor)

    def _replace_word(self, cursor, new_word):
        cursor.beginEditBlock()
        cursor.insertText(new_word)
        cursor.endEditBlock()

    def _add_to_dictionary(self, word):
        if self.spell_checker:
            self.spell_checker.add_to_user_dict(word)
            # Rehighlight via the highlighter stored on this widget (works in both
            # standard and ebook mode; parent().highlighter is unreliable in ebook mode
            # because the editor's parent is EbookFrameWidget, not MainWindow).
            if self.highlighter:
                self.highlighter.rehighlight()
            else:
                self.document().markContentsDirty(0, self.document().characterCount())

    def _update_stats(self):
        text = self.toPlainText()
        self.stats_changed.emit(len(text.split()), len(text))
        
        old_positions = list(self._chapter_positions)
        self._chapter_positions = []
        block = self.document().begin()
        while block.isValid():
            style_name = block.blockFormat().property(STYLE_NAME_PROPERTY)
            if style_name in ("ChapterHeader", "Heading1", "SubHeader", "Heading2"):
                self._chapter_positions.append(block.blockNumber())
            block = block.next()
        if self._chapter_positions != old_positions:
            self.structure_changed.emit()

    @property
    def zoom_steps(self) -> int:
        return self._zoom_steps

    def set_zoom_steps(self, steps: int):
        """Update the internal zoom level and refresh the document."""
        self._zoom_steps = steps
        self._zoom_factor = 1.0 + (steps * 0.1)
        self._zoom_factor = max(0.1, self._zoom_factor)
        self._style_timer.start()

    def zoomIn(self, range=1):
        self._zoom_steps += range
        self.set_zoom_steps(self._zoom_steps)
        self.zoom_changed.emit(float(self._zoom_steps))

    def zoomOut(self, range=1):
        self._zoom_steps -= range
        self.set_zoom_steps(self._zoom_steps)
        self.zoom_changed.emit(float(self._zoom_steps))

    def batch_updates(self, enable: bool):
        """Enable or disable batching of layout/style refreshes.

        While True, calls to refresh_styling() and _update_layout() are suppressed.
        Set to False and then call refresh_styling() manually to apply the accumulated
        changes in a single pass.
        """
        self._suppress_refresh = enable

    def refresh_styling(self):
        """Iterate through all blocks and re-apply styles using the current zoom factor."""
        if self._suppress_refresh:
            return
        if not self._current_doc_ref:
            return
        
        cursor = self.textCursor()
        curr_pos = cursor.position()
        cursor.beginEditBlock()
        
        block = self.document().begin()
        prev_style_name = None
        while block.isValid():
            style_name = block.blockFormat().property(STYLE_NAME_PROPERTY) or "Body"
            style = self._current_doc_ref.styles.get(style_name)
            if style:
                temp_cursor = QTextCursor(block)
                # Apply formats precisely
                temp_cursor.setBlockFormat(self._style_to_block_format(style, prev_style_name))
                temp_cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock, QTextCursor.MoveMode.KeepAnchor)
                temp_cursor.setCharFormat(self._style_to_char_format(style))
            prev_style_name = style_name
            block = block.next()
            
        cursor.endEditBlock()
        # Restore cursor position
        cursor.setPosition(curr_pos)
        self.setTextCursor(cursor)

    def set_max_content_width(self, width_chars: int | None):
        self._max_content_width = width_chars
        self._update_layout()

    def set_visual_margins(self, left: int, right: int):
        self._user_margin_left = left
        self._user_margin_right = right
        self._update_layout()

    def set_text_margin_chars(self, char_count: int):
        """Set text padding from edges in character widths (0 = disabled)."""
        self._text_margin_chars = char_count
        self._update_layout()

    def set_ebook_mode(self, enabled: bool, profile: dict):
        """Toggle device-accurate writing frame. Caller is responsible for restoring palette/margins on disable."""
        self._ebook_mode = enabled
        
        if enabled:
            # Performance: set fields directly to avoid redundant _update_layout() calls
            self._max_content_width = profile.get("content_width_chars")
            self._user_margin_left, self._user_margin_right = profile.get("margins", (40, 40))

            self.setViewportMargins(60, 20, 60, 60)
        else:
            self._max_content_width = None
            self._user_margin_left = 0
            self._user_margin_right = 0

            self.setViewportMargins(0, 0, 0, 0)
            self.viewport().setPalette(self.style().standardPalette())
        
        if self.highlighter:
            self.highlighter.set_ebook_mode(enabled)
            
        self._update_layout()

    def _update_layout(self):
        if self._suppress_refresh:
            return
        left = self._user_margin_left
        right = self._user_margin_right

        # Calculate character-width based margins if enabled
        if self._text_margin_chars > 0:
            from PySide6.QtGui import QFont, QFontMetrics
            font_family = self._display_font_override if self._display_font_override else self.font().family()
            font = QFont(font_family)
            widget_size = self.font().pointSize()
            base_size = widget_size if widget_size > 0 else 11
            font.setPointSize(base_size)
            fm = QFontMetrics(font)
            char_width = fm.horizontalAdvance('0')
            char_margin = char_width * self._text_margin_chars
            left = self._user_margin_left + char_margin
            right = self._user_margin_right + char_margin

        if self._max_content_width:
            # Calculate pixel width based on average character width
            from PySide6.QtGui import QFont, QFontMetrics
            # Use the display font override if available, otherwise the widget font
            font_family = self._display_font_override if self._display_font_override else self.font().family()
            font = QFont(font_family)
            # Use a reasonable base size if the widget font is too small (e.g. system default)
            widget_size = self.font().pointSize()
            base_size = widget_size if widget_size > 0 else 11
            font.setPointSize(base_size)

            fm = QFontMetrics(font)
            char_width = fm.horizontalAdvance('0')
            px_width = char_width * self._max_content_width

            available_width = self.viewport().width()
            # Respect asymmetric minimum margins by centering the block within the remaining space
            extra_space = available_width - px_width - left - right
            if extra_space > 0:
                auto_margin = extra_space // 2
                left = left + auto_margin
                right = right + auto_margin

        doc = self.document()
        fmt = doc.rootFrame().frameFormat()
        if fmt.leftMargin() != left or fmt.rightMargin() != right:
            fmt.setLeftMargin(left)
            fmt.setRightMargin(right)
            doc.rootFrame().setFrameFormat(fmt)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._layout_timer.start()

    def wheelEvent(self, event):
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            delta = event.angleDelta().y()
            if delta > 0:
                self.zoomIn(1)
            else:
                self.zoomOut(1)
            event.accept()
        else:
            super().wheelEvent(event)

    def _setup_shortcuts(self):
        self.bold_action = QAction("Bold", self)
        self.bold_action.setShortcut(QKeySequence.StandardKey.Bold)
        self.bold_action.triggered.connect(self.toggle_bold)
        self.addAction(self.bold_action)
        self.italic_action = QAction("Italic", self)
        self.italic_action.setShortcut(QKeySequence.StandardKey.Italic)
        self.italic_action.triggered.connect(self.toggle_italic)
        self.addAction(self.italic_action)
        self.underline_action = QAction("Underline", self)
        self.underline_action.setShortcut(QKeySequence.StandardKey.Underline)
        self.underline_action.triggered.connect(self.toggle_underline)
        self.addAction(self.underline_action)

        style_keys = [
            (Qt.Modifier.CTRL | Qt.Key.Key_1, "ChapterHeader"),
            (Qt.Modifier.CTRL | Qt.Key.Key_2, "SubHeader"),
            (Qt.Modifier.CTRL | Qt.Key.Key_3, "Body"),
            (Qt.Modifier.CTRL | Qt.Key.Key_4, "BlockQuote"),
        ]
        for key, style_name in style_keys:
            action = QAction(f"Apply {style_name}", self)
            action.setShortcut(QKeySequence(key))
            action.triggered.connect(lambda checked=False, s=style_name: self.style_hotkey_triggered.emit(s))
            self.addAction(action)

    def load_document(self, doc: PortoDocument):
        """Load a PortoDocument into the editor with styling."""
        self._current_doc_ref = doc
        self.document().blockSignals(True)
        try:
            self.clear()
            self._chapter_positions = []
            cursor = self.textCursor()
            
            if not doc.chapters:
                body_style = doc.styles.get("Body")
                if body_style:
                    cursor.setBlockFormat(self._style_to_block_format(body_style, None))
                    cursor.setCharFormat(self._style_to_char_format(body_style))
                self._update_layout()
                return

            cursor.beginEditBlock()
            for i, chapter in enumerate(doc.chapters):
                self._chapter_positions.append(cursor.blockNumber())
                prev_style_name = None
                if chapter.title:
                    header_style = doc.styles.get("ChapterHeader")
                    if header_style:
                        self._insert_styled_block(cursor, chapter.title, header_style, prev_style_name)
                        prev_style_name = "ChapterHeader"
                    else:
                        cursor.insertText(chapter.title)
                        cursor.insertBlock()
                for block in chapter.blocks:
                    style = doc.styles.get(block.style_name)
                    if style:
                        self._insert_styled_block(cursor, block.text, style, prev_style_name)
                        prev_style_name = block.style_name
                    else:
                        cursor.insertText(block.text)
                        cursor.insertBlock()
                        prev_style_name = block.style_name
                
                body_style = doc.styles.get("Body")
                if body_style:
                    cursor.setBlockFormat(self._style_to_block_format(body_style, prev_style_name))
                    cursor.setCharFormat(self._style_to_char_format(body_style))
            cursor.endEditBlock()
        finally:
            self.document().blockSignals(False)

        self._update_stats()
        self._update_layout()
        logger.debug("Document loaded.")

    def scroll_to_chapter(self, index: int):
        """Scroll so the selected chapter is at the TOP of the screen."""
        if 0 <= index < len(self._chapter_positions):
            block_num = self._chapter_positions[index]
            block = self.document().findBlockByNumber(block_num)
            if block.isValid():
                cursor = self.textCursor()
                cursor.setPosition(block.position())
                self.setTextCursor(cursor)
                # Calculate Y position relative to document
                y_pos = self.cursorRect(cursor).top()
                # Adjust for current scrollbar offset to get absolute document coordinate
                absolute_y = y_pos + self.verticalScrollBar().value()
                self.verticalScrollBar().setValue(absolute_y)
                logger.debug("Scrolled chapter %d to top.", index)

    def scroll_to_block(self, chap_idx: int, b_idx: int):
        """Scroll to a specific block within a chapter and place the cursor."""
        if 0 <= chap_idx < len(self._chapter_positions):
            start_block_num = self._chapter_positions[chap_idx]
            target_block_num = start_block_num + b_idx
            
            block = self.document().findBlockByNumber(target_block_num)
            if block.isValid():
                cursor = self.textCursor()
                cursor.setPosition(block.position())
                self.setTextCursor(cursor)
                self.setFocus()
                
                # Center the block in the viewport if possible
                viewport_height = self.viewport().height()
                rect = self.cursorRect(cursor)
                cursor_y_in_viewport = rect.center().y()
                current_scroll = self.verticalScrollBar().value()
                
                target_scroll = current_scroll + cursor_y_in_viewport - (viewport_height // 2)
                self.verticalScrollBar().setValue(max(0, target_scroll))
                
                logger.debug("Scrolled to chap %d, block %d (block_num %d)", chap_idx, b_idx, target_block_num)

    def _insert_styled_block(self, cursor: QTextCursor, text: str, style: StyleDefinition, prev_style_name: str = None):
        block_format = self._style_to_block_format(style, prev_style_name)
        char_format = self._style_to_char_format(style)
        cursor.setBlockFormat(block_format)
        cursor.setCharFormat(char_format)
        cursor.insertText(text)
        cursor.insertBlock()
        cursor.setBlockFormat(QTextBlockFormat())
        cursor.setCharFormat(QTextCharFormat())

    def _style_to_block_format(self, style: StyleDefinition, prev_style_name: str = None) -> QTextBlockFormat:
        fmt = QTextBlockFormat()
        fmt.setProperty(STYLE_NAME_PROPERTY, style.name)
        if style.alignment == "center":
            fmt.setAlignment(Qt.AlignmentFlag.AlignCenter)
        elif style.alignment == "right":
            fmt.setAlignment(Qt.AlignmentFlag.AlignRight)
        elif style.alignment == "justify":
            fmt.setAlignment(Qt.AlignmentFlag.AlignJustify)
        else:
            fmt.setAlignment(Qt.AlignmentFlag.AlignLeft)
        
        lh = self._display_line_height_override if self._display_line_height_override is not None else style.line_height
        fmt.setLineHeight(float(lh * 100), QTextBlockFormat.LineHeightTypes.ProportionalHeight.value)

        dpi_scale = self.logicalDpiY() / 72.0

        fmt.setTopMargin(style.space_before * dpi_scale)
        fmt.setBottomMargin(style.space_after * dpi_scale)
        
        # Specialized Ebook Mode handling for PageBreak
        if style.name == "PageBreak" and self._ebook_mode:
            fmt.setTopMargin(40 * dpi_scale)
            fmt.setBottomMargin(20 * dpi_scale)
            fmt.setAlignment(Qt.AlignmentFlag.AlignCenter)
        elif style.page_break_before or style.name == "ChapterHeader":
            fmt.setTopMargin(max(style.space_before, 40) * dpi_scale)

        if style.name == "Body":
            suppress = ("ChapterHeader", "Heading1", "Heading2", "SubHeader", "SceneBreak", "PageBreak")
            if prev_style_name in suppress:
                fmt.setTextIndent(0)
            else:
                fmt.setTextIndent(18 * dpi_scale)

        return fmt

    def _style_to_char_format(self, style: StyleDefinition) -> QTextCharFormat:
        fmt = QTextCharFormat()
        _MONOSPACE_STYLES = {"Code"}
        use_override = self._display_font_override and style.name not in _MONOSPACE_STYLES
        font_family = self._display_font_override if use_override else style.font_family
        fmt.setFontFamily(font_family)
        fmt.setFontPointSize(style.font_size * self._zoom_factor)
        
        # Specialized Ebook Mode handling for PageBreak
        if style.name == "PageBreak" and self._ebook_mode:
            fmt.setFontPointSize(9 * self._zoom_factor)
            # Foreground is handled by the ephemeral highlighter for better performance

        if style.bold:
            fmt.setFontWeight(QFont.Weight.Bold)
        if style.italic:
            fmt.setFontItalic(True)
        if style.underline:
            fmt.setFontUnderline(True)
        return fmt

    def apply_style_to_block(self, cursor, style_name: str):
        """Apply a named style to the block at the cursor's current position."""
        if not self._current_doc_ref:
            return
        style = self._current_doc_ref.styles.get(style_name)
        if not style:
            return
            
        prev_block = cursor.block().previous()
        prev_style_name = prev_block.blockFormat().property(STYLE_NAME_PROPERTY) if prev_block.isValid() else None
        
        cursor.setBlockFormat(self._style_to_block_format(style, prev_style_name))
        cursor.setCharFormat(self._style_to_char_format(style))

    def apply_style(self, style: StyleDefinition):
        """Surgical application to avoid leakage."""
        cursor = self.textCursor()
        start_pos = cursor.selectionStart()
        end_pos = cursor.selectionEnd()
        cursor.setPosition(start_pos)
        first_block = cursor.blockNumber()
        cursor.setPosition(end_pos)
        last_block = cursor.blockNumber() - 1 if (end_pos > start_pos and cursor.atBlockStart()) else cursor.blockNumber()
            
        cursor.beginEditBlock()
        char_format = self._style_to_char_format(style)
        for i in range(first_block, last_block + 1):
            block = self.document().findBlockByNumber(i)
            if block.isValid():
                prev_block = block.previous()
                prev_style_name = prev_block.blockFormat().property(STYLE_NAME_PROPERTY) if prev_block.isValid() else None
                temp_cursor = QTextCursor(block)
                temp_cursor.setBlockFormat(self._style_to_block_format(style, prev_style_name))
                temp_cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock, QTextCursor.MoveMode.KeepAnchor)
                temp_cursor.setCharFormat(char_format)
        
        # Cascade refresh to the block immediately AFTER the selection if it's Body
        next_block = self.document().findBlockByNumber(last_block + 1)
        if next_block.isValid():
            next_style_name = next_block.blockFormat().property(STYLE_NAME_PROPERTY) or "Body"
            if next_style_name == "Body":
                next_style = self._current_doc_ref.styles.get(next_style_name)
                if next_style:
                    temp_cursor = QTextCursor(next_block)
                    temp_cursor.setBlockFormat(self._style_to_block_format(next_style, style.name))

        cursor.endEditBlock()
        self.setTextCursor(self.textCursor())
        self._update_stats()

    def sync_to_document(self, doc: PortoDocument):
        doc.chapters = []
        current_chapter = None
        block = self.document().begin()
        while block.isValid():
            text = block.text()
            fmt = block.blockFormat()
            style_name = fmt.property(STYLE_NAME_PROPERTY) or "Body"
            drop_cap = bool(fmt.property(DROP_CAP_PROPERTY))
            if style_name == "ChapterHeader":
                current_chapter = doc.add_chapter(text)
            else:
                if current_chapter is None:
                    current_chapter = doc.add_chapter("Untitled")
                if text.strip() or len(current_chapter.blocks) == 0:
                    b = current_chapter.add_block(style_name, text)
                    b.drop_cap = drop_cap
            block = block.next()

    def toggle_bold(self):
        fmt = self.currentCharFormat()
        weight = QFont.Weight.Bold if fmt.fontWeight() != QFont.Weight.Bold else QFont.Weight.Normal
        fmt.setFontWeight(weight)
        self.mergeCurrentCharFormat(fmt)

    def toggle_italic(self):
        fmt = self.currentCharFormat()
        fmt.setFontItalic(not fmt.fontItalic())
        self.mergeCurrentCharFormat(fmt)

    def toggle_underline(self):
        fmt = self.currentCharFormat()
        fmt.setFontUnderline(not fmt.fontUnderline())
        self.mergeCurrentCharFormat(fmt)

    def toggle_drop_cap(self):
        if not self._current_doc_ref:
            return
        cursor = self.textCursor()
        block = cursor.block()
        fmt = block.blockFormat()
        style_name = fmt.property(STYLE_NAME_PROPERTY)
        if style_name != "Body":
            return
            
        current_val = bool(fmt.property(DROP_CAP_PROPERTY))
        new_val = not current_val
        
        cursor.beginEditBlock()
        fmt.setProperty(DROP_CAP_PROPERTY, new_val)
        temp_cursor = QTextCursor(block)
        temp_cursor.setBlockFormat(fmt)
        cursor.endEditBlock()
        
        # Update PortoDocument model
        target_block_idx = block.blockNumber()
        current_idx = 0
        found = False
        for chapter in self._current_doc_ref.chapters:
            # Chapter title counts as the first block in a chapter sequence in the editor
            if current_idx == target_block_idx:
                break # ChapterHeader doesn't support drop_cap in model
            current_idx += 1
            
            for b in chapter.blocks:
                if current_idx == target_block_idx:
                    b.drop_cap = new_val
                    found = True
                    break
                current_idx += 1
            if found:
                break
                
        self.structure_changed.emit()

    def set_current_alignment(self, alignment_str: str) -> None:
        """
        Set the current text alignment to the specified value.

        :param alignment_str: The desired alignment ("left", "center", "right", "justify")    
        """
        cursor = self.textCursor()
        fmt = QTextBlockFormat()

        # Mapping of alignment strings to Qt AlignmentFlags
        alignment_map = {
            "left": Qt.AlignmentFlag.AlignLeft,
            "center": Qt.AlignmentFlag.AlignCenter,
            "right": Qt.AlignmentFlag.AlignRight,
            "justify": Qt.AlignmentFlag.AlignJustify
        }

        if alignment_str in alignment_map:
            fmt.setAlignment(alignment_map[alignment_str])
            cursor.mergeBlockFormat(fmt)
            self.setFocus()
        else:
            raise ValueError(f"Invalid alignment: {alignment_str}")

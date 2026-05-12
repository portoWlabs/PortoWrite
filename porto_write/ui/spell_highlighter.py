import re
from PySide6.QtGui import QSyntaxHighlighter, QTextCharFormat, QColor
from PySide6.QtCore import Qt
from porto_write.constants import STYLE_NAME_PROPERTY

class SpellCheckHighlighter(QSyntaxHighlighter):
    """Highlighter that underlines misspelled words in red and styles mode-specific blocks."""

    def __init__(self, parent, spell_checker):
        super().__init__(parent)
        self.spell_checker = spell_checker
        self._ebook_mode = False
        self._highlight_enabled = True
        self.error_format = QTextCharFormat()
        self.error_format.setUnderlineColor(Qt.GlobalColor.red)
        self.error_format.setUnderlineStyle(QTextCharFormat.UnderlineStyle.SpellCheckUnderline)
        self.word_re = re.compile(r"\b\w+(?:['’]\w+)*\b")

    def set_highlighting_enabled(self, enabled: bool):
        """Enable or disable spell-check highlighting without triggering a rehighlight pass."""
        self._highlight_enabled = enabled

    def set_ebook_mode(self, enabled: bool):
        self._ebook_mode = enabled
        
        # Performance: Instead of full self.rehighlight(), only refresh PageBreak blocks
        doc = self.document()
        if not doc:
            return
            
        block = doc.begin()
        while block.isValid():
            style = block.blockFormat().property(STYLE_NAME_PROPERTY)
            if style == "PageBreak":
                self.rehighlightBlock(block)
            block = block.next()

    def highlightBlock(self, text):
        if not self._highlight_enabled:
            return
            
        # 1. Ebook Mode Specialized Styling
        if self._ebook_mode:
            style = self.currentBlock().blockFormat().property(STYLE_NAME_PROPERTY)
            if style == "PageBreak":
                fmt = QTextCharFormat()
                fmt.setBackground(QColor("#e0e0e0"))  # light gray bar
                fmt.setForeground(QColor("#888888"))  # muted text
                fmt.setFontPointSize(9)
                self.setFormat(0, len(text), fmt)
                return # Skip spell check for system blocks

        # 2. Standard Spell Checking
        if not self.spell_checker:
            return
        for match in self.word_re.finditer(text):
            word = match.group()
            if not self.spell_checker.check(word):
                self.setFormat(match.start(), match.end() - match.start(), self.error_format)

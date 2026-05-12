from PySide6.QtGui import QTextCursor, QTextDocument
from PySide6.QtCore import QRegularExpression


class FindReplaceMixin:
    """Mixin providing find/replace operations for EditorWidget."""

    def find_next(self, text: str, case: bool = False, whole_word: bool = False, use_regex: bool = False) -> bool:
        """Find next occurrence of text, wrapping around at end of document."""
        if not text:
            return False
        flags = QTextDocument.FindFlag(0)
        if case:
            flags |= QTextDocument.FindFlag.FindCaseSensitively
        if whole_word:
            flags |= QTextDocument.FindFlag.FindWholeWords

        if use_regex:
            pattern = QRegularExpression(text)
            if not case:
                pattern.setPatternOptions(QRegularExpression.PatternOption.CaseInsensitiveOption)
            cursor = self.document().find(pattern, self.textCursor(), flags)
            if cursor.isNull():
                cursor = self.document().find(pattern, 0, flags)
        else:
            cursor = self.document().find(text, self.textCursor(), flags)
            if cursor.isNull():
                cursor = self.document().find(text, 0, flags)

        if not cursor.isNull():
            self.setTextCursor(cursor)
            return True
        return False

    def find_prev(self, text: str, case: bool = False, whole_word: bool = False, use_regex: bool = False) -> bool:
        """Find previous occurrence of text, wrapping around at start of document."""
        if not text:
            return False
        flags = QTextDocument.FindFlag.FindBackward
        if case:
            flags |= QTextDocument.FindFlag.FindCaseSensitively
        if whole_word:
            flags |= QTextDocument.FindFlag.FindWholeWords

        if use_regex:
            pattern = QRegularExpression(text)
            if not case:
                pattern.setPatternOptions(QRegularExpression.PatternOption.CaseInsensitiveOption)
            cursor = self.document().find(pattern, self.textCursor(), flags)
            if cursor.isNull():
                end = QTextCursor(self.document())
                end.movePosition(QTextCursor.MoveOperation.End)
                cursor = self.document().find(pattern, end, flags)
        else:
            cursor = self.document().find(text, self.textCursor(), flags)
            if cursor.isNull():
                end = QTextCursor(self.document())
                end.movePosition(QTextCursor.MoveOperation.End)
                cursor = self.document().find(text, end, flags)

        if not cursor.isNull():
            self.setTextCursor(cursor)
            return True
        return False

    def replace_current(self, find_text: str, replace_text: str, case: bool = False, whole_word: bool = False, use_regex: bool = False) -> bool:
        """Replace current selection if it matches, then advance to next match."""
        if not find_text:
            return False
        cursor = self.textCursor()
        selected = cursor.selectedText()

        if use_regex:
            pattern = QRegularExpression(find_text)
            if not case:
                pattern.setPatternOptions(QRegularExpression.PatternOption.CaseInsensitiveOption)
            matched = pattern.match(selected).hasMatch()
        else:
            matched = (selected == find_text) if case else (selected.lower() == find_text.lower())

        if matched:
            cursor.insertText(replace_text)
            self.setTextCursor(cursor)

        self.find_next(find_text, case, whole_word, use_regex)
        return matched

    def replace_all(self, find_text: str, replace_text: str, case: bool = False, whole_word: bool = False, use_regex: bool = False) -> int:
        """Replace all occurrences. Returns count of replacements made."""
        if not find_text:
            return 0
        flags = QTextDocument.FindFlag(0)
        if case:
            flags |= QTextDocument.FindFlag.FindCaseSensitively
        if whole_word:
            flags |= QTextDocument.FindFlag.FindWholeWords

        search_cursor = QTextCursor(self.document())
        search_cursor.movePosition(QTextCursor.MoveOperation.Start)
        search_cursor.beginEditBlock()
        count = 0

        if use_regex:
            pattern = QRegularExpression(find_text)
            if not case:
                pattern.setPatternOptions(QRegularExpression.PatternOption.CaseInsensitiveOption)
            while True:
                found = self.document().find(pattern, search_cursor, flags)
                if found.isNull():
                    break
                found.insertText(replace_text)
                search_cursor = found
                count += 1
        else:
            while True:
                found = self.document().find(find_text, search_cursor, flags)
                if found.isNull():
                    break
                found.insertText(replace_text)
                search_cursor = found
                count += 1

        search_cursor.endEditBlock()
        return count

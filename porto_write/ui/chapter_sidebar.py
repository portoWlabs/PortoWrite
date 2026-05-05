from PySide6.QtWidgets import QListWidget, QListWidgetItem, QStyledItemDelegate, QStyle
from PySide6.QtCore import Signal, Qt, QRect
from PySide6.QtGui import QFont, QColor, QPalette

class ChapterItemDelegate(QStyledItemDelegate):
    """Custom delegate to handle indentation and styling for multi-level headings."""

    def paint(self, painter, option, index):
        level = index.data(Qt.ItemDataRole.UserRole)
        
        # Level 2 indentation
        if level == 2:
            option.rect.setLeft(option.rect.left() + 30)
            
            # Level 2 specific styling
            font = QFont(option.font)
            font.setItalic(True)
            # Slightly smaller than default
            if font.pointSize() > 0:
                font.setPointSize(max(8, font.pointSize() - 1))
            else:
                font.setPixelSize(max(10, font.pixelSize() - 2))
            option.font = font
            
            # Change color if not selected
            if not (option.state & QStyle.StateFlag.State_Selected):
                option.palette.setColor(QPalette.ColorRole.Text, option.palette.color(QPalette.ColorRole.PlaceholderText))

        super().paint(painter, option, index)

class ChapterSidebar(QListWidget):
    """Sidebar widget to display and navigate project chapters with multi-level headings."""
    
    chapter_selected = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.setItemDelegate(ChapterItemDelegate(self))
        self.setStyleSheet("""
            QListWidget {
                border: none;
                background-color: transparent;
                outline: none;
            }
            QListWidget::item {
                padding: 10px 15px;
                border-bottom: 1px solid rgba(128,128,128,0.2);
            }
            QListWidget::item:selected {
                background-color: #3498db;
                color: white;
            }
            QListWidget::item:hover:!selected {
                background-color: rgba(128,128,128,0.12);
            }
        """)
        self.itemClicked.connect(self._on_item_clicked)

    def refresh(self, items: list[tuple[int, str]]):
        """Repopulate the list with the given items (level, title)."""
        self.blockSignals(True)
        self.clear()
        for level, title in items:
            item = QListWidgetItem(title)
            item.setData(Qt.ItemDataRole.UserRole, level)
            self.addItem(item)
        self.blockSignals(False)

    def select_chapter(self, index: int):
        """Highlight the chapter at the given index without emitting signals."""
        if 0 <= index < self.count():
            self.blockSignals(True)
            self.setCurrentRow(index)
            self.blockSignals(False)

    def _on_item_clicked(self, item):
        index = self.row(item)
        self.chapter_selected.emit(index)

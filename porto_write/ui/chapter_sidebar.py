from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLineEdit, QListWidget, QListWidgetItem, 
    QStyledItemDelegate, QStyle
)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QFont, QPalette, QColor

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
                # Use a specific dark grey for better contrast in light mode
                # In dark mode, this role will already be a light grey from the app palette
                text_color = option.palette.color(QPalette.ColorRole.WindowText)
                if text_color.lightness() < 128: # Light theme detection
                    option.palette.setColor(QPalette.ColorRole.Text, QColor("#505050"))
                else: # Dark theme detection
                    option.palette.setColor(QPalette.ColorRole.Text, QColor("#b0b0b0"))

        super().paint(painter, option, index)

class ChapterSidebar(QWidget):
    """Sidebar widget to display and navigate project chapters with search filtering."""
    
    chapter_selected = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 1. Search Field
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search chapters...")
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.setStyleSheet("""
            QLineEdit {
                border: none;
                border-bottom: 1px solid rgba(128,128,128,0.3);
                padding: 8px 12px;
                background-color: transparent;
            }
        """)
        self.search_edit.textChanged.connect(self._on_search_changed)
        layout.addWidget(self.search_edit)

        # 2. Chapter List
        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.list_widget.setItemDelegate(ChapterItemDelegate(self.list_widget))
        self.list_widget.setStyleSheet("""
            QListWidget {
                border: none;
                background-color: transparent;
                outline: none;
            }
            QListWidget::item {
                padding: 10px 15px;
                border-bottom: 1px solid rgba(128,128,128,0.1);
            }
            QListWidget::item:selected {
                background-color: #3498db;
                color: #ffffff;
            }
            QListWidget::item:hover:!selected {
                background-color: rgba(128,128,128,0.15);
            }
        """)
        self.list_widget.itemClicked.connect(self._on_item_clicked)
        layout.addWidget(self.list_widget)

    def refresh(self, items: list[tuple[int, str]]):
        """Repopulate the list with the given items (level, title)."""
        self.list_widget.blockSignals(True)
        self.list_widget.clear()
        for level, title in items:
            item = QListWidgetItem(title)
            item.setData(Qt.ItemDataRole.UserRole, level)
            self.list_widget.addItem(item)
        self.list_widget.blockSignals(False)
        self._on_search_changed(self.search_edit.text())

    def select_chapter(self, index: int):
        """Highlight the chapter at the given index without emitting signals."""
        if 0 <= index < self.list_widget.count():
            self.list_widget.blockSignals(True)
            self.list_widget.setCurrentRow(index)
            self.list_widget.blockSignals(False)

    def _on_item_clicked(self, item):
        index = self.list_widget.row(item)
        self.chapter_selected.emit(index)

    def _on_search_changed(self, text: str):
        search_term = text.lower().strip()
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if not search_term:
                item.setHidden(False)
            else:
                match = search_term in item.text().lower()
                item.setHidden(not match)


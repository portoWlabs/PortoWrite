import copy
import logging
from dataclasses import asdict
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QListWidget, QLabel, 
    QListWidgetItem, QHBoxLayout, QPushButton, QMessageBox, QMenu
)
from PySide6.QtCore import Signal, Qt
from porto_write.styles import StyleDefinition, StyleRegistry
from porto_write.licensing import is_pro

logger = logging.getLogger(__name__)

class StylePanel(QWidget):
    """Sidebar panel for selecting and managing paragraph styles."""
    
    style_selected = Signal(StyleDefinition)
    style_added = Signal(dict)
    style_updated = Signal(str, dict)
    style_deleted = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.registry = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        layout.addWidget(QLabel("Paragraph Styles"))
        
        self.style_list = QListWidget()
        self.style_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.style_list.customContextMenuRequested.connect(self._show_context_menu)
        self.style_list.itemClicked.connect(self._on_item_clicked)
        self.style_list.itemDoubleClicked.connect(self._on_edit_style)
        layout.addWidget(self.style_list)
        
        # CRUD Buttons
        btn_layout = QHBoxLayout()
        self.add_btn = QPushButton("Add")
        self.edit_btn = QPushButton("Edit")
        self.del_btn = QPushButton("Delete")
        
        self.add_btn.clicked.connect(self._on_add_style)
        self.edit_btn.clicked.connect(self._on_edit_style)
        self.del_btn.clicked.connect(self._on_delete_style)
        
        if not is_pro():
            self.add_btn.setEnabled(False)
            self.add_btn.setToolTip("Pro feature — upgrade to use custom styles")
            self.del_btn.setEnabled(False)
            self.del_btn.setToolTip("Pro feature — upgrade to use custom styles")
            
        btn_layout.addWidget(self.add_btn)
        btn_layout.addWidget(self.edit_btn)
        btn_layout.addWidget(self.del_btn)
        layout.addLayout(btn_layout)

    def refresh(self, registry: StyleRegistry):
        """Populate the list with styles from the registry."""
        self.registry = registry
        self.style_list.clear()
        
        # Sort: Built-ins first, then custom
        all_styles = registry.all()
        # G9: Hide aliases and markers
        hidden = ("PageBreak", "SceneBreak", "ChapterHeader", "SubHeader")
        all_styles = [s for s in all_styles if s.name not in hidden]
        
        sorted_styles = sorted(all_styles, key=lambda s: (not registry.is_builtin(s.name), s.name))
        
        for style in sorted_styles:
            item = QListWidgetItem(style.name)
            if registry.is_builtin(style.name):
                item.setToolTip("Built-in Kindle style")
                # Optional: slight visual distinction for built-ins?
            self.style_list.addItem(item)
            
        logger.debug("StylePanel refreshed with %d styles.", len(all_styles))

    def select_style(self, name: str):
        """Highlight a style in the list without emitting style_selected."""
        items = self.style_list.findItems(name, Qt.MatchFlag.MatchExactly)
        if items:
            self.style_list.blockSignals(True)
            self.style_list.setCurrentItem(items[0])
            self.style_list.blockSignals(False)

    def _on_item_clicked(self, item: QListWidgetItem):
        style_name = item.text()
        style = self.registry.get(style_name)
        if style:
            self.style_selected.emit(style)

    def _on_add_style(self):
        # Create a default StyleDefinition based on 'Body'
        base = self.registry.get("Body")
        from porto_write.styles import StyleDefinition
        new_style = StyleDefinition(name="NewStyle", font_family=base.font_family)
        
        from porto_write.ui.dialogs import StyleEditorDialog
        dlg = StyleEditorDialog(new_style, is_builtin=False, parent=self)
        dlg.setWindowTitle("Create New Style")
        if dlg.exec():
            self.style_added.emit(dlg.get_data())

    def _on_edit_style(self):
        item = self.style_list.currentItem()
        if not item: return
        
        style_name = item.text()
        style = self.registry.get(style_name)
        if not style: return
        
        from porto_write.ui.dialogs import StyleEditorDialog
        is_builtin = self.registry.is_builtin(style_name)
        dlg = StyleEditorDialog(style, is_builtin=is_builtin, parent=self)
        if dlg.exec():
            self.style_updated.emit(style_name, dlg.get_data())

    def _on_delete_style(self):
        item = self.style_list.currentItem()
        if not item: return
        
        style_name = item.text()
        if self.registry.is_builtin(style_name):
            QMessageBox.warning(self, "Delete Style", f"'{style_name}' is a built-in style and cannot be deleted.")
            return
            
        res = QMessageBox.question(
            self, "Delete Style", 
            f"Are you sure you want to delete the style '{style_name}'?\n\nBlocks using this style will revert to 'Body'.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if res == QMessageBox.StandardButton.Yes:
            self.style_deleted.emit(style_name)

    def _show_context_menu(self, pos):
        item = self.style_list.itemAt(pos)
        if not item: return

        style_name = item.text()
        menu = QMenu(self)
        
        apply_action = menu.addAction("Apply Style")
        menu.addSeparator()
        
        # Heading-specific toggles (G6)
        if style_name in ("Heading1", "Heading2", "ChapterHeader"):
            style = self.registry.get(style_name)
            pb_action = menu.addAction("Page Break Before")
            pb_action.setCheckable(True)
            pb_action.setChecked(style.page_break_before)
            pb_action.triggered.connect(lambda checked: self._toggle_page_break(style_name, checked))
            menu.addSeparator()

        edit_action = menu.addAction("Edit Style...")
        duplicate_action = menu.addAction("Duplicate Style")
        delete_action = menu.addAction("Delete Style")
        
        if self.registry.is_builtin(style_name):
            delete_action.setEnabled(False)
            
        if not is_pro():
            duplicate_action.setEnabled(False)
            duplicate_action.setToolTip("Pro feature — upgrade to use custom styles")
            delete_action.setEnabled(False)
            delete_action.setToolTip("Pro feature — upgrade to use custom styles")
            
        action = menu.exec(self.style_list.mapToGlobal(pos))
        
        if action == apply_action:
            self._on_item_clicked(item)
        elif action == edit_action:
            self.style_list.setCurrentItem(item)
            self._on_edit_style()
        elif action == duplicate_action:
            self.style_list.setCurrentItem(item)
            self._on_duplicate_style()
        elif action == delete_action:
            self.style_list.setCurrentItem(item)
            self._on_delete_style()

    def _toggle_page_break(self, name: str, checked: bool):
        style = self.registry.get(name)
        if style:
            style.page_break_before = checked
            # Emit style_updated to trigger UI refresh (including preview)
            data = asdict(style)
            self.style_updated.emit(name, data)

    def _on_duplicate_style(self):
        item = self.style_list.currentItem()
        if not item: return
        
        style_name = item.text()
        base_style = self.registry.get(style_name)
        if not base_style: return
        
        new_style = copy.deepcopy(base_style)
        new_style.name = f"{style_name} Copy"
        
        from porto_write.ui.dialogs import StyleEditorDialog
        dlg = StyleEditorDialog(new_style, is_builtin=False, parent=self)
        dlg.setWindowTitle("Duplicate Style")
        if dlg.exec():
            self.style_added.emit(dlg.get_data())


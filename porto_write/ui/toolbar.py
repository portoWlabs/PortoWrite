import logging
from PySide6.QtWidgets import QToolBar, QComboBox, QSizePolicy
from PySide6.QtGui import QAction, QKeySequence, QActionGroup
from porto_write.styles import StyleDefinition

logger = logging.getLogger(__name__)

class EditorToolbar(QToolBar):
    """Toolbar for quick access to formatting and history actions."""

    def __init__(self, parent=None):
        super().__init__("Editor Toolbar", parent)
        self.setMovable(False)
        self._setup_actions()

    def _setup_actions(self):
        # 1. History
        self.undo_action = QAction("Undo", self)
        self.undo_action.setShortcut(QKeySequence.StandardKey.Undo)
        self.addAction(self.undo_action)

        self.redo_action = QAction("Redo", self)
        self.redo_action.setShortcut(QKeySequence.StandardKey.Redo)
        self.addAction(self.redo_action)

        self.addSeparator()

        # 2. Formatting
        self.bold_action = QAction("Bold", self)
        self.bold_action.setShortcut(QKeySequence.StandardKey.Bold)
        self.bold_action.setCheckable(True)
        self.addAction(self.bold_action)

        self.italic_action = QAction("Italic", self)
        self.italic_action.setShortcut(QKeySequence.StandardKey.Italic)
        self.italic_action.setCheckable(True)
        self.addAction(self.italic_action)

        self.underline_action = QAction("Underline", self)
        self.underline_action.setShortcut(QKeySequence.StandardKey.Underline)
        self.underline_action.setCheckable(True)
        self.addAction(self.underline_action)

        self.addSeparator()

        # 2.1 Alignment
        self.align_group = QActionGroup(self)
        self.align_group.setExclusive(True)

        self.align_left_action = QAction("Left", self)
        self.align_left_action.setCheckable(True)
        self.align_left_action.setToolTip("Align Left")
        self.align_group.addAction(self.align_left_action)
        self.addAction(self.align_left_action)

        self.align_center_action = QAction("Center", self)
        self.align_center_action.setCheckable(True)
        self.align_center_action.setToolTip("Align Center")
        self.align_group.addAction(self.align_center_action)
        self.addAction(self.align_center_action)

        self.align_right_action = QAction("Right", self)
        self.align_right_action.setCheckable(True)
        self.align_right_action.setToolTip("Align Right")
        self.align_group.addAction(self.align_right_action)
        self.addAction(self.align_right_action)

        self.align_justify_action = QAction("Justify", self)
        self.align_justify_action.setCheckable(True)
        self.align_justify_action.setToolTip("Justify")
        self.align_group.addAction(self.align_justify_action)
        self.addAction(self.align_justify_action)

        self.addSeparator()

        # 3. Style Selector
        self.style_combo = QComboBox()
        self.style_combo.setToolTip("Select Paragraph Style")
        self.style_combo.setMinimumWidth(150)
        self.addWidget(self.style_combo)

    def refresh_styles(self, names: list[str]):
        """Update the style dropdown list."""
        self.style_combo.clear()
        # G9: Hide aliases and markers
        hidden = ("PageBreak", "SceneBreak", "ChapterHeader", "SubHeader")
        filtered = [n for n in names if n not in hidden]
        self.style_combo.addItems(sorted(filtered))
        logger.debug("Toolbar style dropdown refreshed.")

import logging
from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout
from PySide6.QtGui import QPainter, QColor, QPainterPath, QRegion
from PySide6.QtCore import Qt, QRectF

logger = logging.getLogger(__name__)


class EbookFrameWidget(QWidget):
    """
    Container that wraps EditorWidget and paints a device bezel in ebook mode.
    In standard mode it is a transparent pass-through — the editor fills all space.
    Call activate(profile) / deactivate() to switch modes.
    """

    def __init__(self, editor, parent=None):
        super().__init__(parent)
        self._editor = editor
        self._profile: dict | None = None

        # Main layout: Vertical to hold [Toolbar] and [Device/Editor]
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(10, 0, 10, 10)
        self.main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        # 0. Local Reading Controls Toolbar (Mirroring KindlePreviewWidget)
        from PySide6.QtWidgets import QLabel, QComboBox, QPushButton, QSpacerItem, QSizePolicy
        self.toolbar = QWidget()
        self.toolbar.setStyleSheet("color: #ccc; font-size: 11px;")
        self.toolbar.hide() # Hidden until activated
        
        t_layout = QHBoxLayout(self.toolbar)
        t_layout.setContentsMargins(0, 0, 0, 10)
        
        from porto_write.constants import DEVICE_PROFILES, DEFAULT_DEVICE
        t_layout.addWidget(QLabel("Device:"))
        self.device_combo = QComboBox()
        self.device_combo.addItems(list(DEVICE_PROFILES.keys()))
        self.device_combo.setCurrentText(DEFAULT_DEVICE)
        self.device_combo.setToolTip("Select a physical device profile to simulate (e.g. Kindle Paperwhite).")
        t_layout.addWidget(self.device_combo)

        t_layout.addSpacing(15)

        t_layout.addWidget(QLabel("Theme:"))
        self.theme_combo = QComboBox()
        self.theme_combo.setToolTip("Switch between light, sepia, and night reading themes.")
        # Theme options will be populated by MainWindow/Mixin
        t_layout.addWidget(self.theme_combo)

        t_layout.addSpacing(15)
        
        t_layout.addWidget(QLabel("Aa:"))
        self.btn_fs_down = QPushButton("−")
        self.btn_fs_down.setFixedWidth(24)
        self.btn_fs_down.setToolTip("Cycle through character-per-line presets (45, 55, 65) to optimize readability.")
        t_layout.addWidget(self.btn_fs_down)
        
        self.lbl_zoom = QLabel("55")
        self.lbl_zoom.setFixedWidth(35)
        self.lbl_zoom.setAlignment(Qt.AlignCenter)
        t_layout.addWidget(self.lbl_zoom)
        
        self.btn_fs_up = QPushButton("+")
        self.btn_fs_up.setFixedWidth(24)
        self.btn_fs_up.setToolTip("Cycle through character-per-line presets (45, 55, 65) to optimize readability.")
        t_layout.addWidget(self.btn_fs_up)
        
        t_layout.addSpacing(15)
        
        t_layout.addWidget(QLabel("Margins:"))
        self.btn_m_down = QPushButton("−")
        self.btn_m_down.setFixedWidth(24)
        self.btn_m_down.setToolTip("Adjust the left/right side margins of the simulated screen.")
        t_layout.addWidget(self.btn_m_down)
        
        self.lbl_m = QLabel("40")
        self.lbl_m.setFixedWidth(20)
        self.lbl_m.setAlignment(Qt.AlignCenter)
        t_layout.addWidget(self.lbl_m)
        
        self.btn_m_up = QPushButton("+")
        self.btn_m_up.setFixedWidth(24)
        self.btn_m_up.setToolTip("Adjust the left/right side margins of the simulated screen.")
        t_layout.addWidget(self.btn_m_up)
        
        t_layout.addSpacing(15)
        
        t_layout.addWidget(QLabel("LS:"))
        self.btn_ls_down = QPushButton("−")
        self.btn_ls_down.setFixedWidth(24)
        self.btn_ls_down.setToolTip("Adjust the line spacing (leading) for the text.")
        t_layout.addWidget(self.btn_ls_down)
        
        self.lbl_ls = QLabel("1.4")
        self.lbl_ls.setFixedWidth(25)
        self.lbl_ls.setAlignment(Qt.AlignCenter)
        t_layout.addWidget(self.lbl_ls)
        
        self.btn_ls_up = QPushButton("+")
        self.btn_ls_up.setFixedWidth(24)
        self.btn_ls_up.setToolTip("Adjust the line spacing (leading) for the text.")
        t_layout.addWidget(self.btn_ls_up)
        
        t_layout.addStretch()
        self.main_layout.addWidget(self.toolbar, 0, Qt.AlignmentFlag.AlignHCenter)

        # 1. The Device Frame (Container that mimics physical hardware)
        self.device_container = QWidget()
        self.device_container.setObjectName("EbookDeviceFrame")
        self.device_layout = QHBoxLayout(self.device_container)
        self.device_layout.setContentsMargins(0, 0, 0, 0)
        self.device_layout.setSpacing(0)
        self.device_layout.addWidget(editor)

        # In normal mode, device_container expands to fill width (stretch=1)
        # In ebook mode, it's centered (stretch=0 + alignment)
        self.main_layout.addWidget(self.device_container, 1)
        self.main_layout.addStretch(0)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def activate(self, profile: dict) -> None:
        """Enter device-frame mode: constrain editor width and paint bezel."""
        logger.debug(f"[EBOOK_FRAME] activate() called with profile={profile.get('name', 'unknown')}")
        logger.debug(f"[EBOOK_FRAME] Before: main width={self.width()}, device_container geometry={self.device_container.geometry()}")

        self._profile = profile
        self.toolbar.show()

        # Center device_container in ebook mode (don't expand to full width)
        logger.debug(f"[EBOOK_FRAME] Setting stretch factor to 0 and centering")
        self.main_layout.setStretchFactor(self.device_container, 0)
        self.main_layout.setAlignment(self.device_container, Qt.AlignmentFlag.AlignHCenter)

        # Scaled sizing logic - MATCHING KindlePreviewWidget
        # We don't use the raw profile width (e.g. 1236px) because that's too big for desktop UI.
        # We use the same responsive scaling as the preview.
        logger.debug(f"[EBOOK_FRAME] Calling _rescale_device()")
        self._rescale_device()
        logger.debug(f"[EBOOK_FRAME] After _rescale_device(): device_container geometry={self.device_container.geometry()}, editor geometry={self._editor.geometry()}")

        # Apply corner masking to the editor's viewport to simulate a rounded screen
        self._editor.viewport().installEventFilter(self)
        self._apply_editor_mask()
        self.update()
        logger.debug(f"[EBOOK_FRAME] activate() complete")

    def deactivate(self) -> None:
        """Return to standard pass-through: remove width constraints and bezel."""
        logger.debug(f"[EBOOK_FRAME] deactivate() called")
        logger.debug(f"[EBOOK_FRAME] Before: device_container geometry={self.device_container.geometry()}, editor geometry={self._editor.geometry()}")

        self._profile = None
        self.toolbar.hide()

        # Restore normal mode: device_container expands to fill width
        logger.debug(f"[EBOOK_FRAME] Setting stretch factor to 1")
        self.main_layout.setStretchFactor(self.device_container, 1)
        self.main_layout.setAlignment(self.device_container, Qt.AlignmentFlag.AlignLeft)

        logger.debug(f"[EBOOK_FRAME] Clearing size constraints")
        self._editor.setMinimumSize(0, 0)
        self._editor.setMaximumSize(16_777_215, 16_777_215)
        self.device_container.setMinimumSize(0, 0)
        self.device_container.setMaximumSize(16_777_215, 16_777_215)
        self.device_layout.setContentsMargins(0, 0, 0, 0)

        self._editor.viewport().removeEventFilter(self)
        self._editor.viewport().setMask(QRegion()) # Clear mask

        # Force layout recalculation immediately (not just queue a repaint)
        # Must activate device_layout first (innermost), then main_layout
        logger.debug(f"[EBOOK_FRAME] Calling device_layout.activate()")
        self.device_layout.activate()

        logger.debug(f"[EBOOK_FRAME] Calling main_layout.activate()")
        self.main_layout.activate()
        logger.debug(f"[EBOOK_FRAME] After activate(): device_container geometry={self.device_container.geometry()}, editor geometry={self._editor.geometry()}")

        logger.debug(f"[EBOOK_FRAME] Calling adjustSize() to recalculate widget size")
        self.adjustSize()
        logger.debug(f"[EBOOK_FRAME] After adjustSize(): device_container geometry={self.device_container.geometry()}, editor geometry={self._editor.geometry()}")

        logger.debug(f"[EBOOK_FRAME] Calling updateGeometry() on children")
        self._editor.updateGeometry()
        self.device_container.updateGeometry()

        logger.debug(f"[EBOOK_FRAME] Calling updateGeometry() to notify parent of size change")
        self.updateGeometry()
        logger.debug(f"[EBOOK_FRAME] After updateGeometry(): widget geometry={self.geometry()}")

        # Force parent layout (splitter) to recalculate as well
        logger.debug(f"[EBOOK_FRAME] Forcing parent layout recalculation")
        if self.parentWidget():
            if hasattr(self.parentWidget(), 'layout') and self.parentWidget().layout():
                self.parentWidget().layout().activate()
            self.parentWidget().adjustSize()
        logger.debug(f"[EBOOK_FRAME] After parent recalc: this widget geometry={self.geometry()}")

        logger.debug(f"[EBOOK_FRAME] Calling update() to repaint")
        self.update()
        logger.debug(f"[EBOOK_FRAME] deactivate() complete")

    def resizeEvent(self, event):
        """Responsive sizing - MATCHING KindlePreviewWidget."""
        super().resizeEvent(event)
        if self._profile:
            self._rescale_device()

    def _rescale_device(self):
        """Calculate and apply scaled device geometry matching the reader preview."""
        if not self._profile:
            return

        # MATCHING KindlePreviewWidget.resizeEvent:
        # device_width = min(self.width() - 40, 560)
        # browser_width = device_width - 60
        # browser_height = int(browser_width / 0.756)
        
        device_width = min(self.width() - 40, 560)
        screen_width = device_width - 60
        screen_height = int(screen_width / 0.756)
        
        # Apply to editor — use min+max instead of setFixedSize so resizeEvent
        # can continuously call _rescale_device() and the layout responds.
        self._editor.setMinimumSize(screen_width, screen_height)
        self._editor.setMaximumSize(screen_width, screen_height)

        # Apply to container (with bezels 30, 50, 30, 60)
        # Device width = screen_width + 30 + 30 = screen_width + 60
        container_w = screen_width + 60
        container_h = screen_height + 110  # 50 top + 60 bottom
        self.device_container.setMinimumSize(container_w, container_h)
        self.device_container.setMaximumSize(container_w, container_h)
        self.device_layout.setContentsMargins(30, 50, 30, 60)
        self._apply_editor_mask()

    def eventFilter(self, obj, event):
        from PySide6.QtCore import QEvent
        if obj == self._editor.viewport() and event.type() == QEvent.Type.Resize:
            self._apply_editor_mask()
        return super().eventFilter(obj, event)

    def _apply_editor_mask(self):
        """Apply a rounded-rect mask to the editor viewport."""
        if not self._profile:
            return
        viewport = self._editor.viewport()
        rect = viewport.rect()
        path = QPainterPath()
        r = 4.0
        path.addRoundedRect(rect, r, r)
        viewport.setMask(QRegion(path.toFillPolygon().toPolygon()))

    def current_profile(self) -> dict | None:
        return self._profile

    # ------------------------------------------------------------------
    # Painting
    # ------------------------------------------------------------------

    def paintEvent(self, event):
        if self._profile is None:
            super().paintEvent(event)
            return

        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)

            # 1. Bezel Shell (The #111 frame)
            # Use the device_container's relative geometry
            device_rect = self.device_container.geometry()
            bezel_color = QColor("#111")
            border_color = QColor("#000")
            
            path = QPainterPath()
            r = 30.0 # Match Reader Preview
            path.addRoundedRect(QRectF(device_rect).adjusted(1, 1, -1, -1), r, r)
            
            painter.fillPath(path, bezel_color)
            
            # 2. Outer Border (2px)
            from PySide6.QtGui import QPen
            pen = QPen(border_color, 2)
            painter.setPen(pen)
            painter.drawPath(path)

            # 3. Inner Shadow / Screen Recess
            # The "screen" area is the editor geometry relative to this widget
            # Map the editor's top-left to this widget's coordinate system
            screen_pos = self._editor.mapTo(self, self._editor.rect().topLeft())
            screen_rect = QRectF(screen_pos.x(), screen_pos.y(), self._editor.width(), self._editor.height())
            
            # Paint a subtle dark gradient around the inner edges of the bezel
            from PySide6.QtGui import QLinearGradient
            
            # Top shadow
            top_grad = QLinearGradient(0, screen_rect.top(), 0, screen_rect.top() + 8)
            top_grad.setColorAt(0, QColor(0, 0, 0, 100))
            top_grad.setColorAt(1, QColor(0, 0, 0, 0))
            painter.fillRect(screen_rect.adjusted(0, 0, 0, -screen_rect.height() + 8), top_grad)

            # Left shadow
            left_grad = QLinearGradient(screen_rect.left(), 0, screen_rect.left() + 8, 0)
            left_grad.setColorAt(0, QColor(0, 0, 0, 80))
            left_grad.setColorAt(1, QColor(0, 0, 0, 0))
            painter.fillRect(screen_rect.adjusted(0, 0, -screen_rect.width() + 8, 0), left_grad)

            # Slim rounded outline around the editor for high-contrast separation
            screen_outline_rect = screen_rect.adjusted(-1, -1, 1, 1)
            inner_path = QPainterPath()
            inner_r = 5.0
            inner_path.addRoundedRect(screen_outline_rect, inner_r, inner_r)
            painter.setPen(QPen(QColor("#000"), 1))
            painter.drawPath(inner_path)

        finally:
            painter.end()

class PreviewMixin:
    """Mixin providing Kindle preview sync handlers for MainWindow."""

    def _on_ebook_device_changed(self, device_name: str):
        """Switch the device bezel frame."""
        from porto_write.constants import DEVICE_PROFILES
        profile = DEVICE_PROFILES.get(device_name)
        if profile:
            self.ebook_frame.activate(profile)
            self.settings.ebook_device = device_name
            self.settings.save()
            self.statusBar().showMessage(f"Device profile: {device_name}", 2000)

    def _on_ebook_line_height_changed(self, delta: float):
        """Adjust editor line height in ebook mode."""
        from PySide6.QtWidgets import QApplication
        from PySide6.QtCore import Qt
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        self.editor.setUpdatesEnabled(False)
        try:
            curr = self.settings.ebook_line_height
            new_val = round(curr + delta, 1)
            if 1.0 <= new_val <= 2.5:
                # Set field directly then call refresh_styling() once (avoids the
                # extra pass that set_display_line_height_override() would trigger).
                self.editor._display_line_height_override = new_val
                self.editor.refresh_styling()
                self.settings.ebook_line_height = new_val
                self.settings.save()
                self.ebook_frame.lbl_ls.setText(f"{new_val:.1f}")
        finally:
            self.editor.setUpdatesEnabled(True)
            QApplication.restoreOverrideCursor()

    def _on_ebook_margin_changed(self, delta: int):
        """Adjust editor margins in ebook mode."""
        from PySide6.QtWidgets import QApplication
        from PySide6.QtCore import Qt
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        self.editor.setUpdatesEnabled(False)
        try:
            curr = self.settings.ebook_margin
            new_val = curr + delta
            if 0 <= new_val <= 100:
                # Set fields directly then trigger a single layout pass.
                self.editor._user_margin_left = new_val
                self.editor._user_margin_right = new_val
                self.editor._update_layout()
                self.settings.ebook_margin = new_val
                self.settings.save()
                self.ebook_frame.lbl_m.setText(str(new_val))
        finally:
            self.editor.setUpdatesEnabled(True)
            QApplication.restoreOverrideCursor()

    def _on_ebook_theme_changed(self):
        """Switch the Kindle theme while in ebook edit mode."""
        from porto_write.ui.kindle_preview import KINDLE_THEMES
        from PySide6.QtGui import QPalette, QColor
        action = self.sender()
        if not action:
            return
        theme_name = action.data()
        theme = KINDLE_THEMES.get(theme_name, KINDLE_THEMES["Paperwhite"])

        pal = self.editor.palette()
        pal.setColor(QPalette.ColorRole.Base, QColor(theme["bg"]))
        pal.setColor(QPalette.ColorRole.Text, QColor(theme["fg"]))
        self.editor.setPalette(pal)
        self.editor.viewport().setPalette(pal)
        self.editor.setStyleSheet(f"QTextEdit {{ background-color: {theme['bg']}; color: {theme['fg']}; }}")

        self.preview.set_theme(theme_name)
        self.settings.ebook_theme = theme_name
        self.settings.save()

        # Update device label and check state (Note: _ebook_device_label removed in S22.3)
        actions = getattr(self, "_ebook_theme_actions", {})
        for name, act in actions.items():
            act.setChecked(name == theme_name)

    def _on_ebook_theme_combo_changed(self, theme_name: str):
        """Apply ebook theme from the combo box (theme_name passed directly)."""
        from porto_write.ui.kindle_preview import KINDLE_THEMES
        from PySide6.QtGui import QPalette, QColor
        theme = KINDLE_THEMES.get(theme_name, KINDLE_THEMES["Paperwhite"])

        # Theme changes are palette-only — skip the spell rehighlight pass
        if self.editor.highlighter:
            self.editor.highlighter.set_highlighting_enabled(False)
        try:
            pal = self.editor.palette()
            pal.setColor(QPalette.ColorRole.Base, QColor(theme["bg"]))
            pal.setColor(QPalette.ColorRole.Text, QColor(theme["fg"]))
            self.editor.setPalette(pal)
            self.editor.viewport().setPalette(pal)
            self.editor.setStyleSheet(f"QTextEdit {{ background-color: {theme['bg']}; color: {theme['fg']}; }}")
            self.preview.set_theme(theme_name)
            self.settings.ebook_theme = theme_name
            self.settings.save()
        finally:
            if self.editor.highlighter:
                self.editor.highlighter.set_highlighting_enabled(True)

        actions = getattr(self, "_ebook_theme_actions", {})
        for name, act in actions.items():
            act.setChecked(name == theme_name)

    def _on_ebook_cpl_changed(self, delta: int):
        """Step through CPL presets (45/55/65 chars/line) for Kindle Paperwhite estimates."""
        CPL_PRESETS = [45, 55, 65]
        curr = self.settings.ebook_cpl
        if curr not in CPL_PRESETS:
            curr = 55
        idx = CPL_PRESETS.index(curr)
        new_idx = max(0, min(len(CPL_PRESETS) - 1, idx + delta))
        new_cpl = CPL_PRESETS[new_idx]

        # Width changes only affect layout — skip the spell rehighlight pass
        if self.editor.highlighter:
            self.editor.highlighter.set_highlighting_enabled(False)
        try:
            self.editor.set_max_content_width(new_cpl)
        finally:
            if self.editor.highlighter:
                self.editor.highlighter.set_highlighting_enabled(True)

        self.settings.ebook_cpl = new_cpl
        self.settings.save()
        self.ebook_frame.lbl_zoom.setText(str(new_cpl))

    def _on_reader_preview_toggled(self, checked: bool):
        """Show/Hide the simulated Kindle preview panel."""
        self.preview.setVisible(checked)
        if checked:
            self._update_preview()

    def _on_preview_theme_changed(self):
        """Switch the theme of the Kindle previewer."""
        action = self.sender()
        if action:
            self.preview.set_theme(action.data())

    def _update_preview(self):
        """Trigger re-rendering of the Kindle preview from current editor state."""
        if not self.preview.isVisible():
            return
        self.editor.sync_to_document(self.project.doc)
        self.preview.update_preview(self.project.doc)
        # Defer scroll sync to allow WebKit layout to complete (setHtml is async)
        from PySide6.QtCore import QTimer
        QTimer.singleShot(100, self._sync_preview_scroll)

    def _sync_preview_scroll(self):
        if not self.preview.isVisible():
            return
        ids = self.editor.top_visible_block_ids()
        if ids:
            self.preview.scroll_to_block(*ids)
        else:
            sb = self.editor.verticalScrollBar()
            if sb.maximum() > 0:
                self.preview.set_scroll_percentage(sb.value() / sb.maximum())

    def _on_preview_block_clicked(self, chap_idx: int, b_idx: int):
        self.editor.scroll_to_block(chap_idx, b_idx)

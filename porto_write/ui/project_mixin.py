import logging
import os
from datetime import datetime
from PySide6.QtWidgets import (
    QMessageBox, QFileDialog, QDialog, QApplication, QMenu
)
from PySide6.QtGui import QAction
from porto_write.project import NovelProject

logger = logging.getLogger(__name__)

class ProjectActionsMixin:
    """Mixin for project-related actions in MainWindow."""

    def _on_new(self):
        from porto_write.ui.dialogs import ProjectPickerDialog
        picker = ProjectPickerDialog(self.settings, self)
        # picker._on_new_project() directly triggers NewProjectDialog
        picker._on_new_project()
        if picker.selected_project:
            self._load_project(picker.selected_project)

    def _on_open(self):
        from porto_write.ui.dialogs import ProjectPickerDialog
        picker = ProjectPickerDialog(self.settings, self)
        if picker.exec() == QDialog.Accepted and picker.selected_project:
            self._load_project(picker.selected_project)

    def _on_open_project_folder(self):
        path = QFileDialog.getExistingDirectory(self, "Select Project Folder", self.settings.projects_dir)
        if path:
            try:
                project = NovelProject.load(path)
                self._load_project(project)
            except Exception as e:
                logger.error("Failed to open project from %s: %s", path, e)
                QMessageBox.critical(self, "Error", f"Could not open project: {e}")

    def _on_save(self):
        try:
            self.project.doc.set_metadata("cursor_char_pos", self.editor.textCursor().position())
            self.project.doc.set_metadata("session_seconds", self._session_seconds)
            self.editor.sync_to_document(self.project.doc)
            self.project.save()
            self.is_dirty = False
            self._update_title()
            self.statusBar().showMessage("Project saved (backup created)", 3000)
        except Exception as e:
            logger.error("Failed to save project: %s", e)
            QMessageBox.critical(self, "Save Error", f"Could not save project: {e}")

    def _on_save_as(self):
        """Clone current project to a new folder/title."""
        import copy
        from porto_write.ui.dialogs import NewProjectDialog
        dlg = NewProjectDialog(self.settings, self)
        dlg.setWindowTitle("Save Project As (Clone)")
        dlg.title_edit.setText(f"{self.project.doc.title} (Copy)")

        if dlg.exec() == QDialog.Accepted:
            data = dlg.get_data()
            try:
                self.editor.sync_to_document(self.project.doc)
                # Create new project
                new_project = NovelProject.create(
                    projects_dir=self.settings.projects_dir,
                    title=data["title"],
                    author=data["author"],
                    max_backups=data["max_backups"]
                )
                # Deep-copy current content so the two projects don't share a doc reference
                new_project.doc = copy.deepcopy(self.project.doc)
                new_project.doc.title = data["title"]
                new_project.doc.author = data["author"]
                new_project.save()
                
                self._load_project(new_project)
                self.statusBar().showMessage(f"Project cloned to: {new_project.name}", 3000)
            except Exception as e:
                logger.error("Save As failed: %s", e)
                QMessageBox.critical(self, "Error", f"Could not clone project: {e}")

    def _on_metadata(self):
        """Show dialog to edit project-wide metadata."""
        from porto_write.ui.dialogs import MetadataDialog
        cover_rel = self.project.doc.get_metadata("cover_image")
        
        dlg = MetadataDialog(
            self.project.doc,
            cover_rel,
            self
        )
        
        if dlg.exec() == QDialog.Accepted:
            data = dlg.get_data()
            self.editor.sync_to_document(self.project.doc)
            self.project.doc.title = data["title"]
            self.project.doc.subtitle = data["subtitle"]
            self.project.doc.author = data["author"]
            self.project.doc.series_name = data["series_name"]
            self.project.doc.series_number = data["series_number"]
            self.project.doc.publisher = data["publisher"]
            self.project.doc.isbn = data["isbn"]
            self.project.doc.keywords = data["keywords"]
            self.project.doc.description = data["description"]
            
            if data["new_cover_path"]:
                try:
                    self.project.set_cover(data["new_cover_path"])
                except Exception as e:
                    logger.error("Failed to set cover image: %s", e)
                    QMessageBox.warning(self, "Cover Image Error", f"Could not set cover: {e}")
            else:
                self.project.save()
            
            self._update_title()
            self.statusBar().showMessage("Metadata updated", 3000)

    def _on_toc_editor(self):
        """Show dialog to edit the Table of Contents."""
        from porto_write.ui.dialogs import TocEditorDialog
        
        # Ensure TOC is populated if it's the first time
        if not self.project.doc.toc:
            self.project.doc.refresh_toc()
            
        dlg = TocEditorDialog(self.project.doc, self)
        if dlg.exec() == QDialog.Accepted:
            self.project.save()
            self.statusBar().showMessage("Table of Contents saved", 3000)

    def _on_insert_toc(self):
        from PySide6.QtGui import QTextCursor
        from porto_write.epub_io import generate_toc_text

        # Detect existing TOC
        toc_block = None
        block = self.editor.document().begin()
        while block.isValid():
            if block.text().strip() == "Table of Contents":
                toc_block = block
                break
            block = block.next()

        # If TOC exists, ask user what to do
        if toc_block:
            msg_box = QMessageBox(self)
            msg_box.setIcon(QMessageBox.Icon.Question)
            msg_box.setWindowTitle("TOC Exists")
            msg_box.setText("A Table of Contents already exists.\nDo you want to update it with the current chapters?")
            msg_box.addButton("Update TOC", QMessageBox.ButtonRole.AcceptRole)
            button_cancel = msg_box.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
            msg_box.exec()
            if msg_box.clickedButton() == button_cancel:
                return

        text = generate_toc_text(self.project.doc)
        if not text.strip():
            return

        cursor = QTextCursor(self.editor.document())
        cursor.beginEditBlock()
        try:
            # Remove old TOC section if updating
            if toc_block:
                opening_pb = toc_block.previous()
                while opening_pb.isValid() and opening_pb.text().strip() != "── Page Break ──":
                    opening_pb = opening_pb.previous()

                closing_body = toc_block.next()
                while closing_body.isValid() and closing_body.text().strip() != "── Page Break ──":
                    closing_body = closing_body.next()
                if closing_body.isValid():
                    closing_body = closing_body.next()

                if opening_pb.isValid() and closing_body.isValid():
                    start_pos = opening_pb.position()
                    end_pos = closing_body.position() + closing_body.length() - 1
                    cursor.setPosition(start_pos)
                    cursor.setPosition(end_pos, QTextCursor.MoveMode.KeepAnchor)
                    cursor.removeSelectedText()

            # Insert fresh TOC
            cursor.insertBlock()
            self.editor.apply_style_to_block(cursor, "PageBreak")
            cursor.insertText("── Page Break ──")

            cursor.insertBlock()
            lines = text.split("\n")
            self.editor.apply_style_to_block(cursor, "ChapterHeader")
            cursor.insertText(lines[0])

            for line in lines[2:]:  # skip blank separator
                if line.strip():
                    cursor.insertBlock()
                    self.editor.apply_style_to_block(cursor, "Body")
                    if line.startswith("  "):
                        # Sub-heading entry — indent and italicise to match chapter sidebar level 2
                        from PySide6.QtGui import QTextBlockFormat, QTextCharFormat
                        blk_fmt = cursor.blockFormat()
                        blk_fmt.setLeftMargin(20.0)
                        cursor.setBlockFormat(blk_fmt)
                        char_fmt = cursor.charFormat()
                        char_fmt.setFontItalic(True)
                        cursor.setCharFormat(char_fmt)
                        cursor.insertText(line.strip())
                    else:
                        cursor.insertText(line)

            cursor.insertBlock()
            self.editor.apply_style_to_block(cursor, "PageBreak")
            cursor.insertText("── Page Break ──")

            cursor.insertBlock()
            self.editor.apply_style_to_block(cursor, "Body")

        finally:
            cursor.endEditBlock()

        self.is_dirty = True
        self._update_title()
        self.statusBar().showMessage("Table of Contents updated.", 3000)

    def _on_restore_backup(self):
        from porto_write.ui.dialogs import RestoreBackupDialog
        dlg = RestoreBackupDialog(self.project, self)
        if dlg.exec() == QDialog.Accepted:
            filename = dlg.get_selected_backup()
            if not filename:
                return
                
            try:
                # Load the backup
                imported_doc = self.project.load_backup(filename)
                
                # Replace current doc
                self.project.doc = imported_doc
                
                # Mark as dirty (so they can save it as the new project.json)
                self.is_dirty = True
                
                # Refresh UI
                self._refresh_ui()
                self.statusBar().showMessage(f"Restored from backup: {filename}", 5000)
                logger.info("Project restored from backup: %s", filename)
                
            except Exception as e:
                logger.error("Restore failed: %s", e)
                QMessageBox.critical(self, "Restore Error", f"Failed to restore from backup: {e}")

    def _on_save_snapshot(self):
        from porto_write.ui.dialogs import SaveSnapshotDialog
        dlg = SaveSnapshotDialog(self)
        if dlg.exec() == QDialog.Accepted:
            name, desc = dlg.get_data()
            if not name:
                return
            try:
                self.project.save_snapshot(name, desc)
                self.statusBar().showMessage(f"Snapshot '{name}' saved.", 3000)
                logger.info("Snapshot saved: %s", name)
            except Exception as e:
                logger.error("Save snapshot failed: %s", e)
                QMessageBox.critical(self, "Error", f"Could not save snapshot: {e}")

    def _on_version_history(self):
        from porto_write.ui.dialogs import VersionHistoryDialog
        dlg = VersionHistoryDialog(self.project, self)
        if dlg.exec() == QDialog.Accepted:
            filename = dlg.get_selected_filename()
            if not filename:
                return
                
            try:
                # Load the snapshot
                imported_doc = self.project.restore_snapshot(filename)
                
                # Replace current doc
                self.project.doc = imported_doc
                
                # Mark as dirty
                self.is_dirty = True
                
                # Refresh UI
                self._refresh_ui()
                self.statusBar().showMessage(f"Restored version: {filename}", 5000)
                logger.info("Project restored from snapshot: %s", filename)
                
            except Exception as e:
                logger.error("Restore snapshot failed: %s", e)
                QMessageBox.critical(self, "Restore Error", f"Failed to restore version: {e}")

    def _load_project(self, project: NovelProject):
        self._loading = True
        try:
            self.project = project
            self.editor.load_document(self.project.doc)
            self.style_panel.refresh(self.project.doc.styles)
            self.toolbar.refresh_styles(self.project.doc.styles.names())
            self._on_structure_changed()

            # G8: Clear pending textChanged events while _loading is still True
            QApplication.processEvents()

            self.is_dirty = False
            self._update_title()

            # Check for autosave
            if self.project.has_autosave():
                meta = self.project.get_autosave_metadata()
                mtime_str = meta.get("mtime_str", "Unknown date")
                
                msg_box = QMessageBox(self)
                msg_box.setIcon(QMessageBox.Icon.Question)
                msg_box.setWindowTitle("Autosave Found")
                msg_box.setText(
                    f"An autosave from <b>{mtime_str}</b> was found for '{self.project.name}'.\n\n"
                    "This usually happens after a crash or if the application was forced to close.\n\n"
                    "What would you like to do?"
                )
                
                btn_restore = msg_box.addButton("Restore Autosave", QMessageBox.ButtonRole.AcceptRole)
                btn_delete = msg_box.addButton("Delete Autosave", QMessageBox.ButtonRole.DestructiveRole)
                btn_ignore = msg_box.addButton("Keep & Ignore", QMessageBox.ButtonRole.RejectRole)
                
                msg_box.setDefaultButton(btn_restore)
                msg_box.exec()
                
                clicked = msg_box.clickedButton()
                if clicked == btn_restore:
                    self.project.doc = self.project.load_autosave()
                    self.editor.load_document(self.project.doc)
                    self.style_panel.refresh(self.project.doc.styles)
                    self.toolbar.refresh_styles(self.project.doc.styles.names())
                    self._on_structure_changed()
                    self.is_dirty = True
                    self._update_title()
                    self.statusBar().showMessage(f"Restored from autosave ({mtime_str})", 5000)
                elif clicked == btn_delete:
                    self.project.delete_autosave()
                    self.statusBar().showMessage("Autosave deleted.", 3000)
                else:
                    # Ignore - keep the file on disk but don't load it
                    logger.info("Autosave ignored by user.")

            self._restore_cursor_position()
            self._session_seconds = self.project.doc.get_metadata("session_seconds", 0)
            self._update_modified_label()

            self.settings.add_recent_file(project.project_dir)
            self._update_recent_projects_menu()
            logger.info("Switched to project: %s", project.name)
        finally:
            self._loading = False

    def _update_recent_projects_menu(self):
        """Dynamically rebuild the Recent Projects submenu."""
        self.recent_menu.clear()
        recent_paths = self.settings.recent_files
        
        if not recent_paths:
            action = self.recent_menu.addAction("No recent projects")
            action.setEnabled(False)
            return

        for path in recent_paths:
            name = os.path.basename(path)
            action = QAction(name, self)
            action.setData(path)
            action.triggered.connect(self._on_recent_project_triggered)
            self.recent_menu.addAction(action)

    def _on_recent_project_triggered(self):
        action = self.sender()
        if action:
            path = action.data()
            try:
                project = NovelProject.load(path)
                self._load_project(project)
            except Exception as e:
                logger.error("Failed to open recent project from %s: %s", path, e)
                QMessageBox.critical(self, "Error", f"Could not open recent project: {e}")
                # Optional: remove from settings if it doesn't exist
                if not os.path.exists(path):
                    # self.settings.recent_files.remove(path)
                    pass

    def _on_autosave(self):
        """Auto-save the project to a recovery file (autosave.json)."""
        if self.is_dirty:
            try:
                self.editor.sync_to_document(self.project.doc)
                self.project.save_autosave()
                self.statusBar().showMessage("Auto-saved (recovery copy)", 3000)
                logger.info("Auto-saved recovery copy for project: %s", self.project.name)
            except Exception as e:
                logger.error("Auto-save failed: %s", e)

    def _restart_autosave_timer(self):
        """Restart the auto-save timer with the current interval."""
        self.autosave_timer.stop()
        if self.settings.autosave_interval_minutes > 0:
            ms = self.settings.autosave_interval_minutes * 60 * 1000
            self.autosave_timer.start(ms)
            logger.debug("Auto-save timer started: %d minutes", self.settings.autosave_interval_minutes)
        else:
            logger.debug("Auto-save is disabled (interval=0)")

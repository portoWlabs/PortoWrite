import logging
import os
from PySide6.QtWidgets import QMessageBox, QFileDialog
from porto_write.epub_io import export_epub, import_epub
from porto_write.md_io import export_md, import_md
from porto_write.docx_io import export_docx, import_docx
from porto_write.licensing import is_pro

logger = logging.getLogger(__name__)

class ExportImportMixin:
    """Mixin for export and import actions in MainWindow."""

    def _handle_import(self, extension: str):
        """Import a document filtered by the given file extension."""
        filter_dict = {
            ".epub": "EPUB Document (*.epub)",
            ".md": "Markdown Document (*.md)",
            ".docx": "Word Document (*.docx)",
        }
        filters = filter_dict.get(extension, "")
        file_path, _ = QFileDialog.getOpenFileName(
            self, f"Import {extension.upper()[1:]}", self.settings.last_directory, filters
        )

        if file_path:
            self.settings.last_directory = os.path.dirname(file_path)
            self.settings.save()

            try:
                if extension == ".epub":
                    imported_doc = import_epub(file_path)
                elif extension == ".md":
                    imported_doc = import_md(file_path)
                elif extension == ".docx":
                    imported_doc = import_docx(file_path)
                else:
                    raise ValueError("Unsupported file format")

                self.project.doc = imported_doc
                self.project.save()
                self._refresh_ui()
                self.statusBar().showMessage(f"Imported from: {os.path.basename(file_path)}", 5000)
            except Exception as e:
                logger.error("Import failed: %s", e)
                QMessageBox.critical(self, "Import Error", f"Failed to import: {e}")

    def _on_import_epub(self):
        self._handle_import(".epub")

    def _on_import_md(self):
        if is_pro():
            self._handle_import(".md")

    def _on_import_docx(self):
        if is_pro():
            self._handle_import(".docx")

    def _on_export(self):
        """Export the current document to EPUB, MD, or DOCX."""
        filters = "EPUB Document (*.epub)"
        if is_pro():
            filters += ";;Markdown Document (*.md);;Word Document (*.docx)"
            
        file_path, selected_filter = QFileDialog.getSaveFileName(
            self, "Export Document", self.settings.last_directory, filters
        )
        
        if file_path:
            self.settings.last_directory = os.path.dirname(file_path)
            self.settings.save()
            
            try:
                if ".epub" in selected_filter:
                    from porto_write.ui.dialogs import ValidationResultDialog, ExportOptionsDialog
                    # 1. Ask for platform options
                    opt_dlg = ExportOptionsDialog(file_path, self.settings.export_platform, self)
                    if opt_dlg.exec() != QDialog.Accepted:
                        return
                    
                    platform = opt_dlg.get_platform()
                    self.settings.export_platform = platform
                    self.settings.save()
                    
                    # 2. Export
                    result = export_epub(
                        self.project.doc, 
                        file_path, 
                        project_dir=self.project.project_dir,
                        platform=platform
                    )
                    
                    # 3. Show results
                    dlg = ValidationResultDialog(result, file_path, self)
                    dlg.exec()
                elif ".md" in selected_filter and is_pro():
                    export_md(self.project.doc, file_path)
                elif ".docx" in selected_filter and is_pro():
                    export_docx(self.project.doc, file_path)
                
                self.statusBar().showMessage(f"Exported to: {os.path.basename(file_path)}", 5000)
            except Exception as e:
                logger.error("Export failed: %s", e)
                QMessageBox.critical(self, "Export Error", f"Failed to export: {e}")

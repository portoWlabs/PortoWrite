import os
import sys
import logging
from datetime import datetime
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
    QListWidget, QListWidgetItem, QLabel, QLineEdit, QFormLayout, 
    QSpinBox, QMessageBox, QFileDialog, QDialogButtonBox, QTextEdit
)
from PySide6.QtCore import Qt
from porto_write.constants import APP_NAME, APP_VERSION
from porto_write.project import ProjectManager, NovelProject
from porto_write.settings import AppSettings
from porto_write.licensing import get_edition_label

logger = logging.getLogger(__name__)

class BetaWarningDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("PortoWrite Beta — Important Notice")
        self.setFixedSize(550, 420)
        # Non-closeable via standard buttons
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.CustomizeWindowHint | Qt.WindowType.WindowTitleHint)
        
        layout = QVBoxLayout(self)
        
        text = (
            f"PortoWrite v{APP_VERSION} — IMPORTANT NOTICE\n\n"
            "This software is a BETA release. It may contain bugs, errors, or incomplete features "
            "that could result in unexpected behavior, data corruption, or loss of work.\n\n"
            "PLEASE BACK UP ALL YOUR WORK BEFORE USING THIS PROGRAM.\n\n"
            "THIS SOFTWARE IS PROVIDED \"AS IS\", WITHOUT WARRANTY OF ANY KIND. THE DEVELOPER(S) "
            "OF PORTOWRITE SHALL NOT BE HELD RESPONSIBLE OR LIABLE FOR ANY LOSS OF DATA, CORRUPTION "
            "OF FILES, OR ANY OTHER DAMAGES ARISING FROM THE USE OF THIS SOFTWARE. USE AT YOUR OWN RISK.\n\n"
            "By clicking OK, you acknowledge that you have read and understood this disclaimer."
        )
        
        label = QLabel(text)
        label.setWordWrap(True)
        label.setStyleSheet("font-size: 13px; line-height: 1.4;")
        layout.addWidget(label)
        
        layout.addStretch()
        
        btn_layout = QHBoxLayout()
        exit_btn = QPushButton("Exit Application")
        exit_btn.clicked.connect(lambda: sys.exit(0))
        btn_layout.addWidget(exit_btn)
        
        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self.accept)
        ok_btn.setDefault(True)
        btn_layout.addWidget(ok_btn)
        
        layout.addLayout(btn_layout)

    def closeEvent(self, event):
        # Prevent closing via Alt+F4 or other system methods
        event.ignore()

class BetaInitialsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Disable Beta Warning — Confirm")
        self.setFixedSize(400, 180)
        
        layout = QVBoxLayout(self)
        
        layout.addWidget(QLabel(
            "Type your initials below to confirm you have read and accepted the beta disclaimer. "
            "The warning will no longer appear at startup."
        ))
        
        self.initials_edit = QLineEdit()
        self.initials_edit.setMaxLength(5)
        self.initials_edit.setPlaceholderText("YOUR INITIALS")
        self.initials_edit.textChanged.connect(self._on_text_changed)
        layout.addWidget(self.initials_edit)
        
        layout.addStretch()
        
        btns = QHBoxLayout()
        self.confirm_btn = QPushButton("Confirm")
        self.confirm_btn.setEnabled(False)
        self.confirm_btn.clicked.connect(self.accept)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        
        btns.addStretch()
        btns.addWidget(cancel_btn)
        btns.addWidget(self.confirm_btn)
        layout.addLayout(btns)

    def _on_text_changed(self, text):
        # Force uppercase
        self.initials_edit.blockSignals(True)
        self.initials_edit.setText(text.upper())
        self.initials_edit.blockSignals(False)
        self.confirm_btn.setEnabled(len(text.strip()) > 0)

    def get_initials(self) -> str:
        return self.initials_edit.text().strip().upper()

class ProjectPickerDialog(QDialog):
    """Dialog to pick an existing project or create a new one on startup."""

    def __init__(self, settings: AppSettings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.manager = ProjectManager(self.settings.projects_dir)
        self.selected_project: NovelProject | None = None
        
        self.setWindowTitle("PortoWrite — Project Picker")
        self.setMinimumSize(400, 300)
        
        self._setup_ui()
        self._refresh_list()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        layout.addWidget(QLabel("Select a project to open:"))
        
        self.project_list = QListWidget()
        self.project_list.itemDoubleClicked.connect(self._on_open_selected)
        layout.addWidget(self.project_list)
        
        btn_layout = QHBoxLayout()
        
        new_btn = QPushButton("New Project...")
        new_btn.clicked.connect(self._on_new_project)
        btn_layout.addWidget(new_btn)
        
        open_disk_btn = QPushButton("Open from Disk...")
        open_disk_btn.clicked.connect(self._on_open_from_disk)
        btn_layout.addWidget(open_disk_btn)
        
        layout.addLayout(btn_layout)
        
        # Action buttons
        actions = QHBoxLayout()
        self.open_btn = QPushButton("Open")
        self.open_btn.clicked.connect(self._on_open_selected)
        self.open_btn.setDefault(True)
        
        cancel_btn = QPushButton("Exit")
        cancel_btn.clicked.connect(self.reject)
        
        actions.addStretch()
        actions.addWidget(cancel_btn)
        actions.addWidget(self.open_btn)
        layout.addLayout(actions)

    def _refresh_list(self):
        self.project_list.clear()
        projects = self.manager.list_projects()
        for p in projects:
            self.project_list.addItem(p)
        
        if self.project_list.count() > 0:
            self.project_list.setCurrentRow(0)
            self.open_btn.setEnabled(True)
        else:
            self.open_btn.setEnabled(False)

    def _on_open_selected(self):
        item = self.project_list.currentItem()
        if not item:
            return
        
        name = item.text()
        try:
            self.selected_project = self.manager.open_project(name)
            self.accept()
        except Exception as e:
            logger.error("Failed to open project %s: %s", name, e)
            QMessageBox.critical(self, "Error", f"Could not open project: {e}")

    def _on_new_project(self):
        dlg = NewProjectDialog(self.settings, self)
        if dlg.exec() == QDialog.Accepted:
            data = dlg.get_data()
            try:
                self.selected_project = self.manager.create_project(
                    title=data["title"],
                    author=data["author"],
                    max_backups=data["max_backups"]
                )
                self.accept()
            except Exception as e:
                logger.error("Failed to create project: %s", e)
                QMessageBox.critical(self, "Error", f"Could not create project: {e}")

    def _on_open_from_disk(self):
        path = QFileDialog.getExistingDirectory(self, "Select Project Folder", self.settings.projects_dir)
        if path:
            try:
                self.selected_project = self.manager.open_project_by_path(path)
                self.accept()
            except Exception as e:
                logger.error("Failed to open project from %s: %s", path, e)
                QMessageBox.critical(self, "Error", f"That folder does not appear to be a valid PortoWrite project.\n\n({e})")


class NewProjectDialog(QDialog):
    """Small dialog to prompt for new project details."""

    def __init__(self, settings: AppSettings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.setWindowTitle("Create New Project")
        self.setMinimumSize(600, 500)
        
        layout = QVBoxLayout(self)
        form = QFormLayout()
        
        # 1. Title
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("e.g. My Great Novel")
        self.title_edit.setToolTip(
            "The name of your book. Used as the project folder name and in exported files.\n"
            "You can rename it later via File → Save As."
        )
        form.addRow("Novel Title:", self.title_edit)
        
        title_hint = QLabel("You can rename the project later from File > Save As")
        title_hint.setStyleSheet("color: #777; font-size: 10px; margin-top: -5px; margin-bottom: 10px;")
        form.addRow("", title_hint)
        
        # 2. Author
        self.author_edit = QLineEdit()
        self.author_edit.setPlaceholderText("e.g. Jane Smith")
        self.author_edit.setToolTip(
            "Your name as the author. Appears on the title page and in exported EPUB/DOCX metadata."
        )
        form.addRow("Author:", self.author_edit)
        
        # 3. Backups
        self.backups_spin = QSpinBox()
        self.backups_spin.setRange(0, 100)
        self.backups_spin.setValue(10)
        self.backups_spin.setToolTip(
            "PortoWrite saves a backup copy every time you save your project.\n"
            "This sets the maximum number of backups to keep — the oldest are deleted automatically\n"
            "when the limit is reached. Set to 0 to keep all backups forever."
        )
        form.addRow("Max Backups:", self.backups_spin)
        
        backups_hint = QLabel("(0 = unlimited) — oldest backups are deleted automatically when this limit is reached")
        backups_hint.setStyleSheet("color: #777; font-size: 10px; margin-top: -5px; margin-bottom: 10px;")
        form.addRow("", backups_hint)

        # 4. Location Display
        location_header = QLabel("Project Location:")
        location_header.setStyleSheet("font-weight: bold; margin-top: 10px;")
        form.addRow(location_header)
        
        loc_row = QHBoxLayout()
        self.root_label = QLabel(self.settings.projects_dir)
        self.root_label.setStyleSheet("color: #444; font-size: 11px;")
        self.root_label.setToolTip(
            "The main folder where all your PortoWrite projects are stored.\n"
            "Each project gets its own subfolder inside here."
        )
        loc_row.addWidget(self.root_label, 1)

        browse_btn = QPushButton("Change...")
        browse_btn.setToolTip(
            "Click to choose a different folder on your computer where projects will be stored.\n"
            "All future projects will be saved here by default."
        )
        browse_btn.clicked.connect(self._on_browse_location)
        loc_row.addWidget(browse_btn)
        form.addRow("Root Folder:", loc_row)

        self.path_label = QLabel()
        self.path_label.setWordWrap(True)
        self.path_label.setStyleSheet("color: #666; font-family: monospace; font-size: 11px; background-color: #f8f8f8; padding: 5px; border: 1px solid #ddd;")
        self.path_label.setToolTip(
            "The exact location on your computer where this project's files will be created.\n"
            "This folder is created automatically when you click Create Project."
        )
        form.addRow("Full Path:", self.path_label)
        
        path_hint = QLabel("Each project is stored in its own subfolder within the root.")
        path_hint.setStyleSheet("color: #777; font-size: 10px; margin-top: 2px;")
        form.addRow("", path_hint)
        
        layout.addLayout(form)
        layout.addStretch()
        
        # Buttons
        btns = QHBoxLayout()
        ok_btn = QPushButton("Create Project")
        ok_btn.clicked.connect(self._try_accept)
        ok_btn.setDefault(True)
        ok_btn.setMinimumHeight(35)
        ok_btn.setStyleSheet("font-weight: bold;")
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setMinimumHeight(35)
        
        btns.addStretch()
        btns.addWidget(cancel_btn)
        btns.addWidget(ok_btn)
        layout.addLayout(btns)

        # Signals
        self.title_edit.textChanged.connect(self._update_path_preview)
        self._update_path_preview()

    def _on_browse_location(self):
        path = QFileDialog.getExistingDirectory(self, "Select Projects Root Folder", self.settings.projects_dir)
        if path:
            self.settings.projects_dir = path
            self.settings.save()
            self.root_label.setText(path)
            self._update_path_preview()

    def _try_accept(self):
        if not self.title_edit.text().strip():
            QMessageBox.warning(self, "Title Required",
                                "Please enter a novel title before creating the project.")
            self.title_edit.setFocus()
            return
        self.accept()

    def _update_path_preview(self):
        title = self.title_edit.text().strip() or "Untitled"
        from porto_write.project import _safe_folder_name
        folder_name = _safe_folder_name(title)
        full_path = os.path.join(self.settings.projects_dir, folder_name)
        self.path_label.setText(full_path)

    def get_data(self):
        return {
            "title": self.title_edit.text().strip() or "Untitled",
            "author": self.author_edit.text().strip(),
            "max_backups": self.backups_spin.value()
        }

class RestoreBackupDialog(QDialog):
    def __init__(self, project: NovelProject, parent=None):
        super().__init__(parent)
        self.project = project
        self.setWindowTitle("Restore from Backup")
        self.setFixedSize(500, 350)
        
        main_layout = QVBoxLayout(self)
        
        content_layout = QHBoxLayout()
        main_layout.addLayout(content_layout)
        
        # Left: List
        self.list_widget = QListWidget()
        content_layout.addWidget(self.list_widget, 1)
        
        # Right: Preview
        preview_group = QVBoxLayout()
        content_layout.addLayout(preview_group, 1)
        
        self.title_label = QLabel("<b>Select a backup</b>")
        self.title_label.setWordWrap(True)
        preview_group.addWidget(self.title_label)
        
        self.info_label = QLabel("")
        self.info_label.setWordWrap(True)
        preview_group.addWidget(self.info_label)
        preview_group.addStretch()
        
        # Buttons
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.button(QDialogButtonBox.StandardButton.Ok).setText("Restore")
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        main_layout.addWidget(self.button_box)
        
        self.list_widget.currentItemChanged.connect(self._on_selection_changed)
        self._populate()
        
    def _populate(self):
        backups = self.project.list_backups()
        for b in backups:
            self.list_widget.addItem(b)
        if not backups:
            self.title_label.setText("No backups found.")
            self.button_box.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)

    def _on_selection_changed(self, current, previous):
        if not current:
            return
        filename = current.text()
        try:
            doc = self.project.load_backup(filename)
            self.title_label.setText(f"<b>{doc.title}</b>")
            
            word_count = sum(len(b.text.split()) for ch in doc.chapters for b in ch.blocks)
            
            info = f"Author: {doc.author}\n"
            info += f"Chapters: {len(doc.chapters)}\n"
            info += f"Words: {word_count:,}\n\n"
            info += f"File: {filename}"
            
            self.info_label.setText(info)
        except Exception as e:
            self.title_label.setText("Error loading backup")
            self.info_label.setText(str(e))

    def get_selected_backup(self) -> str:
        item = self.list_widget.currentItem()
        return item.text() if item else ""

class SaveSnapshotDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Save Snapshot")
        self.setFixedSize(400, 250)
        
        layout = QVBoxLayout(self)
        form = QFormLayout()
        
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("e.g. End of Chapter 5")
        form.addRow("Snapshot Name:", self.name_edit)
        
        self.desc_edit = QTextEdit()
        self.desc_edit.setPlaceholderText("Optional details about this version...")
        self.desc_edit.setMaximumHeight(80)
        form.addRow("Description:", self.desc_edit)
        
        layout.addLayout(form)
        
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.button(QDialogButtonBox.StandardButton.Ok).setText("Save Snapshot")
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

    def get_data(self) -> tuple[str, str]:
        return self.name_edit.text().strip(), self.desc_edit.toPlainText().strip()

class VersionHistoryDialog(QDialog):
    def __init__(self, project: NovelProject, parent=None):
        super().__init__(parent)
        self.project = project
        self.setWindowTitle("Version History")
        self.setMinimumSize(650, 450)
        
        main_layout = QVBoxLayout(self)
        
        content_layout = QHBoxLayout()
        main_layout.addLayout(content_layout)
        
        # Left: List
        self.list_widget = QListWidget()
        content_layout.addWidget(self.list_widget, 2)
        
        # Right: Details
        details_group = QVBoxLayout()
        content_layout.addLayout(details_group, 3)
        
        self.name_label = QLabel("<b>Select a version</b>")
        self.name_label.setWordWrap(True)
        self.name_label.setStyleSheet("font-size: 14px;")
        details_group.addWidget(self.name_label)
        
        self.info_label = QLabel("")
        self.info_label.setWordWrap(True)
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        details_group.addWidget(self.info_label)
        details_group.addStretch()
        
        # Bottom Buttons
        btn_layout = QHBoxLayout()
        
        self.restore_btn = QPushButton("Restore Selected")
        self.restore_btn.setEnabled(False)
        self.restore_btn.clicked.connect(self.accept)
        self.restore_btn.setStyleSheet("font-weight: bold; padding: 5px;")
        btn_layout.addWidget(self.restore_btn)
        
        self.delete_btn = QPushButton("Delete")
        self.delete_btn.setEnabled(False)
        self.delete_btn.clicked.connect(self._on_delete)
        btn_layout.addWidget(self.delete_btn)
        
        btn_layout.addStretch()
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.reject)
        btn_layout.addWidget(close_btn)
        
        main_layout.addLayout(btn_layout)
        
        self.list_widget.currentItemChanged.connect(self._on_selection_changed)
        self._populate()
        
    def _populate(self):
        self.list_widget.clear()
        self.snapshots = self.project.list_snapshots()
        for s in self.snapshots:
            # Display name and short date
            display_text = f"{s['name']} ({s['date'][:10]})"
            item = QListWidgetItem(display_text)
            item.setData(Qt.ItemDataRole.UserRole, s)
            self.list_widget.addItem(item)
            
        if not self.snapshots:
            self.name_label.setText("No snapshots found.")
            self.info_label.setText("Use 'Save Snapshot' from the File menu to create permanent versions of your project.")
            self.restore_btn.setEnabled(False)
            self.delete_btn.setEnabled(False)

    def _on_selection_changed(self, current, previous):
        if not current:
            return
            
        s = current.data(Qt.ItemDataRole.UserRole)
        self.name_label.setText(f"<b>{s['name']}</b>")
        
        try:
            dt = datetime.fromisoformat(s['date'])
            date_str = dt.strftime('%Y-%m-%d %H:%M')
        except:
            date_str = s['date']
            
        info = f"Date: {date_str}\n"
        info += f"Words: {s.get('word_count', 0):,}\n\n"
        
        desc = s.get('description', '')
        if desc:
            info += f"Description:\n{desc}"
            
        self.info_label.setText(info)
        self.restore_btn.setEnabled(True)
        self.delete_btn.setEnabled(True)

    def _on_delete(self):
        item = self.list_widget.currentItem()
        if not item:
            return
            
        s = item.data(Qt.ItemDataRole.UserRole)
        res = QMessageBox.question(
            self, "Delete Snapshot",
            f"Are you sure you want to permanently delete the snapshot '{s['name']}'?\n\nThis cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if res == QMessageBox.StandardButton.Yes:
            try:
                self.project.delete_snapshot(s['filename'])
                self._populate()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not delete snapshot: {e}")

    def get_selected_filename(self) -> str:
        item = self.list_widget.currentItem()
        if item:
            s = item.data(Qt.ItemDataRole.UserRole)
            return s['filename']
        return ""

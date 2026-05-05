import logging
import os
from datetime import datetime
from PySide6.QtWidgets import (
    QMainWindow, QLabel, QMenu, QMessageBox, QDockWidget,
    QDialog, QFileDialog, QSplitter, QApplication
)
from PySide6.QtGui import QAction, QActionGroup, QKeySequence, QColor, QPalette, QFont
from porto_write.epub_io import export_epub, import_epub
from porto_write.md_io import export_md, import_md
from porto_write.docx_io import export_docx, import_docx
from PySide6.QtCore import QTimer, Qt
from porto_write.constants import APP_NAME, APP_VERSION, KINDLE_FONTS, STYLE_NAME_PROPERTY
from porto_write.logger import setup_logging
from porto_write.settings import AppSettings
from porto_write.project import NovelProject
from porto_write.spell import SpellChecker
from porto_write.ui.editor_widget import EditorWidget, SpellCheckHighlighter
from porto_write.ui.style_panel import StylePanel
from porto_write.ui.chapter_sidebar import ChapterSidebar
from porto_write.ui.toolbar import EditorToolbar
from porto_write.ui.dialogs import DisplayPreferencesDialog, FindReplaceDialog, AboutDialog, UpgradeDialog
from porto_write.ui.dialogs.licence_key_dialog import LicenceKeyDialog
from porto_write.ui.kindle_preview import KindlePreviewWidget, KINDLE_THEMES
from porto_write.licensing import is_pro, is_commercial, get_edition_label, get_edition, Edition, deactivate_licence

logger = logging.getLogger(__name__)

class MainWindow(QMainWindow):
    """Main application shell for PortoWrite."""

    def __init__(self, settings: AppSettings, project: NovelProject):
        super().__init__()
        self.settings = settings
        self.project = project
        self.is_dirty = False
        self._loading = False
        
        # Unique name for layout persistence
        self.setObjectName("PortoWrite_MainWindow")
        
        self._update_title()
        try:
            self.resize(self.settings.window_width, self.settings.window_height)
        except Exception as e:
            logger.warning(f"Failed to restore window size: {e}")
            self.resize(1000, 800)

        # Setup Debounced Preview Update
        self.preview_timer = QTimer(self)
        self.preview_timer.setSingleShot(True)
        self.preview_timer.setInterval(1000) # 1 second delay
        self.preview_timer.timeout.connect(self._update_preview)

        self._find_replace_dlg = None
        self._setup_ui()

        # Typing Timer + Idle Detection (must be before signal connections)
        self._session_seconds: int = self.project.doc.get_metadata("session_seconds", 0)
        self._typing_timer = QTimer(self)
        self._typing_timer.setInterval(1000)
        self._typing_timer.timeout.connect(self._on_typing_tick)
        self._idle_timer = QTimer(self)
        self._idle_timer.setSingleShot(True)
        self._idle_timer.setInterval(300_000)
        self._idle_timer.timeout.connect(self._on_idle_timeout)

        # Initialize Services with strong references
        try:
            self.spell_checker = SpellChecker()
            self.editor.set_spell_checker(self.spell_checker)
            # Highlighter needs a strong reference to stay alive in PySide
            self.highlighter = SpellCheckHighlighter(self.editor.document(), self.spell_checker)
        except Exception as e:
            logger.error(f"Failed to initialize spelling services: {e}")
            self.spell_checker = None
            self.highlighter = None
        
        # Connect signals
        self.editor.textChanged.connect(self._on_text_changed)
        self.editor.verticalScrollBar().valueChanged.connect(self._sync_preview_scroll)
        self.editor.zoom_changed.connect(self._on_zoom_changed)
        self.editor.stats_changed.connect(self._update_stats_display)
        self.editor.structure_changed.connect(self._on_structure_changed)
        self.style_panel.style_selected.connect(self.editor.apply_style)
        self.style_panel.style_added.connect(self._on_style_added)
        self.style_panel.style_updated.connect(self._on_style_updated)
        self.style_panel.style_deleted.connect(self._on_style_deleted)
        self.chapter_sidebar.chapter_selected.connect(self.editor.scroll_to_chapter)
        self.editor.style_updated.connect(self._on_style_updated)
        
        # Setup Auto-Save Timer
        self.autosave_timer = QTimer(self)
        self.autosave_timer.timeout.connect(self._on_autosave)
        self._restart_autosave_timer()

        # Toolbar actions
        self.toolbar.bold_action.triggered.connect(self.editor.toggle_bold)
        self.toolbar.italic_action.triggered.connect(self.editor.toggle_italic)
        self.toolbar.underline_action.triggered.connect(self.editor.toggle_underline)
        self.toolbar.align_left_action.triggered.connect(lambda: self.editor.set_current_alignment("left"))
        self.toolbar.align_center_action.triggered.connect(lambda: self.editor.set_current_alignment("center"))
        self.toolbar.align_right_action.triggered.connect(lambda: self.editor.set_current_alignment("right"))
        self.toolbar.align_justify_action.triggered.connect(lambda: self.editor.set_current_alignment("justify"))
        self.toolbar.undo_action.triggered.connect(self.editor.undo)
        self.toolbar.redo_action.triggered.connect(self.editor.redo)
        self.toolbar.style_combo.activated.connect(self._on_toolbar_style_selected)
        
        # Style Hotkeys from editor
        self.editor.style_hotkey_triggered.connect(self._on_style_hotkey)

        # Update toolbar button states based on cursor
        self.editor.cursorPositionChanged.connect(self._update_toolbar_states)
        
        # Apply display preferences
        self._apply_display_preferences()
        self._apply_tooltips_preference()

        # Load initial project
        self._load_project(self.project)
        
        # Restore zoom level
        if self.settings.zoom_steps != 0:
            if self.settings.zoom_steps > 0:
                self.editor.zoomIn(self.settings.zoom_steps)
            else:
                self.editor.zoomOut(-self.settings.zoom_steps)
            # Synchronize internal steps in widget
            self.editor.set_zoom_steps(self.settings.zoom_steps)

        logger.debug("MainWindow initialized for project: %s", self.project.name)

    def _update_title(self):
        dirty_indicator = "*" if self.is_dirty else ""
        self.setWindowTitle(f"{self.project.doc.title}{dirty_indicator} — {APP_NAME} v{APP_VERSION}")

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
        
        # Sync editor content to project document first
        self.editor.sync_to_document(self.project.doc)
        self.preview.update_preview(self.project.doc)
        # Re-sync scroll after content update
        self._sync_preview_scroll()

    def _sync_preview_scroll(self):
        if not self.preview.isVisible():
            return
        
        sb = self.editor.verticalScrollBar()
        if sb.maximum() > 0:
            percentage = sb.value() / sb.maximum()
            self.preview.set_scroll_percentage(percentage)

    def _on_text_changed(self):
        if self._loading:
            return
            
        if not self.is_dirty:
            self.is_dirty = True
            self._update_title()

        self.project.doc.set_metadata("last_modified", datetime.now().isoformat())
        self._update_modified_label()

        if not self._typing_timer.isActive():
            self._typing_timer.start()
        self._idle_timer.start()

        if self.preview.isVisible():
            self.preview_timer.start()

    def _update_stats_display(self, words: int, chars: int):
        self.stats_label.setText(f"Words: {words:,} | Chars: {chars:,}")

    def _on_toolbar_style_selected(self, index: int):
        style_name = self.toolbar.style_combo.currentText()
        style = self.project.doc.styles.get(style_name)
        if style:
            self.editor.apply_style(style)
            # The editor will emit cursorPositionChanged, triggering _update_toolbar_states

    def _on_style_hotkey(self, style_name: str):
        style = self.project.doc.styles.get(style_name)
        if style:
            self.editor.apply_style(style)
            # The editor will emit cursorPositionChanged, triggering _update_toolbar_states

    def _update_toolbar_states(self):
        """Update Bold/Italic/Underline button checked state and style indicators based on current cursor format."""
        cursor = self.editor.textCursor()
        char_fmt = cursor.charFormat()
        block_fmt = cursor.blockFormat()
        
        # 1. Basic Formatting
        self.toolbar.bold_action.setChecked(char_fmt.fontWeight() == QFont.Weight.Bold)
        self.toolbar.italic_action.setChecked(char_fmt.fontItalic())
        self.toolbar.underline_action.setChecked(char_fmt.fontUnderline())

        # 1.1 Alignment Formatting
        align = block_fmt.alignment()
        self.toolbar.align_left_action.setChecked(bool(align & Qt.AlignmentFlag.AlignLeft))
        self.toolbar.align_center_action.setChecked(bool(align & Qt.AlignmentFlag.AlignHCenter))
        self.toolbar.align_right_action.setChecked(bool(align & Qt.AlignmentFlag.AlignRight))
        self.toolbar.align_justify_action.setChecked(bool(align & Qt.AlignmentFlag.AlignJustify))
        
        # 2. Style Synchronization
        style_name = block_fmt.property(STYLE_NAME_PROPERTY)
        if style_name:
            # Update Toolbar Dropdown
            self.toolbar.style_combo.blockSignals(True)
            idx = self.toolbar.style_combo.findText(style_name)
            if idx >= 0:
                self.toolbar.style_combo.setCurrentIndex(idx)
            self.toolbar.style_combo.blockSignals(False)
            
            # Update Style Panel
            self.style_panel.blockSignals(True)
            self.style_panel.select_style(style_name)
            self.style_panel.blockSignals(False)

    def _apply_display_preferences(self):
        palette = self.editor.palette()
        palette.setColor(QPalette.ColorRole.Text, QColor(self.settings.display_text_color))
        palette.setColor(QPalette.ColorRole.Base, QColor(self.settings.display_bg_color))
        self.editor.setPalette(palette)

        if self.settings.dynamic_margins:
            self.editor.set_max_content_width(self.settings.max_content_width)
        else:
            self.editor.set_max_content_width(None)

        self.editor.set_visual_margins(self.settings.editor_margin_left, self.settings.editor_margin_right)

        # Apply display font override (if Kindle Font toggle is off)
        if not getattr(self, '_kindle_font_mode', False):
            self.editor.set_display_font_override(self.settings.editor_font)

        self._check_kindle_font()

    def _check_kindle_font(self):
        """Show warning if the selected display font is not native to Kindle."""
        font_name = self.settings.editor_font
        if font_name not in KINDLE_FONTS:
            self.statusBar().showMessage(f"Warning: '{font_name}' is not natively supported on Kindle. Previews may vary.", 5000)
            self.statusBar().setStyleSheet("color: #d35400; font-weight: bold;")
        else:
            self.statusBar().showMessage("Ready", 3000)
            self.statusBar().setStyleSheet("")

    def _on_zoom_changed(self, factor: float):
        self.settings.zoom_steps = int(factor)
        logger.debug("Zoom level: %d steps", self.settings.zoom_steps)

    def _on_typing_tick(self):
        self._session_seconds += 1
        h = self._session_seconds // 3600
        m = (self._session_seconds % 3600) // 60
        s = self._session_seconds % 60
        self.timer_label.setText(f"⏱ {h}:{m:02d}:{s:02d}")

    def _on_idle_timeout(self):
        self._typing_timer.stop()
        logger.debug("Idle timeout — typing timer stopped at %d seconds", self._session_seconds)

    def _update_modified_label(self):
        iso = self.project.doc.get_metadata("last_modified", "")
        if iso:
            try:
                dt = datetime.fromisoformat(iso)
                self.modified_label.setText(f"Modified: {dt.strftime('%H:%M')}")
            except (ValueError, TypeError):
                self.modified_label.setText("")
        else:
            self.modified_label.setText("")

    def _restore_cursor_position(self):
        pos = self.project.doc.get_metadata("cursor_char_pos", 0)
        if pos:
            max_pos = max(0, self.editor.document().characterCount() - 1)
            cursor = self.editor.textCursor()
            cursor.setPosition(min(pos, max_pos))
            self.editor.setTextCursor(cursor)
            self.editor.ensureCursorVisible()

    def _on_kindle_font_toggled(self, checked: bool):
        self._kindle_font_mode = checked
        if checked:
            self.editor.set_display_font_override(None)
        else:
            self.editor.set_display_font_override(self.settings.editor_font)

    def _on_display_prefs(self):
        dlg = DisplayPreferencesDialog(
            self,
            self.settings.editor_font,
            self.settings.editor_font_size,
            self.settings.display_text_color,
            self.settings.display_bg_color,
            self.settings.editor_margin_left,
            self.settings.editor_margin_right,
            self.settings.dynamic_margins,
            self.settings.max_content_width,
            self.settings.show_beta_warning,
            self.settings.beta_warning_initials,
            self.settings.projects_dir,
            self.settings.tooltips_enabled
        )
        if dlg.exec() == QDialog.Accepted:
            data = dlg.get_data()
            self.settings.editor_font = data["font"]
            self.settings.editor_font_size = data.get("font_size", self.settings.editor_font_size)
            self.settings.display_text_color = data["text_color"]
            self.settings.display_bg_color = data["bg_color"]
            self.settings.editor_margin_left = data["m_left"]
            self.settings.editor_margin_right = data["m_right"]
            self.settings.dynamic_margins = data["dynamic_margins"]
            self.settings.max_content_width = data["max_content_width"]
            self.settings.show_beta_warning = data["show_beta_warning"]
            self.settings.beta_warning_initials = data["beta_warning_initials"]
            self.settings.projects_dir = data["projects_dir"]
            self.settings.tooltips_enabled = data["tooltips_enabled"]
            self.settings.save()
            self._apply_display_preferences()
            self._apply_tooltips_preference()

    def _apply_tooltips_preference(self):
        """Enable or disable tooltips on all UI elements based on settings."""
        enabled = self.settings.tooltips_enabled

        # 1. Menus
        for action in self.menuBar().actions():
            menu = action.menu()
            if menu:
                for sub_action in menu.actions():
                    if not enabled:
                        sub_action.setToolTip("")
                    else:
                        self._set_default_tooltip(sub_action)

        # 2. Toolbar
        for action in self.toolbar.actions():
            if not enabled:
                action.setToolTip("")
            else:
                self._set_default_tooltip(action)

    def _set_default_tooltip(self, action: QAction):
        """Restore descriptive tooltips to specific actions."""
        text = action.text()
        if "New Project" in text: action.setToolTip("Create a new novel project folder.")
        elif "Open Project" in text: action.setToolTip("Open an existing PortoWrite project.")
        elif "Save Project" in text: action.setToolTip("Save all changes to disk.")
        elif "Import" in text: action.setToolTip("Import content from another file.")
        elif "Export" in text: action.setToolTip("Convert your novel to a publishable format (EPUB, etc).")
        elif "Bold" in text: action.setToolTip("Make selected text bold.")
        elif "Italic" in text: action.setToolTip("Make selected text italic.")
        elif "Underline" in text: action.setToolTip("Underline selected text.")
        elif "Left" in text: action.setToolTip("Align Left")
        elif "Center" in text: action.setToolTip("Align Center")
        elif "Right" in text: action.setToolTip("Align Right")
        elif "Justify" in text: action.setToolTip("Justify")
        elif "Undo" in text: action.setToolTip("Reverse last action.")
        elif "Redo" in text: action.setToolTip("Re-apply last undone action.")
    def _setup_ui(self):
        # 1. Menus
        menubar = self.menuBar()
        
        file_menu = menubar.addMenu("&File")
        
        new_action = QAction("&New Project...", self)
        new_action.setShortcut(QKeySequence.StandardKey.New)
        new_action.setToolTip("Create a new writing project from scratch.")
        new_action.triggered.connect(self._on_new)
        file_menu.addAction(new_action)

        open_action = QAction("&Open Project...", self)
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        open_action.setToolTip("Open an existing writing project.")
        open_action.triggered.connect(self._on_open)
        file_menu.addAction(open_action)

        open_folder_action = QAction("Open Project &Folder...", self)
        open_folder_action.setToolTip("Browse to and open a project folder directly from your computer.")
        open_folder_action.triggered.connect(self._on_open_project_folder)
        file_menu.addAction(open_folder_action)
        
        self.recent_menu = file_menu.addMenu("Recent Projects")
        self._update_recent_projects_menu()
        
        file_menu.addSeparator()

        save_action = QAction("&Save", self)
        save_action.setShortcut(QKeySequence.StandardKey.Save)
        save_action.setToolTip("Save your work to keep it up-to-date. A backup copy is created automatically (Ctrl+S).")
        save_action.triggered.connect(self._on_save)
        file_menu.addAction(save_action)

        save_as_action = QAction("Save &As...", self)
        save_as_action.setShortcut(QKeySequence.StandardKey.SaveAs)
        save_as_action.setToolTip("Save your current project as a new copy with a different title or location.")
        save_as_action.triggered.connect(self._on_save_as)
        file_menu.addAction(save_as_action)

        restore_action = QAction("&Restore from Backup...", self)
        restore_action.setToolTip("Restore your project to an earlier saved state from the automated backups folder.")
        restore_action.triggered.connect(self._on_restore_backup)
        file_menu.addAction(restore_action)

        save_snapshot_action = QAction("&Save Snapshot...", self)
        save_snapshot_action.setToolTip("Create a permanent named version of your project.")
        save_snapshot_action.triggered.connect(self._on_save_snapshot)
        file_menu.addAction(save_snapshot_action)

        version_history_action = QAction("Version &History...", self)
        version_history_action.setToolTip("View, restore, or delete previous snapshots of your project.")
        version_history_action.triggered.connect(self._on_version_history)
        file_menu.addAction(version_history_action)

        metadata_action = QAction("&Project Metadata...", self)
        metadata_action.setToolTip("Edit book details: title, author, ISBN, publisher, cover image, and description.")
        metadata_action.triggered.connect(self._on_metadata)
        file_menu.addAction(metadata_action)

        toc_action = QAction("&Table of Contents...", self)
        toc_action.setToolTip("View and edit the Table of Contents that will appear in your exported book.")
        toc_action.triggered.connect(self._on_toc_editor)
        file_menu.addAction(toc_action)

        file_menu.addSeparator()

        self._import_submenu = file_menu.addMenu("&Import")
        import_menu = self._import_submenu

        epub_action = QAction("EPUB Document (.epub)...", self)
        epub_action.setToolTip("Import content from an EPUB ebook file.")
        epub_action.triggered.connect(self._on_import_epub)
        import_menu.addAction(epub_action)

        md_action = QAction("Markdown Document (.md)...", self)
        md_action.setToolTip("Import text from a Markdown file.")
        md_action.setEnabled(is_pro())
        md_action.triggered.connect(self._on_import_md)
        import_menu.addAction(md_action)

        docx_action = QAction("Word Document (.docx)...", self)
        docx_action.setToolTip("Import text from a Microsoft Word document.")
        docx_action.setEnabled(is_pro())
        docx_action.triggered.connect(self._on_import_docx)
        import_menu.addAction(docx_action)

        export_action = QAction("&Export As...", self)
        export_action.setToolTip("Export your book to EPUB (for Kindle/Kobo/Apple Books), Markdown, or Word format.")
        export_action.triggered.connect(self._on_export)
        file_menu.addAction(export_action)

        file_menu.addSeparator()

        exit_action = QAction("&Exit", self)
        exit_action.setToolTip("Close PortoWrite. You will be prompted to save any unsaved changes.")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        edit_menu = menubar.addMenu("&Edit")
        find_action = QAction("&Find...", self)
        find_action.setShortcut(QKeySequence.StandardKey.Find)
        find_action.setToolTip("Search for a word or phrase anywhere in your document (Ctrl+F).")
        find_action.triggered.connect(self._on_find)
        edit_menu.addAction(find_action)

        replace_action = QAction("Find & Replace...", self)
        replace_action.setShortcut(QKeySequence.StandardKey.Replace)
        replace_action.setToolTip("Find text and replace it with something else throughout your document (Ctrl+H).")
        replace_action.triggered.connect(self._on_replace)
        edit_menu.addAction(replace_action)
        
        # 3. Central Widget (Splitter)
        self.central_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        self.editor = EditorWidget(self)
        self.central_splitter.addWidget(self.editor)
        
        self.preview = KindlePreviewWidget(self)
        self.preview.setVisible(False) # Hidden by default
        self.central_splitter.addWidget(self.preview)
        
        # Set initial sizes (70% editor, 30% preview)
        self.central_splitter.setStretchFactor(0, 7)
        self.central_splitter.setStretchFactor(1, 3)
        
        self.setCentralWidget(self.central_splitter)

        insert_menu = menubar.addMenu("&Insert")
        page_break_action = QAction("Page &Break", self)
        page_break_action.setShortcut(QKeySequence("Ctrl+Return"))
        page_break_action.setToolTip("Insert a page break — the next paragraph will start on a new page in the exported book (Ctrl+Enter).")
        page_break_action.triggered.connect(self.editor.insert_page_break)
        insert_menu.addAction(page_break_action)

        scene_break_action = QAction("Scene &Break", self)
        scene_break_action.setShortcut(QKeySequence("Ctrl+Shift+Return"))
        scene_break_action.setToolTip("Insert a scene break (⚬ ⚬ ⚬) to indicate a change of scene or time within a chapter (Ctrl+Shift+Enter).")
        scene_break_action.triggered.connect(self.editor.insert_scene_break)
        insert_menu.addAction(scene_break_action)

        self.view_menu = menubar.addMenu("&View")
        self._setup_view_menu(self.view_menu)

        help_menu = menubar.addMenu("&Help")
        
        about_action = QAction("About PortoWrite...", self)
        about_action.setToolTip("View version information and credits for PortoWrite.")
        about_action.triggered.connect(self._on_about)
        help_menu.addAction(about_action)

        user_guide_action = QAction("&User Guide", self)
        user_guide_action.setShortcut("F1")
        user_guide_action.setToolTip("View the integrated manual for PortoWrite.")
        user_guide_action.triggered.connect(self._on_user_guide)
        help_menu.addAction(user_guide_action)

        help_menu.addSeparator()

        upgrade_action = QAction("Donate / Upgrade to Pro...", self)
        upgrade_action.setToolTip("Support PortoWrite development with a donation and unlock Pro features like DOCX and Markdown export.")
        upgrade_action.triggered.connect(self._on_upgrade)
        help_menu.addAction(upgrade_action)

        license_action = QAction("Enter Licence Key...", self)
        license_action.setToolTip("Activate a licence key to unlock your edition (Supporter or Commercial).")
        license_action.triggered.connect(self._on_enter_license)
        help_menu.addAction(license_action)

        if get_edition() != Edition.FREE:
            deactivate_action = QAction("Deactivate Licence", self)
            deactivate_action.triggered.connect(self._on_deactivate_license)
            help_menu.addAction(deactivate_action)
        
        help_menu.addSeparator()

        bug_action = QAction("Report a Bug...", self)
        bug_action.setToolTip("Something not working right? Let us know so we can fix it.")
        bug_action.triggered.connect(lambda: QMessageBox.information(self, "Report a Bug", "Please send bug reports to support@portowrite.dev"))
        help_menu.addAction(bug_action)

        # 2. Status Bar
        self.statusBar().showMessage("Ready")
        self.timer_label = QLabel("⏱ 0:00:00")
        self.modified_label = QLabel("")
        self.stats_label = QLabel("Words: 0 | Chars: 0")
        
        self.edition_label = QLabel(f"<b>{get_edition_label()}</b>")
        self.edition_label.setStyleSheet("color: #2c3e50; font-size: 10px; margin-left: 10px;")
        
        self.statusBar().addPermanentWidget(self.timer_label)
        self.statusBar().addPermanentWidget(self.modified_label)
        self.statusBar().addPermanentWidget(self.stats_label)
        self.statusBar().addPermanentWidget(self.edition_label)

        # 4. Style Panel (Dock)
        self.style_dock = QDockWidget("Styles", self)
        self.style_dock.setObjectName("style_dock")
        self.style_panel = StylePanel(self)
        self.style_dock.setWidget(self.style_panel)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.style_dock)
        
        # 4.1 Chapter Sidebar (Dock)
        self.chapter_dock = QDockWidget("Chapters", self)
        self.chapter_dock.setObjectName("chapter_dock")
        self.chapter_sidebar = ChapterSidebar(self)
        self.chapter_dock.setWidget(self.chapter_sidebar)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.chapter_dock)
        self.chapter_dock.visibilityChanged.connect(
            lambda _: QTimer.singleShot(50, self.editor.refresh_styling)
        )

        # Add toggles to View menu
        self.view_menu_styles_action = self.style_dock.toggleViewAction()
        self.view_menu_styles_action.setText("Style Panel")
        self.view_menu.addAction(self.view_menu_styles_action)
        
        self.view_menu_chapters_action = self.chapter_dock.toggleViewAction()
        self.view_menu_chapters_action.setText("Chapter Sidebar")
        self.view_menu.addAction(self.view_menu_chapters_action)

        # 5. Toolbar
        self.toolbar = EditorToolbar(self)
        self.addToolBar(self.toolbar)

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

    def _setup_view_menu(self, menu: QMenu):
        log_menu = menu.addMenu("Log Level")
        
        self.log_group = QActionGroup(self)
        self.log_group.setExclusive(True)

        for level in ["detailed", "light", "none"]:
            action = QAction(level.capitalize(), self, checkable=True)
            action.setData(level)
            if self.settings.log_level == level:
                action.setChecked(True)
            
            action.triggered.connect(self._on_log_level_changed)
            self.log_group.addAction(action)
            log_menu.addAction(action)
            
        menu.addSeparator()

        # Reader Preview Actions
        preview_action = QAction("Reader Preview", self, checkable=True)
        preview_action.setShortcut(QKeySequence("Ctrl+P"))
        preview_action.setToolTip("Show a side-by-side preview of how your book will look on a Kindle e-reader (Ctrl+P).")
        preview_action.triggered.connect(self._on_reader_preview_toggled)
        menu.addAction(preview_action)
        
        theme_menu = menu.addMenu("Preview Theme")
        self.theme_group = QActionGroup(self)
        for theme_name in KINDLE_THEMES.keys():
            action = QAction(theme_name, self, checkable=True)
            action.setData(theme_name)
            if theme_name == "Paperwhite":
                action.setChecked(True)
            action.triggered.connect(self._on_preview_theme_changed)
            self.theme_group.addAction(action)
            theme_menu.addAction(action)

        menu.addSeparator()
        
        # Zoom Actions
        zoom_in_action = QAction("Zoom &In", self)
        zoom_in_action.setShortcut(QKeySequence.StandardKey.ZoomIn)
        zoom_in_action.setToolTip("Make the editor text larger. This only affects the display — it does not change your exported font size.")
        zoom_in_action.triggered.connect(self.editor.zoomIn)
        menu.addAction(zoom_in_action)

        zoom_out_action = QAction("Zoom &Out", self)
        zoom_out_action.setShortcut(QKeySequence.StandardKey.ZoomOut)
        zoom_out_action.setToolTip("Make the editor text smaller. This only affects the display — it does not change your exported font size.")
        zoom_out_action.triggered.connect(self.editor.zoomOut)
        menu.addAction(zoom_out_action)

        reset_zoom_action = QAction("&Reset Zoom", self)
        reset_zoom_action.setShortcut(QKeySequence(Qt.Modifier.CTRL | Qt.Key.Key_0))
        reset_zoom_action.setToolTip("Restore the editor text to its default display size (Ctrl+0).")
        reset_zoom_action.triggered.connect(lambda: self.editor.set_zoom_steps(0))
        menu.addAction(reset_zoom_action)

        menu.addSeparator()
        self._kindle_font_mode = False
        kindle_font_action = QAction("Use Kindle Font", self, checkable=True)
        kindle_font_action.setToolTip("Switch the editor display to Kindle's native fonts (Bookerly, Caecilia, etc.) so you can preview how the text will look on a real device.")
        kindle_font_action.triggered.connect(self._on_kindle_font_toggled)
        menu.addAction(kindle_font_action)
        self._kindle_font_action = kindle_font_action

        display_prefs_action = QAction("Display Preferences...", self)
        display_prefs_action.setToolTip("Customize the editor's appearance: font, text color, background color, margins, and zoom level.")
        display_prefs_action.triggered.connect(self._on_display_prefs)
        menu.addAction(display_prefs_action)

    def _on_log_level_changed(self):
        action = self.sender()
        if action and action.isChecked():
            level = action.data()
            # Log at current level before switching
            logging.getLogger().info(f"Changing log level to: {level}")
            
            self.settings.log_level = level
            self.settings.save()
            setup_logging(level)
            
            # Log at new level after switching (if not none)
            logging.getLogger().warning(f"Log level is now {level}")
            
            self.statusBar().showMessage(f"Log level changed to {level}", 3000)

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

    def closeEvent(self, event):
        # Persist cursor position and session timer before any dialog
        if self.project.doc is not None:
            self.project.doc.set_metadata("cursor_char_pos", self.editor.textCursor().position())
            self.project.doc.set_metadata("session_seconds", self._session_seconds)

        if self.is_dirty:
            res = QMessageBox.warning(
                self, "Unsaved Changes",
                f"The project '{self.project.name}' has unsaved changes.\n\nDo you want to save them before exiting?",
                QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel
            )

            if res == QMessageBox.StandardButton.Save:
                self._on_save()
                if not self.is_dirty:  # save succeeded
                    self.project.delete_autosave()
                else:  # save failed
                    event.ignore()
                    return
            elif res == QMessageBox.StandardButton.Cancel:
                event.ignore()
                return
            elif res == QMessageBox.StandardButton.Discard:
                try:
                    self.editor.sync_to_document(self.project.doc)
                    self.project.save_autosave()
                    logger.info("Recovery autosave created on discard-close")
                except Exception as exc:
                    logger.error("Recovery autosave failed: %s", exc)
        else:
            # Clean close with no changes, remove any existing autosave
            self.project.delete_autosave()

        self.settings.window_width = self.width()
        self.settings.window_height = self.height()
        self.settings.save()
        logger.debug("Closing MainWindow, settings saved.")
        super().closeEvent(event)

    # --- File Menu Handlers ---

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

    def _refresh_ui(self):
        """Refresh all UI components to reflect current document state."""
        self.editor.load_document(self.project.doc)
        self.style_panel.refresh(self.project.doc.styles)
        self.toolbar.refresh_styles(self.project.doc.styles.names())
        self._on_structure_changed()
        self._update_title()

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
                res = QMessageBox.question(
                    self, "Autosave Found",
                    f"An autosave was found for '{self.project.name}'.\n\n"
                    "This may be from a crash or a discarded session.\n\n"
                    "Restore from autosave?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )
                if res == QMessageBox.StandardButton.Yes:
                    self.project.doc = self.project.load_autosave()
                    self.editor.load_document(self.project.doc)
                    self.style_panel.refresh(self.project.doc.styles)
                    self.toolbar.refresh_styles(self.project.doc.styles.names())
                    self._on_structure_changed()
                    self.is_dirty = True
                    self._update_title()
                    self.statusBar().showMessage("Restored from autosave", 5000)
                else:
                    self.project.delete_autosave()

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

    def _on_structure_changed(self):
        """Called when the document structure (chapters) might have changed."""
        # Refresh the sidebar list
        items = []
        block = self.editor.document().begin()
        while block.isValid():
            style_name = block.blockFormat().property(STYLE_NAME_PROPERTY)
            if style_name in ("ChapterHeader", "Heading1"):
                items.append((1, block.text()))
            elif style_name in ("SubHeader", "Heading2"):
                items.append((2, block.text()))
            block = block.next()
        
        self.chapter_sidebar.refresh(items)

    # --- Style Management Handlers ---

    def _on_style_added(self, data: dict):
        from porto_write.styles import StyleDefinition
        new_style = StyleDefinition(**data)
        self.project.doc.add_style(new_style)
        self.style_panel.refresh(self.project.doc.styles)
        self.toolbar.refresh_styles(self.project.doc.styles.names())
        self.is_dirty = True
        self._update_title()

    def _on_style_updated(self, old_name: str, data: dict):
        new_name = data["name"]
        style = self.project.doc.styles.get(old_name)
        if not style: return

        # Update properties
        for k, v in data.items():
            setattr(style, k, v)

        if old_name != new_name:
            self.project.doc.rename_style(old_name, new_name)
        
        # Refresh UI
        self.style_panel.refresh(self.project.doc.styles)
        self.toolbar.refresh_styles(self.project.doc.styles.names())
        self.editor.refresh_styling()
        self._update_preview()
        
        self.is_dirty = True
        self._update_title()

    def _on_style_deleted(self, name: str):
        # First, revert blocks in the document model
        for chapter in self.project.doc.chapters:
            for block in chapter.blocks:
                if block.style_name == name:
                    block.style_name = "Body"
        
        # Remove from registry
        self.project.doc.remove_style(name)
        
        # Refresh UI
        self.style_panel.refresh(self.project.doc.styles)
        self.toolbar.refresh_styles(self.project.doc.styles.names())
        self.editor.refresh_styling()
        self._update_preview()
        
        self.is_dirty = True
        self._update_title()

    def _on_find(self):
        if not self._find_replace_dlg:
            self._find_replace_dlg = FindReplaceDialog(self.editor, self)
        self._find_replace_dlg.show()
        self._find_replace_dlg.activateWindow()
        self._find_replace_dlg.find_field.setFocus()

    def _on_replace(self):
        if not self._find_replace_dlg:
            self._find_replace_dlg = FindReplaceDialog(self.editor, self)
        self._find_replace_dlg.show()
        self._find_replace_dlg.activateWindow()
        self._find_replace_dlg.find_field.setFocus()

    def _on_about(self):
        dlg = AboutDialog(self)
        dlg.exec()

    def _on_upgrade(self):
        dlg = UpgradeDialog(self)
        dlg.exec()

    def _on_enter_license(self):
        dlg = LicenceKeyDialog(self)
        dlg.exec()

    def _on_user_guide(self):
        from porto_write.ui.dialogs import HelpUserGuideDialog
        dlg = HelpUserGuideDialog(self)
        dlg.exec()

    def _on_deactivate_license(self):
        res = QMessageBox.question(
            self, "Deactivate Licence",
            "Are you sure you want to deactivate your licence?\n\n"
            "This will revert the application to the Free edition.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if res == QMessageBox.StandardButton.Yes:
            deactivate_licence()
            QMessageBox.information(
                self, "Licence Deactivated",
                "Licence deactivated. Restart PortoWrite to apply."
            )

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

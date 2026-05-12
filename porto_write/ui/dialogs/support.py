import logging
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
    QLabel, QDialogButtonBox, QTabWidget, QTextBrowser,
    QApplication, QMessageBox
)
from PySide6.QtCore import Qt
from porto_write.constants import APP_NAME, APP_VERSION
from porto_write.licensing import get_edition_label

logger = logging.getLogger(__name__)

class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"About {APP_NAME}")
        self.setFixedSize(300, 180)
        
        layout = QVBoxLayout(self)
        
        title_label = QLabel(f"<b>{APP_NAME} v{APP_VERSION}</b>")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)
        
        edition_label = QLabel(f"Edition: {get_edition_label()}")
        edition_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(edition_label)
        
        copy_label = QLabel("© 2026 William Porto. All rights reserved.")
        copy_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(copy_label)
        
        link_label = QLabel("<a href='https://github.com'>See TIERS.md for licensing info</a>")
        link_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        link_label.setOpenExternalLinks(True)
        layout.addWidget(link_label)
        
        layout.addStretch()
        
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

class UpgradeDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Upgrade PortoWrite")
        self.setFixedSize(350, 250)
        
        layout = QVBoxLayout(self)
        
        edition_label = QLabel(f"Current Edition: <b>{get_edition_label()}</b>")
        layout.addWidget(edition_label)
        
        info_label = QLabel("<b>Upgrade to Pro to unlock:</b>")
        layout.addWidget(info_label)
        
        features_list = QLabel(
            "• DOCX & Markdown Export\n"
            "• Custom Styles (Create/Edit/Delete)\n"
            "• Future: Footnotes & Hyperlinks\n"
            "• Future: Track Changes\n"
            "• Priority Support"
        )
        layout.addWidget(features_list)
        
        layout.addStretch()
        
        btn_layout = QHBoxLayout()
        license_btn = QPushButton("Request Commercial License")
        license_btn.clicked.connect(self._request_commercial_license)
        license_btn.setStyleSheet("background-color: #2e8b57; color: white; font-weight: bold; padding: 6px;")
        btn_layout.addWidget(license_btn)
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.reject)
        btn_layout.addWidget(close_btn)
        
        layout.addLayout(btn_layout)
        
    def _request_commercial_license(self):
        email = "portowrite@portowlabs.com"
        QApplication.clipboard().setText(email)
        QMessageBox.information(
            self,
            "Commercial License",
            f"For commercial licensing, contact:\n\n{email}\n\n(Email has been copied to your clipboard.)"
        )

class HelpUserGuideDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("PortoWrite User Guide")
        self.resize(650, 550)
        
        layout = QVBoxLayout(self)
        
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        
        self._add_tab("Getting Started", self._get_started_html())
        self._add_tab("Writing", self._get_writing_html())
        self._add_tab("View & Focus", self._get_view_focus_html())
        self._add_tab("Styles", self._get_styles_html())
        self._add_tab("Exporting", self._get_export_html())
        self._add_tab("Backups & Versions", self._get_backup_html())
        
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _add_tab(self, title, html):
        browser = QTextBrowser()
        browser.setHtml(html)
        browser.setOpenExternalLinks(True)
        self.tabs.addTab(browser, title)

    def _get_started_html(self):
        return """
        <h2>Welcome to PortoWrite</h2>
        <p>PortoWrite is a specialized editor designed for novelists. It focuses on clean writing and seamless EPUB generation.</p>
        <h3>Core Workflows:</h3>
        <ul>
            <li><b>New Project:</b> File > New Project. Every novel lives in its own folder.</li>
            <li><b>Open Project:</b> File > Open Project or double-click a project.json.</li>
            <li><b>Project Metadata:</b> File > Project Metadata. Set your Title, Author, and Cover image here.</li>
        </ul>
        """

    def _get_writing_html(self):
        return """
        <h2>The Writing Experience</h2>
        <p>Use the main editor for your manuscript. PortoWrite handles chapters and subheadings via Styles.</p>
        <ul>
            <li><b>Chapters:</b> Use the 'Chapter Header' style for new chapters. They appear automatically in the Sidebar.</li>
            <li><b>Chapter Search:</b> Type in the search box at the top of the Chapter Sidebar to filter chapters by keyword.</li>
            <li><b>Scene Breaks:</b> Insert > Scene Break (Ctrl+Shift+Enter) to insert ⚬ ⚬ ⚬.</li>
            <li><b>Page Breaks:</b> Insert > Page Break (Ctrl+Enter) to force a new page in the exported book.</li>
            <li><b>TOC:</b> Use Insert → Insert Table of Contents to auto-generate a linked TOC from your chapter headings.</li>
            <li><b>Spelling:</b> Misspelled words are underlined in red. Right-click for suggestions.</li>
        </ul>
        """

    def _get_view_focus_html(self):
        return """
        <h2>View Modes & Focus</h2>
        <p>PortoWrite offers several ways to view your manuscript and stay focused.</p>
        <ul>
            <li><b>Reader Preview (Ctrl+P):</b> Opens a side panel showing a device-accurate simulation of your book. Choose from Paperwhite, Sepia, or Night themes.</li>
            <li><b>Ebook Edit Mode:</b> Available via the View menu. It transforms the main editor into a device-accurate Kindle screen.
                <ul>
                    <li><b>Device Selector:</b> Choose which e-reader to simulate (e.g. Kindle Paperwhite, Kobo Libra).</li>
                    <li><b>Aa (CPL):</b> Cycle through character-per-line presets (45, 55, 65) to find your perfect reading density.</li>
                    <li><b>Line Height & Margins:</b> Fine-tune the vertical spacing and side margins to match your comfort.</li>
                    <li><b>Responsive Layout:</b> The editor now automatically centers and scales when you resize the PortoWrite window.</li>
                </ul>
            </li>
            <li><b>Focus Mode (F11):</b> Instantly hides the sidebar, style panel, and toolbar, giving you a completely distraction-free writing surface. Press F11 again to restore your panels.</li>
        </ul>
        """

    def _get_styles_html(self):
        return """
        <h2>Mastering Styles</h2>
        <p>Styles control how your book looks. Use the Style Panel (right side) to apply and edit styles.</p>
        <ul>
            <li><b>Applying Styles:</b> Select text and click a style in the panel or use the toolbar dropdown.</li>
            <li><b>Editing Styles:</b> Right-click a style in the panel > Edit Style. Changes apply instantly to all text using that style.</li>
            <li><b>Built-in Styles:</b> 'Body', 'Chapter Header', and 'Sub Header' are default. You can create custom styles in the Pro edition.</li>
        </ul>
        """

    def _get_export_html(self):
        return """
        <h2>Exporting your Book</h2>
        <p>Convert your manuscript into a publishable format via File > Export As.</p>
        <ul>
            <li><b>EPUB:</b> The primary format for Kindle, Kobo, and Apple Books.</li>
            <li><b>Validation:</b> PortoWrite automatically validates your EPUB against industry standards.</li>
            <li><b>Platform Profiles:</b> Select 'Kindle' or 'Standard' profiles to optimize formatting for specific devices.</li>
            <li><b>TOC:</b> Use File > Table of Contents to review or rename entries before exporting.</li>
        </ul>
        """

    def _get_backup_html(self):
        return """
        <h2>Data Protection</h2>
        <p>Your work is precious. PortoWrite provides multiple layers of protection.</p>
        <ul>
            <li><b>Auto-Save:</b> Saves a recovery copy every 5 minutes (configurable in Preferences).</li>
            <li><b>Automatic Backups:</b> A full project backup is created every time you click 'Save'.</li>
            <li><b>Restore from Backup:</b> File > Restore from Backup. View previews and word counts before rolling back.</li>
            <li><b>Snapshots:</b> File > Save Snapshot. Use these for permanent 'milestone' versions (e.g., 'First Draft Complete').</li>
        </ul>
        """

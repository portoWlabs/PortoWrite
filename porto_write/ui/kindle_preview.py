import logging
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QTextBrowser, 
    QPushButton, QComboBox, QLabel, QSpacerItem, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QUrl
from porto_write.document import PortoDocument

logger = logging.getLogger(__name__)

KINDLE_THEMES = {
    "Paperwhite": {
        "bg": "#ffffff",
        "fg": "#000000",
        "font": "Georgia, serif"
    },
    "Sepia": {
        "bg": "#f4ecd8",
        "fg": "#5b4636",
        "font": "Georgia, serif"
    },
    "Night": {
        "bg": "#1a1a1a",
        "fg": "#cccccc",
        "font": "Georgia, serif"
    }
}

def document_to_kindle_html(doc: PortoDocument, font_size_pt=12, margin_px=40, line_height=1.4) -> str:
    """Convert PortoDocument into semantic Kindle-simulated HTML."""
    html = '<html><head><style>'
    
    # 1. Map StyleRegistry to CSS classes
    for style in doc.styles.all():
        css = f".{style.name} {{"
        css += f" font-family: '{style.font_family}', serif;"
        css += f" font-size: {style.font_size}pt;"
        if style.bold:
            css += " font-weight: bold;"
        if style.italic:
            css += " font-style: italic;"
        if style.underline:
            css += " text-decoration: underline;"
        
        # Alignment
        if style.alignment == "center":
            css += " text-align: center;"
        elif style.alignment == "right":
            css += " text-align: right;"
        elif style.alignment == "justify":
            css += " text-align: justify;"
        else:
            css += " text-align: left;"
            
        css += f" line-height: {style.line_height};"
        css += f" margin-top: {style.space_before}pt;"
        css += f" margin-bottom: {style.space_after}pt;"
        
        # Kindle specifics
        if style.page_break_before:
            css += " page-break-before: always;"
        if style.page_break_after:
            css += " page-break-after: always;"
            
        html += css + " }\n"

    # 2. Base layout and Kindle resets
    html += f"""
    body {{
        margin: 30px {margin_px}px;
        line-height: {line_height};
        font-size: {font_size_pt}pt;
    }}
    h1 {{ font-size: 1.8em; text-align: center; }}
    p {{ margin: 0; padding: 0; text-indent: 0; }}
    a {{ text-decoration: none; color: inherit; }}
    
    .page-break-bar {{
        border-top: 1px dashed #bbb;
        margin: 40px 0 20px 0;
        text-align: center;
        height: 1px;
    }}
    .scene-break-bar {{
        margin: 24px 0;
        text-align: center;
        color: #999;
        font-size: 1.2em;
    }}
    .page-break-label {{
        font-family: sans-serif;
        font-size: 9px;
        color: #999;
        text-transform: uppercase;
        letter-spacing: 1px;
        background: inherit;
        position: relative;
        top: -6px;
        padding: 0 10px;
    }}
    """
    
    # Custom scrollbar hiding for cleaner "device" look
    html += """
    ::-webkit-scrollbar { width: 0px; background: transparent; }
    """

    html += '</style></head><body>'

    # 3. Render content
    for i, chapter in enumerate(doc.chapters):
        html += f'<div class="chapter">'
        
        # Track block counter within chapter for click-to-edit
        b_idx = 0
        
        if chapter.title:
            # G18: Only inject bar if it's NOT the first chapter
            if i > 0:
                html += '<div class="page-break-bar"><span class="page-break-label">Page Break</span></div>'
            
            html += f'<h1 id="b{i}_{b_idx}" class="ChapterHeader"><a href="block://{i}/{b_idx}">{chapter.title}</a></h1>'
            b_idx += 1
        
        for block in chapter.blocks:
            # G18: Specialized handling for marker styles to prevent duplicates
            if block.style_name == "PageBreak":
                html += '<div class="page-break-bar"><span class="page-break-label">Page Break</span></div>'
                b_idx += 1
                continue
            elif block.style_name == "SceneBreak":
                html += '<div class="scene-break-bar">⚬ ⚬ ⚬</div>'
                b_idx += 1
                continue

            style = doc.styles.get(block.style_name)
            if style and style.page_break_before:
                html += '<div class="page-break-bar"><span class="page-break-label">Page Break</span></div>'
                
            text = block.text or "&nbsp;"
            html += f'<div id="b{i}_{b_idx}" class="{block.style_name}"><a href="block://{i}/{b_idx}">{text}</a></div>'
            b_idx += 1
        
        html += '</div>'

    html += '</body></html>'
    return html

class KindlePreviewWidget(QWidget):
    """Simulated Kindle device frame containing a fixed-width reader."""

    block_clicked = Signal(int, int) # (chap_idx, block_idx)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("KindlePreviewPanel")
        self.setStyleSheet("background-color: #2b2b2b;")

        self._font_size_pt = 12
        self._margin_px = 40
        self._line_height = 1.4
        self._current_doc = None
        self._current_theme = "Paperwhite"

        # Main layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
        self.main_layout.setContentsMargins(10, 10, 10, 20)

        # 0. Reading Controls Toolbar
        self.toolbar = QWidget()
        self.toolbar.setStyleSheet("color: #ccc; font-size: 11px;")
        t_layout = QHBoxLayout(self.toolbar)
        t_layout.setContentsMargins(0, 0, 0, 10)

        # Theme
        t_layout.addWidget(QLabel("Theme:"))
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(list(KINDLE_THEMES.keys()))
        self.theme_combo.currentTextChanged.connect(self.set_theme)
        t_layout.addWidget(self.theme_combo)

        t_layout.addSpacing(15)

        # Font Size
        t_layout.addWidget(QLabel("Aa:"))
        btn_fs_down = QPushButton("−")
        btn_fs_down.setFixedWidth(24)
        btn_fs_down.clicked.connect(lambda: self._adjust_font_size(-1))
        t_layout.addWidget(btn_fs_down)

        self.lbl_fs = QLabel(f"{self._font_size_pt}pt")
        self.lbl_fs.setFixedWidth(35)
        self.lbl_fs.setAlignment(Qt.AlignCenter)
        t_layout.addWidget(self.lbl_fs)

        btn_fs_up = QPushButton("+")
        btn_fs_up.setFixedWidth(24)
        btn_fs_up.clicked.connect(lambda: self._adjust_font_size(1))
        t_layout.addWidget(btn_fs_up)

        t_layout.addSpacing(15)

        # Margins
        t_layout.addWidget(QLabel("Margins:"))
        btn_m_down = QPushButton("−")
        btn_m_down.setFixedWidth(24)
        btn_m_down.clicked.connect(lambda: self._cycle_margin(-1))
        t_layout.addWidget(btn_m_down)

        self.lbl_m = QLabel(f"{self._margin_px}")
        self.lbl_m.setFixedWidth(20)
        self.lbl_m.setAlignment(Qt.AlignCenter)
        t_layout.addWidget(self.lbl_m)

        btn_m_up = QPushButton("+")
        btn_m_up.setFixedWidth(24)
        btn_m_up.clicked.connect(lambda: self._cycle_margin(1))
        t_layout.addWidget(btn_m_up)

        t_layout.addSpacing(15)

        # Line Spacing
        t_layout.addWidget(QLabel("LS:"))
        btn_ls_down = QPushButton("−")
        btn_ls_down.setFixedWidth(24)
        btn_ls_down.clicked.connect(lambda: self._cycle_line_height(-1))
        t_layout.addWidget(btn_ls_down)

        self.lbl_ls = QLabel(f"{self._line_height}")
        self.lbl_ls.setFixedWidth(25)
        self.lbl_ls.setAlignment(Qt.AlignCenter)
        t_layout.addWidget(self.lbl_ls)

        btn_ls_up = QPushButton("+")
        btn_ls_up.setFixedWidth(24)
        btn_ls_up.clicked.connect(lambda: self._cycle_line_height(1))
        t_layout.addWidget(btn_ls_up)

        t_layout.addStretch()

        self.main_layout.addWidget(self.toolbar)

        # 1. The Device Frame (Outer Bezel)
        self.device_frame = QFrame()
        self.device_frame.setFixedWidth(440)
        self.device_frame.setStyleSheet("""
            QFrame {
                background-color: #111;
                border: 2px solid #000;
                border-radius: 30px;
            }
        """)
        
        self.device_layout = QVBoxLayout(self.device_frame)
        self.device_layout.setContentsMargins(30, 50, 30, 60) # Asymmetric bezels
        
        # 2. The Screen (QTextBrowser)
        self.browser = QTextBrowser()
        self.browser.setFixedWidth(380)
        self.browser.setReadOnly(True)
        self.browser.setAcceptRichText(True)
        self.browser.setOpenLinks(False)
        self.browser.anchorClicked.connect(self._on_anchor_clicked)
        self.browser.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.browser.setFrameStyle(QFrame.NoFrame)
        
        self.device_layout.addWidget(self.browser)
        self.main_layout.addWidget(self.device_frame)

        self._apply_theme_colors()

    def _on_anchor_clicked(self, url: QUrl):
        """Handle block clicks for 'Click-to-Edit' functionality."""
        url_str = url.toString()
        if url_str.startswith("block://"):
            try:
                # Format: block://chap_idx/block_idx
                parts = url_str[8:].split('/')
                chap_idx = int(parts[0])
                block_idx = int(parts[1])
                self.block_clicked.emit(chap_idx, block_idx)
            except (ValueError, IndexError) as e:
                logger.warning("Failed to parse block anchor: %s", url_str)

    def resizeEvent(self, event):
        """Responsive sizing for the Kindle frame."""
        super().resizeEvent(event)
        
        # Calculate sizing
        device_width = min(self.width() - 40, 560)
        browser_width = device_width - 60
        browser_height = int(browser_width / 0.756)
        
        # Update widgets
        self.device_frame.setFixedWidth(device_width)
        self.browser.setFixedSize(browser_width, browser_height)
        
        # Ensure centered horizontal alignment
        self.main_layout.setAlignment(Qt.AlignTop | Qt.AlignHCenter)

    def set_theme(self, theme_name: str):
        if theme_name in KINDLE_THEMES:
            self._current_theme = theme_name
            self._apply_theme_colors()
            if self._current_doc:
                self.update_preview(self._current_doc)

    def _apply_theme_colors(self):
        theme = KINDLE_THEMES[self._current_theme]
        self.browser.setStyleSheet(f"background-color: {theme['bg']}; color: {theme['fg']}; border: none;")

    def _adjust_font_size(self, delta: int):
        new_size = self._font_size_pt + delta
        if 10 <= new_size <= 22:
            self._font_size_pt = new_size
            self.lbl_fs.setText(f"{self._font_size_pt}pt")
            if self._current_doc:
                self.update_preview(self._current_doc)

    def _cycle_margin(self, direction: int):
        margins = [20, 40, 60]
        try:
            idx = margins.index(self._margin_px)
            new_idx = (idx + direction) % len(margins)
            self._margin_px = margins[new_idx]
            self.lbl_m.setText(f"{self._margin_px}")
            if self._current_doc:
                self.update_preview(self._current_doc)
        except ValueError:
            self._margin_px = 40

    def _cycle_line_height(self, direction: int):
        steps = [1.2, 1.4, 1.6, 1.8]
        try:
            idx = steps.index(self._line_height)
            new_idx = (idx + direction) % len(steps)
            self._line_height = steps[new_idx]
            self.lbl_ls.setText(f"{self._line_height}")
            if self._current_doc:
                self.update_preview(self._current_doc)
        except ValueError:
            self._line_height = 1.4

    def set_scroll_percentage(self, percentage: float):
        """Scroll the preview to a specific percentage (0.0 to 1.0)."""
        sb = self.browser.verticalScrollBar()
        if sb.maximum() > 0:
            target = int(percentage * sb.maximum())
            sb.setValue(target)

    def scroll_to_block(self, chap_idx: int, block_idx: int):
        """Scroll to a specific block using its HTML anchor ID."""
        self.browser.scrollToAnchor(f"b{chap_idx}_{block_idx}")

    def update_preview(self, doc: PortoDocument):
        """Re-render the entire document based on current state."""
        self._current_doc = doc
        if not doc:
            return
        try:
            html_content = document_to_kindle_html(
                doc, 
                font_size_pt=self._font_size_pt, 
                margin_px=self._margin_px, 
                line_height=self._line_height
            )
            self.browser.setHtml(html_content)
            logger.debug("Kindle preview updated.")
        except Exception as e:
            logger.error("Failed to update Kindle preview: %s", e)
            self.browser.setPlainText(f"Error rendering preview: {e}")

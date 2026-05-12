# PortoWrite

PortoWrite is a distraction-free novel writing app for Windows with a built-in Kindle previewer. It gives authors an easy way to write, style, export, and preview books for EPUB, DOCX, Markdown, and Kindle-ready output — all in one place.

![Version](https://img.shields.io/badge/version-0.9.0%20Beta-blue)
![Platform](https://img.shields.io/badge/platform-Windows%2010%2B-lightgrey)

> **Beta** — All features are available to all users during the beta period.

---

## Highlights

- **Writer-first EPUB workflow** — create books without fighting EPUB code or complex formatting tools.
- **Kindle Reader Preview** — side-by-side preview of how your book looks on a Kindle (Paperwhite, Sepia, or Night theme; toggle with Ctrl+P).
- **Ebook Edit Mode** — constrains the editor to a device-accurate width and applies your Kindle theme colours so you write exactly what readers see.
- **Focus Mode** — hide all panels and toolbars with F11 for a completely distraction-free writing surface.
- **Chapter sidebar** — navigate your manuscript with a live multi-level outline.
- **Chapter Search** — filter box at the top of the Chapter Sidebar to jump to any chapter instantly.
- **TOC generation** — Insert → Insert Table of Contents to auto-generate a linked TOC from your headings.
- **Named paragraph styles** — Body, Chapter Title, SubHeader, Block Quote, Code, Scene Break, and more.
- **Alignment toolbar** — Left, Center, Right, and Justify buttons in the main toolbar.
- **Export and import** — EPUB 3 (Kindle / Kobo / Apple Books profiles), DOCX, and Markdown.
- **Find & Replace** — regex, case-sensitive, and whole-word options (Ctrl+F / Ctrl+H).
- **Offline spell check** — Hunspell engine, contraction-aware, with a personal user dictionary.
- **Version snapshots** — save named checkpoints of your manuscript and restore them at any time.
- **Autosave & crash recovery** — automatic saves every 5 minutes; restores cleanly after a crash.
- **Portable install** — all app data lives in the install folder; uninstall by deleting it.

---

## Installation

### Windows Installer (recommended)

Download the latest installer from the [Releases page](https://github.com/portoWlabs/PortoWrite/releases) and run it. No admin rights required.

### Run from Source

**Requirements:** Python 3.10+, Windows 10 or later

```bash
git clone https://github.com/portoWlabs/PortoWrite.git
cd PortoWrite
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

---

## Quick Start

1. **File → New Project** — name your novel and choose a save location
2. Click a chapter in the sidebar to navigate, or just start typing
3. Select a style from the Style Panel or right-click in the editor
4. **File → Export** when ready — choose EPUB, DOCX, or Markdown

---

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| Ctrl+N | New Project |
| Ctrl+O | Open Project |
| Ctrl+S | Save |
| Ctrl+B / I / U | Bold / Italic / Underline |
| Ctrl+F | Find |
| Ctrl+H | Find & Replace |
| Ctrl+Shift+Return | Insert Scene Break |
| Ctrl+Enter | Insert Page Break |
| Ctrl+P | Toggle Reader Preview |
| F11 | Focus Mode |
| Ctrl+0 | Reset Zoom |
| F1 | User Guide |
| Ctrl+Scroll | Zoom editor |

---

## Licence

Free for personal, non-commercial use. See [LICENSE.txt](LICENSE.txt) for full terms.

- Personal use is free — no sign-up, no time limit.
- Commercial use (within a business, for clients, or in any revenue-generating context) requires a separate licence.
- Contact portowrite@portowlabs.com for commercial licensing.

---

## Built With

- [PySide6](https://wiki.qt.io/Qt_for_Python) — Qt6 Python bindings (LGPL v3)
- [ebooklib](https://github.com/aerkalov/ebooklib) — EPUB handling (AGPL v3)
- [python-docx](https://github.com/python-openxml/python-docx) — DOCX generation (MIT)
- [mistune](https://github.com/lepture/mistune) — Markdown parsing (BSD-3-Clause)
- [spylls](https://github.com/zverok/spylls) — Hunspell spell checking (LGPL v2.1)
- [lxml](https://lxml.de) — XML processing (BSD)
- [pyspellchecker](https://github.com/barrust/pyspellchecker) — Spell checking (MIT)

See [ACKNOWLEDGEMENTS.md](ACKNOWLEDGEMENTS.md) for full details.

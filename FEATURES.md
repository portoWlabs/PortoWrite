# PortoWrite — Feature Reference

*Current release: v0.9.0 Beta. All features are available unless marked [v2 planned].*

---

## 1. Project Management

| Feature | Detail |
|---------|--------|
| New project | Creates a named folder under the projects root (`~/Documents/PortoWrite`); stores `project.json` |
| Open project | Browse and select from projects in the current root folder |
| Open from disk | Browse to any folder on disk to open a project stored outside the default root |
| Save | Saves `project.json` in the project folder; creates a timestamped backup in `backups/` |
| Save As (Clone) | Duplicates the current project to a new title/folder |
| Recent files | Last-opened projects listed in File menu |
| Autosave | Saves `autosave.json` every 5 minutes (configurable); never overwrites `project.json` |
| Crash recovery | On next open, if `autosave.json` exists, user is prompted to restore or discard |
| Emergency backup | Optional: on Discard, a timestamped `emergency_*.json` is preserved alongside the autosave |
| Max backups | Configurable cap; oldest backups pruned automatically |
| Restore from Backup | File > Restore from Backup — lists timestamped backups with a live preview (title, author, chapters, word count) before restoring |
| Version Snapshots | File > Versions > Save Snapshot — saves a named checkpoint; File > Versions > Version History — browse, restore, or delete snapshots |
| Projects root folder | Default: `~/Documents/PortoWrite`. File > Preferences > "Projects Root Folder" Browse button — change persists in `settings.json` |

---

## 2. Editor

| Feature | Detail |
|---------|--------|
| WYSIWYG editing | PySide6 QTextEdit with real-time style rendering |
| Named paragraph styles | Body, Chapter Title (Heading1), SubHeader (Heading2), Block Quote, Code, Scene Break, Page Break |
| Inline formatting | Bold, Italic, Underline via toolbar or Ctrl+B/I/U |
| Alignment | Left, Center, Right, Justify via toolbar |
| Drop caps | Right-click "Toggle Drop Cap" on any Body paragraph; exported as `::first-letter` CSS in EPUB |
| Scene breaks | Insert > Scene Break (Ctrl+Shift+Return); renders as "⚬ ⚬ ⚬" in editor |
| Page breaks | Insert > Page Break (Ctrl+Enter); renders as "── Page Break ──" marker |
| Auto-indent | First-body paragraph after a heading/scene break/page break suppresses indent |
| Display font override | View > Use Kindle Font toggles between display font and Kindle export fonts |
| Zoom | Ctrl+Scroll to zoom editor view; persisted in settings |
| Monospace exemption | "Code" style is exempt from display font override |
| Word/character count | Live count in status bar, updated on every keystroke; formatted with commas |
| Active typing timer | Tracks session writing time; persisted to project metadata on close |
| Cursor restore | Cursor position saved on close, restored on next open |

---

## 3. Styles

| Feature | Detail |
|---------|--------|
| Style list panel | Dockable panel listing all available styles |
| Apply style | Click style in panel, or right-click > Apply Style submenu in editor |
| Style editor | Double-click style to open editor: font, size, bold, italic, spacing, alignment |
| Paragraph spacing | Per-style space-before / space-after in pt units |
| Per-paragraph override | Right-click > Paragraph Spacing... — adjusts spacing for selected blocks only without touching style definition |
| Update to match | Right-click > "Update Style 'X' to Match" — reads current block formatting and saves it back to the style definition |
| Duplicate style | Right-click in style panel > Duplicate Style |
| Delete style | Right-click in style panel > Delete Style (disabled for built-in styles) |

---

## 4. Chapter Sidebar

| Feature | Detail |
|---------|--------|
| Multi-level sidebar | Level 1: ChapterHeader / Heading1 — bold. Level 2: SubHeader / Heading2 — indented, italic, grey |
| Navigation | Click chapter item to jump to that location in the editor |
| Live refresh | Sidebar updates as you type/change styles |

---

## 5. Export & Import

| Feature | Detail |
|---------|--------|
| EPUB export | Generates valid EPUB 3 file; platform selector: Kindle / Kobo / Apple Books |
| Kindle CSS | Bookerly fallback, relative em units, `@media amzn-kf8` block, hyphens |
| Kobo CSS | Georgia stack, `-epub-hyphens`, no amzn media queries |
| Apple Books CSS | `-apple-system` font stack, `-webkit-hyphens` |
| Cover image | Optional cover image (JPG/PNG) embedded in EPUB; path stored relative to project dir |
| EPUBCheck validation | Built-in EPUBCheck report in Export dialog |
| DOCX export | Exports to Microsoft Word format via `python-docx` |
| Markdown export | Exports to Markdown with heading-to-style mapping |
| Import submenu | File > Import > EPUB Document / Markdown Document / Word Document — format-specific dialogs |
| Copy with Format | Right-click > Copy with Format — copies selection as plain text + JSON MIME with style metadata |

---

## 6. Spell Check

| Feature | Detail |
|---------|--------|
| Engine | Hunspell via `spylls` (offline, no network required) |
| Dictionary | en_US (`.dic` / `.aff` files bundled at `dictionaries/`) |
| Tokenization | Contraction-aware: `\b\w+(?:'\w+)*\b` — "don't" counts as one token |
| Underlines | Misspelled words underlined in red in the editor |
| User dictionary | Right-click > Add to Dictionary — persists to `data/user_dict.txt` |

---

## 7. Find & Replace

| Feature | Detail |
|---------|--------|
| Find | Ctrl+F — find forward/backward |
| Find & Replace | Ctrl+H — replace current match or all matches |
| Options | Regex mode, case-sensitive, whole-word matching |

---

## 8. Display Preferences

| Feature | Detail |
|---------|--------|
| Editor font | Choose display font (does not affect export) |
| Font size (base pt) | Base font size for the editor view |
| Background / text colors | Customise editor background and text colour |
| Visual margins | Left/right margin width in editor |
| Max content width | Max line width (in characters) |
| Zoom | Persisted zoom level |
| Beta warning at startup | Toggle whether the beta disclaimer shows on launch |

---

## 9. Help

| Feature | Detail |
|---------|--------|
| User Guide | Help > User Guide (F1) — five-tab guide: Getting Started, Writing, Styles, Exporting, Backups & Versions |
| About | Help > About PortoWrite |
| Enter Licence Key | Help > Enter Licence Key |

---

## 10. Licensing & Tiers

> **Beta period:** All features are free for all users. Paid tiers will be introduced at general release.

| Tier | Detail |
|------|--------|
| Free (beta) | All features available to all users during the beta period |
| Supporter | Removes the beta nag screen and shows a Supporter badge — details at release |
| Commercial | For business or revenue-generating use — details at release |

---

## 11. Application

| Feature | Detail |
|---------|--------|
| Beta warning splash | Disclaimer on first launch; requires initials to dismiss |
| Portable install | All app data (settings, user dictionary) stored in the install folder alongside the exe |
| Settings persistence | Preferences saved across sessions |
| Logging | Configurable log level (none / light / detailed) |

> **Disclaimer:** PortoWrite is beta software provided as-is. The author is not responsible for any loss of work or data. Always keep independent backups of your writing.

---

## Planned (v2)

| Feature |
|---------|
| Footnotes / Endnotes |
| Hyperlinks |
| Track Changes |
| Character List |
| Topic List |
| Drop Cap visual hint in editor |

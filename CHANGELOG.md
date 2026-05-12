# PortoWrite — Changelog

All notable changes to PortoWrite are documented here.

---

## [0.9.0 Beta] — 2026-05-05

### New Features
- **Import submenu**: File > Import now has three format-specific actions — EPUB Document, Markdown Document, and Word Document — replacing the single generic import action
- **Restore from Backup dialog**: File > Restore from Backup opens a dialog listing all timestamped project backups with a live preview showing title, author, chapter count, and word count before restoring
- **Version Snapshots**: File > Versions > Save Snapshot captures a named point-in-time snapshot; File > Versions > Version History lists all snapshots with restore and delete options
- **Help / User Guide**: Help > User Guide (F1) opens a five-tab guide covering Getting Started, Writing, Styles, Exporting, and Backups & Versions
- **App icon**: PortoWrite now has a custom icon (navy book with quill); appears in the taskbar, window title bar, and installer
- **Performance Optimizations**: Ebook mode toggling and reading setting adjustments are now up to 100x faster on large novels by batching layout recalculations
- **App Theme**: View > App Theme allows switching between Light, Dark, and System Default modes; custom high-contrast palettes applied app-wide

### Improvements
- Toolbar alignment buttons (Left / Center / Right / Justify) added
- Display Preferences toggle shows tooltip; setting persists correctly across sessions
- Import handlers are format-aware — Markdown and Word import are disabled on the Free tier
- Chapter Sidebar contrast improved for secondary headings in both Light and Dark modes
- Editor background in Ebook Mode now correctly matches the selected reading theme (Paperwhite/Sepia)

### Bug Fixes
- Fixed title not appearing in EPUB metadata after Save As (clone)
- Fixed margin label showing "M" instead of the configured value in the Kindle Preview toolbar
- Fixed duplicate page-break indicators appearing in the editor
- Fixed a crash on launch caused by a missing color definition in the sidebar
- Fixed console warnings regarding active painters in the ebook frame

---

## [0.3.0-beta] — 2026-05-03

Initial public beta release.

### Editor
- WYSIWYG text editor with named paragraph styles: Body, Chapter Title (Heading 1), SubHeader (Heading 2), Block Quote, Code, Scene Break, Page Break
- Inline formatting: Bold, Italic, Underline (Ctrl+B / I / U)
- Drop caps: right-click any Body paragraph to toggle; exported as `::first-letter` CSS in EPUB
- Scene breaks: Insert > Scene Break (Ctrl+Shift+Return); renders as "⚬ ⚬ ⚬"
- Page breaks: Insert > Page Break (Ctrl+Enter)
- Auto-indent: first Body paragraph after a heading, scene break, or page break suppresses indent
- Display font override: View > Use Kindle Font toggles between display font and export fonts
- Zoom: Ctrl+Scroll; persisted across sessions
- Monospace exemption: Code style ignores display font override
- Cursor position saved on close and restored on next open
- Responsive Kindle Preview with adjustable Theme, Font Size, Margins, and Line Spacing

### Project Management
- New / Open / Save / Save As (Clone)
- Recent files list in File menu
- Autosave every 5 minutes (configurable); never overwrites the main save file
- Crash recovery: prompted to restore or discard on next launch if an autosave exists
- Emergency backup: optional timestamped copy preserved when discarding unsaved changes
- Configurable backup cap with automatic pruning of oldest backups
- Configurable projects root folder (File > Preferences)

### Styles
- Dockable Style Panel listing all available styles
- Style Editor: font, size, bold, italic, spacing, alignment per style
- Per-paragraph spacing override without altering the style definition
- "Update Style to Match": reads current block formatting and saves it to the style definition
- Duplicate and Delete style (built-in styles protected)

### Chapter Sidebar
- Two-level outline: Chapter Titles (bold) and SubHeaders (indented, italic)
- Click any entry to jump to that position in the editor
- Live update as you type

### Export & Import
- EPUB 3 export with platform profiles: Kindle, Kobo, Apple Books
  - Kindle: Bookerly fallback, `em` units, `@media amzn-kf8`, hyphens
  - Kobo: Georgia stack, `-epub-hyphens`
  - Apple Books: `-apple-system` stack, `-webkit-hyphens`
- Optional cover image (JPG/PNG) embedded in EPUB
- Built-in EPUBCheck validation report in the Export dialog
- DOCX export and import
- Markdown export and import
- Copy with Format: copies selection as plain text with style metadata

### Spell Check
- Offline Hunspell engine (no network required), en\_US dictionary bundled
- Contraction-aware tokenisation: "don't" treated as one word
- Real-time red underlines; right-click for suggestions and "Add to Dictionary"

### Find & Replace
- Find forward/backward (Ctrl+F)
- Find & Replace with Replace Current and Replace All (Ctrl+H)
- Regex mode, case-sensitive, and whole-word options

### Display Preferences
- Editor font, base font size, background and text colours
- Visual margins, max content width (in characters)
- Persisted zoom level
- Toggle beta disclaimer at startup

### Metadata
- Title, Author, ISBN, Publisher, Series, Language
- Cover image path stored relative to project folder

### Licensing
- Free during beta — all features available to all users
- Supporter tier: Ko-fi donation removes the beta nag and shows a Supporter badge
- Commercial tier: for business or revenue-generating use — contact portowrite@portowlabs.com
- Help > Enter Licence Key to activate

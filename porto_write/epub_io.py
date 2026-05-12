import os
import uuid
import logging
from ebooklib import epub
from lxml import etree, html
from porto_write.document import PortoDocument, Chapter, TextBlock
from porto_write.styles import StyleDefinition, StyleRegistry
from porto_write.epub_validator import EpubValidator, ValidationResult

logger = logging.getLogger(__name__)

def _add_document_metadata_to_epub(doc: PortoDocument, book: epub.EpubBook) -> None:
    """Add expanded metadata from PortoDocument to EpubBook OPF."""
    if doc.subtitle:
        book.add_metadata('DC', 'alternative', doc.subtitle)

    if doc.series_name:
        book.add_metadata('DC', 'relation', f"series:{doc.series_name}")
    if doc.series_number > 0:
        book.add_metadata('DC', 'relation', f"series:number:{doc.series_number}")

    if doc.description:
        book.add_metadata('DC', 'description', doc.description)

    if doc.isbn:
        book.add_metadata('DC', 'identifier', doc.isbn)

    if doc.publisher:
        book.add_metadata('DC', 'publisher', doc.publisher)

    if doc.publish_date:
        book.add_metadata('DC', 'issued', doc.publish_date)

    for keyword in doc.keywords:
        book.add_metadata('DC', 'subject', keyword)

    for contributor in doc.contributors:
        name = contributor.get('name', '')
        role = contributor.get('role', 'contributor').lower()
        if name:
            book.add_metadata('DC', 'creator' if role == 'author' else 'contributor', name)

def _generate_css_kobo(registry: StyleRegistry) -> str:
    """Kobo-optimized CSS: Georgia font stack, epub-hyphens, no amzn media queries."""
    lines = []
    base_size = 12.0

    lines.extend([
        "body {",
        "  font-family: 'Georgia', 'Palatino Linotype', 'Times New Roman', serif;",
        "  font-size: 1em;",
        "  line-height: 1.5;",
        "  margin: 0;",
        "  padding: 0;",
        "}",
        "",
    ])

    for style in registry.all():
        lines.append(f".{style.name} {{")
        lines.append(f"  font-family: '{style.font_family}', serif;")
        em_size = style.font_size / base_size
        lines.append(f"  font-size: {em_size:.2f}em;")
        if style.bold:
            lines.append("  font-weight: bold;")
        if style.italic:
            lines.append("  font-style: italic;")
        if style.underline:
            lines.append("  text-decoration: underline;")
        align_map = {"left": "left", "center": "center", "right": "right", "justify": "justify"}
        text_align = align_map.get(style.alignment, "left")
        if style.name in ("Body", "BlockQuote"):
            text_align = "justify"
            lines.append("  hyphens: auto;")
            lines.append("  -epub-hyphens: auto;")
            lines.append("  -webkit-hyphens: auto;")
            lines.append("  adobe-hyphenate: auto;")
        lines.append(f"  text-align: {text_align};")
        lines.append(f"  line-height: {style.line_height:.2f};")
        lines.append(f"  margin-top: {style.space_before / base_size:.2f}em;")
        lines.append(f"  margin-bottom: {style.space_after / base_size:.2f}em;")
        if style.page_break_before:
            lines.append("  page-break-before: always;")
        if style.page_break_after:
            lines.append("  page-break-after: always;")
        lines.append("}")
        lines.append("")

    lines.extend([
        "p.Body {",
        "  text-indent: 1.5em;",
        "}",
        "",
        "h1 + p, h2 + p, h3 + p, hr + p {",
        "  text-indent: 0 !important;",
        "}",
        "",
        "hr.SceneBreak {",
        "  border: none;",
        "  text-align: center;",
        "  margin: 1.5em auto;",
        "}",
        "hr.SceneBreak::after {",
        "  content: '⚬ ⚬ ⚬';",
        "  font-size: 1em;",
        "  letter-spacing: 0.5em;",
        "}",
        "",
        "p.drop-cap::first-letter {",
        "  font-size: 3em;",
        "  font-weight: bold;",
        "  float: left;",
        "  line-height: 0.8;",
        "  margin-right: 0.05em;",
        "  margin-top: 0.1em;",
        "}",
        "",
        "@media all {",
        "  body { -webkit-text-size-adjust: none; }",
        "}",
    ])
    return "\n".join(lines)


def _generate_css_apple_books(registry: StyleRegistry) -> str:
    """Apple Books-optimized CSS: system font stack, webkit-hyphens, no amzn media queries."""
    lines = []
    base_size = 12.0

    lines.extend([
        "body {",
        "  font-family: '-apple-system', 'Georgia', 'Times New Roman', serif;",
        "  font-size: 1em;",
        "  line-height: 1.5;",
        "  margin: 0;",
        "  padding: 0;",
        "}",
        "",
    ])

    for style in registry.all():
        lines.append(f".{style.name} {{")
        lines.append(f"  font-family: '{style.font_family}', serif;")
        em_size = style.font_size / base_size
        lines.append(f"  font-size: {em_size:.2f}em;")
        if style.bold:
            lines.append("  font-weight: bold;")
        if style.italic:
            lines.append("  font-style: italic;")
        if style.underline:
            lines.append("  text-decoration: underline;")
        align_map = {"left": "left", "center": "center", "right": "right", "justify": "justify"}
        text_align = align_map.get(style.alignment, "left")
        if style.name in ("Body", "BlockQuote"):
            text_align = "justify"
            lines.append("  hyphens: auto;")
            lines.append("  -webkit-hyphens: auto;")
            lines.append("  adobe-hyphenate: auto;")
        lines.append(f"  text-align: {text_align};")
        lines.append(f"  line-height: {style.line_height:.2f};")
        lines.append(f"  margin-top: {style.space_before / base_size:.2f}em;")
        lines.append(f"  margin-bottom: {style.space_after / base_size:.2f}em;")
        if style.page_break_before:
            lines.append("  page-break-before: always;")
        if style.page_break_after:
            lines.append("  page-break-after: always;")
        lines.append("}")
        lines.append("")

    lines.extend([
        "p.Body {",
        "  text-indent: 1.5em;",
        "}",
        "",
        "h1 + p, h2 + p, h3 + p, hr + p {",
        "  text-indent: 0 !important;",
        "}",
        "",
        "hr.SceneBreak {",
        "  border: none;",
        "  text-align: center;",
        "  margin: 1.5em auto;",
        "}",
        "hr.SceneBreak::after {",
        "  content: '⚬ ⚬ ⚬';",
        "  font-size: 1em;",
        "  letter-spacing: 0.5em;",
        "}",
        "",
        "p.drop-cap::first-letter {",
        "  font-size: 3em;",
        "  font-weight: bold;",
        "  float: left;",
        "  line-height: 0.8;",
        "  margin-right: 0.05em;",
        "  margin-top: 0.1em;",
        "}",
        "",
        "@media all {",
        "  html { -webkit-text-size-adjust: 100%; }",
        "}",
    ])
    return "\n".join(lines)


def export_epub(doc: PortoDocument, file_path: str, project_dir: str = None, options: dict = None, platform: str = "kindle") -> ValidationResult:
    """Export a PortoDocument to an EPUB file and validate.

    Returns ValidationResult with validation status, errors, and warnings.
    'options' can contain profile-specific settings (e.g. for Kindle or Kobo).
    """
    options = options or {}
    book = epub.EpubBook()

    # 1. Metadata
    book.set_identifier(doc.get_metadata("uuid", str(uuid.uuid4())))
    book.set_title(doc.title)
    book.set_language(doc.language)
    book.add_author(doc.author)

    # 1.1 Cover Image
    cover_rel_path = doc.get_metadata("cover_image")
    if cover_rel_path and project_dir:
        full_cover_path = os.path.join(project_dir, cover_rel_path)
        if os.path.exists(full_cover_path):
            try:
                # set_cover(file_name, content, create_static_page=True)
                with open(full_cover_path, 'rb') as f:
                    book.set_cover("cover" + os.path.splitext(cover_rel_path)[1], f.read())
                logger.debug("Cover image embedded: %s", cover_rel_path)
            except Exception as e:
                logger.error("Failed to embed cover image: %s", e)
        else:
            logger.warning("Cover image metadata found but file missing: %s", full_cover_path)

    # 2. Styles (CSS) — platform-specific
    _css_generators = {
        "kobo": _generate_css_kobo,
        "apple_books": _generate_css_apple_books,
    }
    css_content = _css_generators.get(platform, _generate_css)(doc.styles)
    style_item = epub.EpubItem(
        uid="style_nav",
        file_name="style/style.css",
        media_type="text/css",
        content=css_content
    )
    book.add_item(style_item)

    # 3. Chapters
    epub_chapters = []
    for i, chapter in enumerate(doc.chapters):
        file_name = f"chap_{i+1}.xhtml"
        uid = f"chap_{i+1}"
        epub_chap = epub.EpubHtml(
            uid=uid,
            title=chapter.title,
            file_name=file_name,
            lang=doc.language
        )
        
        # Build HTML content
        content = ""
        if chapter.title:
            content += f'<h1 class="ChapterHeader">{chapter.title}</h1>'
            
        for block in chapter.blocks:
            if block.style_name == "PageBreak":
                content += '<p style="page-break-before:always;"> </p>'
            elif block.style_name == "SceneBreak":
                content += '<hr class="SceneBreak" />'
            elif block.style_name in ("SubHeader", "Heading2"):
                content += f'<h2 class="{block.style_name}">{block.text}</h2>'
            elif block.style_name in ("ChapterHeader", "Heading1"):
                content += f'<h1 class="{block.style_name}">{block.text}</h1>'
            elif block.style_name in ("Heading3",):
                content += f'<h3 class="{block.style_name}">{block.text}</h3>'
            elif block.style_name in ("Heading4",):
                content += f'<h4 class="{block.style_name}">{block.text}</h4>'
            elif block.style_name in ("Heading5",):
                content += f'<h5 class="{block.style_name}">{block.text}</h5>'
            elif block.style_name in ("Heading6",):
                content += f'<h6 class="{block.style_name}">{block.text}</h6>'
            else:
                css_class = block.style_name
                if block.drop_cap and block.style_name == "Body":
                    css_class = "Body drop-cap"
                content += f'<p class="{css_class}">{block.text}</p>'
            
        epub_chap.content = (
            f'<?xml version="1.0" encoding="utf-8"?>\n'
            f'<!DOCTYPE html>\n'
            f'<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="{doc.language}">\n'
            f'<head><title>{chapter.title}</title>'
            f'<link rel="stylesheet" href="style/style.css" type="text/css" /></head>\n'
            f'<body>{content}</body>\n'
            f'</html>'
        ).encode('utf-8')
        book.add_item(epub_chap)
        epub_chapters.append(epub_chap)

    # 4. Structure (EPUB3 format)
    # Use Link objects so Kindle shows proper chapter titles in navigation menu
    book.toc = tuple(
        epub.Link(chap.file_name, chap.title or f"Chapter {i+1}", chap.id)
        for i, chap in enumerate(epub_chapters)
    )

    # Build logical TOC page (front-matter clickable TOC)
    toc_items = []
    for i, chapter in enumerate(doc.chapters):
        title = chapter.title or f"Chapter {i+1}"
        file_name = f"chap_{i+1}.xhtml"
        toc_items.append(f'<li><a href="{file_name}">{title}</a></li>')

    toc_html = (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<!DOCTYPE html>\n'
        f'<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="{doc.language}">\n'
        '<head><title>Table of Contents</title>'
        '<link rel="stylesheet" href="style/style.css" type="text/css" /></head>\n'
        '<body>\n'
        '<h1 class="ChapterHeader">Contents</h1>\n'
        '<nav epub:type="toc" xmlns:epub="http://www.idpf.org/2007/ops">\n'
        '<ol>\n'
        + '\n'.join(toc_items) +
        '\n</ol>\n</nav>\n</body>\n</html>'
    )
    toc_page = epub.EpubHtml(
        uid='toc_page',
        title='Table of Contents',
        file_name='toc.xhtml',
        lang=doc.language
    )
    toc_page.content = toc_html.encode('utf-8')
    book.add_item(toc_page)

    # Add Nav for EPUB3 and include it in spine
    nav = epub.EpubNav()
    book.add_item(nav)

    # Spine: Nav first (EPUB3 required), then TOC page, then chapters
    book.spine = [nav, toc_page] + epub_chapters

    # 4.5 Add expanded metadata
    _add_document_metadata_to_epub(doc, book)

    # 5. Write
    epub.write_epub(file_path, book, {})
    logger.info("Exported EPUB to %s", file_path)

    # 6. Validate
    validator = EpubValidator()
    result = validator.validate(file_path)
    logger.info("EPUB validation: %s", "PASS" if result.is_valid else "FAIL")
    return result

def import_epub(file_path: str) -> PortoDocument:
    """Import an EPUB file into a PortoDocument."""
    book = epub.read_epub(file_path)
    
    doc = PortoDocument(
        title=book.get_metadata('DC', 'title')[0][0] if book.get_metadata('DC', 'title') else "Untitled",
        author=book.get_metadata('DC', 'creator')[0][0] if book.get_metadata('DC', 'creator') else "",
        language=book.get_metadata('DC', 'language')[0][0] if book.get_metadata('DC', 'language') else "en"
    )
    
    # Try to find our identifier
    ids = book.get_metadata('DC', 'identifier')
    if ids:
        doc.set_metadata("uuid", ids[0][0])

    # TODO: Parse CSS to reconstruct StyleRegistry if it's a PortoWrite EPUB
    # For now, we use the default registry and match by class name

    for item in book.get_items_of_type(epub.ebooklib.ITEM_DOCUMENT):
        if item is None:
            continue
        name = item.get_name()
        if name.startswith("nav") or name.startswith("toc"):
            continue
            
        # Parse HTML
        content = item.get_content()
        if not content or not content.strip():
            continue
            
        tree = html.fromstring(content)
        
        # Extract title from h1.ChapterHeader or <h1> or <title>
        title = ""
        h1s = tree.xpath("//h1[@class='ChapterHeader'] | //h1")
        if h1s:
            title = h1s[0].text or ""
        else:
            title_tags = tree.xpath("//title")
            if title_tags:
                title = title_tags[0].text or ""
        
        chapter = doc.add_chapter(title or "Chapter")
        
        # Extract blocks (h1, h2, p)
        # We walk all children of body to preserve order
        for body in tree.xpath("//body"):
            for element in body.iterchildren():
                tag = element.tag
                style_name = element.get("class")
                text = element.text or ""
                
                if not text and len(element) > 0:
                    text = element.text_content()
                
                if tag == "h1":
                    if text != title:
                        resolved = style_name if style_name in ("ChapterHeader", "Heading1") else "ChapterHeader"
                        chapter.add_block(resolved, text)
                elif tag == "h2":
                    resolved = style_name if style_name in ("SubHeader", "Heading2") else "SubHeader"
                    chapter.add_block(resolved, text)
                elif tag == "h3":
                    chapter.add_block(style_name or "Heading3", text)
                elif tag == "h4":
                    chapter.add_block(style_name or "Heading4", text)
                elif tag == "h5":
                    chapter.add_block(style_name or "Heading5", text)
                elif tag == "h6":
                    chapter.add_block(style_name or "Heading6", text)
                elif tag == "p":
                    chapter.add_block(style_name or "Body", text)
            
    logger.info("Imported EPUB from %s", file_path)
    return doc

def _generate_css(registry: StyleRegistry) -> str:
    """Convert StyleRegistry to Kindle-optimized CSS string using relative em units."""
    lines = []
    base_size = 12.0

    lines.extend([
        "body {",
        "  font-family: 'Bookerly', 'Georgia', 'Times New Roman', serif;",
        "  font-size: 1em;",
        "  line-height: 1.5;",
        "  margin: 0;",
        "  padding: 0;",
        "}",
        "",
    ])

    for style in registry.all():
        lines.append(f".{style.name} {{")
        lines.append(f"  font-family: '{style.font_family}', serif;")

        em_size = style.font_size / base_size
        lines.append(f"  font-size: {em_size:.2f}em;")

        if style.bold:
            lines.append("  font-weight: bold;")
        if style.italic:
            lines.append("  font-style: italic;")
        if style.underline:
            lines.append("  text-decoration: underline;")

        align_map = {"left": "left", "center": "center", "right": "right", "justify": "justify"}
        text_align = align_map.get(style.alignment, "left")
        if style.name in ("Body", "BlockQuote"):
            text_align = "justify"
            lines.append("  hyphens: auto;")
            lines.append("  -webkit-hyphens: auto;")
            lines.append("  adobe-hyphenate: auto;")
        lines.append(f"  text-align: {text_align};")

        lines.append(f"  line-height: {style.line_height:.2f};")
        lines.append(f"  margin-top: {style.space_before / base_size:.2f}em;")
        lines.append(f"  margin-bottom: {style.space_after / base_size:.2f}em;")

        if style.page_break_before:
            lines.append("  page-break-before: always;")
        if style.page_break_after:
            lines.append("  page-break-after: always;")

        lines.append("}")
        lines.append("")

    lines.extend([
        "p.Body {",
        "  text-indent: 1.5em;",
        "}",
        "",
        "h1 + p, h2 + p, h3 + p, hr + p {",
        "  text-indent: 0 !important;",
        "}",
        "",
        "hr.SceneBreak {",
        "  border: none;",
        "  text-align: center;",
        "  margin: 1.5em auto;",
        "}",
        "hr.SceneBreak::after {",
        "  content: '⚬ ⚬ ⚬';",
        "  font-size: 1em;",
        "  letter-spacing: 0.5em;",
        "}",
        "",
        "p.drop-cap::first-letter {",
        "  font-size: 3em;",
        "  font-weight: bold;",
        "  float: left;",
        "  line-height: 0.8;",
        "  margin-right: 0.05em;",
        "  margin-top: 0.1em;",
        "}",
        "",
        "@media amzn-kf8 {",
        "  body { font-size: 1em; }",
        "  p { orphans: 2; widows: 2; }",
        "}",
        "",
        "@media amzn-mobi {",
        "  p { text-indent: 1.5em; margin: 0; }",
        "}",
    ])

    return "\n".join(lines)


def generate_toc_text(doc: PortoDocument) -> str:
    """Return a plain-text TOC listing for insertion into the editor.

    Returns a newline-separated string: heading line + one line per chapter.
    Caller inserts page breaks before/after.
    """
    lines = ["Table of Contents", ""]
    for i, chapter in enumerate(doc.chapters):
        title = chapter.title or f"Chapter {i+1}"
        lines.append(title)
        for block in chapter.blocks:
            if block.style_name in ("Heading2", "SubHeader") and block.text.strip():
                lines.append(f"  {block.text.strip()}")
    return "\n".join(lines)

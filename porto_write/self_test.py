"""
Self-test suite for PortoWrite.
Run via: python main.py --self-test
Each test function returns (name, passed, detail).
"""
import logging
import os
import tempfile
import shutil

logger = logging.getLogger(__name__)


def _pass(name: str) -> tuple:
    logger.debug("PASS: %s", name)
    return (name, True, "")


def _fail(name: str, detail: str) -> tuple:
    logger.error("FAIL: %s - %s", name, detail)
    return (name, False, detail)


# ---------------------------------------------------------------------------
# Document model tests
# ---------------------------------------------------------------------------

def test_style_definition_defaults():
    from porto_write.styles import StyleDefinition
    style = StyleDefinition(name="Test")
    assert style.font_family == "Georgia"
    assert style.font_size == 12
    return _pass("style_definition_defaults")


def test_style_registry_builtins():
    from porto_write.styles import StyleRegistry
    reg = StyleRegistry()
    assert reg.get("Body") is not None
    assert reg.get("ChapterHeader") is not None
    return _pass("style_registry_builtins")


def test_style_registry_builtins_protected():
    from porto_write.styles import StyleRegistry
    reg = StyleRegistry()
    try:
        reg.remove("Body")
        return _fail("style_registry_builtins_protected", "Allowed removal of builtin")
    except ValueError:
        return _pass("style_registry_builtins_protected")


def test_style_registry_crud():
    from porto_write.styles import StyleDefinition, StyleRegistry
    reg = StyleRegistry()
    s = StyleDefinition(name="Custom", font_family="Arial")
    reg.add(s)
    assert reg.get("Custom").font_family == "Arial"
    reg.rename("Custom", "Renamed")
    assert reg.get("Renamed") is not None
    assert reg.get("Custom") is None
    reg.remove("Renamed")
    assert reg.get("Renamed") is None
    return _pass("style_registry_crud")


def test_document_create():
    from porto_write.document import PortoDocument
    doc = PortoDocument(title="Test Novel", author="Author Name")
    assert doc.title == "Test Novel"
    assert doc.author == "Author Name"
    assert len(doc.chapters) == 0
    return _pass("document_create")


def test_document_chapters():
    from porto_write.document import PortoDocument
    doc = PortoDocument()
    doc.add_chapter("Chapter One")
    doc.add_chapter("Chapter Two")
    assert len(doc.chapters) == 2
    doc.remove_chapter(1)
    assert len(doc.chapters) == 1
    return _pass("document_chapters")


def test_document_blocks():
    from porto_write.document import PortoDocument
    doc = PortoDocument()
    ch = doc.add_chapter("Intro")
    ch.add_block("Body", "First paragraph.")
    ch.add_block("Body", "Second paragraph.")
    assert len(ch.blocks) == 2
    assert ch.blocks[0].text == "First paragraph."
    return _pass("document_blocks")


def test_document_rename_style_syncs_blocks():
    from porto_write.document import PortoDocument
    from porto_write.styles import StyleDefinition
    doc = PortoDocument()
    doc.add_style(StyleDefinition(name="OldStyle"))
    ch = doc.add_chapter("Ch")
    ch.add_block("OldStyle", "Text")
    doc.rename_style("OldStyle", "NewStyle")
    assert ch.blocks[0].style_name == "NewStyle"
    return _pass("document_rename_style_syncs_blocks")


def test_document_metadata():
    from porto_write.document import PortoDocument
    doc = PortoDocument()
    doc.set_metadata("isbn_key", "123-456")
    assert doc.get_metadata("isbn_key") == "123-456"
    return _pass("document_metadata")


def test_expanded_metadata():
    from porto_write.document import PortoDocument
    doc = PortoDocument(
        title="Epic Novel",
        subtitle="The Beginning",
        author="Author Name",
        series_name="The Epic Series",
        series_number=1,
        isbn="123456789",
        publisher="Self Pub",
        keywords=["test", "epic"]
    )
    assert doc.title == "Epic Novel"
    assert doc.subtitle == "The Beginning"
    assert doc.series_name == "The Epic Series"
    assert doc.series_number == 1
    assert doc.isbn == "123456789"
    assert doc.publisher == "Self Pub"
    assert "test" in doc.keywords
    return _pass("expanded_metadata")


def test_toc_generation():
    from porto_write.document import PortoDocument
    doc = PortoDocument(title="TOC Test")
    ch1 = doc.add_chapter("Chapter 1")
    ch1.add_block("SubHeader", "A Subheading")
    ch1.add_block("Body", "Some text")
    ch1.add_block("Heading3", "Deep link")
    
    doc.refresh_toc()
    assert len(doc.toc) == 3
    assert doc.toc[0].text == "Chapter 1"
    assert doc.toc[0].level == 1
    assert doc.toc[1].text == "A Subheading"
    assert doc.toc[1].level == 2
    assert doc.toc[2].text == "Deep link"
    assert doc.toc[2].level == 3
    return _pass("toc_generation")


# ---------------------------------------------------------------------------
# Format I/O tests
# ---------------------------------------------------------------------------

def test_epub_roundtrip():
    from porto_write.document import PortoDocument
    from porto_write.epub_io import export_epub, import_epub
    
    doc = PortoDocument(title="EPUB Test", author="Tester")
    ch = doc.add_chapter("Chapter 1")
    ch.add_block("Body", "Para 1.")
    ch.add_block("BlockQuote", "Quote.")
    
    fd, path = tempfile.mkstemp(suffix=".epub")
    os.close(fd)
    
    try:
        export_epub(doc, path)
        doc2 = import_epub(path)
        
        assert doc2.title == doc.title
        assert doc2.author == doc.author
        assert len(doc2.chapters) == 1
        # ebooklib/lxml might add whitespace or subtle changes, 
        # but basic text should match.
        assert "Para 1." in doc2.chapters[0].blocks[0].text
    finally:
        try:
            os.remove(path)
        except:
            pass
            
    return _pass("epub_roundtrip")


def test_epub_with_cover():
    from porto_write.document import PortoDocument
    from porto_write.epub_io import export_epub
    
    doc = PortoDocument(title="Cover Test", author="Tester")
    ch = doc.add_chapter("Chapter 1")
    ch.add_block("Body", "Content.")
    
    # Create a dummy image
    fd, img_path = tempfile.mkstemp(suffix=".png")
    os.close(fd)
    with open(img_path, 'wb') as f:
        # Minimal valid PNG header
        f.write(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDAT\x08\xd7c\xf8\xff\xff? \x05\xfe\x02\xfe\x01\x05\x00\x00\x00\x00IEND\xaeB`\x82')
        
    doc.set_metadata("cover_image", "cover.png")
    
    # Create a project dir
    temp_dir = tempfile.mkdtemp()
    # Copy dummy image to project dir
    shutil.copy2(img_path, os.path.join(temp_dir, "cover.png"))
    
    fd, epub_path = tempfile.mkstemp(suffix=".epub")
    os.close(fd)
    
    try:
        export_epub(doc, epub_path, project_dir=temp_dir)
        # We just verify it doesn't crash and file exists
        assert os.path.exists(epub_path)
        assert os.path.getsize(epub_path) > 0
    finally:
        try:
            os.remove(epub_path)
            os.remove(img_path)
            shutil.rmtree(temp_dir)
        except:
            pass
            
    return _pass("epub_with_cover")


def test_md_roundtrip():
    from porto_write.document import PortoDocument
    from porto_write.md_io import export_md, import_md
    
    doc = PortoDocument(title="MD Test", author="Tester")
    ch = doc.add_chapter("Chapter 1")
    ch.add_block("Body", "Text.")
    
    fd, path = tempfile.mkstemp(suffix=".md")
    os.close(fd)
    
    try:
        export_md(doc, path)
        doc2 = import_md(path)
        assert len(doc2.chapters) == 1
        assert "Text." in doc2.chapters[0].blocks[0].text
    finally:
        try:
            os.remove(path)
        except:
            pass
            
    return _pass("md_roundtrip")


def test_docx_roundtrip():
    from porto_write.document import PortoDocument
    from porto_write.docx_io import export_docx, import_docx
    
    doc = PortoDocument(title="Docx Test", author="Tester")
    ch = doc.add_chapter("Chapter 1")
    ch.add_block("Body", "Text.")
    
    fd, path = tempfile.mkstemp(suffix=".docx")
    os.close(fd)
    
    try:
        export_docx(doc, path)
        doc2 = import_docx(path)
        assert len(doc2.chapters) == 1
        assert "Text." in doc2.chapters[0].blocks[0].text
    finally:
        try:
            os.remove(path)
        except:
            pass
            
    return _pass("docx_roundtrip")


# ---------------------------------------------------------------------------
# Spell Checker tests
# ---------------------------------------------------------------------------

def test_spell_checker():
    from porto_write.spell import SpellChecker
    sc = SpellChecker()
    
    # Test known correct
    assert sc.check("House") is True
    assert sc.check("house") is True
    
    # Test known incorrect
    assert sc.check("houuuse") is False
    
    # Test suggestions
    suggestions = sc.suggest("houuuse")
    assert len(suggestions) > 0
    assert "house" in suggestions
    
    # Test user dictionary
    sc.add_to_user_dict("PortoWriteTestWord")
    assert sc.check("PortoWriteTestWord") is True
    return _pass("spell_checker")


def test_editor_sync():
    from PySide6.QtWidgets import QApplication
    from porto_write.ui.editor_widget import EditorWidget
    from porto_write.document import PortoDocument
    from porto_write.constants import STYLE_NAME_PROPERTY
    import sys
    
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)
        
    doc = PortoDocument()
    editor = EditorWidget()
    
    # 1. Manually insert some blocks
    cursor = editor.textCursor()
    
    # Header 1
    fmt = cursor.blockFormat()
    fmt.setProperty(STYLE_NAME_PROPERTY, "ChapterHeader")
    cursor.setBlockFormat(fmt)
    cursor.insertText("Chapter 1")
    cursor.insertBlock()
    
    # Body 1
    fmt = cursor.blockFormat()
    fmt.setProperty(STYLE_NAME_PROPERTY, "Body")
    cursor.setBlockFormat(fmt)
    cursor.insertText("Content 1")
    cursor.insertBlock()
    
    # Header 2
    fmt = cursor.blockFormat()
    fmt.setProperty(STYLE_NAME_PROPERTY, "ChapterHeader")
    cursor.setBlockFormat(fmt)
    cursor.insertText("Chapter 2")
    
    # Sync
    editor.sync_to_document(doc)
    
    # Verify
    assert len(doc.chapters) == 2
    assert doc.chapters[0].title == "Chapter 1"
    assert len(doc.chapters[0].blocks) == 1
    assert doc.chapters[0].blocks[0].text == "Content 1"
    assert doc.chapters[1].title == "Chapter 2"
    
    return _pass("editor_sync")


def test_style_application():
    from PySide6.QtWidgets import QApplication
    from porto_write.ui.editor_widget import EditorWidget
    from porto_write.styles import StyleRegistry
    from porto_write.constants import STYLE_NAME_PROPERTY
    import sys

    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)

    editor = EditorWidget()
    registry = StyleRegistry()

    styles_to_test = ["Body", "ChapterHeader", "SubHeader", "BlockQuote", "Heading1", "Heading2"]

    for style_name in styles_to_test:
        style = registry.get(style_name)
        assert style is not None, f"Built-in style '{style_name}' not found in registry"
        editor.apply_style(style)
        cursor = editor.textCursor()
        block_format = cursor.blockFormat()
        assert block_format.property(STYLE_NAME_PROPERTY) == style_name, \
            f"STYLE_NAME_PROPERTY not set correctly for '{style_name}'"

    return _pass("style_application")


# ---------------------------------------------------------------------------
# Project / autosave tests
# ---------------------------------------------------------------------------

def test_project_save_load():
    import tempfile, shutil
    from porto_write.project import NovelProject
    tmp = tempfile.mkdtemp()
    try:
        proj = NovelProject.create(tmp, "Save Load Test", author="Tester", max_backups=5)
        ch = proj.doc.add_chapter("Chapter One")
        ch.add_block("Body", "First paragraph.")
        ch.add_block("Body", "Second paragraph.")
        proj.save()

        proj2 = NovelProject.load(proj.project_dir)
        assert proj2.doc.title == "Save Load Test"
        assert proj2.doc.author == "Tester"
        assert len(proj2.doc.chapters) == 1
        assert len(proj2.doc.chapters[0].blocks) == 2
        assert proj2.doc.chapters[0].blocks[0].text == "First paragraph."
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return _pass("project_save_load")


def test_project_backup_rotation():
    import tempfile, shutil
    from porto_write.project import NovelProject
    tmp = tempfile.mkdtemp()
    try:
        proj = NovelProject.create(tmp, "Backup Rotation", max_backups=3)
        proj.save()  # creates first real save
        # Seed 5 fake backup files
        import os
        for i in range(5):
            fake = os.path.join(proj.backups_dir, f"2026-01-01_{i:02d}-00-00.json")
            shutil.copy2(proj.project_file, fake)
        proj._prune_backups()
        assert len(proj.list_backups()) <= 3
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return _pass("project_backup_rotation")


def test_autosave_creates_file():
    import tempfile, shutil
    from porto_write.project import NovelProject
    tmp = tempfile.mkdtemp()
    try:
        proj = NovelProject.create(tmp, "Autosave Test")
        assert not proj.has_autosave()
        proj.save_autosave()
        assert proj.has_autosave()
        proj.delete_autosave()
        assert not proj.has_autosave()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return _pass("autosave_creates_file")


# ---------------------------------------------------------------------------
# Extended I/O tests
# ---------------------------------------------------------------------------

def test_epub_metadata_roundtrip():
    from porto_write.document import PortoDocument
    from porto_write.epub_io import export_epub, import_epub
    import tempfile, os
    doc = PortoDocument(title="Meta Test", author="Auth Test",
                        isbn="9781234567897", publisher="Test Pub")
    ch = doc.add_chapter("Chapter 1")
    ch.add_block("Body", "Content.")
    fd, path = tempfile.mkstemp(suffix=".epub")
    os.close(fd)
    try:
        export_epub(doc, path)
        doc2 = import_epub(path)
        assert doc2.title == "Meta Test"
        assert doc2.author == "Auth Test"
    finally:
        try: os.remove(path)
        except: pass
    return _pass("epub_metadata_roundtrip")


def test_epub_drop_cap_export():
    from porto_write.document import PortoDocument
    from porto_write.epub_io import export_epub
    import tempfile, os, zipfile
    doc = PortoDocument(title="Drop Cap Test")
    ch = doc.add_chapter("Chapter 1")
    blk = ch.add_block("Body", "First letter is big.")
    blk.drop_cap = True
    fd, path = tempfile.mkstemp(suffix=".epub")
    os.close(fd)
    try:
        export_epub(doc, path)
        found = False
        with zipfile.ZipFile(path, "r") as zf:
            for name in zf.namelist():
                if name.endswith((".css", ".xhtml", ".html")):
                    if b"drop-cap" in zf.read(name):
                        found = True
                        break
        if not found:
            return _fail("epub_drop_cap_export", "drop-cap not found in epub contents")
    finally:
        try: os.remove(path)
        except: pass
    return _pass("epub_drop_cap_export")


def test_epub_scene_break_export():
    from porto_write.document import PortoDocument
    from porto_write.epub_io import export_epub
    import tempfile, os, zipfile
    doc = PortoDocument(title="Scene Break Test")
    ch = doc.add_chapter("Chapter 1")
    ch.add_block("Body", "Before break.")
    ch.add_block("SceneBreak", "")
    ch.add_block("Body", "After break.")
    fd, path = tempfile.mkstemp(suffix=".epub")
    os.close(fd)
    try:
        export_epub(doc, path)
        found = False
        with zipfile.ZipFile(path, "r") as zf:
            for name in zf.namelist():
                if name.endswith((".xhtml", ".html")):
                    if b"<hr" in zf.read(name):
                        found = True
                        break
        if not found:
            return _fail("epub_scene_break_export", "<hr> not found in epub HTML")
    finally:
        try: os.remove(path)
        except: pass
    return _pass("epub_scene_break_export")


# ---------------------------------------------------------------------------
# Extended spell checker tests
# ---------------------------------------------------------------------------

def test_spell_contraction():
    from porto_write.spell import SpellChecker
    sc = SpellChecker()
    if not sc.check("don't"):
        return _fail("spell_contraction", "don't failed spell check")
    if not sc.check("can't"):
        return _fail("spell_contraction", "can't failed spell check")
    if sc.check("dnot"):
        return _fail("spell_contraction", "dnot incorrectly passed spell check")
    return _pass("spell_contraction")


# ---------------------------------------------------------------------------
# Extended UI tests
# ---------------------------------------------------------------------------

def test_find_replace():
    from PySide6.QtWidgets import QApplication
    from porto_write.ui.editor_widget import EditorWidget
    import sys
    app = QApplication.instance() or QApplication(sys.argv)
    editor = EditorWidget()
    editor.setPlainText("Hello world. Hello again.")
    found = editor.find_next("Hello", case=False)
    if not found:
        return _fail("find_replace", "find_next did not find 'Hello'")
    count = editor.replace_all("Hello", "Hi")
    text = editor.toPlainText()
    if "Hello" in text:
        return _fail("find_replace", "replace_all left 'Hello' in text")
    if "Hi" not in text:
        return _fail("find_replace", "replace_all did not insert 'Hi'")
    return _pass("find_replace")


# ---------------------------------------------------------------------------
# Licensing tests
# ---------------------------------------------------------------------------

def test_licensing_key_validation():
    from porto_write.licensing import validate_supporter_key, validate_commercial_key
    # Wrong key must return False
    assert validate_supporter_key("test@example.com", "XXXX-XXXX-XXXX-XXXX") is False
    assert validate_commercial_key("Test Corp", "XXXX-XXXX-XXXX-XXXX") is False
    # Return type must be bool
    result = validate_supporter_key("test@example.com", "XXXX-XXXX-XXXX-XXXX")
    assert isinstance(result, bool)
    return _pass("licensing_key_validation")


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def test_ui_smoke():
    from porto_write.ui.smoke_test import run_ui_smoke_test
    try:
        if run_ui_smoke_test():
            return _pass("ui_smoke_test")
        else:
            return _fail("ui_smoke_test", "smoke test returned False")
    except Exception as e:
        return _fail("ui_smoke_test", str(e))


DOCUMENT_TESTS = [
    test_style_definition_defaults,
    test_style_registry_builtins,
    test_style_registry_builtins_protected,
    test_style_registry_crud,
    test_document_create,
    test_document_chapters,
    test_document_blocks,
    test_document_rename_style_syncs_blocks,
    test_document_metadata,
    test_expanded_metadata,
    test_toc_generation,
]

IO_TESTS = [
    test_epub_roundtrip,
    test_epub_with_cover,
    test_md_roundtrip,
    test_docx_roundtrip,
    test_epub_metadata_roundtrip,
    test_epub_drop_cap_export,
    test_epub_scene_break_export,
]

SPELL_TESTS = [
    test_spell_checker,
    test_spell_contraction,
]

UI_TESTS = [
    test_ui_smoke,
    test_editor_sync,
    test_style_application,
    test_find_replace,
]

PROJECT_TESTS = [
    test_project_save_load,
    test_project_backup_rotation,
    test_autosave_creates_file,
]

LICENSING_TESTS = [
    test_licensing_key_validation,
]


def run_all() -> list[tuple]:
    results = []
    all_tests = DOCUMENT_TESTS + IO_TESTS + SPELL_TESTS + UI_TESTS + PROJECT_TESTS + LICENSING_TESTS
    for test_fn in all_tests:
        try:
            results.append(test_fn())
        except Exception as exc:
            results.append(_fail(test_fn.__name__, str(exc)))
            
    passed = sum(1 for _, ok, _ in results if ok)
    total = len(results)
    logger.info("Self-test complete: %d/%d passed", passed, total)
    return results

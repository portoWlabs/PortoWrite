from dataclasses import dataclass
from ebooklib import epub
from typing import List
import logging
import zipfile
import os

logger = logging.getLogger(__name__)

@dataclass
class ValidationResult:
    is_valid: bool
    errors: List[str]
    warnings: List[str]

class EpubValidator:
    def validate(self, epub_path: str) -> ValidationResult:
        """Validate EPUB file structure and content."""
        errors = []
        warnings = []

        if not os.path.exists(epub_path):
            errors.append(f"EPUB file not found: {epub_path}")
            return ValidationResult(is_valid=False, errors=errors, warnings=[])

        try:
            book = epub.read_epub(epub_path)
        except Exception as e:
            errors.append(f"Failed to read EPUB file: {str(e)}")
            return ValidationResult(is_valid=False, errors=errors, warnings=[])

        # Check for required components
        if not book.toc or len(book.toc) == 0:
            warnings.append("No table of contents defined")

        items = list(book.get_items())
        if not items:
            errors.append("EPUB contains no content items")

        # Check for chapters (HTML documents)
        html_items = [i for i in items if hasattr(i, 'file_name') and i.file_name.endswith(('.xhtml', '.html'))]
        if not html_items:
            warnings.append("No chapters found in EPUB")

        # Check metadata
        if not book.title:
            warnings.append("EPUB title not set")

        try:
            self._validate_zip_structure(epub_path)
        except Exception as e:
            warnings.append(f"ZIP structure validation: {str(e)}")

        is_valid = len(errors) == 0
        logger.info(f"EPUB validation: {'PASS' if is_valid else 'FAIL'} ({len(errors)} errors, {len(warnings)} warnings)")

        return ValidationResult(is_valid=is_valid, errors=errors, warnings=warnings)

    def _validate_zip_structure(self, epub_path: str) -> bool:
        """Verify EPUB is a valid ZIP with proper structure."""
        with zipfile.ZipFile(epub_path, 'r') as z:
            files = z.namelist()
            if 'mimetype' not in files:
                raise ValueError("Missing mimetype file")
            if not any('opf' in f.lower() for f in files):
                raise ValueError("Missing package document (.opf)")
            # EPUB3 uses Nav document instead of legacy NCX, so don't require NCX
        return True


# Self-tests
def test_validate_missing_file():
    validator = EpubValidator()
    result = validator.validate("/nonexistent/path.epub")
    assert not result.is_valid
    assert len(result.errors) > 0
    assert "not found" in result.errors[0].lower()

def test_validate_valid_structure():
    # Create a minimal valid EPUB in memory
    import tempfile
    from ebooklib import epub

    book = epub.EpubBook()
    book.set_identifier('test-id')
    book.set_title('Test Book')
    book.set_language('en')
    book.add_author('Test Author')

    c1 = epub.EpubHtml(title='Chapter 1', file_name='chap_1.xhtml', lang='en')
    c1.content = b'<h1>Chapter 1</h1><p>Content</p>'
    book.add_item(c1)
    book.toc = (c1,)
    book.add_item(epub.EpubNav())
    book.spine = ['nav', c1]

    with tempfile.NamedTemporaryFile(suffix='.epub', delete=False) as f:
        epub.write_epub(f.name, book, {})
        temp_path = f.name

    try:
        validator = EpubValidator()
        result = validator.validate(temp_path)
        assert result.is_valid
        assert len(result.errors) == 0
    finally:
        os.unlink(temp_path)

def test_validate_empty_structure():
    # Create EPUB with minimal content (no chapters)
    import tempfile
    from ebooklib import epub

    book = epub.EpubBook()
    book.set_identifier('test-empty')
    book.set_title('Empty Book')
    book.set_language('en')

    # Add nav item for EPUB3 format
    book.add_item(epub.EpubNav())

    with tempfile.NamedTemporaryFile(suffix='.epub', delete=False) as f:
        epub.write_epub(f.name, book, {})
        temp_path = f.name

    try:
        validator = EpubValidator()
        result = validator.validate(temp_path)
        assert result.is_valid is True  # No chapters is a warning, not error
        assert result.warnings, f"Expected warnings but got: {result.warnings}"
    finally:
        os.unlink(temp_path)

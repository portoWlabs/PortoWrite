import logging
from dataclasses import dataclass, field

from porto_write.styles import StyleDefinition, StyleRegistry
from porto_write.toc import TocEntry, generate_toc

logger = logging.getLogger(__name__)


@dataclass
class TextBlock:
    style_name: str
    text: str
    drop_cap: bool = False


@dataclass
class Chapter:
    title: str
    blocks: list[TextBlock] = field(default_factory=list)

    def add_block(self, style_name: str, text: str) -> TextBlock:
        block = TextBlock(style_name=style_name, text=text)
        self.blocks.append(block)
        return block


class PortoDocument:
    def __init__(
        self,
        title: str = "Untitled",
        author: str = "",
        language: str = "en",
        subtitle: str = "",
        series_name: str = "",
        series_number: int = 0,
        description: str = "",
        isbn: str = "",
        publisher: str = "",
        publish_date: str = "",
        keywords: list[str] | None = None,
        contributors: list[dict] | None = None,
    ) -> None:
        self.title = title
        self.author = author
        self.language = language
        self.subtitle = subtitle
        self.series_name = series_name
        self.series_number = series_number
        self.description = description
        self.isbn = isbn
        self.publisher = publisher
        self.publish_date = publish_date
        self.keywords = keywords or []
        self.contributors = contributors or []
        self.chapters: list[Chapter] = []
        self.styles: StyleRegistry = StyleRegistry()
        self.toc: list[TocEntry] = []
        self.metadata: dict = {}
        logger.debug("PortoDocument created: '%s'", title)

    # --- Chapter management ---

    def add_chapter(self, title: str = "Chapter") -> Chapter:
        chapter = Chapter(title=title)
        self.chapters.append(chapter)
        logger.debug("Chapter added: '%s'", title)
        return chapter

    def remove_chapter(self, index: int) -> None:
        if not 0 <= index < len(self.chapters):
            raise IndexError(f"No chapter at index {index}")
        removed = self.chapters.pop(index)
        logger.debug("Chapter removed: '%s'", removed.title)

    def move_chapter(self, from_index: int, to_index: int) -> None:
        chapter = self.chapters.pop(from_index)
        self.chapters.insert(to_index, chapter)

    def refresh_toc(self) -> None:
        """Regenerate the Table of Contents from the current document structure."""
        self.toc = generate_toc(self)
        logger.debug("TOC refreshed: %d entries", len(self.toc))

    # --- Style CRUD (delegated to registry, exposed here for convenience) ---

    def add_style(self, style: StyleDefinition) -> None:
        self.styles.add(style)
        logger.debug("Style added: '%s'", style.name)

    def remove_style(self, name: str) -> None:
        self.styles.remove(name)
        logger.debug("Style removed: '%s'", name)

    def rename_style(self, old_name: str, new_name: str) -> None:
        self.styles.rename(old_name, new_name)
        for chapter in self.chapters:
            for block in chapter.blocks:
                if block.style_name == old_name:
                    block.style_name = new_name
        logger.debug("Style renamed: '%s' → '%s'", old_name, new_name)

    def clone_style(self, source_name: str, new_name: str) -> StyleDefinition:
        style = self.styles.clone(source_name, new_name)
        logger.debug("Style cloned: '%s' → '%s'", source_name, new_name)
        return style

    # --- Metadata ---

    def set_metadata(self, key: str, value) -> None:
        self.metadata[key] = value

    def get_metadata(self, key: str, default=None):
        return self.metadata.get(key, default)

    def __repr__(self) -> str:
        return (
            f"PortoDocument(title={self.title!r}, author={self.author!r}, "
            f"series={self.series_name or 'None'}, "
            f"chapters={len(self.chapters)}, styles={len(self.styles.names())})"
        )

from dataclasses import dataclass
from typing import List

@dataclass
class TocEntry:
    text: str          # The text displayed in the TOC
    level: int         # 1-6
    chapter_index: int # Index of the chapter it belongs to
    block_index: int   # Index of the block within the chapter (-1 if it's the chapter title)

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "level": self.level,
            "chapter_index": self.chapter_index,
            "block_index": self.block_index
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TocEntry":
        return cls(
            text=data.get("text", ""),
            level=data.get("level", 1),
            chapter_index=data.get("chapter_index", 0),
            block_index=data.get("block_index", -1)
        )

def generate_toc(doc) -> List[TocEntry]:
    """
    Generate a default Table of Contents based on chapters and heading styles.
    """
    toc_entries = []
    
    # Heading style mapping
    HEADING_LEVELS = {
        "ChapterHeader": 1,
        "SubHeader": 2,
        "Heading3": 3,
        "Heading4": 4,
        "Heading5": 5,
        "Heading6": 6
    }

    for chapter_index, chapter in enumerate(doc.chapters):
        # 1. Always include Chapter Title as Level 1
        toc_entries.append(TocEntry(
            text=chapter.title,
            level=1,
            chapter_index=chapter_index,
            block_index=-1
        ))

        # 2. Scan blocks for nested headings
        for block_index, block in enumerate(chapter.blocks):
            level = HEADING_LEVELS.get(block.style_name)
            if level:
                # Avoid duplicate if it's just repeating the chapter title 
                # (though usually chapter titles aren't in blocks)
                toc_entries.append(TocEntry(
                    text=block.text,
                    level=level,
                    chapter_index=chapter_index,
                    block_index=block_index
                ))

    return toc_entries

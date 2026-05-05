import copy
from dataclasses import dataclass


@dataclass
class StyleDefinition:
    name: str
    font_family: str = "Georgia"
    font_size: int = 12
    bold: bool = False
    italic: bool = False
    underline: bool = False
    alignment: str = "left"         # "left" | "center" | "right" | "justify"
    line_height: float = 1.5        # Kindle recommended: 1.5 - 1.68
    space_before: int = 0           # points
    space_after: int = 6            # points
    page_break_before: bool = False
    page_break_after: bool = False


_BUILTIN_STYLES: list[StyleDefinition] = [
    StyleDefinition(
        name="Body",
        font_family="Georgia",
        font_size=12,
        bold=False,
        italic=False,
        alignment="justify",
        line_height=1.5,
        space_before=0,
        space_after=6,
    ),
    StyleDefinition(
        name="ChapterHeader",
        font_family="Georgia",
        font_size=24,
        bold=True,
        italic=False,
        alignment="center",
        line_height=1.2,
        space_before=24,
        space_after=12,
        page_break_before=True,
    ),
    StyleDefinition(
        name="SubHeader",
        font_family="Georgia",
        font_size=18,
        bold=True,
        italic=False,
        alignment="left",
        line_height=1.5,
        space_before=12,
        space_after=6,
    ),
    StyleDefinition(
        name="Heading3",
        font_family="Georgia",
        font_size=16,
        bold=True,
        alignment="left",
        space_before=10,
        space_after=4,
    ),
    StyleDefinition(
        name="Heading4",
        font_family="Georgia",
        font_size=14,
        bold=True,
        alignment="left",
        space_before=10,
        space_after=4,
    ),
    StyleDefinition(
        name="Heading5",
        font_family="Georgia",
        font_size=12,
        bold=True,
        italic=True,
        alignment="left",
        space_before=10,
        space_after=4,
    ),
    StyleDefinition(
        name="Heading6",
        font_family="Georgia",
        font_size=12,
        italic=True,
        alignment="left",
        space_before=10,
        space_after=4,
    ),
    StyleDefinition(
        name="Heading1",
        font_family="Georgia",
        font_size=24,
        bold=True,
        italic=False,
        alignment="center",
        line_height=1.2,
        space_before=24,
        space_after=12,
        page_break_before=True,
    ),
    StyleDefinition(
        name="Heading2",
        font_family="Georgia",
        font_size=18,
        bold=True,
        italic=False,
        alignment="left",
        line_height=1.5,
        space_before=12,
        space_after=6,
    ),
    StyleDefinition(
        name="BlockQuote",
        font_family="Georgia",
        font_size=11,
        bold=False,
        italic=True,
        alignment="left",
        line_height=1.5,
        space_before=6,
        space_after=6,
    ),
    StyleDefinition(
        name="Code",
        font_family="Courier New",
        font_size=11,
        bold=False,
        italic=False,
        alignment="left",
        line_height=1.4,
        space_before=4,
        space_after=4,
    ),
    StyleDefinition(
        name="PageBreak",
        font_family="Georgia",
        font_size=10,
        bold=False,
        italic=True,
        alignment="center",
        line_height=1.0,
        space_before=8,
        space_after=8,
        page_break_before=True,
    ),
    StyleDefinition(
        name="SceneBreak",
        font_family="Georgia",
        font_size=11,
        bold=False,
        italic=False,
        alignment="center",
        line_height=1.0,
        space_before=12,
        space_after=12,
        page_break_before=False,
    ),
]

BUILTIN_NAMES: frozenset[str] = frozenset(s.name for s in _BUILTIN_STYLES)


class StyleRegistry:
    def __init__(self) -> None:
        self._styles: dict[str, StyleDefinition] = {}
        for style in _BUILTIN_STYLES:
            self._styles[style.name] = copy.copy(style)

    def is_builtin(self, name: str) -> bool:
        return name in BUILTIN_NAMES

    def get(self, name: str) -> StyleDefinition | None:
        return self._styles.get(name)

    def all(self) -> list[StyleDefinition]:
        return list(self._styles.values())

    def names(self) -> list[str]:
        return list(self._styles.keys())

    def add(self, style: StyleDefinition) -> None:
        self._styles[style.name] = style

    def remove(self, name: str) -> None:
        if name in BUILTIN_NAMES:
            raise ValueError(f"Cannot remove built-in style '{name}'")
        self._styles.pop(name, None)

    def rename(self, old_name: str, new_name: str) -> None:
        if old_name in BUILTIN_NAMES:
            raise ValueError(f"Cannot rename built-in style '{old_name}'")
        style = self._styles.pop(old_name)
        style.name = new_name
        self._styles[new_name] = style

    def clone(self, source_name: str, new_name: str) -> StyleDefinition:
        source = self._styles[source_name]
        new_style = copy.copy(source)
        new_style.name = new_name
        self._styles[new_name] = new_style
        return new_style

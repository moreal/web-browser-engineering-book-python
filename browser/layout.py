from __future__ import annotations

import functools
import logging
from dataclasses import dataclass
from tkinter.font import Font
from typing import TYPE_CHECKING, Callable, Literal, Protocol, TypedDict

if TYPE_CHECKING:
    import tkinter

from browser.css import CssAttributes, CSSParser, Selector
from browser.html_parser import Element, ElementLike, Text

BLOCK_ELEMENTS = frozenset(
    {
        "html",
        "body",
        "article",
        "section",
        "nav",
        "aside",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "hgroup",
        "header",
        "footer",
        "address",
        "p",
        "hr",
        "pre",
        "blockquote",
        "ol",
        "ul",
        "menu",
        "li",
        "dl",
        "dt",
        "dd",
        "figure",
        "figcaption",
        "main",
        "div",
        "table",
        "form",
        "fieldset",
        "legend",
        "details",
        "summary",
    }
)

SKIP_ELEMENTS = frozenset(
    {
        "head",
    }
)


@dataclass(frozen=True)
class DrawText:
    x: int
    y: int
    text: str
    font: FontWrapper
    color: str

    @property
    def top(self) -> int:
        return self.y

    @property
    def bottom(self) -> int:
        metrics = self.font.metrics()
        if isinstance(metrics, dict):
            return self.y + metrics.get("linespace", 20)
        return self.y + metrics

    def execute(self, scroll: int, canvas: tkinter.Canvas) -> None:
        canvas.create_text(
            self.x,
            self.y - scroll,
            text=self.text,
            font=self.font.font,
            anchor="nw",
            fill=self.color,
        )


@dataclass(frozen=True)
class DrawRect:
    x1: int
    y1: int
    x2: int
    y2: int
    color: str

    @property
    def top(self) -> int:
        return self.y1

    @property
    def bottom(self) -> int:
        return self.y2

    def execute(self, scroll: int, canvas: tkinter.Canvas) -> None:
        canvas.create_rectangle(
            self.x1, self.y1 - scroll, self.x2, self.y2 - scroll, fill=self.color
        )


DrawCommand = DrawText | DrawRect


@dataclass(frozen=True)
class LayoutBox:
    x: int
    y: int
    width: int
    height: int
    children: tuple["LayoutBox", ...]
    display_list: tuple[DrawCommand, ...]
    node: ElementLike | Text


class FontWrapper:
    def __init__(self, font: Font):
        self.font = font

    @functools.cache
    def measure(self, text: str) -> int:
        return self.font.measure(text)

    @functools.cache
    def metrics(
        self, option: Literal["ascent", "descent", "linespace"] | None = None
    ) -> int | _MetricsDict:
        if option is None:
            return self.font.metrics()
        return self.font.metrics(option)


GetFont = Callable[[int, bool, bool], FontWrapper]


FONT_CACHE: dict[tuple[int, bool, bool], FontWrapper] = {}


class _MetricsDict(TypedDict):
    ascent: int
    descent: int
    linespace: int
    fixed: bool


def get_font(size: int, bold: bool, italic: bool) -> FontWrapper:
    logger = logging.getLogger(__name__)
    key = (size, bold, italic)
    if key not in FONT_CACHE:
        logger.debug("Font cache missed %s", key)
        FONT_CACHE[key] = FontWrapper(
            Font(
                size=size,
                weight="bold" if bold else "normal",
                slant="italic" if italic else "roman",
            ),
        )
    return FONT_CACHE[key]


def get_layout_mode(node: ElementWithStyle | Text) -> str:
    """Return 'inline' or 'block' based on node type and children."""
    if isinstance(node, Text):
        return "inline"

    if not node.children:
        return "block"

    for child in node.children:
        if isinstance(child, Element) and child.tag in BLOCK_ELEMENTS:
            return "block"

    return "inline"


def layout_document(
    node: ElementLike, width: int, hstep: int, vstep: int, get_font: GetFont
) -> LayoutBox:
    """Layout the entire document, returns immutable LayoutBox tree."""

    return layout_block(node, hstep, 0, width - 2 * hstep, hstep, get_font)


def layout_block(
    node: ElementLike | Text,
    x: int,
    y: int,
    width: int,
    hstep: int,
    get_font: GetFont,
) -> LayoutBox:
    """Layout a single block, returns immutable LayoutBox."""
    mode = get_layout_mode(node)
    background_cmds: list[DrawCommand] = []

    if mode == "inline":
        content_display_list, height = layout_inline(node, x, y, width, hstep, get_font)

        if isinstance(node, Element) and "background-color" in node.style:
            background_color = node.style["background-color"]
            if background_color != "transparent":
                background_cmds.append(
                    DrawRect(
                        x1=x, y1=y, x2=x + width, y2=y + height, color=background_color
                    )
                )

        return LayoutBox(
            x=x,
            y=y,
            width=width,
            height=height,
            children=(),
            display_list=tuple(background_cmds) + content_display_list,
            node=node,
        )
    else:
        children: list[LayoutBox] = []
        cursor_y = y

        for child in node.children:
            if isinstance(child, Element) and child.tag in SKIP_ELEMENTS:
                continue
            child_box = layout_block(child, x, cursor_y, width, hstep, get_font)
            children.append(child_box)
            cursor_y = child_box.y + child_box.height

        total_height = cursor_y - y

        if isinstance(node, Element) and "background-color" in node.style:
            background_color = node.style["background-color"]
            print(background_color)
            if background_color != "transparent":
                background_cmds.append(
                    DrawRect(
                        x1=x,
                        y1=y,
                        x2=x + width,
                        y2=y + total_height,
                        color=background_color,
                    )
                )

        return LayoutBox(
            x=x,
            y=y,
            width=width,
            height=total_height,
            children=tuple(children),
            display_list=tuple(background_cmds),
            node=node,
        )


class _InlineLayoutState:
    """Mutable state for inline layout."""

    def __init__(
        self, x: int, y: int, width: int, hstep: int, get_font: GetFont
    ) -> None:
        self.start_x = x
        self.cursor_x = x
        self.cursor_y = y
        self.width = width
        self.max_x = x + width  # Pre-computed line break boundary
        self.hstep = hstep
        self.get_font = get_font

        self.weight = "normal"
        self.style = "roman"
        self.size = 16

        self.line: list[tuple[int, str, FontWrapper, str]] = []
        self.display_list: list[DrawCommand] = []

    def word(self, node: ElementLike, word: str) -> None:
        color = node.style["color"]
        weight = node.style["font-weight"]
        style = (
            "roman"
            if node.style["font-style"] == "normal"
            else node.style["font-style"]
        )
        size = int(float(node.style["font-size"][:-2]) * 0.75)
        font = self.get_font(size, weight == "bold", style == "italic")
        w = font.measure(word)
        if self.cursor_x + w > self.max_x:
            self.flush()
        self.line.append((self.cursor_x, word, font, color))
        self.cursor_x += w + font.measure(" ")

    def open_tag(self, tag: str) -> None:
        if tag == "b":
            self.weight = "bold"
        elif tag == "i":
            self.style = "italic"
        elif tag == "big":
            self.size += 4
        elif tag == "small":
            self.size -= 2
        elif tag == "br":
            self.flush()

    def close_tag(self, tag: str) -> None:
        if tag == "b":
            self.weight = "normal"
        elif tag == "i":
            self.style = "roman"
        elif tag == "big":
            self.size -= 4
        elif tag == "small":
            self.size += 2
        elif tag == "p":
            self.flush()
            self.cursor_y += 16

    def flush(self) -> None:
        if not self.line:
            return

        # Collect metrics once, extract ascent/descent values
        line_with_metrics = [
            (x, word, font, font.metrics(), color) for x, word, font, color in self.line
        ]
        max_ascent = max(
            m["ascent"] if isinstance(m, dict) else m
            for _, _, _, m, _ in line_with_metrics
        )
        baseline = self.cursor_y + 1.25 * max_ascent

        for x, word, font, m, color in line_with_metrics:
            ascent = m["ascent"] if isinstance(m, dict) else 0
            y = baseline - ascent
            self.display_list.append(
                DrawText(x=x, y=int(y), text=word, font=font, color=color)
            )

        max_descent = max(
            m["descent"] if isinstance(m, dict) else 4
            for _, _, _, m, _ in line_with_metrics
        )
        self.cursor_y = baseline + 1.25 * max_descent
        self.cursor_x = self.start_x
        self.line = []


def _recurse_inline(state: _InlineLayoutState, node: ElementLike | Text) -> None:
    """Recursively process nodes for inline layout."""
    if isinstance(node, Text):
        for word in node.text.split():
            assert isinstance(node.parent, Element)
            state.word(node.parent, word)
    else:
        state.open_tag(node.tag)
        for child in node.children:
            _recurse_inline(state, child)
        state.close_tag(node.tag)


def layout_inline(
    node: ElementLike | Text,
    x: int,
    y: int,
    width: int,
    hstep: int,
    get_font: GetFont,
) -> tuple[tuple[DrawCommand, ...], int]:
    """Layout inline content, returns (display_list, height)."""
    state = _InlineLayoutState(x, y, width, hstep, get_font)
    _recurse_inline(state, node)
    state.flush()

    height = int(state.cursor_y - y)
    return tuple(state.display_list), height


def collect_display_list(box: LayoutBox) -> list[DrawCommand]:
    """Recursively collect all DrawCommands from LayoutBox tree."""
    result: list[DrawCommand] = []
    result.extend(box.display_list)
    for child in box.children:
        result.extend(collect_display_list(child))
    return result

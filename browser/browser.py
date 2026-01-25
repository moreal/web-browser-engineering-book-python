import pathlib
import tkinter
from dataclasses import dataclass
from typing import Iterator, Literal

from browser.content import Content, CssContent, HtmlContent
from browser.content_fetcher import _parse_url, fetch_content
from browser.css import CssAttributes, CSSParser, Selector
from browser.html_parser import Element, ElementLike, HTMLParser
from browser.layout import (
    DrawCommand,
    DrawRect,
    collect_display_list,
    get_font,
    layout_document,
)

from .url import Url


@dataclass(frozen=True)
class BrowserOptions:
    http_version: Literal["1.0", "1.1"] = "1.0"


DisplayList = list[DrawCommand]


HORIZONTAL_SCROLL_WIDTH = 10
SCROLL_STEP = 100


class Browser:
    def __init__(self, height: int = 800, width: int = 600, rtl: bool = False) -> None:
        self.height = height
        self.width = width
        self.rtl = rtl
        self.HSTEP, self.VSTEP = 13, 18
        self._current_url: Url | None = None

        self.window = tkinter.Tk()
        self.canvas = tkinter.Canvas(
            self.window, height=self.height, width=self.width, bg="white"
        )
        self.canvas.pack(fill=tkinter.BOTH, expand=True)

        self.scroll = 0

        self._bind_events()
        self._current_content: Content | None = None
        self._current_display_list: DisplayList = []
        self._current_max_height: int = 0

    def _bind_events(self):
        self.window.bind("<Down>", self._scrolldown)
        self.window.bind("<Up>", self._scrollup)
        self.window.bind("<MouseWheel>", self._mousewheel)
        self.window.bind("<Button-4>", self._scrollup)
        self.window.bind("<Button-5>", self._scrollup)
        self.window.bind("<Configure>", self._configure)

    def _scrolldown(self, event):
        self._update_scroll(SCROLL_STEP)

    def _scrollup(self, event):
        self._update_scroll(-SCROLL_STEP)

    def _mousewheel(self, event: tkinter.Event):
        # macOS: event.delta is typically ±1 to ±3
        # Windows: event.delta is typically ±120
        # Normalize and apply scroll step
        if abs(event.delta) > 10:
            # Windows style (delta is ±120)
            direction = -1 if event.delta > 0 else 1
        else:
            # macOS style (delta is ±1 to ±3)
            direction = -event.delta
        self._update_scroll(direction * SCROLL_STEP)

    def _configure(self, event: tkinter.Event):
        if self.height == event.height and self.width == event.width:
            return
        self.height = event.height
        self.width = event.width
        self._update_display_list()

    def _update_scroll(self, delta: int):
        self.scroll = max(
            min(self.scroll + delta, self._current_max_height - self.height), 0
        )
        self._update_display_list()

    def open(self, url: str | Url) -> None:
        self._current_url = _parse_url(url)
        self.update_content(fetch_content(url))

    def _render(self):
        match self._current_content:
            case HtmlContent():
                self._display(self._current_display_list)
            case _:
                pass

    def update_content(self, content: Content):
        self._current_content = content
        self._update_display_list()

    def _update_display_list(self):
        assert self._current_content is not None
        assert self._current_url is not None
        display_list = _get_display_list(
            self._current_content,
            width=self.width,
            hstep=self.HSTEP,
            vstep=self.VSTEP,
            url=self._current_url,
            rtl=self.rtl,
        )
        self._current_max_height = _get_max_height(display_list, self.VSTEP)
        if (
            vertical_scroll_bar := _get_vertical_scroll_bar(
                max_height=self._current_max_height,
                scroll=self.scroll,
                width=self.width,
                height=self.height,
            )
        ) is not None:
            display_list.append(vertical_scroll_bar)

        self._current_display_list = display_list
        self._render()

    def _display(self, display_list: DisplayList):
        self.canvas.delete("all")
        for cmd in display_list:
            if cmd.top > self.scroll + self.height:
                continue
            if cmd.bottom < self.scroll:
                continue
            cmd.execute(self.scroll, self.canvas)


def _get_max_height(display_list: DisplayList, vstep: int) -> int:
    if not display_list:
        return vstep
    return max(cmd.bottom for cmd in display_list) + vstep


def _get_vertical_scroll_bar(
    *, max_height: int, scroll: int, width: int, height: int
) -> DrawCommand | None:
    if max_height <= height:
        return None

    rate = height / max_height
    vertical_scroll_length = int(height * rate)
    scroll_y = int(scroll * rate)
    return DrawRect(
        x1=width - HORIZONTAL_SCROLL_WIDTH,
        y1=scroll + scroll_y,
        x2=width,
        y2=scroll + scroll_y + vertical_scroll_length,
        color="gray",
    )


_image_cache: dict[str, tkinter.PhotoImage] = {}


def _load_image(path: str) -> tkinter.PhotoImage:
    if path not in _image_cache:
        _image_cache[path] = tkinter.PhotoImage(file=path)
    return _image_cache[path]


BROWSER_CSS = """
pre { background-color: gray; }
a { color: blue; }
i { font-style: italic; }
b { font-weight: bold; }
small { font-size: 90%; }
big { font-size: 110%; }
h1 { font-size: 200%; }
h2 { font-size: 150%; }
h3 { font-size: 125%; }
h4 { font-size: 110%; }
h5 { font-size: 100%; }
h6 { font-size: 90%; }
.thisisclass { color: red; }
"""
RULES = CSSParser(BROWSER_CSS).parse()

DEFAULT_INHERITED_PROPERTIES = {
    "font-size": "16px",
    "font-style": "normal",
    "font-weight": "normal",
    "color": "black",
}


def fill_style_with_rules(
    element: ElementLike, rules: list[tuple[Selector, CssAttributes]]
) -> ElementLike:
    style = {}

    # Inheritence
    for property, default_value in DEFAULT_INHERITED_PROPERTIES.items():
        if element.parent:  # from parent.
            element.style[property] = element.parent.style[property]
        else:  # from default. (maybe only root)
            element.style[property] = default_value

    for selector, attributes in rules:
        if selector.matches(element):
            style.update(attributes)

    if "style" in element.attributes:
        style_string = element.attributes["style"]
        style.update(CSSParser(style_string).parse_body())

    element.style.update(style)

    if element.style["font-size"].endswith("%"):
        if element.parent:
            parent_font_size = element.parent.style["font-size"]
        else:
            parent_font_size = DEFAULT_INHERITED_PROPERTIES["font-size"]
        node_pct = float(element.style["font-size"][:-1]) / 100
        parent_px = float(parent_font_size[:-2])
        element.style["font-size"] = str(node_pct * parent_px) + "px"

    children = list(
        map(
            lambda child: fill_style_with_rules(child, rules)
            if isinstance(child, Element)
            else child,
            element.children,
        )
    )

    return Element(element.tag, element.attributes, element.parent, children, style)


def iterate_element_recursively(element: ElementLike) -> Iterator[ElementLike]:
    yield element
    for child in element.children:
        if isinstance(child, Element):
            yield from iterate_element_recursively(child)


def cascade_priority(rule: tuple[Selector, dict[str, str]]):
    selector, _ = rule
    return selector.priority


def _get_display_list(
    content: Content, *, hstep: int, vstep: int, width: int, url: Url, rtl: bool = False
) -> DisplayList:
    match content:
        case HtmlContent():
            body = content.data.decode("utf-8")
            document = HTMLParser(body).parse()
            links = [
                url.resolve(element.attributes["href"])
                for element in iterate_element_recursively(document)
                if element.tag == "link"
                and element.attributes.get("rel") == "stylesheet"
                and "href" in element.attributes
            ]
            # print(links)
            rules = sorted(RULES, key=cascade_priority)
            css_contents = [fetch_content(link) for link in links]
            # print(css_contents)
            assert all(isinstance(x, CssContent) for x in css_contents)
            document = fill_style_with_rules(document, rules)
            box = layout_document(document, width, hstep, vstep, get_font)
            return collect_display_list(box)
        case _:
            return []


_OPENMOJI_BASE_PATH = pathlib.Path("data/openmoji")


# Make iterator receives string and
class _TextIterator:
    def __init__(self, text: str):
        self.text = text
        self.index = 0

    def __iter__(self):
        return self

    def __next__(self) -> tuple[Literal["text", "emoji"], str]:
        if self.index >= len(self.text):
            raise StopIteration

        for i in range(10, 0, -1):
            if _exist_emoji(self.text[self.index : self.index + i]):
                char = self.text[self.index : self.index + i]
                self.index += i
                return ("emoji", char)

        char = self.text[self.index]
        self.index += 1
        return ("text", char)


def _to_emoji_filename(s: str) -> str:
    return f"{'-'.join((hex(ord(c))[2:] for c in s))}.png"


def _to_emoji_filepath(s: str) -> pathlib.Path:
    return _OPENMOJI_BASE_PATH.joinpath(_to_emoji_filename(s)).absolute()


def _exist_emoji(s: str) -> bool:
    pathval = _to_emoji_filepath(s)
    retval = pathval.exists()
    return retval

import pathlib
import tkinter
from dataclasses import dataclass
from tkinter.font import Font
from typing import Literal, assert_never

from browser.content import Content, HtmlContent
from browser.content_fetcher import fetch_content
from browser.lex import Text, Tag, lex

from .url import AboutUrl, Url, UrlParseError


@dataclass(frozen=True)
class BrowserOptions:
    http_version: Literal["1.0", "1.1"] = "1.0"


Position = tuple[int, int]
TextElement = tuple[Literal["text"], str, Font]
BoxElement = tuple[Literal["box"], tuple[int, int]]
ImageElement = tuple[Literal["image"], str, tuple[int, int]]
Element = TextElement | BoxElement | ImageElement
DisplayList = list[tuple[Position, Element]]


HORIZONTAL_SCROLL_WIDTH = 10


class Browser:
    def __init__(self, height: int = 800, width: int = 600, rtl: bool = False) -> None:
        self.height = height
        self.width = width
        self.rtl = rtl
        self.HSTEP, self.VSTEP = 13, 18

        self.window = tkinter.Tk()
        self.canvas = tkinter.Canvas(self.window, height=self.height, width=self.width)
        self.canvas.pack(fill=tkinter.BOTH, expand=True)

        self.scroll = 0

        self._bind_events()
        self._current_content: Content | None = None
        self._current_display_list: DisplayList = []

    def _bind_events(self):
        self.window.bind("<Down>", self._scrolldown)
        self.window.bind("<Up>", self._scrollup)
        self.window.bind("<MouseWheel>", self._mousewheel)
        self.window.bind("<Button-4>", self._scrollup)
        self.window.bind("<Button-5>", self._scrollup)
        self.window.bind("<Configure>", self._configure)

    def _scrolldown(self, event):
        self._update_scroll(100)

    def _scrollup(self, event):
        self._update_scroll(-100)

    def _mousewheel(self, event: tkinter.Event):
        # FIXME: care cross platform (Windows, macOS, Linux)
        self._update_scroll(event.delta)

    def _configure(self, event: tkinter.Event):
        self.height = event.height
        self.width = event.width
        self._update_display_list()

    def _update_scroll(self, delta: int):
        max_height = _get_max_height(self._current_display_list, self.VSTEP)
        self.scroll = max(min(self.scroll + delta, max_height - self.height), 0)
        self._update_display_list()

    def open(self, url: str | Url) -> None:
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
        display_list = _get_display_list(
            self._current_content,
            width=self.width,
            hstep=self.HSTEP,
            vstep=self.VSTEP,
            rtl=self.rtl,
        )
        if (
            vertical_scroll_bar := _get_vertical_scroll_bar(
                display_list,
                scroll=self.scroll,
                width=self.width,
                vstep=self.VSTEP,
                height=self.height,
            )
        ) is not None:
            display_list.append(vertical_scroll_bar)

        self._current_display_list = display_list
        self._render()

    def _display(self, display_list: DisplayList):
        self.canvas.delete("all")
        for (x, y), element in display_list:
            if y > self.scroll + self.height:
                continue
            match element:
                case ("text", text, font):
                    self.canvas.create_text(
                        x, y - self.scroll, text=text, font=font, anchor="nw"
                    )
                case ("image", path, size):
                    image = _load_image(path)
                    self.canvas.create_image(
                        x, y - self.scroll, image=image, anchor="nw"
                    )
                case ("box", (width, height)):
                    self.canvas.create_rectangle(
                        x, y, x + width, y + height, fill="gray"
                    )


FONT_CACHE: dict[tuple[int, bool, bool], Font] = {}


def get_font(size: int, bold: bool, italic: bool) -> Font:
    key = (size, bold, italic)
    if key not in FONT_CACHE:
        FONT_CACHE[key] = Font(
            size=size,
            weight="bold" if bold else "normal",
            slant="italic" if italic else "roman",
        )
    return FONT_CACHE[key]


class Layout:
    def __init__(self, tokens: list[Text | Tag], width: int, hstep: int):
        self.width = width
        self.hstep = hstep
        self.cursor_x = hstep
        self.cursor_y = 0
        self.weight = "normal"
        self.style = "roman"
        self.size = 16
        self.line: list[tuple[int, str, Font]] = []
        self.display_list: DisplayList = []

        for tok in tokens:
            self.token(tok)
        self.flush()

    def token(self, tok: Text | Tag):
        if isinstance(tok, Text):
            self.text(tok)
        else:
            self.tag(tok)

    def text(self, tok: Text):
        font = get_font(self.size, self.weight == "bold", self.style == "italic")
        for word in tok.text.split():
            w = font.measure(word)
            if self.cursor_x + w > self.width - self.hstep:
                self.flush()
            self.line.append((self.cursor_x, word, font))
            self.cursor_x += w + font.measure(" ")

    def tag(self, tok: Tag):
        tag = tok.tag.lower()
        if tag == "b":
            self.weight = "bold"
        elif tag == "/b":
            self.weight = "normal"
        elif tag == "i":
            self.style = "italic"
        elif tag == "/i":
            self.style = "roman"
        elif tag == "big":
            self.size += 4
        elif tag == "/big":
            self.size -= 4
        elif tag == "small":
            self.size -= 2
        elif tag == "/small":
            self.size += 2
        elif tag == "br":
            self.flush()
        elif tag == "/p":
            self.flush()
            self.cursor_y += 16

    def flush(self):
        if not self.line:
            return
        metrics = [font.metrics() for _, _, font in self.line]
        max_ascent = max(m["ascent"] for m in metrics)
        baseline = self.cursor_y + 1.25 * max_ascent
        for x, word, font in self.line:
            y = baseline - font.metrics("ascent")
            self.display_list.append(((x, int(y)), ("text", word, font)))
        max_descent = max(m["descent"] for m in metrics)
        self.cursor_y = baseline + 1.25 * max_descent
        self.cursor_x = self.hstep
        self.line = []


def _get_max_height(display_list: DisplayList, vstep: int) -> int:
    return max(map(lambda x: x[0][1], display_list)) + vstep


def _get_vertical_scroll_bar(
    display_list: DisplayList, *, scroll: int, width: int, height: int, vstep: int
) -> tuple[Position, BoxElement] | None:
    max_height = _get_max_height(display_list, vstep)

    if max_height <= height:
        return None

    rate = height / max_height
    vertical_scroll_length = int(height * rate)
    scroll_y = int(scroll * rate)
    return (width - HORIZONTAL_SCROLL_WIDTH, scroll_y), (
        "box",
        (HORIZONTAL_SCROLL_WIDTH, vertical_scroll_length),
    )


_image_cache: dict[str, tkinter.PhotoImage] = {}


def _load_image(path: str) -> tkinter.PhotoImage:
    if path not in _image_cache:
        _image_cache[path] = tkinter.PhotoImage(file=path)
    return _image_cache[path]


def _get_display_list(
    content: Content, *, hstep: int, vstep: int, width: int, rtl: bool = False
) -> DisplayList:
    match content:
        case HtmlContent():
            body = content.data.decode("utf-8")
            tokens = lex(body)
            layout = Layout(tokens, width, hstep)
            return layout.display_list
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

from typing import Protocol


class Text:
    def __init__(self, text: str, parent: Element | None):
        self.text = text
        self.children: list[Text | Element] = []
        self.parent = parent

    def __repr__(self):
        return repr(self.text)


class ElementLike(Protocol):
    tag: str
    parent: ElementLike | None
    children: list[Text | ElementLike]
    attributes: dict[str, str]
    style: dict[str, str]


class Element(ElementLike):
    def __init__(
        self,
        tag: str,
        attributes: dict[str, str],
        parent: ElementLike | None,
        children: list[Text | ElementLike] | None = None,
        style: dict[str, str] | None = None,
    ):
        self.tag = tag
        self.attributes = attributes
        self.children = children or []
        self.parent = parent
        self.style = style or {}

    def __repr__(self):
        return "<" + self.tag + ">"


SELF_CLOSING_TAGS = frozenset(
    {
        "area",
        "base",
        "br",
        "col",
        "embed",
        "hr",
        "img",
        "input",
        "link",
        "meta",
        "param",
        "source",
        "track",
        "wbr",
    }
)

HEAD_TAGS = frozenset(
    {
        "base",
        "basefont",
        "bgsound",
        "noscript",
        "link",
        "meta",
        "title",
        "style",
        "script",
    }
)


def get_attributes(text: str) -> tuple[str, dict[str, str]]:
    from browser.parser_combinator import (
        ParseResult,
        alt,
        char,
        map,
        seq,
        take_until,
        take_while1,
        whitespace,
    )

    # Tag name parser
    tag_name = take_while1(lambda c: not c.isspace())

    # Attribute name: non-space, non-equals characters
    attr_name = take_while1(lambda c: c not in ("=", " ", "\t", "\n", "\r", ">"))

    # Quoted value with specific quote character
    def quoted_value(quote: str):
        return map(
            seq(char(quote), take_until(quote), char(quote)),
            lambda parts: parts[1],
        )

    # Unquoted value
    unquoted_value = take_while1(lambda c: not c.isspace())

    # Attribute value (quoted or unquoted)
    attr_value = alt(quoted_value('"'), quoted_value("'"), unquoted_value)

    # Full attribute: name with optional =value
    def attribute(input: str) -> ParseResult[tuple[str, str]] | None:
        name_result = attr_name(input)
        if name_result is None:
            return None
        name = name_result.value.casefold()
        input = name_result.remaining

        eq_result = char("=")(input)
        if eq_result is None:
            return ParseResult((name, ""), name_result.remaining)

        input = eq_result.remaining
        value_result = attr_value(input)
        if value_result is None:
            return ParseResult((name, ""), input)

        return ParseResult((name, value_result.value), value_result.remaining)

    # Parse tag name
    ws_result = whitespace(text)
    text = ws_result.remaining

    tag_result = tag_name(text)
    if tag_result is None:
        return "", {}

    tag = tag_result.value.casefold()
    text = tag_result.remaining

    # Parse attributes
    attributes: dict[str, str] = {}
    while True:
        ws_result = whitespace(text)
        text = ws_result.remaining

        if not text:
            break

        attr_result = attribute(text)
        if attr_result is None:
            break

        key, value = attr_result.value
        attributes[key] = value
        text = attr_result.remaining

    return tag, attributes


class HTMLParser:
    def __init__(self, body: str):
        self.body = body
        self.unfinished: list[Element] = []

    def parse(self) -> Element:
        text: list[str] = []
        in_tag = False
        for c in self.body:
            if c == "<":
                in_tag = True
                if text:
                    self.add_text("".join(text))
                text = []
            elif c == ">":
                in_tag = False
                self.add_tag("".join(text))
                text = []
            else:
                text.append(c)
        if not in_tag and text:
            self.add_text("".join(text))
        return self.finish()

    def add_text(self, text: str) -> None:
        if text.isspace():
            return
        self.implicit_tags(None)
        parent = self.unfinished[-1]
        node = Text(text, parent)
        parent.children.append(node)

    def add_tag(self, tag: str) -> None:
        tag, attributes = get_attributes(tag)
        if tag.startswith("!"):
            return
        self.implicit_tags(tag)
        if tag.startswith("/"):
            if len(self.unfinished) == 1:
                return
            node = self.unfinished.pop()
            parent = self.unfinished[-1]
            parent.children.append(node)
        elif tag in SELF_CLOSING_TAGS:
            parent = self.unfinished[-1]
            node = Element(tag, attributes, parent)
            parent.children.append(node)
        else:
            parent = self.unfinished[-1] if self.unfinished else None
            node = Element(tag, attributes, parent)
            self.unfinished.append(node)

    def implicit_tags(self, tag: str | None) -> None:
        while True:
            num_open = len(self.unfinished)
            if num_open == 0 and tag != "html":
                self.add_tag("html")
            elif (
                num_open == 1
                and self.unfinished[0].tag == "html"
                and tag not in {"head", "body", "/html"}
            ):
                if tag in HEAD_TAGS:
                    self.add_tag("head")
                else:
                    self.add_tag("body")
            elif (
                num_open == 2
                and self.unfinished[0].tag == "html"
                and self.unfinished[1].tag == "head"
                and tag not in {"/head"} | HEAD_TAGS
            ):
                self.add_tag("/head")
            else:
                break

    def finish(self) -> Element:
        if not self.unfinished:
            self.implicit_tags(None)
        while len(self.unfinished) > 1:
            node = self.unfinished.pop()
            parent = self.unfinished[-1]
            parent.children.append(node)
        return self.unfinished.pop()


def print_tree(node: Text | Element, indent: int = 0) -> None:
    print(" " * indent, node)
    for child in node.children:
        print_tree(child, indent + 2)

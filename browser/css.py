from dataclasses import dataclass
from typing import Protocol

from browser.html_parser import ElementLike


class Selector(Protocol):
    priority: int

    def matches(self, element: ElementLike) -> bool: ...


@dataclass(frozen=True)
class TagSelector(Selector):
    tag: str
    priority: int = 1

    def matches(self, element: ElementLike) -> bool:
        return element.tag == self.tag


@dataclass(frozen=True)
class ClassSelector(Selector):
    class_name: str
    priority: int = 10

    def matches(self, element: ElementLike) -> bool:
        return (
            "class" in element.attributes
            and self.class_name in element.attributes["class"].split()
        )


class DecendantSelector(Selector):
    def __init__(self, ancestor: Selector, descendant: Selector):
        self.ancestor = ancestor
        self.descendant = descendant
        self.priority = ancestor.priority + descendant.priority

    def matches(self, element: ElementLike) -> bool:
        # Let assume self is (ancestor=div, descendant=p)
        # Ensure element is p. If not, return False
        if not self.descendant.matches(element):
            return False

        # Ensure some parent, grand parent, grand grand parent, ..., is div.
        current_element = element
        while current_element.parent:
            if self.ancestor.matches(current_element.parent):
                return True
            current_element = current_element.parent

        # If not, return False.
        return False


type CssAttributes = dict[str, str]


class CSSParser:
    def __init__(self, text: str):
        self.text = text
        self.cursor = 0

    def selector(self) -> Selector:
        tag = self.word(".-#").casefold()
        if tag.startswith("."):
            selector = ClassSelector(tag[1:])
        else:
            selector = TagSelector(tag)
        self.skip_whitespace()
        while self.cursor < len(self.text) and self.text[self.cursor] != "{":
            tag = self.word(".-#").casefold()
            if tag.startswith("."):
                decendant_selector = ClassSelector(tag[1:])
            else:
                decendant_selector = TagSelector(tag)
            selector = DecendantSelector(selector, decendant_selector)
            self.skip_whitespace()
        return selector

    def parse(self) -> list[tuple[Selector, dict[str, str]]]:
        rules = []
        self.skip_whitespace()
        while self.cursor < len(self.text):
            selector = self.selector()
            self.skip_whitespace()
            self.require_char("{")
            self.skip_whitespace()
            attributes = self.parse_body()
            rules.append((selector, attributes))
            self.skip_whitespace()
            self.require_char("}")
            self.skip_whitespace()
        return rules

    def parse_body(self) -> dict[str, str]:
        pairs = {}
        self.skip_whitespace()
        while self.cursor < len(self.text) and self.text[self.cursor] != "}":
            key = self.word()
            self.skip_whitespace()
            self.skip_until({":"})
            self.require_char(":")
            self.skip_whitespace()
            value = self.word()
            pairs[key] = value
            why = self.skip_until({"}", ";"})
            if why == ";":
                self.cursor += 1
            self.skip_whitespace()
        return pairs

    def word(self, allowed_characters: str = "-#.%"):
        start = self.cursor
        while self.cursor < len(self.text) and (
            self.text[self.cursor].isalnum()
            or self.text[self.cursor] in allowed_characters
        ):
            self.cursor += 1
        if self.cursor == start:
            raise ValueError("Expected word")
        return self.text[start : self.cursor]

    def require_char(self, char: str):
        if self.cursor < len(self.text) and self.text[self.cursor] == char:
            self.cursor += 1
            return
        raise ValueError(f"Expected '{char}'")

    def optional_char(self, char: str):
        if self.cursor < len(self.text) and self.text[self.cursor] == char:
            self.cursor += 1
            return

    def skip_whitespace(self):
        while self.cursor < len(self.text) and self.text[self.cursor].isspace():
            self.cursor += 1

    def skip_until(self, stop_characters: set[str]) -> str | None:
        while self.cursor < len(self.text):
            if self.text[self.cursor] in stop_characters:
                return self.text[self.cursor]
            else:
                self.cursor += 1

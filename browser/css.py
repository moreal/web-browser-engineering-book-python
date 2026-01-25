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


class SelectorSequence(Selector):
    def __init__(self, *selectors: Selector):
        self.selectors = selectors
        self.priority = sum(selector.priority for selector in selectors)

    def matches(self, element: ElementLike) -> bool:
        for selector in self.selectors:
            if not selector.matches(element):
                return False
        return True


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


# Expected input:
# .aa
# aa.bb.cc
def tag_to_selector(tag: str) -> Selector:
    # Currently it doesn't support IdSelector.
    selectors: list[Selector] = []
    while tag:
        if tag.startswith("."):  # Consume class
            tag = tag[1:]
            next_dot_index = tag.find(".")
            if next_dot_index == -1:
                selectors.append(ClassSelector(tag))
                tag = ""
            else:
                selectors.append(ClassSelector(tag[:next_dot_index]))
                tag = tag[next_dot_index:]
        else:  # Just tag not supporting id.
            next_dot_index = tag.find(".")
            if next_dot_index == -1:
                selectors.append(TagSelector(tag))
                tag = ""
            else:
                selectors.append(TagSelector(tag[:next_dot_index]))
                tag = tag[next_dot_index:]

    if len(selectors) == 1:
        return selectors[0]
    elif len(selectors) > 1:
        return SelectorSequence(*selectors)
    else:
        raise ValueError("Invalid selector")


class CSSParser:
    def __init__(self, text: str):
        self.text = text
        self.cursor = 0

    def selector(self) -> Selector:
        tag = self.word(".-#").casefold()
        selector = tag_to_selector(tag)
        self.skip_whitespace()
        while self.cursor < len(self.text) and self.text[self.cursor] != "{":
            tag = self.word(".-#").casefold()
            decendant_selector = tag_to_selector(tag)
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

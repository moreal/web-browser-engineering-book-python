from dataclasses import dataclass

from browser.cascade.selector import (
    ClassSelector,
    DecendantSelector,
    Selector,
    SelectorSequence,
    TagSelector,
)

type CssAttributes = dict[str, str]


@dataclass(frozen=True)
class Declaration:
    name: str
    value: str
    important: bool = False


@dataclass(frozen=True)
class QualifiedRule:
    selector: Selector
    declarations: list[Declaration]


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

    def parse(self) -> list[QualifiedRule]:
        rules = []
        self.skip_whitespace()
        while self.cursor < len(self.text):
            selector = self.selector()
            self.skip_whitespace()
            self.require_char("{")
            self.skip_whitespace()
            declarations = self.parse_body()
            rules.append(QualifiedRule(selector, declarations))
            self.skip_whitespace()
            self.require_char("}")
            self.skip_whitespace()
        return rules

    def parse_body(self) -> list[Declaration]:
        declarations = []
        self.skip_whitespace()
        while self.cursor < len(self.text) and self.text[self.cursor] != "}":
            key = self.word()
            self.skip_whitespace()
            self.skip_until({":"})
            self.require_char(":")
            self.skip_whitespace()
            value = self.word()
            declarations.append(Declaration(name=key, value=value))
            why = self.skip_until({"}", ";"})
            if why == ";":
                self.cursor += 1
            self.skip_whitespace()
        return declarations

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

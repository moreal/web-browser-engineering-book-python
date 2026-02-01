from dataclasses import dataclass
from typing import Protocol

from browser.cascade.weight import SpecificityWeight
from browser.html_parser import ElementLike


class Selector(Protocol):
    priority: SpecificityWeight

    def matches(self, element: ElementLike) -> bool: ...


@dataclass(frozen=True)
class TagSelector(Selector):
    tag: str
    priority: SpecificityWeight = SpecificityWeight(0, 0, 1)

    def matches(self, element: ElementLike) -> bool:
        return element.tag == self.tag


@dataclass(frozen=True)
class ClassSelector(Selector):
    class_name: str
    priority: SpecificityWeight = SpecificityWeight(0, 1, 0)

    def matches(self, element: ElementLike) -> bool:
        return (
            "class" in element.attributes
            and self.class_name in element.attributes["class"].split()
        )


class SelectorSequence(Selector):
    def __init__(self, *selectors: Selector):
        self.selectors = selectors
        self.priority = sum(
            (selector.priority for selector in selectors),
            start=SpecificityWeight(0, 0, 0),
        )

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
        if not self.descendant.matches(element):
            return False

        current_element = element
        while current_element.parent:
            if self.ancestor.matches(current_element.parent):
                return True
            current_element = current_element.parent

        return False

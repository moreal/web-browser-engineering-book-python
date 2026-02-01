from browser.cascade.selector import (
    ClassSelector,
    DecendantSelector,
    SelectorSequence,
    TagSelector,
)
from browser.cascade.weight import SpecificityWeight


def test_tag_selector_priority():
    assert TagSelector("div").priority == SpecificityWeight(0, 0, 1)


def test_class_selector_priority():
    assert ClassSelector("foo").priority == SpecificityWeight(0, 1, 0)


def test_selector_sequence_priority():
    seq = SelectorSequence(TagSelector("div"), ClassSelector("foo"))
    assert seq.priority == SpecificityWeight(0, 1, 1)


def test_descendant_selector_priority():
    desc = DecendantSelector(TagSelector("div"), ClassSelector("foo"))
    assert desc.priority == SpecificityWeight(0, 1, 1)


def test_tag_selector_less_than_class_selector():
    assert TagSelector("div").priority < ClassSelector("foo").priority

import pytest
from browser.lex import lex, Text, Tag


class TestLex:
    def test_plain_text(self):
        tokens = lex("hello world")
        assert len(tokens) == 1
        assert isinstance(tokens[0], Text)
        assert tokens[0].text == "hello world"

    def test_single_tag(self):
        tokens = lex("<b>")
        assert len(tokens) == 1
        assert isinstance(tokens[0], Tag)
        assert tokens[0].tag == "b"

    def test_text_with_tag(self):
        tokens = lex("<b>Bold</b>")
        assert len(tokens) == 3
        assert isinstance(tokens[0], Tag)
        assert tokens[0].tag == "b"
        assert isinstance(tokens[1], Text)
        assert tokens[1].text == "Bold"
        assert isinstance(tokens[2], Tag)
        assert tokens[2].tag == "/b"

    def test_mixed_content(self):
        tokens = lex("Hello <b>Bold</b> World")
        assert len(tokens) == 5
        assert isinstance(tokens[0], Text)
        assert tokens[0].text == "Hello "
        assert isinstance(tokens[1], Tag)
        assert tokens[1].tag == "b"
        assert isinstance(tokens[2], Text)
        assert tokens[2].text == "Bold"
        assert isinstance(tokens[3], Tag)
        assert tokens[3].tag == "/b"
        assert isinstance(tokens[4], Text)
        assert tokens[4].text == " World"

    def test_nested_tags(self):
        tokens = lex("<b><i>text</i></b>")
        assert len(tokens) == 5
        assert isinstance(tokens[0], Tag)
        assert tokens[0].tag == "b"
        assert isinstance(tokens[1], Tag)
        assert tokens[1].tag == "i"
        assert isinstance(tokens[2], Text)
        assert tokens[2].text == "text"
        assert isinstance(tokens[3], Tag)
        assert tokens[3].tag == "/i"
        assert isinstance(tokens[4], Tag)
        assert tokens[4].tag == "/b"

    def test_empty_input(self):
        tokens = lex("")
        assert len(tokens) == 0

    def test_self_closing_tag(self):
        tokens = lex("<br>")
        assert len(tokens) == 1
        assert isinstance(tokens[0], Tag)
        assert tokens[0].tag == "br"

    def test_tag_with_attributes(self):
        tokens = lex('<a href="test">link</a>')
        assert len(tokens) == 3
        assert isinstance(tokens[0], Tag)
        assert tokens[0].tag == 'a href="test"'
        assert isinstance(tokens[1], Text)
        assert tokens[1].text == "link"
        assert isinstance(tokens[2], Tag)
        assert tokens[2].tag == "/a"

    def test_multiple_tags(self):
        tokens = lex("<b>bold</b> and <i>italic</i>")
        assert len(tokens) == 7
        assert tokens[0].tag == "b"
        assert tokens[1].text == "bold"
        assert tokens[2].tag == "/b"
        assert tokens[3].text == " and "
        assert tokens[4].tag == "i"
        assert tokens[5].text == "italic"
        assert tokens[6].tag == "/i"

    def test_whitespace_preservation(self):
        tokens = lex("  hello  ")
        assert len(tokens) == 1
        assert tokens[0].text == "  hello  "

    def test_newlines_in_text(self):
        tokens = lex("line1\nline2")
        assert len(tokens) == 1
        assert tokens[0].text == "line1\nline2"

    def test_unclosed_tag_at_end(self):
        tokens = lex("text<unclosed")
        assert len(tokens) == 1
        assert isinstance(tokens[0], Text)
        assert tokens[0].text == "text"

    def test_lt_gt_in_text(self):
        tokens = lex("a < b > c")
        assert len(tokens) == 3
        assert isinstance(tokens[0], Text)
        assert tokens[0].text == "a "
        assert isinstance(tokens[1], Tag)
        assert tokens[1].tag == " b "
        assert isinstance(tokens[2], Text)
        assert tokens[2].text == " c"

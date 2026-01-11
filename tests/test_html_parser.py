import pytest
from browser.html_parser import HTMLParser, Text, Element


class TestHTMLParser:
    def test_simple_text(self):
        tree = HTMLParser("Hello").parse()
        assert tree.tag == "html"
        body = tree.children[0]
        assert body.tag == "body"
        text = body.children[0]
        assert isinstance(text, Text)
        assert text.text == "Hello"

    def test_simple_tag(self):
        tree = HTMLParser("<b>Hello</b>").parse()
        body = tree.children[0]
        b = body.children[0]
        assert b.tag == "b"
        text = b.children[0]
        assert isinstance(text, Text)
        assert text.text == "Hello"

    def test_nested_tags(self):
        tree = HTMLParser("<b><i>Hello</i></b>").parse()
        body = tree.children[0]
        b = body.children[0]
        assert b.tag == "b"
        i = b.children[0]
        assert i.tag == "i"
        text = i.children[0]
        assert isinstance(text, Text)
        assert text.text == "Hello"

    def test_self_closing_tag(self):
        tree = HTMLParser("Hello<br>World").parse()
        body = tree.children[0]
        assert len(body.children) == 3
        assert isinstance(body.children[0], Text)
        assert body.children[1].tag == "br"
        assert isinstance(body.children[2], Text)

    def test_attributes(self):
        tree = HTMLParser('<a href="test.html">Link</a>').parse()
        body = tree.children[0]
        a = body.children[0]
        assert a.tag == "a"
        assert a.attributes["href"] == "test.html"

    def test_attributes_unquoted(self):
        tree = HTMLParser("<a href=test>Link</a>").parse()
        body = tree.children[0]
        a = body.children[0]
        assert a.attributes["href"] == "test"

    def test_attributes_casefold(self):
        tree = HTMLParser("<A HREF=test>Link</A>").parse()
        body = tree.children[0]
        a = body.children[0]
        assert a.tag == "a"
        assert a.attributes["href"] == "test"

    def test_implicit_html(self):
        tree = HTMLParser("Hello").parse()
        assert tree.tag == "html"

    def test_implicit_body(self):
        tree = HTMLParser("<html>Hello</html>").parse()
        body = tree.children[0]
        assert body.tag == "body"

    def test_implicit_head(self):
        tree = HTMLParser("<title>Test</title>").parse()
        head = tree.children[0]
        assert head.tag == "head"
        title = head.children[0]
        assert title.tag == "title"

    def test_doctype_ignored(self):
        tree = HTMLParser("<!DOCTYPE html><html><body>Hi</body></html>").parse()
        assert tree.tag == "html"

    def test_whitespace_only_text_ignored(self):
        tree = HTMLParser("<p>  </p><p>Hi</p>").parse()
        body = tree.children[0]
        p1 = body.children[0]
        assert len(p1.children) == 0
        p2 = body.children[1]
        assert len(p2.children) == 1

    def test_unclosed_tag(self):
        tree = HTMLParser("<p>Hello").parse()
        body = tree.children[0]
        p = body.children[0]
        assert p.tag == "p"
        text = p.children[0]
        assert isinstance(text, Text)
        assert text.text == "Hello"


class TestGetAttributes:
    def test_no_attributes(self):
        parser = HTMLParser("")
        tag, attrs = parser.get_attributes("div")
        assert tag == "div"
        assert attrs == {}

    def test_single_attribute(self):
        parser = HTMLParser("")
        tag, attrs = parser.get_attributes('a href="test"')
        assert tag == "a"
        assert attrs["href"] == "test"

    def test_multiple_attributes(self):
        parser = HTMLParser("")
        tag, attrs = parser.get_attributes('a href="test" class="link"')
        assert attrs["href"] == "test"
        assert attrs["class"] == "link"

    def test_boolean_attribute(self):
        parser = HTMLParser("")
        tag, attrs = parser.get_attributes("input disabled")
        assert attrs["disabled"] == ""

    def test_single_quoted(self):
        parser = HTMLParser("")
        tag, attrs = parser.get_attributes("a href='test'")
        assert attrs["href"] == "test"

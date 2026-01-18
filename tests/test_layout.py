from browser.html_parser import Element, Text
from browser.layout import (
    BLOCK_ELEMENTS,
    DrawRect,
    DrawText,
    FontLike,
    LayoutBox,
    collect_display_list,
    get_layout_mode,
    layout_block,
    layout_document,
    layout_inline,
)


class MockFont:
    """FontLike Protocol implementation for testing."""

    def __init__(self, size: int = 16):
        self.size = size

    def measure(self, text: str) -> int:
        return len(text) * self.size

    def metrics(self, key: str | None = None) -> int | dict[str, int]:
        if key == "ascent":
            return self.size
        if key == "descent":
            return 4
        if key == "linespace":
            return int(self.size * 1.2)
        return {
            "ascent": self.size,
            "descent": 4,
            "linespace": int(self.size * 1.2),
        }


def mock_get_font(size: int, bold: bool, italic: bool) -> FontLike:
    return MockFont(size)


class TestGetLayoutMode:
    def test_text_node_returns_inline(self):
        text = Text("hello", parent=None)
        assert get_layout_mode(text) == "inline"

    def test_block_children_returns_block(self):
        parent = Element("div", {}, None)
        child = Element("p", {}, parent)
        parent.children.append(child)

        assert get_layout_mode(parent) == "block"

    def test_inline_only_returns_inline(self):
        parent = Element("span", {}, None)
        child = Text("hello", parent)
        parent.children.append(child)

        assert get_layout_mode(parent) == "inline"

    def test_no_children_returns_block(self):
        element = Element("div", {}, None)
        assert get_layout_mode(element) == "block"


class TestLayoutDocument:
    def test_dimensions(self):
        root = Element("html", {}, None)
        body = Element("body", {}, root)
        root.children.append(body)
        text = Text("hello world", body)
        body.children.append(text)

        box = layout_document(root, width=800, hstep=13, vstep=18, get_font=mock_get_font)

        assert box.x == 13
        assert box.y == 0
        assert box.width == 800 - 2 * 13


class TestLayoutBlock:
    def test_vertical_stacking(self):
        parent = Element("div", {}, None)
        p1 = Element("p", {}, parent)
        p1.children.append(Text("first", p1))
        p2 = Element("p", {}, parent)
        p2.children.append(Text("second", p2))
        parent.children.append(p1)
        parent.children.append(p2)

        box = layout_block(parent, x=0, y=0, width=800, hstep=13, get_font=mock_get_font)

        assert len(box.children) == 2
        child1, child2 = box.children
        assert child1.y == 0
        assert child2.y == child1.y + child1.height

    def test_height_equals_sum_of_children(self):
        parent = Element("div", {}, None)
        p1 = Element("p", {}, parent)
        p1.children.append(Text("first", p1))
        p2 = Element("p", {}, parent)
        p2.children.append(Text("second", p2))
        parent.children.append(p1)
        parent.children.append(p2)

        box = layout_block(parent, x=0, y=0, width=800, hstep=13, get_font=mock_get_font)

        expected_height = sum(child.height for child in box.children)
        assert box.height == expected_height


class TestLayoutInline:
    def test_word_wrap(self):
        # Width is small enough to force wrapping
        text = Text("hello world foo bar", None)

        display_list, height = layout_inline(
            text, x=0, y=0, width=100, hstep=13, get_font=mock_get_font
        )

        # Multiple lines means we should have multiple DrawText commands
        assert len(display_list) > 0
        # Get all unique y coordinates
        y_coords = {cmd.y for cmd in display_list if isinstance(cmd, DrawText)}
        # With word wrap, we should have multiple lines (y values)
        assert len(y_coords) > 1


class TestCollectDisplayList:
    def test_collects_from_tree(self):
        root = Element("html", {}, None)
        body = Element("body", {}, root)
        root.children.append(body)
        text = Text("hello world", body)
        body.children.append(text)

        box = layout_document(root, width=800, hstep=13, vstep=18, get_font=mock_get_font)
        display_list = collect_display_list(box)

        assert len(display_list) > 0
        assert all(isinstance(cmd, (DrawText, DrawRect)) for cmd in display_list)


class TestDrawText:
    def test_top_bottom_properties(self):
        font = MockFont(16)
        cmd = DrawText(x=10, y=20, text="hello", font=font)

        assert cmd.top == 20
        assert cmd.bottom == 20 + font.metrics()["linespace"]


class TestDrawRect:
    def test_top_bottom_properties(self):
        cmd = DrawRect(x1=0, y1=10, x2=100, y2=50, color="gray")

        assert cmd.top == 10
        assert cmd.bottom == 50


class TestPreTagBackground:
    def test_pre_tag_has_background_rect(self):
        pre = Element("pre", {}, None)
        text = Text("code here", pre)
        pre.children.append(text)

        box = layout_block(pre, x=0, y=0, width=800, hstep=13, get_font=mock_get_font)
        display_list = collect_display_list(box)

        # Find DrawRect commands
        rects = [cmd for cmd in display_list if isinstance(cmd, DrawRect)]
        assert len(rects) > 0
        assert rects[0].color == "gray"

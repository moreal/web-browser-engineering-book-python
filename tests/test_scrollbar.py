from browser.browser import (
    HORIZONTAL_SCROLL_WIDTH,
    _get_max_height,
    _get_vertical_scroll_bar,
)
from browser.layout import DrawRect


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


def _make_rect(y1: int, y2: int) -> DrawRect:
    """Helper to create a DrawRect with specified y bounds."""
    return DrawRect(x1=0, y1=y1, x2=100, y2=y2, color="black")


def _get_screen_y1(result: DrawRect, scroll: int) -> int:
    """Get the screen y1 position after scroll offset is applied."""
    return result.y1 - scroll


def _get_screen_y2(result: DrawRect, scroll: int) -> int:
    """Get the screen y2 position after scroll offset is applied."""
    return result.y2 - scroll


class TestGetMaxHeight:
    def test_empty_display_list_returns_vstep(self):
        vstep = 18
        result = _get_max_height([], vstep)
        assert result == vstep

    def test_single_item_returns_bottom_plus_vstep(self):
        vstep = 18
        display_list = [_make_rect(0, 100)]
        result = _get_max_height(display_list, vstep)
        assert result == 100 + vstep

    def test_multiple_items_returns_max_bottom_plus_vstep(self):
        vstep = 18
        display_list = [
            _make_rect(0, 50),
            _make_rect(60, 150),
            _make_rect(100, 120),
        ]
        result = _get_max_height(display_list, vstep)
        assert result == 150 + vstep


class TestGetVerticalScrollBarVisibility:
    """Test scrollbar visibility (not visible issue)."""

    def test_content_smaller_than_viewport_returns_none(self):
        height = 800
        vstep = 18
        # Content height = 400 + vstep = 418 < 800
        display_list = [_make_rect(0, 400)]
        result = _get_vertical_scroll_bar(
            display_list, scroll=0, width=600, height=height, vstep=vstep
        )
        assert result is None

    def test_content_equal_to_viewport_returns_none(self):
        height = 800
        vstep = 18
        # Content height = (800 - vstep) + vstep = 800 = height
        display_list = [_make_rect(0, height - vstep)]
        result = _get_vertical_scroll_bar(
            display_list, scroll=0, width=600, height=height, vstep=vstep
        )
        assert result is None

    def test_content_larger_than_viewport_returns_draw_rect(self):
        height = 800
        vstep = 18
        # Content height = 1000 + vstep > 800
        display_list = [_make_rect(0, 1000)]
        result = _get_vertical_scroll_bar(
            display_list, scroll=0, width=600, height=height, vstep=vstep
        )
        assert result is not None
        assert isinstance(result, DrawRect)


class TestGetVerticalScrollBarPosition:
    """Test scrollbar position (incorrect position issue)."""

    def test_scrollbar_x_position(self):
        width = 600
        height = 800
        vstep = 18
        display_list = [_make_rect(0, 2000)]
        result = _get_vertical_scroll_bar(
            display_list, scroll=0, width=width, height=height, vstep=vstep
        )
        assert result is not None
        assert result.x1 == width - HORIZONTAL_SCROLL_WIDTH
        assert result.x2 == width

    def test_scroll_zero_scrollbar_screen_y1_is_zero(self):
        scroll = 0
        display_list = [_make_rect(0, 2000)]
        result = _get_vertical_scroll_bar(
            display_list, scroll=scroll, width=600, height=800, vstep=18
        )
        assert result is not None
        screen_y1 = _get_screen_y1(result, scroll)
        assert screen_y1 == 0

    def test_scroll_at_middle_scrollbar_screen_y1_proportional(self):
        height = 800
        vstep = 18
        display_list = [_make_rect(0, 2000)]
        max_height = 2000 + vstep

        # Scroll to middle
        scroll = (max_height - height) // 2
        result = _get_vertical_scroll_bar(
            display_list, scroll=scroll, width=600, height=height, vstep=vstep
        )

        assert result is not None
        rate = height / max_height
        expected_screen_y1 = int(scroll * rate)
        screen_y1 = _get_screen_y1(result, scroll)
        assert screen_y1 == expected_screen_y1

    def test_scroll_at_max_scrollbar_screen_y2_within_viewport(self):
        height = 800
        vstep = 18
        display_list = [_make_rect(0, 2000)]
        max_height = 2000 + vstep

        # Scroll to maximum
        scroll = max_height - height
        result = _get_vertical_scroll_bar(
            display_list, scroll=scroll, width=600, height=height, vstep=vstep
        )

        assert result is not None
        screen_y2 = _get_screen_y2(result, scroll)
        assert screen_y2 <= height


class TestGetVerticalScrollBarSize:
    """Test scrollbar size (incorrect size issue)."""

    def test_scrollbar_length_formula(self):
        height = 800
        vstep = 18
        scroll = 0
        display_list = [_make_rect(0, 2000)]
        max_height = 2000 + vstep

        result = _get_vertical_scroll_bar(
            display_list, scroll=scroll, width=600, height=height, vstep=vstep
        )

        assert result is not None
        expected_length = int(height * (height / max_height))
        screen_y1 = _get_screen_y1(result, scroll)
        screen_y2 = _get_screen_y2(result, scroll)
        actual_length = screen_y2 - screen_y1
        assert actual_length == expected_length

    def test_content_2x_viewport_scrollbar_half_length(self):
        height = 800
        vstep = 18
        scroll = 0
        # Make content exactly 2x viewport
        content_bottom = 2 * height - vstep
        display_list = [_make_rect(0, content_bottom)]
        max_height = content_bottom + vstep  # = 2 * height

        result = _get_vertical_scroll_bar(
            display_list, scroll=scroll, width=600, height=height, vstep=vstep
        )

        assert result is not None
        screen_y1 = _get_screen_y1(result, scroll)
        screen_y2 = _get_screen_y2(result, scroll)
        actual_length = screen_y2 - screen_y1
        # With 2x content, scrollbar should be half the viewport height
        assert actual_length == height // 2


class TestGetVerticalScrollBarBounds:
    """Test scrollbar bounds (overflow issue)."""

    def test_scrollbar_screen_y1_no_top_overflow(self):
        scroll = 0
        display_list = [_make_rect(0, 2000)]
        result = _get_vertical_scroll_bar(
            display_list, scroll=scroll, width=600, height=800, vstep=18
        )
        assert result is not None
        screen_y1 = _get_screen_y1(result, scroll)
        assert screen_y1 >= 0

    def test_scrollbar_screen_y2_no_bottom_overflow(self):
        height = 800
        vstep = 18
        scroll = 0
        display_list = [_make_rect(0, 2000)]
        result = _get_vertical_scroll_bar(
            display_list, scroll=scroll, width=600, height=height, vstep=vstep
        )
        assert result is not None
        screen_y2 = _get_screen_y2(result, scroll)
        assert screen_y2 <= height

    def test_at_max_scroll_scrollbar_stays_within_viewport(self):
        height = 800
        vstep = 18
        display_list = [_make_rect(0, 2000)]
        max_height = 2000 + vstep

        # Scroll to maximum
        scroll = max_height - height
        result = _get_vertical_scroll_bar(
            display_list, scroll=scroll, width=600, height=height, vstep=vstep
        )

        assert result is not None
        screen_y1 = _get_screen_y1(result, scroll)
        screen_y2 = _get_screen_y2(result, scroll)
        assert screen_y1 >= 0
        assert screen_y2 <= height

    def test_scrollbar_stays_fixed_while_scrolling(self):
        """Verify scrollbar screen position is independent of content scroll."""
        height = 800
        vstep = 18
        display_list = [_make_rect(0, 2000)]

        # At scroll=500, screen position should be within viewport
        scroll = 500
        result = _get_vertical_scroll_bar(
            display_list, scroll=scroll, width=600, height=height, vstep=vstep
        )

        assert result is not None
        screen_y1 = _get_screen_y1(result, scroll)
        screen_y2 = _get_screen_y2(result, scroll)
        # Scrollbar should always be visible on screen
        assert screen_y1 >= 0
        assert screen_y2 <= height


class TestScrollbarColor:
    """Test scrollbar color is gray."""

    def test_scrollbar_color_is_gray(self):
        display_list = [_make_rect(0, 2000)]
        result = _get_vertical_scroll_bar(
            display_list, scroll=0, width=600, height=800, vstep=18
        )
        assert result is not None
        assert result.color == "gray"

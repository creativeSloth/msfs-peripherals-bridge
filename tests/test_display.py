from msfs_peripherals_bridge.mapping.display import (
    BLANK,
    MINUS,
    display_cells,
    format_row,
)


def test_simple_number_is_right_justified_blank_padded():
    # heading 90 -> "   90"
    assert format_row(90) == [BLANK, BLANK, BLANK, 9, 0]


def test_full_width_number():
    # altitude 10000 fills the row exactly
    assert format_row(10000) == [1, 0, 0, 0, 0]


def test_zero():
    assert format_row(0) == [BLANK, BLANK, BLANK, BLANK, 0]


def test_negative_has_minus_cell():
    # vertical speed -500 -> " -500"
    assert format_row(-500) == [BLANK, MINUS, 5, 0, 0]


def test_value_is_rounded():
    assert format_row(123.6) == [BLANK, BLANK, 1, 2, 4]


def test_none_renders_blank_row():
    assert format_row(None) == [BLANK] * 5


def test_overflow_renders_blank_rather_than_truncating():
    assert format_row(123456) == [BLANK] * 5
    assert format_row(-99999) == [BLANK] * 5  # 6 chars incl. minus


def test_display_cells_concatenates_top_then_bottom():
    cells = display_cells(top=90, bottom=-500)
    assert cells == [BLANK, BLANK, BLANK, 9, 0, BLANK, MINUS, 5, 0, 0]
    assert len(cells) == 10

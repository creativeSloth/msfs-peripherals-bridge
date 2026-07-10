"""Pure grid helpers for the detachable value panel (no display needed)."""

from msfs_peripherals_bridge.gui import (
    _panel_cell_from_point,
    _panel_first_free,
    _panel_fit_tiles,
)


def test_first_free_row_major():
    assert _panel_first_free(set(), 3, 2) == (0, 0)
    assert _panel_first_free({(0, 0), (1, 0)}, 3, 2) == (2, 0)
    full = {(c, r) for r in range(2) for c in range(3)}
    assert _panel_first_free(full, 3, 2) is None


def test_cell_from_point_clamps():
    # 4x3 grid, 40x30 px cells.
    assert _panel_cell_from_point(0, 0, 4, 3, 40, 30) == (0, 0)
    assert _panel_cell_from_point(85, 65, 4, 3, 40, 30) == (2, 2)
    assert _panel_cell_from_point(9999, 9999, 4, 3, 40, 30) == (3, 2)  # clamp high
    assert _panel_cell_from_point(-5, -5, 4, 3, 40, 30) == (0, 0)  # clamp low


def test_fit_tiles_relocates_conflicts_and_out_of_range():
    tiles = [
        {"kind": "A:", "name": "a", "col": 0, "row": 0},
        {"kind": "A:", "name": "b", "col": 5, "row": 5},  # out of a 2x2 range
        {"kind": "A:", "name": "c", "col": 0, "row": 0},  # conflicts with a
    ]
    dropped = _panel_fit_tiles(tiles, 2, 2)
    assert dropped == []  # 2x2 holds 4 -> all fit
    cells = {(t["col"], t["row"]) for t in tiles}
    assert len(cells) == 3  # all unique now
    assert (0, 0) in cells


def test_fit_tiles_drops_when_grid_too_small():
    tiles = [{"kind": "A:", "name": str(i), "col": 9, "row": 9} for i in range(5)]
    dropped = _panel_fit_tiles(tiles, 2, 2)  # only 4 cells
    assert len(dropped) == 1

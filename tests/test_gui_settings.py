"""Persistence of the GUI's Statistik var selection (load/save round-trip).

The helpers live in ``gui`` but import no tkinter at module load, so they are
testable headless.
"""

from msfs_peripherals_bridge.gui import (
    load_panel_state,
    load_statistik_selection,
    save_panel_state,
    save_statistik_selection,
)


def test_round_trip(tmp_path):
    p = tmp_path / "gui-settings.json"
    vars_ = [
        {"kind": "A:", "name": "AUTOPILOT ALTITUDE LOCK VAR", "unit": "feet"},
        {"kind": "L:", "name": "AUTOPILOT_alt", "unit": "number"},
        {"kind": "K:", "name": "AP_MASTER", "unit": ""},
    ]
    save_statistik_selection(vars_, path=p)
    assert load_statistik_selection(path=p) == vars_


def test_missing_file_is_empty(tmp_path):
    assert load_statistik_selection(path=tmp_path / "nope.json") == []


def test_save_creates_parent_dirs(tmp_path):
    p = tmp_path / "nested" / "dir" / "gui-settings.json"
    save_statistik_selection([{"kind": "A:", "name": "X", "unit": "u"}], path=p)
    assert p.is_file()
    assert load_statistik_selection(path=p) == [{"kind": "A:", "name": "X", "unit": "u"}]


def test_malformed_json_is_empty(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("{ this is not json", encoding="utf-8")
    assert load_statistik_selection(path=p) == []


def test_missing_unit_defaults_to_empty(tmp_path):
    p = tmp_path / "gui-settings.json"
    p.write_text('{"statistik_vars": [{"kind": "A:", "name": "X"}]}', encoding="utf-8")
    assert load_statistik_selection(path=p) == [{"kind": "A:", "name": "X", "unit": ""}]


def test_non_dict_entries_are_skipped(tmp_path):
    p = tmp_path / "gui-settings.json"
    p.write_text(
        '{"statistik_vars": ["junk", {"kind": "A:", "name": "OK", "unit": "u"}]}',
        encoding="utf-8",
    )
    assert load_statistik_selection(path=p) == [{"kind": "A:", "name": "OK", "unit": "u"}]


def test_panel_state_round_trip(tmp_path):
    p = tmp_path / "s.json"
    state = {
        "cols": 6,
        "rows": 5,
        "geometry": "560x360+100+80",
        "visible": True,
        "tiles": [
            {"kind": "A:", "name": "PLANE ALTITUDE", "unit": "Feet", "col": 0, "row": 0},
            {"kind": "L:", "name": "AUTOPILOT_alt", "unit": "number", "col": 2, "row": 1},
        ],
    }
    save_panel_state(state, path=p)
    assert load_panel_state(path=p) == state


def test_panel_state_defaults(tmp_path):
    assert load_panel_state(path=tmp_path / "nope.json") == {
        "cols": 4,
        "rows": 3,
        "geometry": "",
        "visible": False,
        "tiles": [],
    }


def test_panel_state_clamps_bad_grid(tmp_path):
    p = tmp_path / "s.json"
    p.write_text(
        '{"panel": {"cols": 99, "rows": 0, "tiles": [{"kind": "A:", "name": "X"}]}}',
        encoding="utf-8",
    )
    st = load_panel_state(path=p)
    assert st["cols"] == 4 and st["rows"] == 3  # out-of-range -> defaults
    assert st["tiles"] == [{"kind": "A:", "name": "X", "unit": "", "col": 0, "row": 0}]


def test_statistik_and_panel_coexist(tmp_path):
    # Saving one section must not clobber the other in the shared settings file.
    p = tmp_path / "s.json"
    save_statistik_selection([{"kind": "A:", "name": "V", "unit": "u"}], path=p)
    save_panel_state(
        {
            "cols": 4,
            "rows": 3,
            "geometry": "",
            "tiles": [{"kind": "A:", "name": "V", "unit": "u", "col": 0, "row": 0}],
        },
        path=p,
    )
    assert load_statistik_selection(path=p) == [{"kind": "A:", "name": "V", "unit": "u"}]
    assert load_panel_state(path=p)["tiles"][0]["name"] == "V"


def test_wire_name_covers_virtual_vars():
    from msfs_peripherals_bridge.gui import _wire_name

    assert _wire_name("V:", "mode") == "V:mode"
    assert _wire_name("V:", "V:mode") == "V:mode"  # already prefixed
    assert _wire_name("L:", "AUTOPILOT_MODE") == "L:AUTOPILOT_MODE"
    assert _wire_name("A:", "AIRSPEED INDICATED") == "AIRSPEED INDICATED"
    assert _wire_name("K:", "GEAR_TOGGLE") is None

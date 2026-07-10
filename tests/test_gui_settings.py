"""Persistence of the GUI's Statistik var selection (load/save round-trip).

The helpers live in ``gui`` but import no tkinter at module load, so they are
testable headless.
"""

from msfs_peripherals_bridge.gui import (
    load_statistik_selection,
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

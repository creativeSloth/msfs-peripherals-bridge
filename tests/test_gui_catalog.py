"""The GUI variable catalog: bundled SDK SimVars/events + parsed JF L:vars."""

from pathlib import Path

from msfs_peripherals_bridge.gui_catalog import (
    KIND_EVENT,
    KIND_LVAR,
    KIND_SIMVAR,
    CatalogVar,
    filter_catalog,
    load_catalog,
)

REFERENCE_MD = Path(__file__).resolve().parents[1] / "docs" / "simvars-reference.md"


def test_bundled_catalog_is_large_and_typed():
    cat = load_catalog()  # bundled SDK only, no L:
    simvars = [v for v in cat if v.kind == KIND_SIMVAR]
    events = [v for v in cat if v.kind == KIND_EVENT]
    # The whole point of bundling the SDK list: hundreds, not the old ~46/~17.
    assert len(simvars) > 500
    assert len(events) > 500
    assert not [v for v in cat if v.kind == KIND_LVAR]  # no reference_md -> no L:


def test_known_names_and_units_present():
    cat = load_catalog()
    by_name = {(v.kind, v.name): v for v in cat}
    assert by_name[(KIND_SIMVAR, "AUTOPILOT ALTITUDE LOCK VAR")].unit  # a real unit
    assert (KIND_SIMVAR, "GENERAL ENG RPM:1") in by_name  # :index normalised to :1
    assert (KIND_EVENT, "COM_STBY_RADIO_SWAP") in by_name
    # The settable flag is carried through: a decent chunk of SimVars are writable.
    assert by_name[(KIND_SIMVAR, "GENERAL ENG THROTTLE LEVER POSITION:1")].settable is True
    assert sum(1 for v in cat if v.kind == KIND_SIMVAR and v.settable) > 100


def test_lvars_merged_when_reference_given():
    cat = load_catalog(reference_md=REFERENCE_MD)
    lvars = [v for v in cat if v.kind == KIND_LVAR]
    assert len(lvars) > 100  # the JF Arrow enumeration


def test_filter_by_kind_and_query():
    cat = load_catalog()
    only_events = filter_catalog(cat, kind=KIND_EVENT)
    assert only_events and all(v.kind == KIND_EVENT for v in only_events)
    hits = filter_catalog(cat, kind=KIND_SIMVAR, query="autopilot altitude")
    assert hits and all("autopilot altitude" in v.name.lower() for v in hits)


def test_missing_sdk_file_is_empty(tmp_path):
    # A bad sdk_json path yields no SDK vars (best-effort), doesn't raise.
    assert load_catalog(sdk_json=tmp_path / "nope.json") == []


def test_label_formats_unit():
    v = CatalogVar(name="X", kind=KIND_SIMVAR, unit="Feet", category="c")
    assert v.label == "A: X  [Feet]"
    assert CatalogVar(name="E", kind=KIND_EVENT, unit="", category="c").label == "K: E"

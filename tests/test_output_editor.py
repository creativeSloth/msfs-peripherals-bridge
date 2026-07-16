"""Stufe C output editor: model-driven field tree + comment-preserving edits."""

from pathlib import Path

import pytest

from msfs_peripherals_bridge import gui_mapper as gm
from msfs_peripherals_bridge import profile_writer as pw
from msfs_peripherals_bridge.mapping.loader import load_profile

PROFILES = Path(__file__).resolve().parents[1] / "profiles"
ARROW = load_profile(PROFILES / "piper_arrow.yaml")


def _node_at(output, path):
    return next(n for n in gm.output_nodes(output) if n.path == path)


# --------------------------------------------------------------------------- #
# output_nodes: the flattened field tree
# --------------------------------------------------------------------------- #
def test_output_nodes_covers_every_output_type():
    for outs in ARROW.outputs.values():
        for o in outs:
            nodes = gm.output_nodes(o)
            assert nodes, f"no nodes for {type(o).__name__}"
            # the discriminator is present but read-only
            assert _node_at(o, ("type",)).kind == "ro"


def test_output_nodes_multi_panel_shapes():
    o = ARROW.outputs["multi_panel"][0]
    sel = _node_at(o, ("selector",))
    assert sel.kind == "list" and sel.addable == "selector"
    entry = _node_at(o, ("selector", 0))
    assert entry.kind == "entry" and entry.removable
    simvar = _node_at(o, ("selector", 0, "simvar"))
    assert simvar.kind == "str" and simvar.pickable
    label = _node_at(o, ("selector", 0, "label"))
    assert label.kind == "str" and not label.pickable
    row = _node_at(o, ("selector", 0, "display_row"))
    assert row.kind == "choice" and set(row.choices) == {"top", "bottom"}
    leds = _node_at(o, ("bool_leds",))
    assert leds.kind == "dict" and leds.addable == "bool_leds"
    # a mapped LED is an editable, removable, pickable leaf
    led_key = next(iter(o.bool_leds))
    led = _node_at(o, ("bool_leds", led_key))
    assert led.kind == "str" and led.pickable and led.removable


def test_output_nodes_radio_bank_entries_show_their_kind():
    o = ARROW.outputs["radio_panel"][0]
    banks = _node_at(o, ("units", 0, "banks"))
    assert banks.kind == "list" and banks.addable == "banks"
    # a bank entry (units[u].banks[i]) carries its kind tag (dme/adf/xpdr)
    entry_labels = [n.label for n in gm.output_nodes(o)
                    if n.kind == "entry" and len(n.path) == 4 and n.path[2] == "banks"]
    assert entry_labels and any("dme" in x for x in entry_labels)


def test_output_nodes_unset_optional_shows_dash():
    o = ARROW.outputs["switch_panel"][0]  # gear_leds: flat, power is set
    power = _node_at(o, ("power",))
    assert power.kind == "str" and power.optional
    # an unset optional scalar renders as a dash
    from msfs_peripherals_bridge.models import GearLedOutput

    g = GearLedOutput(power=None)
    rp = _node_at(g, ("power",))
    assert rp.value == "—" and rp.optional


# --------------------------------------------------------------------------- #
# parse_output_value
# --------------------------------------------------------------------------- #
def test_parse_output_value_types_and_errors():
    o = ARROW.outputs["multi_panel"][0]
    assert gm.parse_output_value(o, ("selector", 0, "step"), "250") == 250
    assert gm.parse_output_value(o, ("selector", 0, "code"), "3") == 3
    assert gm.parse_output_value(o, ("selector", 0, "display_row"), "bottom") == "bottom"
    assert gm.parse_output_value(o, ("selector", 0, "rollover"), "ja") is True
    with pytest.raises(ValueError, match="Zahl"):
        gm.parse_output_value(o, ("selector", 0, "step"), "abc")
    with pytest.raises(ValueError, match="display_row"):
        gm.parse_output_value(o, ("selector", 0, "display_row"), "middle")
    with pytest.raises(ValueError, match="fehlt"):
        gm.parse_output_value(o, ("selector", 0, "simvar"), "  ")


def test_parse_output_value_empty_optional():
    o = ARROW.outputs["multi_panel"][0]
    # fast_step default None: emptying removes the key
    assert gm.parse_output_value(o, ("selector", 0, "fast_step"), "") is gm.UNSET
    # gear power default is a var (not None): emptying means an explicit null
    g = ARROW.outputs["switch_panel"][0]
    assert gm.parse_output_value(g, ("power",), "") is None


def test_parse_output_value_dict_entry_is_plain_str():
    o = ARROW.outputs["multi_panel"][0]
    key = next(iter(o.bool_leds))
    assert gm.parse_output_value(o, ("bool_leds", key), " L:X ") == "L:X"


# --------------------------------------------------------------------------- #
# templates validate when inserted into a real profile
# --------------------------------------------------------------------------- #
def test_every_add_template_validates_in_place():
    data = pw.load(PROFILES / "piper_arrow.yaml")
    o = ARROW.outputs["multi_panel"][0]
    for path in (("selector",), ("selector", 0, "alt_sources"),
                 ("dimmer", "targets")):
        for tpl in gm.output_add_options(o, path).values():
            pw.add_output_entry(data, "multi_panel", 0, path, tpl)
    r = ARROW.outputs["radio_panel"][0]
    for tpl in gm.output_add_options(r, ("units", 0, "banks")).values():
        pw.add_output_entry(data, "radio_panel", 0, ("units", 0, "banks"), tpl)
    for name, tpl in gm.OPTIONAL_TEMPLATES.items():
        pw.set_output_value(data, "multi_panel", 0, (name,), tpl)
    pw.validate(data)  # every template must produce a loadable profile


def test_output_dict_key_options_excludes_used_buttons():
    o = ARROW.outputs["multi_panel"][0]
    free = gm.output_dict_key_options(o, ("bool_leds",))
    assert free and not (set(free) & set(o.bool_leds))


# --------------------------------------------------------------------------- #
# writer: point edits keep comments and survive a reload
# --------------------------------------------------------------------------- #
def test_set_output_value_roundtrip(tmp_path):
    data = pw.load(PROFILES / "piper_arrow.yaml")
    pw.set_output_value(data, "multi_panel", 0, ("selector", 0, "step"), 250)
    pw.validate(data)
    out = tmp_path / "p.yaml"
    pw.dump(data, out)
    prof = load_profile(out)
    assert prof.outputs["multi_panel"][0].selector[0].step == 250
    # comments around the outputs block survive the point edit
    assert "# --- Fulcrum One Yoke" in out.read_text(encoding="utf-8")


def test_set_output_value_unset_removes_key(tmp_path):
    data = pw.load(PROFILES / "piper_arrow.yaml")
    pw.set_output_value(data, "multi_panel", 0, ("selector", 0, "fast_step"), pw.UNSET)
    pw.validate(data)
    out = tmp_path / "p.yaml"
    pw.dump(data, out)
    assert load_profile(out).outputs["multi_panel"][0].selector[0].fast_step is None


def test_add_and_remove_output_entry(tmp_path):
    data = pw.load(PROFILES / "piper_arrow.yaml")
    before = len(ARROW.outputs["multi_panel"][0].selector)
    pw.add_output_entry(data, "multi_panel", 0, ("selector",),
                        {"code": 0, "label": "NEU", "simvar": "X", "min": 0, "max": 1})
    assert len(pw.validate(data).outputs["multi_panel"][0].selector) == before + 1
    pw.remove_output_entry(data, "multi_panel", 0, ("selector",), before)
    assert len(pw.validate(data).outputs["multi_panel"][0].selector) == before


def test_set_output_value_creates_missing_dict_key(tmp_path):
    data = pw.load(PROFILES / "piper_arrow.yaml")
    o = ARROW.outputs["multi_panel"][0]
    free = gm.output_dict_key_options(o, ("bool_leds",))[0]
    pw.set_output_value(data, "multi_panel", 0, ("bool_leds", free), "L:TEST")
    prof = pw.validate(data)
    assert prof.outputs["multi_panel"][0].bool_leds[free] == "L:TEST"


def test_output_groups_and_group_fields():
    # the editor window shows meaning-groups (nav) + per-group scalar fields
    o = ARROW.outputs["multi_panel"][0]
    nodes = gm.output_nodes(o)
    groups = gm.output_groups(nodes)
    assert groups[0].kind == "root" and groups[0].path == ()
    paths = [g.path for g in groups]
    assert ("selector",) in paths and ("selector", 0) in paths
    assert ("bool_leds",) in paths and ("dimmer",) in paths
    # root fields: top-level scalars only — no containers, no fixed 'type'
    names = [f.path[-1] for f in gm.group_fields(nodes, ())]
    assert "ap_master" in names and "power" in names
    assert "selector" not in names and "type" not in names
    # entry fields: one selector entry's scalars; nested lists stay out
    enames = [f.path[-1] for f in gm.group_fields(nodes, ("selector", 0))]
    assert "simvar" in enames and "alt_sources" not in enames


def test_output_leaf_labels_are_german_where_known():
    o = ARROW.outputs["multi_panel"][0]
    nodes = gm.output_nodes(o)
    sim = next(n for n in nodes if n.path == ("selector", 0, "simvar"))
    assert sim.label == "Variable"
    assert "Encoder" in gm.output_field_help(("selector", 0, "sticky")) or \
        gm.output_field_help(("selector", 0, "sticky")).startswith("Anzeige")
    assert gm.output_field_help(("selector", 0)) == ""  # containers: no leaf help


def test_output_block_templates_validate_and_remove_cleans_up():
    # "+ Panel": every whole-block template must validate as inserted, and
    # removing the blocks again leaves no empty stubs in the YAML.
    data = pw.load(PROFILES / "cessna_172.yaml")
    for tpl in gm.OUTPUT_BLOCK_TEMPLATES.values():
        pw.add_output(data, "yoke", dict(tpl))
    prof = pw.validate(data)
    assert len(prof.outputs["yoke"]) == len(gm.OUTPUT_BLOCK_TEMPLATES)
    for _ in range(len(gm.OUTPUT_BLOCK_TEMPLATES)):
        pw.remove_output(data, "yoke", 0)
    assert "outputs" not in data
    pw.validate(data)


def test_group_role_classifies_input_vs_display():
    assert gm.group_role(("bool_leds",)) == "Anzeige (LED)"
    assert gm.group_role(("source_toggle",)) == "Eingabe"
    assert gm.group_role(("dimmer", "targets", 0)) == "Licht"
    assert gm.group_role(("units", 0, "banks")) == "Eingabe→Anzeige"
    assert gm.group_role(()) == ""


def test_entry_labels_are_short_german_words():
    o = ARROW.outputs["multi_panel"][0]
    sel0 = next(n for n in gm.output_nodes(o) if n.path == ("selector", 0))
    assert sel0.label.startswith("Position ")
    r = ARROW.outputs["radio_panel"][0]
    unit0 = next(n for n in gm.output_nodes(r) if n.path == ("units", 0))
    assert unit0.label.startswith("Einheit ")


def test_gear_led_solo_groups_have_own_windows():
    # each physical LED is its own tree row/window; Allgemein keeps the rest
    o = ARROW.outputs["switch_panel"][0]
    nodes = gm.output_nodes(o)
    groups = gm.output_groups(nodes)
    labels = {g.label for g in groups}
    assert {"LED Bugrad", "LED links", "LED rechts"} <= labels
    solo = next(g for g in groups if g.label == "LED Bugrad")
    fields = gm.group_fields(nodes, solo.path)
    assert [f.path for f in fields] == [("nose",)]
    root_fields = {f.path[-1] for f in gm.group_fields(nodes, ())}
    assert "nose" not in root_fields and "down_at" in root_fields

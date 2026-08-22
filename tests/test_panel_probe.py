"""Pure tests for the 🔦 test-send report builders (mapping.panel_test)."""

from msfs_peripherals_bridge.mapping.display import BLANK, DOT
from msfs_peripherals_bridge.mapping.panel_probe import (
    TEST_GLYPH,
    blank_report,
    multi_cell_report,
    multi_led_report,
    probe_targets,
    radio_cell_report,
    switch_led_report,
)
from msfs_peripherals_bridge.models import (
    GearLedOutput,
    MultiPanelOutput,
    RadioBank,
    RadioPanelOutput,
    RadioUnit,
    SelectorEntry,
)


def _multi() -> MultiPanelOutput:
    return MultiPanelOutput(
        selector=[SelectorEntry(code=0, label="ALT", simvar="AP ALT", min=0, max=9)]
    )


def _radio() -> RadioPanelOutput:
    bank = RadioBank(
        code=0,
        label="COM1",
        active="A",
        standby="S",
        swap_event="SW",
        whole_inc="wi",
        whole_dec="wd",
        fract_inc="fi",
        fract_dec="fd",
    )
    return RadioPanelOutput(
        units=[
            RadioUnit(
                name="upper",
                row="upper",
                banks=[bank],
                outer_cw=0,
                outer_ccw=1,
                inner_cw=2,
                inner_ccw=3,
                swap=4,
            ),
        ]
    )


# -- switch panel gear LEDs -------------------------------------------------


def test_switch_led_report_isolates_one_wheel_and_colour():
    # nose green = bit 0 (0x01); left red = bit 4 (0x10); report id leads.
    assert switch_led_report("nose", "green") == bytes([0x00, 0x01])
    assert switch_led_report("left", "red") == bytes([0x00, 0x10])
    assert switch_led_report("right", "green") == bytes([0x00, 0x04])


# -- multi panel ------------------------------------------------------------


def test_multi_led_report_lights_one_button_display_blank():
    rep = multi_led_report("ap")  # ap = bit 0
    assert len(rep) == 13  # id + 10 cells + led + spare
    assert rep[0] == 0x00
    assert list(rep[1:11]) == [BLANK] * 10  # display blank
    assert rep[11] == 0x01  # LED byte, ap bit
    assert rep[12] == 0x00
    assert multi_led_report("hdg")[11] == 0x02  # hdg = bit 1


def test_multi_cell_report_shows_eight_in_one_cell():
    rep = multi_cell_report(3)
    assert len(rep) == 13
    assert rep[1 + 3] == TEST_GLYPH
    assert [rep[1 + i] for i in range(10) if i != 3] == [BLANK] * 9
    # dot rides on the digit
    assert multi_cell_report(3, dot=True)[1 + 3] == TEST_GLYPH + DOT


# -- radio panel ------------------------------------------------------------


def test_radio_cell_report_shape_and_dot():
    rep = radio_cell_report(0)
    assert len(rep) == 23  # id + 20 cells + 2 flags
    assert rep[1] == TEST_GLYPH
    assert list(rep[-2:]) == [0x00, 0x00]  # flag bytes
    assert radio_cell_report(19, dot=True)[1 + 19] == TEST_GLYPH + DOT


# -- clear ------------------------------------------------------------------


def test_blank_report_per_type():
    assert blank_report("gear_leds") == bytes([0x00, 0x00])
    assert blank_report("multi_panel") == bytes([0x00, *([BLANK] * 10), 0x00, 0x00])
    assert blank_report("radio_panel") == bytes([0x00, *([BLANK] * 20), 0x00, 0x00])


# -- target enumeration -----------------------------------------------------


def test_gear_targets_are_three_wheels_two_colours():
    ts = probe_targets(GearLedOutput())
    assert len(ts) == 6
    assert {t.key for t in ts} == {
        f"gear:{w}:{c}" for w in ("nose", "left", "right") for c in ("green", "red")
    }
    assert all(t.dot_report is None for t in ts)  # LEDs have no decimal point


def test_multi_targets_eight_leds_ten_cells():
    ts = probe_targets(_multi())
    leds = [t for t in ts if t.key.startswith("led:")]
    cells = [t for t in ts if t.key.startswith("cell:")]
    assert len(leds) == 8
    assert len(cells) == 10


def test_radio_targets_are_twenty_cells_with_dot_variant():
    ts = probe_targets(_radio())
    assert len(ts) == 20
    assert all(t.key.startswith("cell:") for t in ts)
    assert all(t.dot_report is not None for t in ts)  # cells can flash their dot
    # four display groups (upper/lower x active/standby)
    assert len({t.group for t in ts}) == 4


# --------------------------------------------------------------------------- #
# Schritt D — generic output-scan probes (parameterised by report length)
# --------------------------------------------------------------------------- #
def test_generic_led_report_sets_only_one_bit():
    from msfs_peripherals_bridge.mapping.panel_probe import generic_led_report

    assert generic_led_report(3, 1, 3) == bytes([0x00, 0x00, 0x08, 0x00])
    assert generic_led_report(2, 0, 0) == bytes([0x00, 0x01, 0x00])
    # out-of-range address -> all blank, never an index error
    assert generic_led_report(2, 5, 0) == bytes([0x00, 0x00, 0x00])


def test_generic_cell_report_shows_eight_with_optional_dot():
    from msfs_peripherals_bridge.mapping.display import DOT
    from msfs_peripherals_bridge.mapping.panel_probe import TEST_GLYPH, generic_cell_report

    assert generic_cell_report(3, 2) == bytes([0x00, 0x00, 0x00, TEST_GLYPH])
    assert generic_cell_report(3, 2, dot=True) == bytes([0x00, 0x00, 0x00, TEST_GLYPH + DOT])


def test_generic_blank_and_target_enumeration():
    from msfs_peripherals_bridge.mapping.panel_probe import (
        generic_blank,
        generic_cell_targets,
        generic_led_targets,
    )

    assert generic_blank(4) == bytes([0x00, 0x00, 0x00, 0x00, 0x00])  # id + 4 data
    assert generic_led_targets(2) == [
        (0, 0),
        (0, 1),
        (0, 2),
        (0, 3),
        (0, 4),
        (0, 5),
        (0, 6),
        (0, 7),
        (1, 0),
        (1, 1),
        (1, 2),
        (1, 3),
        (1, 4),
        (1, 5),
        (1, 6),
        (1, 7),
    ]
    assert generic_cell_targets(3) == [0, 1, 2]

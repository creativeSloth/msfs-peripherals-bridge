from msfs_peripherals_bridge.mapping.leds import gear_led_byte, multi_button_led_byte

# Bit layout: 0/1/2 = nose/left/right green, 3/4/5 = nose/left/right red.
GREEN = (1 << 0, 1 << 1, 1 << 2)
RED = (1 << 3, 1 << 4, 1 << 5)


def test_all_down_locked_is_all_green():
    assert gear_led_byte([1.0, 1.0, 1.0]) == GREEN[0] | GREEN[1] | GREEN[2]


def test_all_up_is_off():
    assert gear_led_byte([0.0, 0.0, 0.0]) == 0


def test_in_transit_is_red_per_wheel():
    # Nose down, left in transit, right up.
    assert gear_led_byte([1.0, 0.4, 0.0]) == GREEN[0] | RED[1]


def test_down_at_threshold_leaves_locking_tolerance():
    # 0.95 default: 0.96 counts as locked (green), 0.94 still red.
    assert gear_led_byte([0.96, 0.0, 0.0]) == GREEN[0]
    assert gear_led_byte([0.94, 0.0, 0.0]) == RED[0]


def test_unknown_position_renders_off():
    assert gear_led_byte([None, 1.0, None]) == GREEN[1]


def test_unpowered_is_all_off_regardless_of_position():
    assert gear_led_byte([1.0, 0.5, 0.0], powered=False) == 0


def test_custom_down_at():
    assert gear_led_byte([0.6, 0.0, 0.0], down_at=0.5) == GREEN[0]


# Multi Panel button LEDs: bit 0=AP 1=HDG 2=NAV 3=IAS 6=APR 7=REV.
AP = 1 << 0
NAV = 1 << 2
IAS = 1 << 3


def test_multi_mode_led_shows_even_with_ap_off():
    # Mode LEDs track the selected mode regardless of master, so the rotary
    # position stays visible in the off state; only the AP LED needs the master.
    assert multi_button_led_byte(ap_master=False, mode=2) == (1 << 1)  # HDG, no AP bit
    assert multi_button_led_byte(ap_master=False, mode=None) == 0  # nothing selected -> dark


def test_multi_omni_blinks_ias_over_solid_nav():
    # OMNI (mode 1): NAV solid always; IAS follows the blink phase.
    assert multi_button_led_byte(ap_master=True, mode=1, blink_on=True) == AP | NAV | IAS
    assert multi_button_led_byte(ap_master=True, mode=1, blink_on=False) == AP | NAV
    # Works with the AP off too (NAV solid + IAS blink, just no AP bit).
    assert multi_button_led_byte(ap_master=False, mode=1, blink_on=True) == NAV | IAS
    # Plain NAV (mode 0) never lights IAS, in either phase.
    assert multi_button_led_byte(ap_master=True, mode=0, blink_on=True) == AP | NAV


def test_multi_ap_on_lights_ap_and_active_mode():
    # mode 2 = HDG (bit 1)
    assert multi_button_led_byte(ap_master=True, mode=2) == AP | (1 << 1)
    # mode 0 = NAV (bit 2)
    assert multi_button_led_byte(ap_master=True, mode=0) == AP | (1 << 2)
    # mode 3 = APR (bit 6), mode 4 = REV (bit 7)
    assert multi_button_led_byte(ap_master=True, mode=3) == AP | (1 << 6)
    assert multi_button_led_byte(ap_master=True, mode=4) == AP | (1 << 7)


def test_multi_ap_on_no_mode_lights_only_ap():
    assert multi_button_led_byte(ap_master=True, mode=None) == AP
    # an unmapped mode value also leaves only AP lit
    assert multi_button_led_byte(ap_master=True, mode=9) == AP


ALT = 1 << 4
VS = 1 << 5


def test_bool_leds_light_alt_vs_on_top_of_mode():
    # ALT/VS hold modes coexist with a lateral mode: HDG (bit 1) solid from the
    # enum, ALT lit from its own bool at the same time.
    HDG = 1 << 1
    assert (
        multi_button_led_byte(ap_master=True, mode=2, bool_leds={"alt": True, "vs": False})
        == AP | HDG | ALT
    )
    # Both holds can be on together, and stay lit with the AP master off.
    assert (
        multi_button_led_byte(ap_master=False, mode=None, bool_leds={"alt": True, "vs": True})
        == ALT | VS
    )
    # A false/absent bool lights nothing extra.
    assert multi_button_led_byte(ap_master=True, mode=None, bool_leds={"alt": False}) == AP
    assert multi_button_led_byte(ap_master=True, mode=None, bool_leds={}) == AP


# --- configurable AP-mode LED map ------------------------------------------


def test_mode_leds_default_matches_jf_arrow():
    # default map: 0/1=NAV(bit2), 2=HDG(bit1), 3=APR(bit6), 4=REV(bit7)
    assert multi_button_led_byte(ap_master=False, mode=3) == (1 << 6)
    assert multi_button_led_byte(ap_master=False, mode=4) == (1 << 7)


def test_mode_leds_override_lights_a_different_button():
    # a different autopilot: mode 2 lights NAV instead of HDG
    custom = {2: "nav"}
    assert multi_button_led_byte(ap_master=False, mode=2, mode_leds=custom) == (1 << 2)
    # a mode absent from the map lights nothing
    assert multi_button_led_byte(ap_master=False, mode=3, mode_leds=custom) == 0


def test_mode_blink_leds_configurable():
    byte_on = multi_button_led_byte(
        ap_master=False, mode=2, mode_leds={2: "hdg"}, mode_blink_leds={2: "apr"}, blink_on=True
    )
    byte_off = multi_button_led_byte(
        ap_master=False, mode=2, mode_leds={2: "hdg"}, mode_blink_leds={2: "apr"}, blink_on=False
    )
    assert byte_on == (1 << 1) | (1 << 6)  # HDG solid + APR blink
    assert byte_off == (1 << 1)  # blink phase off -> only HDG


def test_mode_leds_reject_unknown_button():
    import pytest

    from msfs_peripherals_bridge.models import MultiPanelOutput, SelectorEntry

    with pytest.raises(ValueError, match="unknown Multi Panel LED button"):
        MultiPanelOutput(
            selector=[SelectorEntry(code=0, label="ALT", simvar="X", min=0, max=9)],
            mode_leds={0: "bogus"},
        )

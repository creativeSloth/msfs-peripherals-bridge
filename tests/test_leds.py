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


# Multi Panel button LEDs: bit 0=AP 1=HDG 2=NAV 6=APR 7=REV.
AP = 1 << 0


def test_multi_ap_off_is_all_dark():
    assert multi_button_led_byte(ap_master=False, mode=2) == 0


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

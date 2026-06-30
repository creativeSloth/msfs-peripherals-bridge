from msfs_peripherals_bridge.mapping.leds import gear_led_byte

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

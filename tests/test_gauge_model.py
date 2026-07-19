"""Gauge model: needle math ported from the Air Manager luas (pure)."""

import pytest

from msfs_peripherals_bridge import gauge_model as gm


def _needle(**kw) -> gm.NeedleSpec:
    return gm.NeedleSpec(**kw)


# --------------------------------------------------------------------------- #
# angle math
# --------------------------------------------------------------------------- #
def test_angle_linear_map_preset_endpoints():
    # MAP: 10..50 over 180° from -90° (the lua: ZWEI_PI=180, OMEGA=-90)
    n = _needle(v_min=10, v_max=50, sweep=180, omega=-90)
    assert gm.angle_for(n, 10) == pytest.approx(-90)
    assert gm.angle_for(n, 50) == pytest.approx(90)
    assert gm.angle_for(n, 30) == pytest.approx(0)  # mid-scale = north


def test_angle_rpm_preset_matches_lua_formula():
    # RPM lua: Alpha = 290/3500 * RPM + 215
    n = _needle(v_min=0, v_max=3500, sweep=290, omega=215)
    for rpm in (0, 1000, 2650, 3500):
        assert gm.angle_for(n, rpm) == pytest.approx(290 / 3500 * rpm + 215)


def test_angle_clamps_out_of_range_values():
    n = _needle(v_min=0, v_max=100, sweep=270, omega=-135)
    assert gm.angle_for(n, -50) == pytest.approx(-135)
    assert gm.angle_for(n, 500) == pytest.approx(135)


def test_angle_power_law_exponent():
    # h compresses the lower end: half-scale sits below the linear midpoint
    n = _needle(v_min=0, v_max=100, sweep=100, omega=0, h=2)
    assert gm.angle_for(n, 100) == pytest.approx(100)  # full scale unchanged
    assert gm.angle_for(n, 50) == pytest.approx(100 * 0.5**2)


def test_factor_scales_raw_values():
    # e.g. a var streaming in Hz displayed in kHz
    n = _needle(v_min=0, v_max=10, sweep=100, omega=0, factor=0.001)
    assert gm.display_value(n, 5000) == pytest.approx(5)
    assert gm.angle_for(n, 5000) == pytest.approx(50)


def test_polar_screen_convention():
    x, y = gm.polar(100, 100, 50, 0)  # north = straight up (y shrinks)
    assert (x, y) == pytest.approx((100, 50))
    x, y = gm.polar(100, 100, 50, 90)  # east = to the right
    assert (x, y) == pytest.approx((150, 100))


# --------------------------------------------------------------------------- #
# ticks + arcs
# --------------------------------------------------------------------------- #
def test_ticks_major_and_minor():
    n = _needle(v_min=0, v_max=20, sweep=100, omega=0, major=10, minor=5)
    tk = gm.ticks(n)
    majors = [(v, a) for v, a, is_major in tk if is_major]
    minors = [(v, a) for v, a, is_major in tk if not is_major]
    assert [v for v, _ in majors] == [0, 10, 20]
    assert [v for v, _ in minors] == [5, 15]  # majors not repeated
    assert majors[0][1] == pytest.approx(0)
    assert majors[-1][1] == pytest.approx(100)


def test_arc_angles_ordered_and_clamped():
    n = _needle(v_min=10, v_max=50, sweep=180, omega=-90)
    a1, a2 = gm.arc_angles(n, gm.Arc(10, 41))
    assert a1 == pytest.approx(-90)
    assert a1 < a2 < 90


# --------------------------------------------------------------------------- #
# wires + persistence + presets
# --------------------------------------------------------------------------- #
def test_wire_name_conventions():
    assert gm.wire_name(_needle(kind="A:", var="AIRSPEED INDICATED")) == "AIRSPEED INDICATED"
    assert gm.wire_name(_needle(kind="L:", var="AUTOPILOT_MODE")) == "L:AUTOPILOT_MODE"
    assert gm.wire_name(_needle(kind="L:", var="L:AUTOPILOT_MODE")) == "L:AUTOPILOT_MODE"
    assert gm.wire_name(_needle(var="")) is None


def test_roundtrip_dict():
    g = gm.presets()["MAP + Fuel Flow"]
    d = gm.to_dict(g)
    back = gm.from_dict(d)
    assert back == g
    assert isinstance(d["needles"][0]["arcs"][0], dict)  # JSON-friendly


def test_presets_are_sane():
    for name, g in gm.presets().items():
        assert g.needles, name
        for n in g.needles:
            assert n.v_min < n.v_max, name
            assert 0 < n.sweep <= 360, name
            assert 0 < n.radius <= 1.0, name
            # arcs sit inside the scale
            for a in n.arcs:
                assert n.v_min <= a.v_from < a.v_to <= n.v_max, (name, a)
            # angles are monotonic across the scale
            angles = [gm.angle_for(n, n.v_min + f * n.span / 10) for f in range(11)]
            assert angles == sorted(angles), name


def test_wire_name_virtual():
    assert gm.wire_name(_needle(kind="V:", var="mode")) == "V:mode"
    assert gm.wire_name(_needle(kind="V:", var="V:mode")) == "V:mode"


# --------------------------------------------------------------------------- #
# faithful Air Manager scaling: the Fuel-Flow power-law scale + cluster shape
# --------------------------------------------------------------------------- #
def test_fuel_flow_preset_matches_lua_power_law():
    # lua: Alpha = (ZWEI_PI/Δ · v)^1.8 + 100 with ZWEI_PI = 165^(1/1.8),
    # i.e. Alpha(v) = 165·(v/25)^1.8 + 100. This is what h=1.8 must reproduce.
    ff = next(n for n in gm.presets()["MAP + Fuel Flow"].needles if n.label == "FF")
    assert ff.h == pytest.approx(1.8)
    for v in (0, 5, 12.5, 20, 25):
        assert gm.angle_for(ff, v) == pytest.approx(165 * (v / 25) ** 1.8 + 100)
    # and it is genuinely compressed low — mid-scale sits well below the linear mid
    assert gm.angle_for(ff, 12.5) < 100 + 165 * 0.5 - 20


def test_cluster_shape_and_centres():
    g = gm.presets()["Fuel L/R + Druck (Cluster)"]
    assert g.aspect == pytest.approx(6.0)
    assert [round(n.cx, 3) for n in g.needles] == [0.167, 0.5, 0.833]
    assert all(n.cy == pytest.approx(0.5) for n in g.needles)


def test_aspect_and_centres_roundtrip():
    g = gm.presets()["Fuel L/R + Druck (Cluster)"]
    back = gm.from_dict(gm.to_dict(g))
    assert back == g
    assert back.aspect == pytest.approx(6.0)


def test_from_dict_tolerates_unknown_needle_keys():
    # a persisted gauge from an older/newer schema must still load
    d = {"name": "X", "aspect": 1.0,
         "needles": [{"label": "A", "v_min": 0, "v_max": 10, "bogus": 7}]}
    g = gm.from_dict(d)
    assert g.needles[0].label == "A" and g.needles[0].cx == 0.5

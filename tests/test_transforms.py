import math

from msfs_peripherals_bridge.mapping import transforms as tf
from msfs_peripherals_bridge.models import CurveKind, Transform


def test_normalise_endpoints_and_center():
    assert tf.normalise(0, 0, 1023) == -1.0
    assert tf.normalise(1023, 0, 1023) == 1.0
    assert math.isclose(tf.normalise(511.5, 0, 1023), 0.0, abs_tol=1e-9)


def test_normalise_clamps_out_of_range():
    assert tf.normalise(-5000, 0, 1023) == -1.0
    assert tf.normalise(99999, 0, 1023) == 1.0


def test_normalise_degenerate_range():
    assert tf.normalise(10, 5, 5) == 0.0


def test_deadzone_zeros_small_input_and_keeps_edge():
    assert tf.apply_deadzone(0.1, 0.2) == 0.0
    assert tf.apply_deadzone(1.0, 0.2) == 1.0
    assert tf.apply_deadzone(-1.0, 0.2) == -1.0


def test_curve_squared_preserves_sign():
    assert math.isclose(tf.apply_curve(0.5, CurveKind.SQUARED, 0.0), 0.25)
    assert math.isclose(tf.apply_curve(-0.5, CurveKind.SQUARED, 0.0), -0.25)


def test_expo_zero_is_linear():
    assert math.isclose(tf.apply_curve(0.4, CurveKind.EXPO, 0.0), 0.4)


def test_rescale_maps_full_range():
    assert tf.rescale(-1.0, -16383, 16383) == -16383
    assert tf.rescale(1.0, -16383, 16383) == 16383
    assert math.isclose(tf.rescale(0.0, -16383, 16383), 0.0)


def test_shape_axis_full_pipeline_with_invert():
    t = Transform(invert=True, out_min=-100, out_max=100)
    # raw at min -> normalise -1 -> invert -> +1 -> rescale -> out_max
    assert tf.shape_axis(0, 0, 1023, t) == 100
    assert tf.shape_axis(1023, 0, 1023, t) == -100


def test_normalise_window_dead_band_and_smooth_sides():
    # dead window [400, 600] on a 0..1000 axis: inside = 0, each side rescaled to full
    assert tf.normalise_window(500, 0, 1000, 400, 600) == 0.0
    assert tf.normalise_window(400, 0, 1000, 400, 600) == 0.0
    assert tf.normalise_window(600, 0, 1000, 400, 600) == 0.0
    assert tf.normalise_window(0, 0, 1000, 400, 600) == -1.0
    assert tf.normalise_window(1000, 0, 1000, 400, 600) == 1.0
    assert math.isclose(tf.normalise_window(200, 0, 1000, 400, 600), -0.5)
    assert math.isclose(tf.normalise_window(800, 0, 1000, 400, 600), 0.5)


def test_normalise_window_degenerate_side_collapses():
    # window edge sitting on the travel end -> that side has no span, returns 0
    assert tf.normalise_window(0, 0, 1000, 0, 600) == 0.0
    assert tf.normalise_window(1000, 0, 1000, 400, 1000) == 0.0


def test_shape_axis_uses_raw_window_when_set():
    t = Transform(deadzone_min=400, deadzone_max=600, out_min=-100, out_max=100)
    assert tf.shape_axis(500, 0, 1000, t) == 0
    assert tf.shape_axis(0, 0, 1000, t) == -100
    assert tf.shape_axis(1000, 0, 1000, t) == 100
    assert tf.shape_axis(200, 0, 1000, t) == -50


def test_shape_axis_window_takes_precedence_over_fraction():
    # both set: the raw window wins, the legacy fraction is ignored
    t = Transform(deadzone=0.9, deadzone_min=400, deadzone_max=600, out_min=-100, out_max=100)
    assert tf.shape_axis(800, 0, 1000, t) == 50

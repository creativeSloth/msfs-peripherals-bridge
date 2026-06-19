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

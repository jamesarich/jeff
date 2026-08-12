import pytest

from eye_watcher.gaze import landmarks_to_offset


def test_center_of_frame_gives_zero_offset():
    offset = landmarks_to_offset(320, 240, 640, 480)
    assert offset.dx == pytest.approx(0.0)
    assert offset.dy == pytest.approx(0.0)


def test_point_left_of_center_gives_negative_dx():
    offset = landmarks_to_offset(160, 240, 640, 480)
    assert offset.dx < 0


def test_point_above_center_gives_negative_dy():
    offset = landmarks_to_offset(320, 120, 640, 480)
    assert offset.dy < 0


def test_offset_is_clamped_to_unit_range():
    offset = landmarks_to_offset(-1000, 5000, 640, 480)
    assert offset.dx == -1.0
    assert offset.dy == 1.0

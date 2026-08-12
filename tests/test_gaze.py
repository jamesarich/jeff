from types import SimpleNamespace

import pytest

from eye_watcher.gaze import landmarks_to_offset, largest_face


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


def _face(x0: float, y0: float, x1: float, y1: float):
    return [SimpleNamespace(x=x0, y=y0), SimpleNamespace(x=x1, y=y1)]


def test_largest_face_picks_biggest_bounding_box():
    small = _face(0.4, 0.4, 0.5, 0.5)
    big = _face(0.1, 0.1, 0.9, 0.9)
    assert largest_face([small, big]) is big
    assert largest_face([big, small]) is big


def test_largest_face_single_face_returned_unchanged():
    only = _face(0.2, 0.2, 0.6, 0.6)
    assert largest_face([only]) is only

import random

import pytest

from eye_watcher.calibration import Calibration, EyeCalibration
from eye_watcher.eyes import Blinker, GazeHold, PupilAnimator, idle_offset


def make_calibration() -> Calibration:
    return Calibration(
        left=EyeCalibration(center_x=100.0, center_y=200.0, radius=15.0),
        right=EyeCalibration(center_x=180.0, center_y=200.0, radius=15.0),
    )


def test_zero_target_keeps_pupils_centered():
    animator = PupilAnimator(calibration=make_calibration(), smoothing_alpha=1.0)
    left, right = animator.update(0.0, 0.0)
    assert left == pytest.approx((100.0, 200.0))
    assert right == pytest.approx((180.0, 200.0))


def test_update_clamps_large_target_to_max_offset():
    cal = make_calibration()
    animator = PupilAnimator(calibration=cal, smoothing_alpha=1.0, max_offset_fraction=0.6)
    left, _ = animator.update(5.0, 0.0)
    max_dx = cal.left.radius * 0.6
    assert left == pytest.approx((cal.left.center_x + max_dx, cal.left.center_y))


def test_update_smooths_toward_target_gradually():
    cal = make_calibration()
    animator = PupilAnimator(calibration=cal, smoothing_alpha=0.5, max_offset_fraction=0.6)
    max_dx = cal.left.radius * 0.6
    fully_clamped_x = cal.left.center_x + max_dx

    first_left, _ = animator.update(1.0, 0.0)
    second_left, _ = animator.update(1.0, 0.0)

    assert abs(second_left[0] - fully_clamped_x) < abs(first_left[0] - fully_clamped_x)


def test_idle_offset_at_zero_time_is_centered():
    assert idle_offset(0.0) == pytest.approx((0.0, 0.0))


def test_idle_offset_stays_within_small_range():
    for t in [0.5, 1.0, 3.14159, 10.0]:
        dx, dy = idle_offset(t)
        assert -0.5 <= dx <= 0.5
        assert -0.5 <= dy <= 0.5


def test_gaze_hold_passes_through_tracked_target():
    hold = GazeHold(hold_seconds=2.0)
    assert hold.update(True, 0.4, -0.2, now=10.0) == (0.4, -0.2)


def test_gaze_hold_keeps_last_target_during_brief_dropout():
    hold = GazeHold(hold_seconds=2.0)
    hold.update(True, 0.4, -0.2, now=10.0)
    # single dropped frame: target must NOT jump to idle drift
    assert hold.update(False, 0.0, 0.0, now=10.1) == (0.4, -0.2)
    assert hold.update(False, 0.0, 0.0, now=11.9) == (0.4, -0.2)


def test_gaze_hold_falls_back_to_idle_after_grace():
    hold = GazeHold(hold_seconds=2.0)
    hold.update(True, 0.4, -0.2, now=10.0)
    result = hold.update(False, 0.0, 0.0, now=13.0)
    assert result == idle_offset(13.0)


def test_gaze_hold_idles_before_any_face_seen():
    hold = GazeHold(hold_seconds=2.0)
    assert hold.update(False, 0.0, 0.0, now=5.0) == idle_offset(5.0)


def make_blinker(**kwargs) -> Blinker:
    return Blinker(rng=random.Random(0), min_interval=3.0, max_interval=3.0, duration=0.2, **kwargs)


def test_blinker_eyes_open_before_first_blink():
    blinker = make_blinker()
    assert blinker.amount(0.0) == 0.0
    assert blinker.amount(2.9) == 0.0


def test_blinker_fully_closed_at_blink_midpoint():
    blinker = make_blinker()
    blinker.amount(0.0)                      # schedules first blink at t=3.0
    assert blinker.amount(3.1) == pytest.approx(1.0)


def test_blinker_reopens_after_blink():
    blinker = make_blinker()
    blinker.amount(0.0)
    blinker.amount(3.1)
    assert blinker.amount(3.25) == 0.0


def test_blinker_blinks_again_after_next_interval():
    blinker = make_blinker()
    blinker.amount(0.0)
    blinker.amount(3.1)      # mid-blink
    blinker.amount(3.25)     # blink over, next scheduled 3s later
    assert blinker.amount(6.0) == 0.0
    assert blinker.amount(6.35) == pytest.approx(1.0)

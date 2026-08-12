import pytest

from eye_watcher.calibration import Calibration, EyeCalibration
from eye_watcher.eyes import PupilAnimator, idle_offset


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

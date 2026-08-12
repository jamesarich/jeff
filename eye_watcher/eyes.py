import math

from eye_watcher.calibration import Calibration, EyeCalibration


def _clamp_to_unit_circle(dx: float, dy: float) -> tuple[float, float]:
    magnitude = math.hypot(dx, dy)
    if magnitude <= 1.0:
        return dx, dy
    return dx / magnitude, dy / magnitude


def _pupil_point(eye: EyeCalibration, dx: float, dy: float, max_offset_fraction: float) -> tuple[float, float]:
    max_offset = eye.radius * max_offset_fraction
    return eye.center_x + dx * max_offset, eye.center_y + dy * max_offset


def idle_offset(t: float) -> tuple[float, float]:
    dx = 0.3 * math.sin(t * 0.5)
    dy = 0.15 * math.sin(t * 0.3)
    return dx, dy


class PupilAnimator:
    def __init__(self, calibration: Calibration, smoothing_alpha: float = 0.3, max_offset_fraction: float = 0.6):
        self.calibration = calibration
        self.smoothing_alpha = smoothing_alpha
        self.max_offset_fraction = max_offset_fraction
        self._smoothed_dx = 0.0
        self._smoothed_dy = 0.0

    def update(self, target_dx: float, target_dy: float) -> tuple[tuple[float, float], tuple[float, float]]:
        self._smoothed_dx += self.smoothing_alpha * (target_dx - self._smoothed_dx)
        self._smoothed_dy += self.smoothing_alpha * (target_dy - self._smoothed_dy)

        clamped_dx, clamped_dy = _clamp_to_unit_circle(self._smoothed_dx, self._smoothed_dy)

        left = _pupil_point(self.calibration.left, clamped_dx, clamped_dy, self.max_offset_fraction)
        right = _pupil_point(self.calibration.right, clamped_dx, clamped_dy, self.max_offset_fraction)
        return left, right

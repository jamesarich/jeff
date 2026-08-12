import math
import random

from eye_watcher.calibration import Calibration, EyeCalibration
from eye_watcher.gaze import FaceOffset
from eye_watcher.state import FACE_LOST_GRACE_SECONDS

# Eye geometry, as fractions of the calibrated eye radius. The renderer derives
# the sclera size from these so the pupil's travel range always fits inside the
# drawn eye opening — change them here and both modules stay consistent.
HORIZONTAL_TRAVEL_FRACTION = 0.6
VERTICAL_TRAVEL_FRACTION = 0.35
PUPIL_RADIUS_FRACTION = 0.35


def _clamp_to_unit_circle(dx: float, dy: float) -> tuple[float, float]:
    magnitude = math.hypot(dx, dy)
    if magnitude <= 1.0:
        return dx, dy
    return dx / magnitude, dy / magnitude


def _pupil_point(eye: EyeCalibration, dx: float, dy: float) -> tuple[float, float]:
    return (
        eye.center_x + dx * eye.radius * HORIZONTAL_TRAVEL_FRACTION,
        eye.center_y + dy * eye.radius * VERTICAL_TRAVEL_FRACTION,
    )


def idle_offset(t: float) -> tuple[float, float]:
    dx = 0.3 * math.sin(t * 0.5)
    dy = 0.15 * math.sin(t * 0.3)
    return dx, dy


class GazeHold:
    """Bridge brief detection dropouts so the gaze doesn't dart to idle drift."""

    def __init__(self, hold_seconds: float = FACE_LOST_GRACE_SECONDS):
        self.hold_seconds = hold_seconds
        self._last: tuple[float, float, float] | None = None  # (dx, dy, seen_time)

    def update(self, offset: FaceOffset | None, now: float) -> tuple[float, float]:
        if offset is not None:
            self._last = (offset.dx, offset.dy, now)
            return offset.dx, offset.dy
        if self._last is not None:
            dx, dy, seen_time = self._last
            if (now - seen_time) < self.hold_seconds:
                return dx, dy
        return idle_offset(now)


class Blinker:
    """Periodic blink: returns eyelid closure 0.0 (open) → 1.0 (closed)."""

    def __init__(
        self,
        rng: random.Random | None = None,
        min_interval: float = 3.0,
        max_interval: float = 7.0,
        duration: float = 0.2,
    ):
        self._rng = rng if rng is not None else random.Random()
        self.min_interval = min_interval
        self.max_interval = max_interval
        self.duration = duration
        self._next_blink_time: float | None = None

    def _schedule(self, now: float) -> None:
        self._next_blink_time = now + self._rng.uniform(self.min_interval, self.max_interval)

    def amount(self, now: float) -> float:
        if self._next_blink_time is None:
            self._schedule(now)
            return 0.0
        if now < self._next_blink_time:
            return 0.0
        progress = (now - self._next_blink_time) / self.duration
        if progress >= 1.0:
            self._schedule(now)
            return 0.0
        # triangle wave: open -> closed -> open over the blink duration
        return 1.0 - abs(2.0 * progress - 1.0)


class PupilAnimator:
    def __init__(self, calibration: Calibration, smoothing_alpha: float = 0.3):
        self.calibration = calibration
        self.smoothing_alpha = smoothing_alpha
        self._smoothed_dx = 0.0
        self._smoothed_dy = 0.0

    def update(self, target_dx: float, target_dy: float) -> tuple[tuple[float, float], tuple[float, float]]:
        self._smoothed_dx += self.smoothing_alpha * (target_dx - self._smoothed_dx)
        self._smoothed_dy += self.smoothing_alpha * (target_dy - self._smoothed_dy)

        clamped_dx, clamped_dy = _clamp_to_unit_circle(self._smoothed_dx, self._smoothed_dy)

        left = _pupil_point(self.calibration.left, clamped_dx, clamped_dy)
        right = _pupil_point(self.calibration.right, clamped_dx, clamped_dy)
        return left, right

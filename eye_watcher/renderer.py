from pathlib import Path

import pygame

from eye_watcher.calibration import Calibration, EyeCalibration
from eye_watcher.eyes import (
    HORIZONTAL_TRAVEL_FRACTION,
    PUPIL_RADIUS_FRACTION,
    VERTICAL_TRAVEL_FRACTION,
)

SCLERA_COLOR = (245, 240, 232)
PUPIL_COLOR = (20, 20, 20)
SCLERA_MARGIN = 1.05


class _EyeSprite:
    """Precomputed drawing geometry for one eye (calibration never changes)."""

    def __init__(self, eye: EyeCalibration):
        # Sclera sized to cover the pupil's full travel range plus a margin,
        # derived from the same fractions the animator uses.
        self.rx = int(eye.radius * (HORIZONTAL_TRAVEL_FRACTION + PUPIL_RADIUS_FRACTION) * SCLERA_MARGIN)
        self.open_ry = int(eye.radius * (VERTICAL_TRAVEL_FRACTION + PUPIL_RADIUS_FRACTION) * SCLERA_MARGIN)
        self.center = (int(eye.center_x), int(eye.center_y))
        self.pupil_radius = int(eye.radius * PUPIL_RADIUS_FRACTION)
        self.rect = pygame.Rect(0, 0, self.rx * 2, self.open_ry * 2)


class Renderer:
    def __init__(self, image_path: Path, calibration: Calibration, fullscreen: bool = False):
        pygame.init()
        raw_image = pygame.image.load(str(image_path))
        width, height = raw_image.get_size()
        # SCALED lets the compositor stretch the photo-sized surface to the
        # actual display resolution instead of asking for a video mode that
        # matches the image dimensions.
        flags = pygame.FULLSCREEN | pygame.SCALED if fullscreen else 0
        self.screen = pygame.display.set_mode((width, height), flags)
        pygame.display.set_caption("Jeff Is Watching")
        self.image = raw_image.convert()
        self._eyes = (_EyeSprite(calibration.left), _EyeSprite(calibration.right))
        self._last_drawn: tuple | None = None

    def _draw_eye(self, sprite: _EyeSprite, pupil: tuple[int, int], openness: float) -> None:
        if openness <= 0.1:
            return  # lid closed: the photo's own eye shows through
        # Blink squashes the visible eye opening vertically; the rect clip
        # doubles as the eyelid, hiding the pupil as the lid closes.
        sprite.rect.height = max(2, int(sprite.open_ry * openness) * 2)
        sprite.rect.center = sprite.center
        self.screen.set_clip(sprite.rect)
        pygame.draw.ellipse(self.screen, SCLERA_COLOR, sprite.rect)
        pygame.draw.circle(self.screen, PUPIL_COLOR, pupil, sprite.pupil_radius)
        self.screen.set_clip(None)

    def draw(
        self,
        left_pupil: tuple[float, float],
        right_pupil: tuple[float, float],
        blink: float = 0.0,
    ) -> None:
        left = (int(left_pupil[0]), int(left_pupil[1]))
        right = (int(right_pupil[0]), int(right_pupil[1]))
        openness = 1.0 - blink
        frame_key = (left, right, round(openness, 2))
        if frame_key == self._last_drawn:
            return  # steady state: output would be byte-identical
        self._last_drawn = frame_key

        self.screen.blit(self.image, (0, 0))
        self._draw_eye(self._eyes[0], left, openness)
        self._draw_eye(self._eyes[1], right, openness)
        pygame.display.flip()

    def close(self) -> None:
        pygame.quit()

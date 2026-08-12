from pathlib import Path

import pygame

from eye_watcher.calibration import Calibration


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
        self.calibration = calibration
        self.pupil_radius = min(calibration.left.radius, calibration.right.radius) * 0.35

    def _draw_eye(self, eye, pupil: tuple[float, float], blink: float) -> None:
        # White sclera under the pupil so it stays visible against the photo's
        # dark eyes; sized to cover the pupil's full travel range.
        sclera_rx = eye.radius * 1.1
        sclera_ry = eye.radius * 0.7
        openness = 1.0 - blink
        if openness <= 0.1:
            return  # lid closed: the photo's own eye shows through
        # Blink squashes the visible eye opening vertically; the rect clip
        # doubles as the eyelid, hiding the pupil as the lid closes.
        open_ry = max(1, int(sclera_ry * openness))
        sclera_rect = pygame.Rect(0, 0, int(sclera_rx * 2), open_ry * 2)
        sclera_rect.center = (int(eye.center_x), int(eye.center_y))
        self.screen.set_clip(sclera_rect)
        pygame.draw.ellipse(self.screen, (245, 240, 232), sclera_rect)
        pygame.draw.circle(self.screen, (20, 20, 20), (int(pupil[0]), int(pupil[1])), int(self.pupil_radius))
        self.screen.set_clip(None)

    def draw(
        self,
        left_pupil: tuple[float, float],
        right_pupil: tuple[float, float],
        blink: float = 0.0,
    ) -> None:
        self.screen.blit(self.image, (0, 0))
        self._draw_eye(self.calibration.left, left_pupil, blink)
        self._draw_eye(self.calibration.right, right_pupil, blink)
        pygame.display.flip()

    def close(self) -> None:
        pygame.quit()

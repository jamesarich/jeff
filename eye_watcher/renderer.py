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

    def draw(self, left_pupil: tuple[float, float], right_pupil: tuple[float, float]) -> None:
        self.screen.blit(self.image, (0, 0))
        pygame.draw.circle(self.screen, (20, 20, 20), (int(left_pupil[0]), int(left_pupil[1])), int(self.pupil_radius))
        pygame.draw.circle(self.screen, (20, 20, 20), (int(right_pupil[0]), int(right_pupil[1])), int(self.pupil_radius))
        pygame.display.flip()

    def close(self) -> None:
        pygame.quit()

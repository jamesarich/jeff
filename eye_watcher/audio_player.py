from pathlib import Path

import pygame


class AudioPlayer:
    def __init__(self):
        pygame.mixer.init()
        self._channel: pygame.mixer.Channel | None = None

    def play(self, clip_path: Path) -> None:
        if self._channel is not None and self._channel.get_busy():
            return
        sound = pygame.mixer.Sound(str(clip_path))
        self._channel = sound.play()

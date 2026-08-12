import sys
from pathlib import Path

import pygame


class AudioPlayer:
    def __init__(self):
        # A kiosk without a working audio device should still run (silently),
        # not crash at startup.
        try:
            pygame.mixer.init()
            self._enabled = True
        except pygame.error as exc:
            print(f"Audio disabled (mixer init failed: {exc})", file=sys.stderr)
            self._enabled = False
        self._channel: pygame.mixer.Channel | None = None

    def play(self, clip_path: Path) -> bool:
        if not self._enabled:
            return False
        try:
            sound = pygame.mixer.Sound(str(clip_path))
        except (pygame.error, FileNotFoundError) as exc:
            print(f"Could not load clip {clip_path}: {exc}", file=sys.stderr)
            return False
        # One clip per trigger: cut off a still-playing clip rather than
        # silently dropping the new one (the trigger and its cooldown are
        # already consumed by the time we get here).
        if self._channel is not None and self._channel.get_busy():
            self._channel.stop()
        self._channel = sound.play()
        return True

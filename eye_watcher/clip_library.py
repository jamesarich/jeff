import random
from pathlib import Path

AUDIO_EXTENSIONS = {".wav", ".ogg", ".mp3"}


class ClipLibrary:
    def __init__(self, folder: Path, rng: random.Random | None = None):
        self._rng = rng if rng is not None else random.Random()
        self._clips = (
            sorted(p for p in folder.iterdir() if p.suffix.lower() in AUDIO_EXTENSIONS)
            if folder.is_dir()
            else []
        )
        self._last_picked: Path | None = None

    def clips(self) -> list[Path]:
        return list(self._clips)

    def pick(self) -> Path | None:
        available = self._clips
        if not available:
            return None
        if len(available) > 1 and self._last_picked in available:
            available = [c for c in available if c != self._last_picked]
        choice = self._rng.choice(available)
        self._last_picked = choice
        return choice

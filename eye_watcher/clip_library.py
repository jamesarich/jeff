import random
from pathlib import Path

AUDIO_EXTENSIONS = {".wav", ".mp3"}


class ClipLibrary:
    def __init__(self, folder: Path):
        self.folder = Path(folder)
        self._last_picked: Path | None = None

    def clips(self) -> list[Path]:
        if not self.folder.is_dir():
            return []
        return sorted(p for p in self.folder.iterdir() if p.suffix.lower() in AUDIO_EXTENSIONS)

    def pick(self, rng: random.Random | None = None) -> Path | None:
        available = self.clips()
        if not available:
            return None
        if len(available) > 1 and self._last_picked in available:
            available = [c for c in available if c != self._last_picked]
        choice = rng.choice(available) if rng is not None else random.choice(available)
        self._last_picked = choice
        return choice

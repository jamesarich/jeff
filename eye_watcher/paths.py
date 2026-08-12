"""Single home for repo-anchored paths so the app and tools/ agree.

Anchored to the repo, not the process cwd, so launching from a systemd unit /
autostart entry (cwd = / or $HOME) still finds the files.
"""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DEFAULT_IMAGE_PATH = PROJECT_ROOT / "assets" / "jeff.jpg"
DEFAULT_CALIBRATION_PATH = PROJECT_ROOT / "calibration.json"
DEFAULT_SOUNDS_DIR = PROJECT_ROOT / "sounds"
DEFAULT_MODEL_PATH = PROJECT_ROOT / "models" / "face_landmarker.task"

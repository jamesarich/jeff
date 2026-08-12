from dataclasses import dataclass, asdict
import json
from pathlib import Path


@dataclass
class EyeCalibration:
    center_x: float
    center_y: float
    radius: float


@dataclass
class Calibration:
    left: EyeCalibration
    right: EyeCalibration


def save_calibration(path: Path, calibration: Calibration) -> None:
    path.write_text(json.dumps(asdict(calibration), indent=2))


def load_calibration(path: Path) -> Calibration:
    data = json.loads(path.read_text())
    return Calibration(
        left=EyeCalibration(**data["left"]),
        right=EyeCalibration(**data["right"]),
    )

"""Trim near-white margins from the base photo and shift calibration to match."""

import argparse
from dataclasses import replace
from pathlib import Path

import cv2
import numpy as np

from _common import load_image

from eye_watcher.calibration import Calibration, load_calibration, save_calibration
from eye_watcher.paths import DEFAULT_CALIBRATION_PATH


def find_content_box(image, threshold: int = 240) -> tuple[int, int, int, int]:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    content = gray < threshold
    rows = np.any(content, axis=1)
    cols = np.any(content, axis=0)
    if not rows.any():
        raise ValueError("Image is entirely white — nothing to crop to")
    y0 = int(np.argmax(rows))
    y1 = int(len(rows) - np.argmax(rows[::-1]))
    x0 = int(np.argmax(cols))
    x1 = int(len(cols) - np.argmax(cols[::-1]))
    return x0, y0, x1, y1


def shift_calibration(calibration: Calibration, dx: float, dy: float) -> Calibration:
    def shift(eye):
        return replace(eye, center_x=eye.center_x - dx, center_y=eye.center_y - dy)

    return Calibration(left=shift(calibration.left), right=shift(calibration.right))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", type=Path, help="Image to crop in place")
    parser.add_argument("--calibration", type=Path, default=DEFAULT_CALIBRATION_PATH,
                        help="Calibration file to shift by the crop offset (skipped if missing)")
    parser.add_argument("--threshold", type=int, default=240,
                        help="Pixels with gray value >= this count as margin")
    args = parser.parse_args()

    image = load_image(args.image)

    x0, y0, x1, y1 = find_content_box(image, args.threshold)
    height, width = image.shape[:2]
    if (x0, y0, x1, y1) == (0, 0, width, height):
        print("No margin found; image unchanged")
        return

    cv2.imwrite(str(args.image), image[y0:y1, x0:x1])
    print(f"Cropped {width}x{height} -> {x1 - x0}x{y1 - y0} (offset {x0},{y0})")

    if args.calibration.is_file():
        save_calibration(args.calibration, shift_calibration(load_calibration(args.calibration), x0, y0))
        print(f"Shifted calibration in {args.calibration}")


if __name__ == "__main__":
    main()

"""Detect the photo subject's eyes with MediaPipe and write calibration.json."""

import argparse
import math
import sys
from pathlib import Path

import mediapipe as mp

from _common import load_image

from eye_watcher.calibration import Calibration, EyeCalibration, save_calibration
from eye_watcher.paths import DEFAULT_CALIBRATION_PATH, DEFAULT_MODEL_PATH
from eye_watcher.tracker import create_landmarker, to_mp_image

# Canonical face-mesh eye-corner landmark indices (subject's right eye appears
# on the image's left in an unmirrored portrait, and vice versa).
RIGHT_EYE_CORNERS = (33, 133)
LEFT_EYE_CORNERS = (362, 263)


def _eye_from_corners(landmarks, corner_indices, width: int, height: int) -> EyeCalibration:
    (ax, ay), (bx, by) = (
        (landmarks[i].x * width, landmarks[i].y * height) for i in corner_indices
    )
    return EyeCalibration(
        center_x=(ax + bx) / 2,
        center_y=(ay + by) / 2,
        radius=math.dist((ax, ay), (bx, by)) / 2,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", type=Path, help="Path to the base photo")
    parser.add_argument("--output", type=Path, default=DEFAULT_CALIBRATION_PATH)
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL_PATH)
    args = parser.parse_args()

    image = load_image(args.image)
    height, width = image.shape[:2]

    landmarker = create_landmarker(args.model, mp.tasks.vision.RunningMode.IMAGE, num_faces=1)
    try:
        result = landmarker.detect(to_mp_image(image))
    finally:
        landmarker.close()

    if not result.face_landmarks:
        sys.exit(f"No face detected in {args.image} — fall back to python tools/calibrate.py")

    landmarks = result.face_landmarks[0]
    eyes = sorted(
        (
            _eye_from_corners(landmarks, RIGHT_EYE_CORNERS, width, height),
            _eye_from_corners(landmarks, LEFT_EYE_CORNERS, width, height),
        ),
        key=lambda eye: eye.center_x,
    )
    calibration = Calibration(left=eyes[0], right=eyes[1])
    save_calibration(args.output, calibration)
    print(f"left  eye: center=({eyes[0].center_x:.0f},{eyes[0].center_y:.0f}) r={eyes[0].radius:.1f}")
    print(f"right eye: center=({eyes[1].center_x:.0f},{eyes[1].center_y:.0f}) r={eyes[1].radius:.1f}")
    print(f"Saved calibration to {args.output}")


if __name__ == "__main__":
    main()

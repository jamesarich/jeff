"""Manual fallback calibration: click eye centers/edges on the base photo."""

import argparse
import math
import sys
from pathlib import Path

import cv2

from _common import load_image

from eye_watcher.calibration import Calibration, EyeCalibration, save_calibration
from eye_watcher.paths import DEFAULT_CALIBRATION_PATH

POINT_LABELS = [
    "Click LEFT eye CENTER",
    "Click LEFT eye EDGE (sets radius)",
    "Click RIGHT eye CENTER",
    "Click RIGHT eye EDGE (sets radius)",
]


def _collect_points(image_path: Path) -> list[tuple[int, int]]:
    image = load_image(image_path)
    points: list[tuple[int, int]] = []
    window = "Calibrate (click 4 points, q to quit)"

    def on_click(event, x, y, flags, userdata):
        # waitKey can deliver several queued clicks per loop iteration; without
        # this guard a double-click on the 4th point overshoots the 4-tuple
        # unpack at the call site.
        if event == cv2.EVENT_LBUTTONDOWN and len(points) < 4:
            points.append((x, y))

    cv2.namedWindow(window)
    cv2.setMouseCallback(window, on_click)

    while len(points) < 4:
        display = image.copy()
        label = POINT_LABELS[len(points)]
        cv2.putText(display, label, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        for px, py in points:
            cv2.circle(display, (px, py), 3, (0, 0, 255), -1)
        cv2.imshow(window, display)
        if cv2.waitKey(20) & 0xFF == ord("q"):
            sys.exit("Calibration cancelled")
        if cv2.getWindowProperty(window, cv2.WND_PROP_VISIBLE) < 1:
            sys.exit("Calibration cancelled (window closed)")

    cv2.destroyWindow(window)
    return points


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", type=Path, help="Path to the base Jeff photo")
    parser.add_argument("--output", type=Path, default=DEFAULT_CALIBRATION_PATH)
    args = parser.parse_args()

    left_center, left_edge, right_center, right_edge = _collect_points(args.image)

    calibration = Calibration(
        left=EyeCalibration(
            center_x=left_center[0], center_y=left_center[1],
            radius=math.dist(left_center, left_edge),
        ),
        right=EyeCalibration(
            center_x=right_center[0], center_y=right_center[1],
            radius=math.dist(right_center, right_edge),
        ),
    )
    save_calibration(args.output, calibration)
    print(f"Saved calibration to {args.output}")


if __name__ == "__main__":
    main()

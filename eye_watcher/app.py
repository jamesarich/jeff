import argparse
import sys
import time
from pathlib import Path

import pygame

from eye_watcher.audio_player import AudioPlayer
from eye_watcher.calibration import load_calibration
from eye_watcher.clip_library import ClipLibrary
from eye_watcher.eyes import Blinker, GazeHold, PupilAnimator
from eye_watcher.paths import DEFAULT_CALIBRATION_PATH, DEFAULT_IMAGE_PATH, DEFAULT_SOUNDS_DIR
from eye_watcher.renderer import Renderer
from eye_watcher.state import VisitorStateMachine
from eye_watcher.tracker import FaceTracker


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Jeff Is Watching You: eye-contact edition")
    parser.add_argument("--image", type=Path, default=DEFAULT_IMAGE_PATH)
    parser.add_argument("--calibration", type=Path, default=DEFAULT_CALIBRATION_PATH)
    parser.add_argument("--sounds-dir", type=Path, default=DEFAULT_SOUNDS_DIR)
    parser.add_argument("--camera-index", type=int, default=0)
    parser.add_argument("--cooldown", type=float, default=60.0)
    parser.add_argument("--smoothing-alpha", type=float, default=0.3)
    parser.add_argument("--fps", type=float, default=15.0)
    # Correct horizontal sense depends on the camera's placement relative to
    # the display. Default verified against a real setup; if the eyes track
    # the wrong way horizontally on yours, pass --mirror.
    parser.add_argument("--mirror", action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument("--fullscreen", action="store_true")
    parser.add_argument("--debug", action="store_true")
    return parser.parse_args(argv)


def _wants_quit() -> bool:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            return True
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            return True
    return False


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)

    if not args.image.is_file():
        sys.exit(f"Base image not found: {args.image} — see assets/README.md")
    try:
        calibration = load_calibration(args.calibration)
    except FileNotFoundError:
        sys.exit(
            f"Calibration file not found: {args.calibration} — "
            f"run: python tools/autocalibrate.py {args.image}"
        )

    animator = PupilAnimator(calibration=calibration, smoothing_alpha=args.smoothing_alpha)
    state_machine = VisitorStateMachine(cooldown_seconds=args.cooldown)
    gaze_hold = GazeHold()
    blinker = Blinker()
    clips = ClipLibrary(args.sounds_dir)

    tracker = None
    renderer = None
    try:
        # Renderer first: the photo goes up while the camera and the mediapipe
        # model (seconds on a Pi) are still initialising.
        renderer = Renderer(image_path=args.image, calibration=calibration, fullscreen=args.fullscreen)
        renderer.draw(*animator.update(0.0, 0.0))
        tracker = FaceTracker(camera_index=args.camera_index, debug=args.debug, mirror=args.mirror)
        audio = AudioPlayer()
        clock = pygame.time.Clock()

        while not _wants_quit():
            now = time.monotonic()
            offset = tracker.read()

            target_dx, target_dy = gaze_hold.update(offset, now)
            left_pupil, right_pupil = animator.update(target_dx, target_dy)

            if state_machine.update(offset is not None, now):
                clip = clips.pick()
                if clip is not None:
                    audio.play(clip)

            renderer.draw(left_pupil, right_pupil, blink=blinker.amount(now))
            clock.tick(args.fps)
    except KeyboardInterrupt:
        pass
    finally:
        if tracker is not None:
            tracker.release()
        if renderer is not None:
            renderer.close()

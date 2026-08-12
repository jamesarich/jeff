import argparse
import sys
import time
from pathlib import Path

import pygame

from eye_watcher.audio_player import AudioPlayer
from eye_watcher.calibration import load_calibration
from eye_watcher.clip_library import ClipLibrary
from eye_watcher.eyes import GazeHold, PupilAnimator
from eye_watcher.renderer import Renderer
from eye_watcher.state import VisitorStateMachine
from eye_watcher.tracker import FaceTracker

# Anchor defaults to the repo, not the process cwd, so launching from a
# systemd unit / autostart entry (cwd = / or $HOME) still finds the files.
PROJECT_ROOT = Path(__file__).resolve().parent.parent


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Jeff Is Watching You: eye-contact edition")
    parser.add_argument("--image", type=Path, default=PROJECT_ROOT / "assets" / "jeff.jpg")
    parser.add_argument("--calibration", type=Path, default=PROJECT_ROOT / "calibration.json")
    parser.add_argument("--sounds-dir", type=Path, default=PROJECT_ROOT / "sounds")
    parser.add_argument("--camera-index", type=int, default=0)
    parser.add_argument("--cooldown", type=float, default=60.0)
    parser.add_argument("--smoothing-alpha", type=float, default=0.3)
    parser.add_argument("--fps", type=float, default=15.0)
    # Correct horizontal sense depends on where the camera sits relative to the
    # display: mirrored is right when the camera is mounted on the display
    # (kiosk/Pi build); --no-mirror for off-axis camera placements.
    parser.add_argument("--mirror", action=argparse.BooleanOptionalAction, default=True)
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
            f"run: python tools/calibrate.py {args.image}"
        )

    animator = PupilAnimator(calibration=calibration, smoothing_alpha=args.smoothing_alpha)
    state_machine = VisitorStateMachine(cooldown_seconds=args.cooldown)
    gaze_hold = GazeHold()
    clips = ClipLibrary(args.sounds_dir)

    tracker = None
    renderer = None
    try:
        tracker = FaceTracker(camera_index=args.camera_index, debug=args.debug, mirror=args.mirror)
        renderer = Renderer(image_path=args.image, calibration=calibration, fullscreen=args.fullscreen)
        audio = AudioPlayer()
        clock = pygame.time.Clock()

        while not _wants_quit():
            now = time.monotonic()
            result = tracker.read()

            target_dx, target_dy = gaze_hold.update(
                result.face_found, result.offset.dx, result.offset.dy, now
            )

            left_pupil, right_pupil = animator.update(target_dx, target_dy)

            if state_machine.update(result.face_found, now):
                clip = clips.pick()
                if clip is not None:
                    audio.play(clip)

            renderer.draw(left_pupil, right_pupil)
            clock.tick(args.fps)
    except KeyboardInterrupt:
        pass
    finally:
        if tracker is not None:
            tracker.release()
        if renderer is not None:
            renderer.close()


if __name__ == "__main__":
    main()

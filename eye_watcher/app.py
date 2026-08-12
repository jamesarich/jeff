import argparse
import time
from pathlib import Path

from eye_watcher.audio_player import AudioPlayer
from eye_watcher.calibration import load_calibration
from eye_watcher.clip_library import ClipLibrary
from eye_watcher.eyes import PupilAnimator, idle_offset
from eye_watcher.renderer import Renderer
from eye_watcher.state import VisitorStateMachine
from eye_watcher.tracker import FaceTracker


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Jeff Is Watching You: eye-contact edition")
    parser.add_argument("--image", type=Path, default=Path("assets/jeff.jpg"))
    parser.add_argument("--calibration", type=Path, default=Path("calibration.json"))
    parser.add_argument("--sounds-dir", type=Path, default=Path("sounds"))
    parser.add_argument("--camera-index", type=int, default=0)
    parser.add_argument("--cooldown", type=float, default=60.0)
    parser.add_argument("--smoothing-alpha", type=float, default=0.3)
    parser.add_argument("--fullscreen", action="store_true")
    parser.add_argument("--debug", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)

    calibration = load_calibration(args.calibration)
    animator = PupilAnimator(calibration=calibration, smoothing_alpha=args.smoothing_alpha)
    state_machine = VisitorStateMachine(cooldown_seconds=args.cooldown)
    clips = ClipLibrary(args.sounds_dir)
    tracker = FaceTracker(camera_index=args.camera_index, debug=args.debug)
    renderer = Renderer(image_path=args.image, calibration=calibration, fullscreen=args.fullscreen)
    audio = AudioPlayer()

    start_time = time.monotonic()
    try:
        while True:
            now = time.monotonic()
            result = tracker.read()

            if result.face_found:
                target_dx, target_dy = result.offset.dx, result.offset.dy
            else:
                target_dx, target_dy = idle_offset(now - start_time)

            left_pupil, right_pupil = animator.update(target_dx, target_dy)

            if state_machine.update(result.face_found, now):
                clip = clips.pick()
                if clip is not None:
                    audio.play(clip)

            renderer.draw(left_pupil, right_pupil)
    except KeyboardInterrupt:
        pass
    finally:
        tracker.release()
        renderer.close()


if __name__ == "__main__":
    main()

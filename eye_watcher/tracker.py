import time
from dataclasses import dataclass
from pathlib import Path

import cv2
import mediapipe as mp

from eye_watcher.gaze import FaceOffset, landmarks_to_offset, largest_face

NOSE_TIP_LANDMARK_INDEX = 1
DEFAULT_MODEL_PATH = Path(__file__).resolve().parent.parent / "models" / "face_landmarker.task"

# After ~3s of consecutive read failures (at the app's 15fps pacing), assume the
# camera device went away and try reopening it rather than failing forever.
REOPEN_AFTER_FAILURES = 45


@dataclass
class TrackResult:
    face_found: bool
    offset: FaceOffset


class FaceTracker:
    def __init__(
        self,
        camera_index: int = 0,
        debug: bool = False,
        model_path: Path = DEFAULT_MODEL_PATH,
        mirror: bool = False,
    ):
        if not Path(model_path).is_file():
            raise FileNotFoundError(
                f"MediaPipe model not found: {model_path} — see README.md for the download step"
            )

        self._camera_index = camera_index
        self._cap = cv2.VideoCapture(camera_index)
        if not self._cap.isOpened():
            raise RuntimeError(f"Could not open camera index {camera_index}")

        options = mp.tasks.vision.FaceLandmarkerOptions(
            base_options=mp.tasks.BaseOptions(model_asset_path=str(model_path)),
            running_mode=mp.tasks.vision.RunningMode.VIDEO,
            num_faces=5,
        )
        self._landmarker = mp.tasks.vision.FaceLandmarker.create_from_options(options)
        self._debug = debug
        self._mirror = mirror
        self._start_time = time.monotonic()
        self._last_timestamp_ms = -1
        self._consecutive_failures = 0

    def _next_timestamp_ms(self) -> int:
        # detect_for_video requires strictly increasing timestamps reflecting
        # real elapsed time; fabricated fixed-rate timestamps desync its
        # temporal tracking whenever the camera runs slower than assumed.
        timestamp_ms = int((time.monotonic() - self._start_time) * 1000)
        if timestamp_ms <= self._last_timestamp_ms:
            timestamp_ms = self._last_timestamp_ms + 1
        self._last_timestamp_ms = timestamp_ms
        return timestamp_ms

    def read(self) -> TrackResult:
        ok, frame = self._cap.read()
        if not ok:
            self._consecutive_failures += 1
            if self._consecutive_failures >= REOPEN_AFTER_FAILURES:
                self._cap.release()
                self._cap = cv2.VideoCapture(self._camera_index)
                self._consecutive_failures = 0
            return TrackResult(face_found=False, offset=FaceOffset(0.0, 0.0))
        self._consecutive_failures = 0

        height, width, _ = frame.shape
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

        result = self._landmarker.detect_for_video(mp_image, self._next_timestamp_ms())

        if not result.face_landmarks:
            if self._debug:
                cv2.imshow("eye-watcher debug", frame)
                cv2.waitKey(1)
            return TrackResult(face_found=False, offset=FaceOffset(0.0, 0.0))

        landmarks = largest_face(result.face_landmarks)
        nose = landmarks[NOSE_TIP_LANDMARK_INDEX]
        nose_x, nose_y = nose.x * width, nose.y * height
        offset = landmarks_to_offset(nose_x, nose_y, width, height, mirror_x=self._mirror)

        if self._debug:
            debug_frame = frame.copy()
            cv2.circle(debug_frame, (int(nose_x), int(nose_y)), 5, (0, 255, 0), -1)
            cv2.imshow("eye-watcher debug", debug_frame)
            cv2.waitKey(1)

        return TrackResult(face_found=True, offset=offset)

    def release(self) -> None:
        self._cap.release()
        self._landmarker.close()
        if self._debug:
            cv2.destroyAllWindows()

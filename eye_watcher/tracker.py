import time
from pathlib import Path

import cv2
import mediapipe as mp

from eye_watcher.gaze import FaceOffset, landmarks_to_offset, largest_face
from eye_watcher.paths import DEFAULT_MODEL_PATH

NOSE_TIP_LANDMARK_INDEX = 1
DEBUG_WINDOW = "eye-watcher debug"

CAPTURE_WIDTH = 640
CAPTURE_HEIGHT = 480

# After this long without a successful read, assume the camera device went
# away and try reopening it rather than failing forever.
REOPEN_AFTER_SECONDS = 3.0


def validate_model_path(model_path: Path) -> Path:
    if not model_path.is_file():
        raise FileNotFoundError(
            f"MediaPipe model not found: {model_path} — see README.md for the download step"
        )
    return model_path


def create_landmarker(model_path: Path, running_mode, num_faces: int):
    options = mp.tasks.vision.FaceLandmarkerOptions(
        base_options=mp.tasks.BaseOptions(model_asset_path=str(validate_model_path(model_path))),
        running_mode=running_mode,
        num_faces=num_faces,
    )
    return mp.tasks.vision.FaceLandmarker.create_from_options(options)


def to_mp_image(bgr_frame) -> mp.Image:
    rgb = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2RGB)
    return mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)


class FaceTracker:
    def __init__(
        self,
        camera_index: int = 0,
        debug: bool = False,
        model_path: Path = DEFAULT_MODEL_PATH,
        mirror: bool = False,
    ):
        self._camera_index = camera_index
        self._cap = self._open_camera()
        if not self._cap.isOpened():
            raise RuntimeError(f"Could not open camera index {camera_index}")

        self._landmarker = create_landmarker(
            model_path, mp.tasks.vision.RunningMode.VIDEO, num_faces=2
        )
        self._debug = debug
        self._mirror = mirror
        self._start_time = time.monotonic()
        self._last_timestamp_ms = -1
        self._first_failure_time: float | None = None

    def _open_camera(self) -> cv2.VideoCapture:
        cap = cv2.VideoCapture(self._camera_index)
        # Pin a modest resolution (the Pi camera can default far higher) and a
        # single-frame buffer so read() returns the freshest frame, not a
        # queued stale one.
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAPTURE_WIDTH)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAPTURE_HEIGHT)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        return cap

    def _next_timestamp_ms(self) -> int:
        # detect_for_video requires strictly increasing timestamps reflecting
        # real elapsed time; fabricated fixed-rate timestamps desync its
        # temporal tracking whenever the camera runs slower than assumed.
        timestamp_ms = int((time.monotonic() - self._start_time) * 1000)
        if timestamp_ms <= self._last_timestamp_ms:
            timestamp_ms = self._last_timestamp_ms + 1
        self._last_timestamp_ms = timestamp_ms
        return timestamp_ms

    def _show_debug(self, frame) -> None:
        if self._debug:
            cv2.imshow(DEBUG_WINDOW, frame)
            cv2.waitKey(1)

    def read(self) -> FaceOffset | None:
        """One tracking step; None when no face is currently visible."""
        ok, frame = self._cap.read()
        if not ok:
            now = time.monotonic()
            if self._first_failure_time is None:
                self._first_failure_time = now
            elif now - self._first_failure_time >= REOPEN_AFTER_SECONDS:
                self._cap.release()
                self._cap = self._open_camera()
                self._first_failure_time = None
            return None
        self._first_failure_time = None

        if self._mirror:
            # Flip at acquisition so landmarks, the debug overlay, and the
            # returned offset all share one coordinate space.
            frame = cv2.flip(frame, 1)

        height, width, _ = frame.shape
        result = self._landmarker.detect_for_video(to_mp_image(frame), self._next_timestamp_ms())

        if not result.face_landmarks:
            self._show_debug(frame)
            return None

        nose = largest_face(result.face_landmarks)[NOSE_TIP_LANDMARK_INDEX]
        nose_x, nose_y = nose.x * width, nose.y * height

        if self._debug:
            cv2.circle(frame, (int(nose_x), int(nose_y)), 5, (0, 255, 0), -1)
            self._show_debug(frame)

        return landmarks_to_offset(nose_x, nose_y, width, height)

    def release(self) -> None:
        self._cap.release()
        self._landmarker.close()
        if self._debug:
            cv2.destroyAllWindows()

from dataclasses import dataclass
from pathlib import Path

import cv2
import mediapipe as mp

from eye_watcher.gaze import FaceOffset, landmarks_to_offset

NOSE_TIP_LANDMARK_INDEX = 1
DEFAULT_MODEL_PATH = Path(__file__).resolve().parent.parent / "models" / "face_landmarker.task"


@dataclass
class TrackResult:
    face_found: bool
    offset: FaceOffset


class FaceTracker:
    def __init__(self, camera_index: int = 0, debug: bool = False, model_path: Path = DEFAULT_MODEL_PATH):
        self._cap = cv2.VideoCapture(camera_index)
        if not self._cap.isOpened():
            raise RuntimeError(f"Could not open camera index {camera_index}")

        options = mp.tasks.vision.FaceLandmarkerOptions(
            base_options=mp.tasks.BaseOptions(model_asset_path=str(model_path)),
            running_mode=mp.tasks.vision.RunningMode.VIDEO,
            num_faces=1,
        )
        self._landmarker = mp.tasks.vision.FaceLandmarker.create_from_options(options)
        self._debug = debug
        self._frame_index = 0

    def read(self) -> TrackResult:
        ok, frame = self._cap.read()
        if not ok:
            return TrackResult(face_found=False, offset=FaceOffset(0.0, 0.0))

        height, width, _ = frame.shape
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        timestamp_ms = int(self._frame_index * (1000 / 30))
        self._frame_index += 1

        result = self._landmarker.detect_for_video(mp_image, timestamp_ms)

        if not result.face_landmarks:
            if self._debug:
                cv2.imshow("eye-watcher debug", frame)
                cv2.waitKey(1)
            return TrackResult(face_found=False, offset=FaceOffset(0.0, 0.0))

        nose = result.face_landmarks[0][NOSE_TIP_LANDMARK_INDEX]
        nose_x, nose_y = nose.x * width, nose.y * height
        offset = landmarks_to_offset(nose_x, nose_y, width, height)

        if self._debug:
            debug_frame = frame.copy()
            cv2.circle(debug_frame, (int(nose_x), int(nose_y)), 5, (0, 255, 0), -1)
            cv2.imshow("eye-watcher debug", debug_frame)
            cv2.waitKey(1)

        return TrackResult(face_found=True, offset=offset)

    def release(self) -> None:
        self._cap.release()
        if self._debug:
            cv2.destroyAllWindows()

# Jeff Is Watching You: Eye-Contact Edition Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python app that shows a photo of Jeff Goldblum whose eyes track a viewer's face via camera in real time, playing a random audio clip the first time someone comes into view, prototyped on this dev machine (USB webcam, windowed) and portable to a Raspberry Pi (Camera Module, fullscreen kiosk) unchanged.

**Architecture:** Small pure-logic modules (calibration storage, pupil math, visitor state machine, clip picking, landmark-to-offset geometry) are each independently unit tested. Hardware-facing modules (camera+face-mesh tracking, Pygame rendering, audio playback) are thin wrappers around those pure modules, verified manually since they need a real camera/display/speaker. `app.py` wires everything into one frame loop, controlled entirely by CLI flags — the same code path runs windowed on this machine and fullscreen on the Pi.

**Tech Stack:** Python 3.10+, OpenCV (`opencv-python`) for camera capture, MediaPipe (`mediapipe`, `solutions.face_mesh`) for face landmark detection, Pygame for rendering + audio, pytest for tests.

## Global Constraints

- Camera frames are processed in memory only and are never written to disk or sent over a network, in any mode.
- The optional local debug preview window (`--debug`) is off by default and only ever shows a live local window — it never saves or transmits frames.
- Tracking loop targets 10-15fps; no need to push higher.
- Pupils move together (parallel gaze) and are clamped so they never leave the eye's sclera.
- Default cooldown between "new visitor" sound triggers is 60 seconds.
- Sound clips are supplied by the user in `sounds/`; the app never fetches or bundles audio itself.
- One codebase, windowed vs. fullscreen and camera index selected via CLI flags — no per-platform branches.

---

### Task 1: Project scaffolding

**Files:**
- Create: `eye_watcher/__init__.py`
- Create: `requirements.txt`
- Create: `pytest.ini`
- Create: `tests/test_sanity.py`
- Create: `README.md`

**Interfaces:**
- Consumes: nothing
- Produces: an importable `eye_watcher` package and a working `pytest` run, which every later task relies on.

- [ ] **Step 1: Create the package and config files**

`eye_watcher/__init__.py`:
```python
```
(empty file — just marks `eye_watcher` as a package)

`requirements.txt`:
```
opencv-python
mediapipe
pygame
pytest
```
(Note: if `mediapipe.solutions.face_mesh` is missing on your installed version, install an older `mediapipe` 0.10.x release — the `solutions` API has been superseded by a newer Tasks API in some releases.)

`pytest.ini`:
```ini
[pytest]
pythonpath = .
testpaths = tests
```

`README.md`:
```markdown
# Jeff Is Watching You: Eye-Contact Edition

An animated eye-contact version of the "Jeff Goldblum is watching you poop" meme.
A photo of Jeff Goldblum tracks your face with its eyes via camera, and plays a
random sound clip the first time you come into view.

## Setup

1. `pip install -r requirements.txt`
2. Add a front-facing photo of Jeff Goldblum at `assets/jeff.jpg` (see `assets/README.md`).
3. Run `python tools/calibrate.py assets/jeff.jpg` and click the 4 requested points
   to generate `calibration.json`.
4. Add a few `.wav`/`.mp3` clips to `sounds/` (see `sounds/README.md`).
5. Run `python main.py` (add `--debug` to see the tracking overlay, `--fullscreen`
   for kiosk mode, `--camera-index N` to pick a different camera).
```

- [ ] **Step 2: Write a sanity test**

`tests/test_sanity.py`:
```python
def test_pytest_runs():
    assert True
```

- [ ] **Step 3: Run pytest to verify the scaffold works**

Run: `pytest -v`
Expected: 1 passed (`tests/test_sanity.py::test_pytest_runs`)

- [ ] **Step 4: Commit**

```bash
git add eye_watcher requirements.txt pytest.ini tests/test_sanity.py README.md
git commit -m "chore: project scaffolding"
```

---

### Task 2: Calibration storage

**Files:**
- Create: `eye_watcher/calibration.py`
- Test: `tests/test_calibration.py`

**Interfaces:**
- Consumes: nothing
- Produces: `EyeCalibration(center_x: float, center_y: float, radius: float)`,
  `Calibration(left: EyeCalibration, right: EyeCalibration)`,
  `save_calibration(path: Path, calibration: Calibration) -> None`,
  `load_calibration(path: Path) -> Calibration` — used by Tasks 3, 8, 10, 11.

- [ ] **Step 1: Write the failing test**

`tests/test_calibration.py`:
```python
from eye_watcher.calibration import Calibration, EyeCalibration, save_calibration, load_calibration


def test_save_and_load_round_trip(tmp_path):
    cal = Calibration(
        left=EyeCalibration(center_x=100.0, center_y=200.0, radius=15.0),
        right=EyeCalibration(center_x=180.0, center_y=200.0, radius=15.0),
    )
    path = tmp_path / "calibration.json"

    save_calibration(path, cal)
    loaded = load_calibration(path)

    assert loaded == cal
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_calibration.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'eye_watcher.calibration'`

- [ ] **Step 3: Write minimal implementation**

`eye_watcher/calibration.py`:
```python
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
    data = {
        "left": asdict(calibration.left),
        "right": asdict(calibration.right),
    }
    path.write_text(json.dumps(data, indent=2))


def load_calibration(path: Path) -> Calibration:
    data = json.loads(path.read_text())
    return Calibration(
        left=EyeCalibration(**data["left"]),
        right=EyeCalibration(**data["right"]),
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_calibration.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add eye_watcher/calibration.py tests/test_calibration.py
git commit -m "feat: add calibration load/save"
```

---

### Task 3: Pupil animation math

**Files:**
- Create: `eye_watcher/eyes.py`
- Test: `tests/test_eyes.py`

**Interfaces:**
- Consumes: `Calibration`, `EyeCalibration` from `eye_watcher.calibration` (Task 2)
- Produces: `PupilAnimator(calibration: Calibration, smoothing_alpha: float = 0.3, max_offset_fraction: float = 0.6)`
  with `.update(target_dx: float, target_dy: float) -> tuple[tuple[float, float], tuple[float, float]]`
  returning `(left_pupil_xy, right_pupil_xy)` in absolute pixel coordinates; and
  `idle_offset(t: float) -> tuple[float, float]` — used by Task 11 (`app.py`).

- [ ] **Step 1: Write the failing tests**

`tests/test_eyes.py`:
```python
import pytest

from eye_watcher.calibration import Calibration, EyeCalibration
from eye_watcher.eyes import PupilAnimator, idle_offset


def make_calibration() -> Calibration:
    return Calibration(
        left=EyeCalibration(center_x=100.0, center_y=200.0, radius=15.0),
        right=EyeCalibration(center_x=180.0, center_y=200.0, radius=15.0),
    )


def test_zero_target_keeps_pupils_centered():
    animator = PupilAnimator(calibration=make_calibration(), smoothing_alpha=1.0)
    left, right = animator.update(0.0, 0.0)
    assert left == pytest.approx((100.0, 200.0))
    assert right == pytest.approx((180.0, 200.0))


def test_update_clamps_large_target_to_max_offset():
    cal = make_calibration()
    animator = PupilAnimator(calibration=cal, smoothing_alpha=1.0, max_offset_fraction=0.6)
    left, _ = animator.update(5.0, 0.0)
    max_dx = cal.left.radius * 0.6
    assert left == pytest.approx((cal.left.center_x + max_dx, cal.left.center_y))


def test_update_smooths_toward_target_gradually():
    cal = make_calibration()
    animator = PupilAnimator(calibration=cal, smoothing_alpha=0.5, max_offset_fraction=0.6)
    max_dx = cal.left.radius * 0.6
    fully_clamped_x = cal.left.center_x + max_dx

    first_left, _ = animator.update(1.0, 0.0)
    second_left, _ = animator.update(1.0, 0.0)

    assert abs(second_left[0] - fully_clamped_x) < abs(first_left[0] - fully_clamped_x)


def test_idle_offset_at_zero_time_is_centered():
    assert idle_offset(0.0) == pytest.approx((0.0, 0.0))


def test_idle_offset_stays_within_small_range():
    for t in [0.5, 1.0, 3.14159, 10.0]:
        dx, dy = idle_offset(t)
        assert -0.5 <= dx <= 0.5
        assert -0.5 <= dy <= 0.5
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_eyes.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'eye_watcher.eyes'`

- [ ] **Step 3: Write minimal implementation**

`eye_watcher/eyes.py`:
```python
import math

from eye_watcher.calibration import Calibration, EyeCalibration


def _clamp_to_unit_circle(dx: float, dy: float) -> tuple[float, float]:
    magnitude = math.hypot(dx, dy)
    if magnitude <= 1.0:
        return dx, dy
    return dx / magnitude, dy / magnitude


def _pupil_point(eye: EyeCalibration, dx: float, dy: float, max_offset_fraction: float) -> tuple[float, float]:
    max_offset = eye.radius * max_offset_fraction
    return eye.center_x + dx * max_offset, eye.center_y + dy * max_offset


def idle_offset(t: float) -> tuple[float, float]:
    dx = 0.3 * math.sin(t * 0.5)
    dy = 0.15 * math.sin(t * 0.3)
    return dx, dy


class PupilAnimator:
    def __init__(self, calibration: Calibration, smoothing_alpha: float = 0.3, max_offset_fraction: float = 0.6):
        self.calibration = calibration
        self.smoothing_alpha = smoothing_alpha
        self.max_offset_fraction = max_offset_fraction
        self._smoothed_dx = 0.0
        self._smoothed_dy = 0.0

    def update(self, target_dx: float, target_dy: float) -> tuple[tuple[float, float], tuple[float, float]]:
        self._smoothed_dx += self.smoothing_alpha * (target_dx - self._smoothed_dx)
        self._smoothed_dy += self.smoothing_alpha * (target_dy - self._smoothed_dy)

        clamped_dx, clamped_dy = _clamp_to_unit_circle(self._smoothed_dx, self._smoothed_dy)

        left = _pupil_point(self.calibration.left, clamped_dx, clamped_dy, self.max_offset_fraction)
        right = _pupil_point(self.calibration.right, clamped_dx, clamped_dy, self.max_offset_fraction)
        return left, right
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_eyes.py -v`
Expected: PASS (6 tests)

- [ ] **Step 5: Commit**

```bash
git add eye_watcher/eyes.py tests/test_eyes.py
git commit -m "feat: add pupil animation math"
```

---

### Task 4: Visitor state machine

**Files:**
- Create: `eye_watcher/state.py`
- Test: `tests/test_state.py`

**Interfaces:**
- Consumes: nothing
- Produces: `VisitorState` enum (`IDLE`, `WATCHING`), `VisitorStateMachine(cooldown_seconds: float = 60.0)`
  with `.state: VisitorState` and `.update(face_found: bool, now: float) -> bool` (returns `True` exactly
  when a new-visitor sound trigger fires) — used by Task 11 (`app.py`).

- [ ] **Step 1: Write the failing tests**

`tests/test_state.py`:
```python
from eye_watcher.state import VisitorState, VisitorStateMachine


def test_no_face_stays_idle_and_never_triggers():
    sm = VisitorStateMachine(cooldown_seconds=60.0)
    assert sm.update(False, 0.0) is False
    assert sm.state is VisitorState.IDLE


def test_first_detection_triggers_and_enters_watching():
    sm = VisitorStateMachine(cooldown_seconds=60.0)
    sm.update(False, 0.0)
    assert sm.update(True, 1.0) is True
    assert sm.state is VisitorState.WATCHING


def test_continued_presence_does_not_retrigger():
    sm = VisitorStateMachine(cooldown_seconds=60.0)
    sm.update(True, 1.0)
    assert sm.update(True, 2.0) is False
    assert sm.update(True, 3.0) is False


def test_leaving_and_returning_within_cooldown_does_not_retrigger():
    sm = VisitorStateMachine(cooldown_seconds=60.0)
    sm.update(True, 1.0)          # triggers, last_trigger_time = 1.0
    sm.update(False, 2.0)         # leaves frame -> IDLE
    assert sm.update(True, 10.0) is False   # 10 - 1 = 9s < 60s cooldown
    assert sm.state is VisitorState.WATCHING


def test_leaving_and_returning_after_cooldown_retriggers():
    sm = VisitorStateMachine(cooldown_seconds=60.0)
    sm.update(True, 1.0)          # triggers, last_trigger_time = 1.0
    sm.update(False, 2.0)         # leaves frame -> IDLE
    assert sm.update(True, 70.0) is True    # 70 - 1 = 69s >= 60s cooldown
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_state.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'eye_watcher.state'`

- [ ] **Step 3: Write minimal implementation**

`eye_watcher/state.py`:
```python
from enum import Enum, auto


class VisitorState(Enum):
    IDLE = auto()
    WATCHING = auto()


class VisitorStateMachine:
    def __init__(self, cooldown_seconds: float = 60.0):
        self.cooldown_seconds = cooldown_seconds
        self.state = VisitorState.IDLE
        self._last_trigger_time: float | None = None

    def update(self, face_found: bool, now: float) -> bool:
        triggered = False
        if face_found:
            if self.state is VisitorState.IDLE:
                cooldown_elapsed = (
                    self._last_trigger_time is None
                    or (now - self._last_trigger_time) >= self.cooldown_seconds
                )
                if cooldown_elapsed:
                    triggered = True
                    self._last_trigger_time = now
            self.state = VisitorState.WATCHING
        else:
            self.state = VisitorState.IDLE
        return triggered
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_state.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add eye_watcher/state.py tests/test_state.py
git commit -m "feat: add visitor state machine"
```

---

### Task 5: Clip library

**Files:**
- Create: `eye_watcher/clip_library.py`
- Test: `tests/test_clip_library.py`

**Interfaces:**
- Consumes: nothing
- Produces: `ClipLibrary(folder: Path)` with `.clips() -> list[Path]` and
  `.pick(rng: random.Random | None = None) -> Path | None` — used by Task 11 (`app.py`).

- [ ] **Step 1: Write the failing tests**

`tests/test_clip_library.py`:
```python
import random

from eye_watcher.clip_library import ClipLibrary


def test_pick_returns_none_when_folder_empty(tmp_path):
    lib = ClipLibrary(tmp_path)
    assert lib.pick() is None


def test_pick_returns_none_when_folder_missing(tmp_path):
    lib = ClipLibrary(tmp_path / "does-not-exist")
    assert lib.pick() is None


def test_clips_ignores_non_audio_files(tmp_path):
    (tmp_path / "notes.txt").write_text("x")
    (tmp_path / "clip.wav").write_bytes(b"\x00")
    lib = ClipLibrary(tmp_path)
    assert lib.clips() == [tmp_path / "clip.wav"]


def test_pick_avoids_immediate_repeat(tmp_path):
    (tmp_path / "a.wav").write_bytes(b"\x00")
    (tmp_path / "b.wav").write_bytes(b"\x00")
    lib = ClipLibrary(tmp_path)
    rng = random.Random(0)

    picks = [lib.pick(rng) for _ in range(20)]

    for previous, current in zip(picks, picks[1:]):
        assert previous != current
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_clip_library.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'eye_watcher.clip_library'`

- [ ] **Step 3: Write minimal implementation**

`eye_watcher/clip_library.py`:
```python
import random
from pathlib import Path

AUDIO_EXTENSIONS = {".wav", ".mp3"}


class ClipLibrary:
    def __init__(self, folder: Path):
        self.folder = Path(folder)
        self._last_picked: Path | None = None

    def clips(self) -> list[Path]:
        if not self.folder.is_dir():
            return []
        return sorted(p for p in self.folder.iterdir() if p.suffix.lower() in AUDIO_EXTENSIONS)

    def pick(self, rng: random.Random | None = None) -> Path | None:
        rng = rng or random
        available = self.clips()
        if not available:
            return None
        if len(available) > 1 and self._last_picked in available:
            available = [c for c in available if c != self._last_picked]
        choice = rng.choice(available)
        self._last_picked = choice
        return choice
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_clip_library.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add eye_watcher/clip_library.py tests/test_clip_library.py
git commit -m "feat: add clip library random selection"
```

---

### Task 6: Landmark-to-offset geometry

**Files:**
- Create: `eye_watcher/gaze.py`
- Test: `tests/test_gaze.py`

**Interfaces:**
- Consumes: nothing
- Produces: `FaceOffset(dx: float, dy: float)`,
  `landmarks_to_offset(point_x: float, point_y: float, frame_width: int, frame_height: int) -> FaceOffset`
  — used by Task 7 (`tracker.py`).

- [ ] **Step 1: Write the failing tests**

`tests/test_gaze.py`:
```python
import pytest

from eye_watcher.gaze import landmarks_to_offset


def test_center_of_frame_gives_zero_offset():
    offset = landmarks_to_offset(320, 240, 640, 480)
    assert offset.dx == pytest.approx(0.0)
    assert offset.dy == pytest.approx(0.0)


def test_point_left_of_center_gives_negative_dx():
    offset = landmarks_to_offset(160, 240, 640, 480)
    assert offset.dx < 0


def test_point_above_center_gives_negative_dy():
    offset = landmarks_to_offset(320, 120, 640, 480)
    assert offset.dy < 0


def test_offset_is_clamped_to_unit_range():
    offset = landmarks_to_offset(-1000, 5000, 640, 480)
    assert offset.dx == -1.0
    assert offset.dy == 1.0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_gaze.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'eye_watcher.gaze'`

- [ ] **Step 3: Write minimal implementation**

`eye_watcher/gaze.py`:
```python
from dataclasses import dataclass


@dataclass
class FaceOffset:
    dx: float
    dy: float


def landmarks_to_offset(point_x: float, point_y: float, frame_width: int, frame_height: int) -> FaceOffset:
    center_x = frame_width / 2
    center_y = frame_height / 2

    dx = (point_x - center_x) / center_x
    dy = (point_y - center_y) / center_y

    dx = max(-1.0, min(1.0, dx))
    dy = max(-1.0, min(1.0, dy))

    return FaceOffset(dx=dx, dy=dy)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_gaze.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add eye_watcher/gaze.py tests/test_gaze.py
git commit -m "feat: add landmark-to-offset geometry"
```

---

### Task 7: Face tracker (camera + face mesh)

**Files:**
- Create: `eye_watcher/tracker.py`

**Interfaces:**
- Consumes: `landmarks_to_offset`, `FaceOffset` from `eye_watcher.gaze` (Task 6)
- Produces: `TrackResult(face_found: bool, offset: FaceOffset)`,
  `FaceTracker(camera_index: int = 0, debug: bool = False)` with
  `.read() -> TrackResult` and `.release() -> None` — used by Task 11 (`app.py`).

No automated tests here — a real camera and (for `--debug`) a display are required,
neither of which is available in an automated test run. Verify manually per Step 2.

- [ ] **Step 1: Write the implementation**

`eye_watcher/tracker.py`:
```python
from dataclasses import dataclass

import cv2
import mediapipe as mp

from eye_watcher.gaze import FaceOffset, landmarks_to_offset

NOSE_TIP_LANDMARK_INDEX = 1


@dataclass
class TrackResult:
    face_found: bool
    offset: FaceOffset


class FaceTracker:
    def __init__(self, camera_index: int = 0, debug: bool = False):
        self._cap = cv2.VideoCapture(camera_index)
        if not self._cap.isOpened():
            raise RuntimeError(f"Could not open camera index {camera_index}")

        self._face_mesh = mp.solutions.face_mesh.FaceMesh(
            max_num_faces=1,
            refine_landmarks=False,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        self._debug = debug

    def read(self) -> TrackResult:
        ok, frame = self._cap.read()
        if not ok:
            return TrackResult(face_found=False, offset=FaceOffset(0.0, 0.0))

        height, width, _ = frame.shape
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self._face_mesh.process(rgb)

        if not results.multi_face_landmarks:
            if self._debug:
                cv2.imshow("eye-watcher debug", frame)
                cv2.waitKey(1)
            return TrackResult(face_found=False, offset=FaceOffset(0.0, 0.0))

        nose = results.multi_face_landmarks[0].landmark[NOSE_TIP_LANDMARK_INDEX]
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
```

- [ ] **Step 2: Verify manually**

Run this from the repo root (uses your dev machine's USB webcam):
```bash
python -c "
import time
from eye_watcher.tracker import FaceTracker

tracker = FaceTracker(camera_index=0, debug=True)
try:
    for _ in range(150):
        result = tracker.read()
        print(result.face_found, result.offset)
        time.sleep(0.05)
finally:
    tracker.release()
"
```
Expected: a debug window opens showing your webcam feed; a green dot appears on your
nose when your face is detected; the printed `dx, dy` offsets move toward negative
when you lean left of frame-center and toward positive when you lean right (and
similarly up/down). If the sign feels backwards once wired into the full app in
Task 11, flip it in `eye_watcher/gaze.py`'s `landmarks_to_offset`.

- [ ] **Step 3: Commit**

```bash
git add eye_watcher/tracker.py
git commit -m "feat: add camera face tracker"
```

---

### Task 8: Renderer

**Files:**
- Create: `eye_watcher/renderer.py`

**Interfaces:**
- Consumes: `Calibration` from `eye_watcher.calibration` (Task 2)
- Produces: `Renderer(image_path: Path, calibration: Calibration, fullscreen: bool = False)`
  with `.draw(left_pupil: tuple[float, float], right_pupil: tuple[float, float]) -> None`
  and `.close() -> None` — used by Task 11 (`app.py`).

No automated tests — a real display is required. Verify manually per Step 2.

- [ ] **Step 1: Write the implementation**

`eye_watcher/renderer.py`:
```python
from pathlib import Path

import pygame

from eye_watcher.calibration import Calibration


class Renderer:
    def __init__(self, image_path: Path, calibration: Calibration, fullscreen: bool = False):
        pygame.init()
        self.image = pygame.image.load(str(image_path)).convert()
        width, height = self.image.get_size()
        flags = pygame.FULLSCREEN if fullscreen else 0
        self.screen = pygame.display.set_mode((width, height), flags)
        pygame.display.set_caption("Jeff Is Watching")
        self.calibration = calibration
        self.pupil_radius = min(calibration.left.radius, calibration.right.radius) * 0.35

    def draw(self, left_pupil: tuple[float, float], right_pupil: tuple[float, float]) -> None:
        self.screen.blit(self.image, (0, 0))
        pygame.draw.circle(self.screen, (20, 20, 20), (int(left_pupil[0]), int(left_pupil[1])), int(self.pupil_radius))
        pygame.draw.circle(self.screen, (20, 20, 20), (int(right_pupil[0]), int(right_pupil[1])), int(self.pupil_radius))
        pygame.display.flip()

    def close(self) -> None:
        pygame.quit()
```

- [ ] **Step 2: Verify manually**

Requires `assets/jeff.jpg` to exist (see Task 12) and a calibration file. If you
don't have real calibration yet, use placeholder values matching your test image's
size:
```bash
python -c "
import time
from pathlib import Path
from eye_watcher.calibration import Calibration, EyeCalibration
from eye_watcher.renderer import Renderer

cal = Calibration(
    left=EyeCalibration(center_x=200.0, center_y=250.0, radius=20.0),
    right=EyeCalibration(center_x=280.0, center_y=250.0, radius=20.0),
)
renderer = Renderer(image_path=Path('assets/jeff.jpg'), calibration=cal, fullscreen=False)
try:
    for i in range(100):
        offset = 10 * ((i % 40) - 20) / 20
        renderer.draw((cal.left.center_x + offset, cal.left.center_y), (cal.right.center_x + offset, cal.right.center_y))
        time.sleep(0.03)
finally:
    renderer.close()
"
```
Expected: a window opens showing the base image with two dark circles sweeping
left-right across the eye positions.

- [ ] **Step 3: Commit**

```bash
git add eye_watcher/renderer.py
git commit -m "feat: add pygame renderer"
```

---

### Task 9: Audio player

**Files:**
- Create: `eye_watcher/audio_player.py`

**Interfaces:**
- Consumes: nothing
- Produces: `AudioPlayer()` with `.play(clip_path: Path) -> None` — used by Task 11 (`app.py`).

No automated tests — a real audio device is required. Verify manually per Step 2.

- [ ] **Step 1: Write the implementation**

`eye_watcher/audio_player.py`:
```python
from pathlib import Path

import pygame


class AudioPlayer:
    def __init__(self):
        pygame.mixer.init()
        self._channel: pygame.mixer.Channel | None = None

    def play(self, clip_path: Path) -> None:
        if self._channel is not None and self._channel.get_busy():
            return
        sound = pygame.mixer.Sound(str(clip_path))
        self._channel = sound.play()
```

- [ ] **Step 2: Verify manually**

With any short `.wav`/`.mp3` file at hand:
```bash
python -c "
import time
from pathlib import Path
from eye_watcher.audio_player import AudioPlayer

player = AudioPlayer()
player.play(Path('/path/to/a/test/clip.wav'))
time.sleep(3)
"
```
Expected: the clip plays through your speakers. Also confirm calling `.play()`
again immediately while it's still playing does not overlap/stutter.

- [ ] **Step 3: Commit**

```bash
git add eye_watcher/audio_player.py
git commit -m "feat: add audio player"
```

---

### Task 10: Calibration tool

**Files:**
- Create: `tools/calibrate.py`

**Interfaces:**
- Consumes: `Calibration`, `EyeCalibration`, `save_calibration` from `eye_watcher.calibration` (Task 2)
- Produces: a `calibration.json` file on disk, consumed by Task 11 (`app.py`) via `load_calibration`.

No automated tests — this is an interactive click tool requiring a display and
mouse input. Verify manually per Step 2.

- [ ] **Step 1: Write the implementation**

`tools/calibrate.py`:
```python
import argparse
import sys
from pathlib import Path

import cv2

from eye_watcher.calibration import Calibration, EyeCalibration, save_calibration

POINT_LABELS = [
    "Click LEFT eye CENTER",
    "Click LEFT eye EDGE (sets radius)",
    "Click RIGHT eye CENTER",
    "Click RIGHT eye EDGE (sets radius)",
]


def _collect_points(image_path: Path) -> list[tuple[int, int]]:
    image = cv2.imread(str(image_path))
    if image is None:
        raise FileNotFoundError(f"Could not load image: {image_path}")

    points: list[tuple[int, int]] = []
    window = "Calibrate (click 4 points, q to quit)"

    def on_click(event, x, y, flags, userdata):
        if event == cv2.EVENT_LBUTTONDOWN:
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

    cv2.destroyWindow(window)
    return points


def _distance(a: tuple[int, int], b: tuple[int, int]) -> float:
    return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5


def main() -> None:
    parser = argparse.ArgumentParser(description="Click eye centers/edges to build calibration.json")
    parser.add_argument("image", type=Path, help="Path to the base Jeff photo")
    parser.add_argument("--output", type=Path, default=Path("calibration.json"))
    args = parser.parse_args()

    left_center, left_edge, right_center, right_edge = _collect_points(args.image)

    calibration = Calibration(
        left=EyeCalibration(
            center_x=left_center[0], center_y=left_center[1],
            radius=_distance(left_center, left_edge),
        ),
        right=EyeCalibration(
            center_x=right_center[0], center_y=right_center[1],
            radius=_distance(right_center, right_edge),
        ),
    )
    save_calibration(args.output, calibration)
    print(f"Saved calibration to {args.output}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Verify manually**

Requires `assets/jeff.jpg` (see Task 12):
```bash
python tools/calibrate.py assets/jeff.jpg
```
Expected: a window opens on the image; click left-eye-center, left-eye-edge,
right-eye-center, right-eye-edge in that order (each prompt updates the on-screen
label); after the 4th click the window closes and `calibration.json` is written.
Open it and confirm the `center_x`/`center_y`/`radius` values look sane relative
to where you actually clicked on the eyes.

- [ ] **Step 3: Commit**

```bash
git add tools/calibrate.py
git commit -m "feat: add interactive calibration tool"
```

---

### Task 11: App wiring and CLI

**Files:**
- Create: `eye_watcher/app.py`
- Create: `main.py`
- Test: `tests/test_app_cli.py`

**Interfaces:**
- Consumes: everything from Tasks 2-9 (`load_calibration`, `PupilAnimator`, `idle_offset`,
  `VisitorStateMachine`, `ClipLibrary`, `FaceTracker`, `Renderer`, `AudioPlayer`)
- Produces: `parse_args(argv: list[str] | None = None) -> argparse.Namespace` (unit tested)
  and `main(argv: list[str] | None = None) -> None` (the app entry point, manually verified).

- [ ] **Step 1: Write the failing test for argument parsing**

`tests/test_app_cli.py`:
```python
from eye_watcher.app import parse_args


def test_parse_args_defaults():
    args = parse_args([])
    assert args.fullscreen is False
    assert args.debug is False
    assert args.camera_index == 0
    assert args.cooldown == 60.0
    assert args.smoothing_alpha == 0.3


def test_parse_args_overrides():
    args = parse_args(["--fullscreen", "--debug", "--camera-index", "2", "--cooldown", "10"])
    assert args.fullscreen is True
    assert args.debug is True
    assert args.camera_index == 2
    assert args.cooldown == 10.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_app_cli.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'eye_watcher.app'`

- [ ] **Step 3: Write the implementation**

`eye_watcher/app.py`:
```python
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
```

`main.py`:
```python
from eye_watcher.app import main

if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_app_cli.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Run the full test suite**

Run: `pytest -v`
Expected: all tests across every task pass.

- [ ] **Step 6: Commit**

```bash
git add eye_watcher/app.py main.py tests/test_app_cli.py
git commit -m "feat: wire app loop and CLI"
```

---

### Task 12: Assets, sounds, and end-to-end verification

**Files:**
- Create: `assets/README.md`
- Create: `sounds/README.md`

**Interfaces:**
- Consumes: the complete app from Task 11
- Produces: a working end-to-end demo on this dev machine

- [ ] **Step 1: Add asset/sound folder instructions**

`assets/README.md`:
```markdown
# assets/

Put a front-facing photo of Jeff Goldblum here as `jeff.jpg`. A pose with both
eyes clearly visible and facing roughly toward the camera works best for a
convincing pupil-tracking effect.
```

`sounds/README.md`:
```markdown
# sounds/

Drop `.wav` or `.mp3` clips here. One is chosen at random (never repeating the
previous pick back-to-back) each time a new visitor is detected. Source your own
clips — the app does not fetch or bundle any audio.
```

- [ ] **Step 2: Commit**

```bash
git add assets/README.md sounds/README.md
git commit -m "docs: add asset and sound folder instructions"
```

- [ ] **Step 3: Manual end-to-end verification**

With `assets/jeff.jpg` in place, `calibration.json` generated via
`python tools/calibrate.py assets/jeff.jpg`, and at least one clip in `sounds/`:

```bash
python main.py --debug
```

Expected:
1. A windowed view of the Jeff photo appears alongside the debug camera overlay.
2. Walking into camera view makes the pupils turn to track your face within a
   second or two, smoothly (not twitchy).
3. The first time you appear, a random sound clip plays once.
4. Stepping out and back in within 60 seconds does not replay a sound; waiting
   over 60 seconds before returning does.
5. Moving out of frame entirely returns the pupils to a slow idle drift.

Then confirm the same command with `--fullscreen` fills the screen correctly —
this is the mode the Pi deployment will use.

---

## Later: Porting to the Raspberry Pi

Not part of this plan's scope, but the codebase is ready for it: install the
same `requirements.txt` on the Pi, swap `--camera-index` for the Pi Camera
Module's index (or adjust `FaceTracker` to use `picamera2` if the Camera
Module isn't exposed as a `cv2.VideoCapture` index on your Pi OS version), copy
over `assets/`, `sounds/`, and `calibration.json`, and run
`python main.py --fullscreen` at boot (e.g. via a systemd service or autostart
entry).

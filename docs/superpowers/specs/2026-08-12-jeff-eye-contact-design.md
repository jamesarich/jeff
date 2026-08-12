# Jeff Is Watching You: Eye-Contact Edition — Design

## Summary

A physical novelty display (prototyped on a laptop, deployed on a Raspberry Pi) that
shows a photo of Jeff Goldblum whose eyes track whoever is looking at it, animating
the classic "Jeff Goldblum is watching you poop" meme into a real eye-contact effect.
A face is detected via camera, the pupils are redrawn each frame to point at it, and
a random Jeff Goldblum audio clip plays the first time someone comes into view.

## Hardware

Prototype: this development machine, using its USB webcam and a windowed display.

Deployment target (Raspberry Pi):

| Part | Choice | Why |
|---|---|---|
| Board | Raspberry Pi 4 (4GB) or Pi 5 | Enough CPU headroom for real-time face tracking. |
| Camera | Raspberry Pi Camera Module 3 (CSI) | Lower CPU overhead than USB, easy discreet mount. |
| Display | Existing bare monitor, via HDMI | No new purchase. |
| Storage | 32GB+ microSD or USB SSD boot | OS + app. |
| Audio out | USB/3.5mm speaker or monitor's built-in speakers | Plays detection clips. |
| Power | Official Pi USB-C supply | Avoids brownouts under CV load. |
| Mounting | Small clip/mount near top-center of the monitor | Aligns the camera's view with where Jeff's eyes appear on screen. |

Same Python codebase runs on both; only the camera source and windowed-vs-fullscreen
config differ.

## Software architecture

**Stack:** Python, OpenCV (camera capture), MediaPipe Face Landmarker (face/eye
tracking), Pygame (rendering + audio).

**Data flow**, entirely in-process, nothing leaves the machine:

```
camera → OpenCV frame → MediaPipe face landmarks
                               │
                   face found? ├─ no  → IDLE state (pupils centered/drift, no sound)
                               └─ yes → compute gaze target (x, y)
                                          │
                              IDLE→WATCHING transition? → trigger random sound (with cooldown)
                                          │
                              smooth pupil position (EMA) → Pygame draws frame
```

A single config value controls windowed (dev) vs. fullscreen kiosk (Pi) — no code
branching needed beyond that.

## Eye-tracking & animation

- **Base image:** a Jeff Goldblum photo (user-supplied), front-facing enough for
  believable pupil movement.
- **Calibration:** a one-time setup script where the user clicks each eye's center
  and iris radius on the base image; saved as config alongside the image.
- **Gaze mapping:** MediaPipe's face position/angle maps to a target pupil offset,
  clamped to each eye's radius so pupils never leave the sclera. Both eyes move
  together (parallel gaze).
- **Smoothing:** pupil position is an exponential moving average of the raw target,
  not a direct snap — removes per-frame jitter from landmark detection.
- **Multiple faces:** track the largest/closest face in frame; ignore the rest.
- **Frame rate:** 10-15fps tracking is sufficient and keeps Pi CPU load low.

## Detection behavior & audio

- **States:** `IDLE` (no face — pupils centered or slowly drifting) and `WATCHING`
  (face detected — pupils track it).
- **Trigger:** the `IDLE → WATCHING` transition ("new visitor") plays one random
  clip from a local `sounds/` folder. A cooldown (default 60s) prevents re-triggering
  from brief in-frame movement.
- **Clip sourcing:** out of scope for this build — the user supplies their own
  `.wav`/`.mp3` files in `sounds/` (ripped from movies they own, self-recorded
  quotes, etc.). The app only requires that the folder contain playable audio files.
- **Playback:** one clip per trigger; no overlapping playback.

## Privacy

- **Strict default:** camera frames exist only in memory for the current frame's
  processing and are discarded immediately after. No video or image is ever written
  to disk or sent over a network, on the dev machine or the Pi.
- **Debug preview (opt-in, local only):** a `--debug` flag opens a local OpenCV
  window showing the live feed with tracked landmarks overlaid, for tuning during
  development. Off by default; never networked; does not record.

## Testing / bring-up plan

1. Prototype fully on the dev machine with the USB webcam, windowed display.
2. Tune calibration, smoothing, and detection thresholds against the real image.
3. Verify `--debug` overlay lines up tracked landmarks with actual eye position.
4. Verify IDLE/WATCHING transition and cooldown behave correctly with a person
   walking in and out of frame.
5. Port to the Pi: swap camera source to the Camera Module, switch to fullscreen
   kiosk config, verify frame rate and audio output on target hardware.

## Out of scope (for now)

- Head/face rotation or parallax (pupils-only tracking for v1).
- Cloud/network features of any kind.
- Sourcing or clearing rights on audio clips (user's responsibility).

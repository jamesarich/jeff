# Jeff Is Watching You: Eye-Contact Edition

An animated eye-contact version of the "Jeff Goldblum is watching you poop" meme.
A photo of Jeff Goldblum tracks your face with its eyes via camera, and plays a
random sound clip the first time you come into view.

## Setup

1. `pip install -r requirements.txt`
2. Download the face landmark model mediapipe needs:
   ```bash
   mkdir -p models
   curl -sL -o models/face_landmarker.task \
     https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task
   ```
3. Add a front-facing photo of Jeff Goldblum at `assets/jeff.jpg` (see `assets/README.md`).
4. Run `python tools/calibrate.py assets/jeff.jpg` and click the 4 requested points
   to generate `calibration.json`.
5. Add a few `.wav`/`.mp3` clips to `sounds/` (see `sounds/README.md`).
6. Run `python main.py` (add `--debug` to see the tracking overlay, `--fullscreen`
   for kiosk mode, `--camera-index N` to pick a different camera).

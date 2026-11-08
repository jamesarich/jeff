import {
  Blinker,
  ClipPicker,
  GazeHold,
  NOSE_TIP_LANDMARK_INDEX,
  PupilAnimator,
  REFERENCE_FPS,
  VisitorStateMachine,
  landmarkToOffset,
  largestFace,
  scleraGeometry,
} from "./logic.js";

const TASKS_VISION = "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@1.2.2";
const MODEL_URL =
  "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task";

const SCLERA_COLOR = "rgb(245, 240, 232)";
const PUPIL_COLOR = "rgb(20, 20, 20)";
const COOLDOWN_SECONDS = 60;
const DETECT_INTERVAL_MS = 1000 / REFERENCE_FPS;
const MIRROR_KEY = "jeff.mirror";

const canvas = document.getElementById("stage");
const ctx = canvas.getContext("2d", { alpha: false });
const overlay = document.getElementById("overlay");
const startButton = document.getElementById("start");
const controls = document.getElementById("controls");
const mirrorButton = document.getElementById("mirror");
const fullscreenButton = document.getElementById("fullscreen");
const statusEl = document.getElementById("status");
const video = document.getElementById("camera");

const setStatus = (text) => {
  statusEl.textContent = text;
};

// A front camera sees the visitor the way another person would, so a visitor
// who steps to their right drifts left in the frame. Mirroring undoes that so
// the pupils follow the visitor instead of fleeing them.
let mirror = (() => {
  try {
    const saved = localStorage.getItem(MIRROR_KEY);
    return saved === null ? true : saved === "1";
  } catch {
    return true;
  }
})();

function renderMirrorButton() {
  mirrorButton.setAttribute("aria-pressed", String(mirror));
}

function toggleMirror() {
  mirror = !mirror;
  renderMirrorButton();
  try {
    localStorage.setItem(MIRROR_KEY, mirror ? "1" : "0");
  } catch {
    // Per-viewer convenience only; fine without storage.
  }
}

function toggleFullscreen() {
  if (document.fullscreenElement) {
    document.exitFullscreen?.();
  } else {
    document.documentElement.requestFullscreen?.().catch(() => {});
  }
}

async function loadJson(path) {
  const res = await fetch(path);
  if (!res.ok) throw new Error(`${path}: HTTP ${res.status}`);
  return res.json();
}

function loadImage(src) {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => resolve(img);
    img.onerror = () => reject(new Error(`could not load ${src}`));
    img.src = src;
  });
}

class Renderer {
  constructor(image, calibration) {
    this.image = image;
    this.calibration = calibration;
    canvas.width = image.naturalWidth;
    canvas.height = image.naturalHeight;
    this.eyes = [scleraGeometry(calibration.left), scleraGeometry(calibration.right)];
    this._lastKey = null;
  }

  _drawEye(eye, pupil, openness) {
    if (openness <= 0.1) return; // lid closed: the photo's own eye shows through
    const height = Math.max(2, Math.floor(eye.openRy * openness) * 2);
    ctx.save();
    ctx.beginPath();
    ctx.rect(eye.cx - eye.rx, eye.cy - height / 2, eye.rx * 2, height);
    ctx.clip();
    ctx.fillStyle = SCLERA_COLOR;
    ctx.beginPath();
    ctx.ellipse(eye.cx, eye.cy, eye.rx, height / 2, 0, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = PUPIL_COLOR;
    ctx.beginPath();
    ctx.arc(pupil[0], pupil[1], eye.pupilRadius, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();
  }

  draw(leftPupil, rightPupil, blink = 0) {
    const left = [Math.round(leftPupil[0]), Math.round(leftPupil[1])];
    const right = [Math.round(rightPupil[0]), Math.round(rightPupil[1])];
    const openness = 1 - blink;
    const key = `${left}|${right}|${openness.toFixed(2)}`;
    if (key === this._lastKey) return;
    this._lastKey = key;
    ctx.drawImage(this.image, 0, 0);
    this._drawEye(this.eyes[0], left, openness);
    this._drawEye(this.eyes[1], right, openness);
  }
}

class Greeter {
  constructor(audioContext, buffers) {
    this.audioContext = audioContext;
    this.picker = new ClipPicker(buffers);
  }

  static async load(audioContext, urls) {
    const buffers = await Promise.all(
      urls.map(async (url) => {
        try {
          const res = await fetch(url);
          if (!res.ok) return null;
          return await audioContext.decodeAudioData(await res.arrayBuffer());
        } catch {
          return null;
        }
      }),
    );
    return new Greeter(audioContext, buffers.filter(Boolean));
  }

  play() {
    const buffer = this.picker.pick();
    if (!buffer) return;
    const source = this.audioContext.createBufferSource();
    source.buffer = buffer;
    source.connect(this.audioContext.destination);
    source.start();
  }
}

async function openCamera() {
  const stream = await navigator.mediaDevices.getUserMedia({
    audio: false,
    video: { facingMode: "user", width: { ideal: 640 }, height: { ideal: 480 } },
  });
  video.srcObject = stream;
  await video.play();
  return stream;
}

async function createLandmarker() {
  const { FaceLandmarker, FilesetResolver } = await import(`${TASKS_VISION}/vision_bundle.mjs`);
  const fileset = await FilesetResolver.forVisionTasks(`${TASKS_VISION}/wasm`);
  const options = (delegate) => ({
    baseOptions: { modelAssetPath: MODEL_URL, delegate },
    runningMode: "VIDEO",
    numFaces: 2,
  });
  try {
    return await FaceLandmarker.createFromOptions(fileset, options("GPU"));
  } catch {
    return await FaceLandmarker.createFromOptions(fileset, options("CPU"));
  }
}

async function requestWakeLock() {
  try {
    const lock = await navigator.wakeLock?.request("screen");
    document.addEventListener("visibilitychange", async () => {
      if (document.visibilityState === "visible" && lock?.released) {
        await navigator.wakeLock?.request("screen").catch(() => {});
      }
    });
  } catch {
    // Optional nicety.
  }
}

function run({ renderer, landmarker, greeter }) {
  const animator = new PupilAnimator(renderer.calibration, 0.3);
  const gazeHold = new GazeHold();
  const blinker = new Blinker();
  const visitors = new VisitorStateMachine(COOLDOWN_SECONDS);

  let target = [0, 0];
  let lastDetectMs = -Infinity;
  let lastVideoTimeMs = -1;
  let lastFrameMs = performance.now();

  const frame = (nowMs) => {
    const now = nowMs / 1000;
    const dt = Math.min(0.25, (nowMs - lastFrameMs) / 1000);
    lastFrameMs = nowMs;

    if (nowMs - lastDetectMs >= DETECT_INTERVAL_MS && video.readyState >= 2) {
      lastDetectMs = nowMs;
      // detectForVideo wants strictly increasing timestamps; a repeated video
      // frame would otherwise be rejected.
      const videoTimeMs = Math.max(Math.floor(video.currentTime * 1000), lastVideoTimeMs + 1);
      lastVideoTimeMs = videoTimeMs;
      let offset = null;
      try {
        const result = landmarker.detectForVideo(video, videoTimeMs);
        if (result.faceLandmarks.length > 0) {
          const nose = largestFace(result.faceLandmarks)[NOSE_TIP_LANDMARK_INDEX];
          offset = landmarkToOffset(nose.x, nose.y, mirror);
        }
      } catch (err) {
        console.warn("detect failed", err);
      }
      target = gazeHold.update(offset, now);
      if (visitors.update(offset !== null, now)) greeter.play();
      document.body.dataset.watching = String(visitors.watching);
    } else if (!visitors.watching) {
      target = gazeHold.update(null, now);
    }

    const [left, right] = animator.update(target[0], target[1], dt);
    renderer.draw(left, right, blinker.amount(now));
    requestAnimationFrame(frame);
  };
  requestAnimationFrame(frame);
}

async function start() {
  startButton.disabled = true;
  overlay.hidden = true;
  controls.hidden = false;
  setStatus("asking for the camera…");

  // Audio must be unlocked inside the click, before any await.
  const audioContext = new (window.AudioContext || window.webkitAudioContext)();
  audioContext.resume().catch(() => {});

  try {
    const [, greeter, landmarker] = await Promise.all([
      openCamera().then(() => setStatus("loading face tracking…")),
      loadJson("sounds.json").then((manifest) => Greeter.load(audioContext, manifest.clips)),
      createLandmarker(),
    ]);
    setStatus("");
    requestWakeLock();
    run({ renderer: RENDERER, landmarker, greeter });
  } catch (err) {
    console.error(err);
    const denied = err?.name === "NotAllowedError" || err?.name === "SecurityError";
    const noCamera = err?.name === "NotFoundError" || err?.name === "OverconstrainedError";
    setStatus(
      denied
        ? "Camera blocked. Allow camera access for this site and reload."
        : noCamera
          ? "No camera found."
          : `Could not start: ${err?.message ?? err}`,
    );
    overlay.hidden = false;
    startButton.disabled = false;
  }
}

let RENDERER = null;

async function init() {
  renderMirrorButton();
  mirrorButton.addEventListener("click", toggleMirror);
  fullscreenButton.addEventListener("click", toggleFullscreen);
  document.addEventListener("keydown", (e) => {
    if (e.key === "m") toggleMirror();
    if (e.key === "f") toggleFullscreen();
  });

  try {
    const [image, calibration] = await Promise.all([loadImage("jeff.jpg"), loadJson("calibration.json")]);
    RENDERER = new Renderer(image, calibration);
    RENDERER.draw(...new PupilAnimator(calibration).update(0, 0));
  } catch (err) {
    console.error(err);
    setStatus(`Could not load the page assets: ${err.message}`);
    return;
  }

  if (!navigator.mediaDevices?.getUserMedia) {
    setStatus("This browser has no camera access. Jeff can only stare straight ahead.");
    startButton.disabled = true;
    return;
  }
  startButton.addEventListener("click", start);
}

init();

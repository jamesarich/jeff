// Pure tracking, eye and visitor logic. No DOM, no timers: callers pass time in
// seconds, so this runs unchanged under node tests and in the browser.

// Eye geometry as fractions of the calibrated eye radius. The renderer derives
// the sclera size from these so the pupil's travel always fits the opening.
export const HORIZONTAL_TRAVEL_FRACTION = 0.6;
export const VERTICAL_TRAVEL_FRACTION = 0.35;
export const PUPIL_RADIUS_FRACTION = 0.35;
export const SCLERA_MARGIN = 1.05;

// Detection flickers off for a few frames whenever the visitor moves; neither
// the greeting nor the gaze treats that as the visitor leaving.
export const FACE_LOST_GRACE_SECONDS = 2.0;

// The Python app smooths once per frame at this rate; the browser matches it
// regardless of its own frame rate.
export const REFERENCE_FPS = 15;

export const NOSE_TIP_LANDMARK_INDEX = 1;

const clampUnit = (v) => Math.max(-1, Math.min(1, v));

export function landmarkToOffset(normX, normY, mirror) {
  const dx = clampUnit((normX - 0.5) / 0.5);
  const dy = clampUnit((normY - 0.5) / 0.5);
  return { dx: mirror ? -dx : dx, dy };
}

export function largestFace(faces) {
  if (faces.length === 1) return faces[0];
  const area = (landmarks) => {
    let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
    for (const p of landmarks) {
      if (p.x < minX) minX = p.x;
      if (p.x > maxX) maxX = p.x;
      if (p.y < minY) minY = p.y;
      if (p.y > maxY) maxY = p.y;
    }
    return (maxX - minX) * (maxY - minY);
  };
  let best = faces[0];
  let bestArea = area(best);
  for (const face of faces.slice(1)) {
    const a = area(face);
    if (a > bestArea) {
      best = face;
      bestArea = a;
    }
  }
  return best;
}

export function idleOffset(t) {
  return [0.3 * Math.sin(t * 0.5), 0.15 * Math.sin(t * 0.3)];
}

function clampToUnitCircle(dx, dy) {
  const magnitude = Math.hypot(dx, dy);
  return magnitude <= 1 ? [dx, dy] : [dx / magnitude, dy / magnitude];
}

function pupilPoint(eye, dx, dy) {
  return [
    eye.center_x + dx * eye.radius * HORIZONTAL_TRAVEL_FRACTION,
    eye.center_y + dy * eye.radius * VERTICAL_TRAVEL_FRACTION,
  ];
}

export function scleraGeometry(eye) {
  return {
    cx: Math.floor(eye.center_x),
    cy: Math.floor(eye.center_y),
    rx: Math.floor(eye.radius * (HORIZONTAL_TRAVEL_FRACTION + PUPIL_RADIUS_FRACTION) * SCLERA_MARGIN),
    openRy: Math.floor(eye.radius * (VERTICAL_TRAVEL_FRACTION + PUPIL_RADIUS_FRACTION) * SCLERA_MARGIN),
    pupilRadius: Math.floor(eye.radius * PUPIL_RADIUS_FRACTION),
  };
}

export class GazeHold {
  constructor(holdSeconds = FACE_LOST_GRACE_SECONDS) {
    this.holdSeconds = holdSeconds;
    this._last = null;
  }

  update(offset, now) {
    if (offset) {
      this._last = { dx: offset.dx, dy: offset.dy, seen: now };
      return [offset.dx, offset.dy];
    }
    if (this._last && now - this._last.seen < this.holdSeconds) {
      return [this._last.dx, this._last.dy];
    }
    return idleOffset(now);
  }
}

export class Blinker {
  constructor(random = Math.random, minInterval = 3, maxInterval = 7, duration = 0.2) {
    this._random = random;
    this.minInterval = minInterval;
    this.maxInterval = maxInterval;
    this.duration = duration;
    this._next = null;
  }

  _schedule(now) {
    this._next = now + this.minInterval + this._random() * (this.maxInterval - this.minInterval);
  }

  amount(now) {
    if (this._next === null) {
      this._schedule(now);
      return 0;
    }
    if (now < this._next) return 0;
    const progress = (now - this._next) / this.duration;
    if (progress >= 1) {
      this._schedule(now);
      return 0;
    }
    return 1 - Math.abs(2 * progress - 1);
  }
}

export class PupilAnimator {
  constructor(calibration, smoothingAlpha = 0.3) {
    this.calibration = calibration;
    this.smoothingAlpha = smoothingAlpha;
    this._dx = 0;
    this._dy = 0;
  }

  update(targetDx, targetDy, dtSeconds = 1 / REFERENCE_FPS) {
    const alpha = 1 - Math.pow(1 - this.smoothingAlpha, dtSeconds * REFERENCE_FPS);
    this._dx += alpha * (targetDx - this._dx);
    this._dy += alpha * (targetDy - this._dy);
    const [dx, dy] = clampToUnitCircle(this._dx, this._dy);
    return [pupilPoint(this.calibration.left, dx, dy), pupilPoint(this.calibration.right, dx, dy)];
  }
}

export class VisitorStateMachine {
  constructor(cooldownSeconds = 60, lostGraceSeconds = FACE_LOST_GRACE_SECONDS) {
    this.cooldownSeconds = cooldownSeconds;
    this.lostGraceSeconds = lostGraceSeconds;
    this.watching = false;
    this._lastTrigger = null;
    this._lastSeen = null;
  }

  update(faceFound, now) {
    let triggered = false;
    if (faceFound) {
      this._lastSeen = now;
      if (!this.watching) {
        const cooldownElapsed = this._lastTrigger === null || now - this._lastTrigger >= this.cooldownSeconds;
        if (cooldownElapsed) {
          triggered = true;
          this._lastTrigger = now;
        }
      }
      this.watching = true;
    } else if (this.watching) {
      if (this._lastSeen === null || now - this._lastSeen >= this.lostGraceSeconds) {
        this.watching = false;
      }
    }
    return triggered;
  }
}

export class ClipPicker {
  constructor(clips, random = Math.random) {
    this._clips = [...clips];
    this._random = random;
    this._last = null;
  }

  pick() {
    let available = this._clips;
    if (available.length === 0) return null;
    if (available.length > 1 && this._last !== null) {
      available = available.filter((c) => c !== this._last);
    }
    const choice = available[Math.floor(this._random() * available.length)];
    this._last = choice;
    return choice;
  }
}

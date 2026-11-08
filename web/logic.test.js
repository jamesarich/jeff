import { test } from "node:test";
import assert from "node:assert/strict";

import {
  Blinker,
  ClipPicker,
  GazeHold,
  PupilAnimator,
  VisitorStateMachine,
  idleOffset,
  landmarkToOffset,
  largestFace,
  scleraGeometry,
  FACE_LOST_GRACE_SECONDS,
} from "./logic.js";

const CAL = {
  left: { center_x: 200, center_y: 270, radius: 30 },
  right: { center_x: 350, center_y: 266, radius: 30 },
};

test("landmarkToOffset maps the frame centre to zero and clamps the edges", () => {
  assert.deepEqual(landmarkToOffset(0.5, 0.5, false), { dx: 0, dy: 0 });
  assert.deepEqual(landmarkToOffset(1.0, 0.0, false), { dx: 1, dy: -1 });
  assert.deepEqual(landmarkToOffset(1.5, -0.5, false), { dx: 1, dy: -1 });
});

test("landmarkToOffset mirror flips only the horizontal sense", () => {
  assert.deepEqual(landmarkToOffset(0.75, 0.25, true), { dx: -0.5, dy: -0.5 });
});

test("largestFace picks the face with the biggest bounding box", () => {
  const small = [{ x: 0.4, y: 0.4 }, { x: 0.5, y: 0.5 }];
  const big = [{ x: 0.1, y: 0.1 }, { x: 0.9, y: 0.9 }];
  assert.equal(largestFace([small, big]), big);
  assert.equal(largestFace([small]), small);
});

test("PupilAnimator converges on the target and stays inside the travel range", () => {
  const animator = new PupilAnimator(CAL, 0.3);
  let left;
  for (let i = 0; i < 60; i++) [left] = animator.update(1, 1, 1 / 15);
  assert.ok(Math.abs(left[0] - (200 + 30 * 0.6 / Math.SQRT2)) < 0.5);
  assert.ok(Math.abs(left[1] - (270 + 30 * 0.35 / Math.SQRT2)) < 0.5);
});

test("PupilAnimator smoothing is frame-rate independent", () => {
  const slow = new PupilAnimator(CAL, 0.3);
  const fast = new PupilAnimator(CAL, 0.3);
  const [slowLeft] = slow.update(1, 0, 1 / 15);
  let fastLeft;
  for (let i = 0; i < 4; i++) [fastLeft] = fast.update(1, 0, 1 / 60);
  assert.ok(Math.abs(slowLeft[0] - fastLeft[0]) < 0.01);
});

test("scleraGeometry covers the pupil's full travel plus margin", () => {
  const g = scleraGeometry(CAL.left);
  assert.equal(g.rx, Math.floor(30 * (0.6 + 0.35) * 1.05));
  assert.equal(g.openRy, Math.floor(30 * (0.35 + 0.35) * 1.05));
  assert.equal(g.pupilRadius, Math.floor(30 * 0.35));
});

test("GazeHold bridges a short dropout, then falls back to idle drift", () => {
  const hold = new GazeHold();
  assert.deepEqual(hold.update({ dx: 0.4, dy: -0.2 }, 10), [0.4, -0.2]);
  assert.deepEqual(hold.update(null, 10 + FACE_LOST_GRACE_SECONDS / 2), [0.4, -0.2]);
  const t = 10 + FACE_LOST_GRACE_SECONDS + 1;
  assert.deepEqual(hold.update(null, t), idleOffset(t));
});

test("Blinker is open between blinks and closes as a triangle wave", () => {
  const blinker = new Blinker(() => 0.5, 3, 7, 0.2);
  assert.equal(blinker.amount(0), 0);
  assert.equal(blinker.amount(4.9), 0);
  assert.ok(Math.abs(blinker.amount(5.1) - 1) < 1e-9);
  assert.equal(blinker.amount(5.25), 0);
  assert.equal(blinker.amount(9.9), 0);
});

test("VisitorStateMachine greets once per visit and honours the cooldown", () => {
  const sm = new VisitorStateMachine(60, 2);
  assert.equal(sm.update(true, 0), true);
  assert.equal(sm.update(true, 1), false);
  assert.equal(sm.update(false, 2), false);
  assert.equal(sm.update(true, 3), false);
  assert.equal(sm.update(false, 4), false);
  assert.equal(sm.update(false, 7), false);
  assert.equal(sm.watching, false);
  assert.equal(sm.update(true, 8), false);
  assert.equal(sm.update(false, 20), false);
  assert.equal(sm.update(false, 23), false);
  assert.equal(sm.update(true, 61), true);
});

test("ClipPicker never repeats back to back when it has a choice", () => {
  const picker = new ClipPicker(["a", "b", "c"], () => 0);
  let previous = picker.pick();
  for (let i = 0; i < 10; i++) {
    const next = picker.pick();
    assert.notEqual(next, previous);
    previous = next;
  }
  assert.equal(new ClipPicker([], () => 0).pick(), null);
  assert.equal(new ClipPicker(["only"], () => 0).pick(), "only");
});

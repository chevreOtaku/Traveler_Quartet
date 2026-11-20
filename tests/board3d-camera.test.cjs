"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const C = require("../examples/board3d/camera.js");

const walk = (player, from = 3, to = 7) => ({kind: "moved", player,
  data: {from, to, kind: "dice", travel: "walk", steps: to - from}});

test("a human's walk is followed, a computer's or a remote player's is not", () => {
  const seats = ["human", "computer", "remote", "computer"];
  assert.equal(C.followSeat(seats, walk(0), false), 0);
  assert.equal(C.followSeat(seats, walk(1), false), null);
  assert.equal(C.followSeat(seats, walk(2), false), null);
});

test("a table without a human is never followed", () => {
  const seats = ["computer", "computer", "computer", "computer"];
  for (let seat = 0; seat < 4; seat++) assert.equal(C.followSeat(seats, walk(seat), false), null);
});

test("reduced motion, a teleport or another event: no follow", () => {
  const seats = ["human", "computer"];
  assert.equal(C.followSeat(seats, walk(0), true), null);
  assert.equal(C.followSeat(seats, {...walk(0), data: {...walk(0).data, travel: "teleport", steps: null}}, false), null);
  assert.equal(C.followSeat(seats, {kind: "rolled", player: 0, data: {dice: [1, 2]}}, false), null);
  assert.equal(C.followSeat(undefined, walk(0), false), null);
});

test("the follow camera stands outside the ring, above the pawn, and looks at it", () => {
  for (const pawn of [[0, .16, 5], [5, .16, 0], [-5, .16, -5], [2, .16, -5]]) {
    const {position, target} = C.followView(pawn);
    assert.ok(Math.hypot(position[0], position[2]) > Math.hypot(pawn[0], pawn[2]), "outside the ring");
    assert.ok(position[1] > pawn[1] + 1, "above");
    assert.ok(Math.hypot(target[0] - pawn[0], target[2] - pawn[2]) < .5, "aimed at the pawn");
  }
});

test("the camera eases toward its goal and never overshoots", () => {
  const goal = [10, 0, 0];
  let current = [0, 0, 0];
  for (let i = 0; i < 30; i++) {
    const next = C.approach(current, goal, 1 / 60);
    assert.ok(next[0] > current[0] && next[0] <= goal[0]);
    current = next;
  }
  assert.deepEqual(C.approach([1, 1, 1], goal, 0), [1, 1, 1]);
});

test("the seat kinds of a snapshot are checked", () => {
  assert.ok(C.validSeats(["human", "computer"], 2));
  assert.ok(!C.validSeats(["human"], 2));
  assert.ok(!C.validSeats(["normal", "computer"], 2));
  assert.ok(!C.validSeats(undefined, 2));
});

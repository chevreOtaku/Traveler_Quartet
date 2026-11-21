"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const P = require("../examples/board3d/play.js");

const board = Array.from({length: 40}, (_, index) => ({index, name: `Square ${index}`}));

test("each legal action gets words, with the square's name when it has one", () => {
  assert.equal(P.actionLabel("roll", board), "Roll the dice");
  assert.equal(P.actionLabel("build:12", board), "Build on Square 12");
  assert.equal(P.actionLabel("mortgage:3", board), "Mortgage Square 3");
  assert.equal(P.actionLabel("raise:25", board), "Raise the auction by 25");
  assert.equal(P.actionLabel("bid:40", board), "Sealed bid: 40 gold");
  assert.equal(P.actionLabel("curse:2", board), "Curse player 2");
});

test("an action it does not know is shown as the engine wrote it, never dropped", () => {
  assert.equal(P.actionLabel("something_new:1", board), "something_new:1");
  assert.equal(P.actionLabel("build:77", board), "Build on square 77");
});

test("the tab's seat comes from the ONE token the server gave it", () => {
  assert.deepEqual(P.humanSeat({abc: 0}), {token: "abc", seat: 0});
  assert.equal(P.humanSeat({}), null);
  assert.equal(P.humanSeat({a: 0, b: 2}), null);
  assert.equal(P.humanSeat(undefined), null);
  assert.equal(P.storageKey("g1"), "traveler-quartet:seat:g1");
});

test("a human in debt reads how much they owe and to whom; nobody else's debt is said as theirs", () => {
  const owing = (to, debtor = 0) => ({me: {seat: 0}, debt_context: {debtor, to, amount: 680}});
  assert.equal(P.debtWords(owing(1)), "You owe 680 gold to player 1.");
  assert.equal(P.debtWords(owing("bank")), "You owe 680 gold to the bank.");
  assert.equal(P.debtWords(owing("jackpot")), "You owe 680 gold to the jackpot.");
  assert.equal(P.debtWords(owing(1, 2)), "");
  assert.equal(P.debtWords({me: {seat: 0}}), "");
});

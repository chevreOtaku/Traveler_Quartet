"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const T = require("../examples/board3d/trade.js");

function board() {
  const squares = Array.from({length: 40}, (_, index) => ({index, name: `Square ${index}`, kind: "special", town: null,
    owner: null, buildings: 0}));
  for (const [index, town] of [[1, "brown"], [3, "brown"], [6, "sky"], [8, "sky"], [9, "sky"]])
    Object.assign(squares[index], {kind: "district", town});
  return squares;
}

function view({mine = [], theirs = [], negotiations = ["offer:1", "offer:2"], built = [], trade} = {}) {
  const squares = board();
  for (const i of mine) squares[i].owner = 0;
  for (const i of theirs) squares[i].owner = 1;
  for (const i of built) squares[i].buildings = 1;
  return {me: {seat: 0, cash: 500, cards: ["rope"]}, board: squares, negotiations, trade, your_turn: true};
}

function fakeMake() {
  // Like the DOM: `dataset` is a READ-ONLY property (only its entries can be set) -- a page that assigns it breaks.
  return () => {
    const element = {children: [], handlers: {}, value: "", textContent: "",
      append(...items) { this.children.push(...items); }, replaceChildren(...items) { this.children = [...items]; },
      addEventListener(kind, fn) { this.handlers[kind] = fn; }};
    const data = {};
    Object.defineProperty(element, "dataset", {get: () => data, enumerable: true});
    return element;
  };
}

function all(node) {
  return [node, ...node.children.flatMap(all)];
}

test("a side may hand over its districts, except those of a town with a building, and its other squares", () => {
  const v = view({mine: [1, 6, 12], theirs: [3, 8], built: [9]});
  v.board[12].kind = "portal";
  v.board[9].owner = 1;
  assert.deepEqual(T.tradable(v, 0), [1, 12]);
  assert.deepEqual(T.tradable(v, 1), [3]);
});

test("the contract is written as the engine reads it", () => {
  assert.equal(T.contract("offer", 1, {gold: 40}, {squares: [3]}), "offer:1:40:::0:3:");
  assert.equal(T.contract("offer", 2, {squares: [6, 8], cards: ["rope"]}, {gold: 120}), "offer:2:0:6,8:rope:120::");
  assert.equal(T.contract("counter", null, {squares: [3]}, {gold: 10}), "counter:0:3::10::");
});

test("which trade forms are open comes from the engine's negotiations only", () => {
  assert.deepEqual(T.forms(view()), [{kind: "offer", rivals: [1, 2]}]);
  assert.deepEqual(T.forms(view({negotiations: ["counter"]})), [{kind: "counter", rivals: []}]);
  assert.deepEqual(T.forms(view({negotiations: []})), []);
});

test("an offer waiting for the human is said in words, with the districts' names", () => {
  const trade = {proposer: 1, responder: 0, counters: 0,
    terms: {give_gold: 45, give_squares: [], give_cards: [], ask_gold: 0, ask_squares: [3], ask_cards: []}};
  assert.equal(T.offerWords(view({trade})), "Player 1 offers you 45 gold in exchange for Square 3.");
  assert.equal(T.offerWords(view()), "");
});

test("the offer form sends the contract built from what the human ticked and typed", () => {
  const sent = [];
  const v = view({mine: [1, 6], theirs: [3, 8]});
  const form = T.form(fakeMake(), v, {kind: "offer", rivals: [1, 2]}, action => sent.push(action));
  const nodes = all(form);
  const boxes = nodes.filter(n => n.type === "checkbox");
  assert.deepEqual(boxes.map(b => b.dataset), [{side: "give", square: "1"}, {side: "give", square: "6"},
    {side: "give", card: "rope"}, {side: "ask", square: "3"}, {side: "ask", square: "8"}]);
  nodes.find(n => n.name === "give_gold").value = "40";
  boxes[0].checked = true;
  boxes[3].checked = true;
  nodes.find(n => n.name === "send").handlers.click();
  assert.deepEqual(sent, ["offer:1:40:1::0:3:"]);
});

test("choosing another rival shows that rival's districts to ask for", () => {
  const v = view({mine: [1], theirs: [3]});
  v.board[8].owner = 2;
  const form = T.form(fakeMake(), v, {kind: "offer", rivals: [1, 2]}, () => {});
  const rival = all(form).find(n => n.name === "rival");
  assert.deepEqual(rival.children.map(o => o.value), ["1", "2"]);
  rival.value = "2";
  rival.handlers.change();
  const asked = all(form).filter(n => n.type === "checkbox" && n.dataset.side === "ask");
  assert.deepEqual(asked.map(b => b.dataset.square), ["8"]);
});

test("a counter-offer form has no rival to choose and sends a counter", () => {
  const sent = [];
  const trade = {proposer: 1, responder: 0, counters: 0,
    terms: {give_gold: 45, give_squares: [], give_cards: [], ask_gold: 0, ask_squares: [1], ask_cards: []}};
  const v = view({mine: [1], theirs: [3], negotiations: ["counter"], trade});
  const form = T.form(fakeMake(), v, {kind: "counter", rivals: []}, action => sent.push(action));
  const nodes = all(form);
  assert.equal(nodes.some(n => n.name === "rival"), false);
  assert.deepEqual(nodes.filter(n => n.dataset?.side === "ask").map(b => b.dataset.square), ["3"]);
  nodes.find(n => n.name === "ask_gold").value = "60";
  nodes.find(n => n.name === "send").handlers.click();
  assert.deepEqual(sent, ["counter:0:::60::"]);
});

test("a gold amount that is not a whole number of at least zero is sent as zero, never as text", () => {
  const sent = [];
  const form = T.form(fakeMake(), view({mine: [1], theirs: [3]}), {kind: "offer", rivals: [1]}, a => sent.push(a));
  const nodes = all(form);
  nodes.find(n => n.name === "give_gold").value = "-5";
  nodes.find(n => n.name === "ask_gold").value = "1:2";
  nodes.find(n => n.name === "send").handlers.click();
  assert.deepEqual(sent, ["offer:1:0:::0::"]);
});

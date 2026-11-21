"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const A = require("../examples/board3d/art.js");

const dir = path.join(__dirname, "..", "examples", "board3d", "art", "illustrations");
const read = name => JSON.parse(fs.readFileSync(path.join(dir, name), "utf8"));
const index = A.buildIndex(read("catalog.json"), read("web.json"), read("banner-crops.json"));

test("every square of the board has an arrival banner, and every file it names exists as a shipped WebP", () => {
  for (let square = 0; square < 40; square++) {
    const banner = A.squareBanner(index, square);
    assert.ok(banner, `square ${square} has no banner`);
    assert.match(banner.url, /^\/art\/illustrations\/[a-z_]+\/[a-z0-9-]+\.webp$/);
    assert.ok(fs.existsSync(path.join(dir, banner.url.replace("/art/illustrations/", ""))), banner.url);
  }
  assert.equal(A.squareBanner(index, 40), null);
});

test("a square has ITS place: a location before a deck emblem, and the start square its own scene", () => {
  assert.match(A.squareBanner(index, 0).url, /locations\/00-start-v1\.webp$/);
  assert.match(A.squareBanner(index, 1).url, /locations\/01-cabbage-row-v1\.webp$/);
  assert.match(A.squareBanner(index, 7).url, /symbols\/chance-emblem-v1\.webp$/);
});

test("the 4:1 banner uses the approved crop when there is one, a centred band otherwise", () => {
  assert.deepEqual(A.squareBanner(index, 1).rect, {x: 0, y: 0.06, width: 1, height: 0.5});
  assert.deepEqual(A.squareBanner(index, 6).rect, {x: 0, y: 0.25, width: 1, height: 0.5});
});

test("a crop rectangle becomes a CSS background that shows exactly that part, whatever the frame size", () => {
  assert.deepEqual(A.background({x: 0, y: 0.06, width: 1, height: 0.5}),
    {size: "100% auto", position: "0% 12%"});
  assert.deepEqual(A.background({x: 0.2, y: 0, width: 0.75, height: 1}), {size: "133.333% auto", position: "80% 0%"});
});

test("the banner never hides the pawn: on the far side (squares 20-29) it goes down, elsewhere up", () => {
  assert.equal(A.bannerSide(25), "bottom");
  for (const square of [0, 5, 10, 15, 19, 30, 39]) assert.equal(A.bannerSide(square), "top");
});

test("a drawn card shows its face; a KEPT card shows the common mask, never its face, whoever drew it", () => {
  const face = A.cardFace(index, {kind: "card", data: {card: "slime"}});
  assert.match(face.url, /chance\/chance-slime-v1\.webp$/);
  assert.equal(face.masked, false);
  const kept = A.cardFace(index, {kind: "card", data: {card: "a kept card"}});
  assert.match(kept.url, /card_backs\/kept-card-mask-v1\.webp$/);
  assert.equal(kept.masked, true);
  assert.equal(A.cardFace(index, {kind: "card", data: {card: "no-such-card"}}), null);
  assert.equal(A.cardFace(index, {kind: "moved", data: {}}), null);
});

test("without the art files the page still works: an empty index gives no banner and no card", () => {
  const empty = A.buildIndex(null, null, null);
  assert.equal(A.squareBanner(empty, 1), null);
  assert.equal(A.cardFace(empty, {kind: "card", data: {card: "slime"}}), null);
});

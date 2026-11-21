"use strict";
// The illustrations on the table (D57): which picture a square's arrival banner shows, how the approved 4:1 crop
// becomes a CSS background, which side of the screen keeps the pawn visible, and which face a drawn card shows. Pure:
// the page reads the catalogue, the WebP list and the crops, then asks this module. A KEPT card is only ever known as
// "a kept card" in the public journal: this module gives it the common mask and has no way to name its face.
globalThis.Board3DArt = (() => {
  const BASE = "/art/illustrations/";
  const KEPT = "a kept card", MASK = "kept-card-mask-v1";
  const CENTRED_BAND = {x: 0, y: 0.25, width: 1, height: 0.5};
  const SQUARE_ORDER = ["locations", "portals", "symbols"];

  function squaresOf(asset) {
    const listed = Array.isArray(asset.squares) ? asset.squares : [];
    return Number.isInteger(asset.square) ? [asset.square, ...listed] : listed;
  }

  function buildIndex(catalog, web, crops) {
    const files = new Map((web?.assets || []).map(a => [a.id, BASE + a.file]));
    const index = {squares: new Map(), cards: new Map(), mask: files.get(MASK) || null, crops: crops?.banner || {}};
    for (const category of SQUARE_ORDER)
      for (const asset of catalog?.assets || [])
        if (asset.category === category && files.has(asset.id))
          for (const square of squaresOf(asset))
            if (!index.squares.has(square)) index.squares.set(square, asset.id);
    for (const asset of catalog?.assets || [])
      if (asset.card_id && files.has(asset.id)) index.cards.set(asset.card_id, {id: asset.id, url: files.get(asset.id)});
    index.files = files;
    return index;
  }

  function squareBanner(index, square) {
    const id = index.squares.get(square);
    if (!id) return null;
    return {id, url: index.files.get(id), rect: index.crops[id] || CENTRED_BAND};
  }

  const percent = value => `${Number((value * 100).toFixed(3))}%`;

  // CSS places point p% of the image on point p% of the frame: showing [x, x+w] of the image needs p = x / (1 - w).
  function background(rect) {
    const at = (start, size) => (size >= 1 ? 0 : start / (1 - size));
    return {size: `${percent(1 / rect.width)} auto`, position: `${percent(at(rect.x, rect.width))} ${percent(at(rect.y, rect.height))}`};
  }

  // The board camera looks from the Start side: squares 20-29 are at the top of the screen.
  const bannerSide = square => (Math.floor(square / 10) === 2 ? "bottom" : "top");

  function cardFace(index, row) {
    if (row?.kind !== "card") return null;
    if (row.data?.card === KEPT) return index.mask ? {url: index.mask, masked: true} : null;
    const face = index.cards.get(row.data?.card);
    return face ? {url: face.url, masked: false} : null;
  }

  return {buildIndex, squareBanner, background, bannerSide, cardFace};
})();
if (typeof module !== "undefined") module.exports = globalThis.Board3DArt;

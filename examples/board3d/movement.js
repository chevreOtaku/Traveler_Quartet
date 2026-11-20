"use strict";
globalThis.Board3DMovement = (() => {
  const wrap = (index, size) => ((index % size) + size) % size;
  function movementSquares(event, size) {
    const d = event?.data;
    const validSquare = n => Number.isInteger(n) && n >= 0 && n < size;
    if (!Number.isInteger(size) || size < 1 || event?.kind !== "moved" || !d ||
        !validSquare(d.from) || !validSquare(d.to) ||
        !["dice", "card", "portal", "dungeon"].includes(d.kind))
      throw new Error("Invalid movement contract");
    if (d.travel === "teleport" && d.steps === null) return [];
    if (d.travel !== "walk" || !Number.isSafeInteger(d.steps) ||
        wrap(d.from + d.steps, size) !== d.to)
      throw new Error("Invalid movement steps or destination");
    return Array.from({length: Math.abs(d.steps)}, (_, i) => wrap(d.from + Math.sign(d.steps) * (i + 1), size));
  }
  function motionFrame(event, size, elapsedHops, reducedMotion) {
    const route = movementSquares(event, size), d = event.data;
    if (!Number.isFinite(elapsedHops) || elapsedHops < 0) throw new Error("Invalid movement time");
    if (reducedMotion || !route.length || elapsedHops >= route.length)
      return {from:d.to, to:d.to, progress:1, lift:0, done:true};
    const index = Math.floor(elapsedHops), progress = elapsedHops - index;
    return {from:index ? route[index - 1] : d.from, to:route[index], progress,
      lift:Math.sin(progress * Math.PI) * 0.12, done:false};
  }
  return {movementSquares, motionFrame};
})();
if (typeof module !== "undefined") module.exports = globalThis.Board3DMovement;

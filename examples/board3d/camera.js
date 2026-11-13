"use strict";
// Which view a move gets (D51, chevre 13/11): at a table WITHOUT a human, the whole board; when a HUMAN's pawn walks
// after a roll, the camera comes close and follows its hops, then goes back to the board. Pure functions only.
globalThis.Board3DCamera = (() => {
  const KINDS = ["human", "remote", "computer"];
  // Steep and close: the neighbours on the same square stay below the line of sight, and aiming a little ABOVE the
  // pawn puts it in the lower half of the screen, clear of the move panel (measured on a 1080p capture, 13/11).
  const FOLLOW = {distance: 1.25, height: 2.05, lookInside: .2, lookUp: .55};

  function validSeats(seats, players) {
    return Array.isArray(seats) && seats.length === players && seats.every(kind => KINDS.includes(kind));
  }

  function followSeat(seats, row, reducedMotion) {
    if (reducedMotion || row?.kind !== "moved" || row.data?.travel !== "walk") return null;
    return seats?.[row.player] === "human" ? row.player : null;
  }

  function followView(pawn) {
    const [x, y, z] = pawn, length = Math.hypot(x, z) || 1, out = [x / length, z / length];
    return {
      position: [x + out[0] * FOLLOW.distance, y + FOLLOW.height, z + out[1] * FOLLOW.distance],
      target: [x - out[0] * FOLLOW.lookInside, y + FOLLOW.lookUp, z - out[1] * FOLLOW.lookInside],
    };
  }

  function approach(current, goal, seconds, rate = 7) {
    const share = 1 - Math.exp(-rate * Math.max(0, seconds));
    return current.map((value, i) => value + (goal[i] - value) * share);
  }

  return {KINDS, FOLLOW, validSeats, followSeat, followView, approach};
})();
if (typeof module !== "undefined") module.exports = globalThis.Board3DCamera;

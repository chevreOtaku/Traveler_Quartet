"use strict";
// A human at the table (D51): the words on the buttons, and where the tab keeps its seat. The engine gives the legal
// actions; this module only names them -- it never decides which one is good.
globalThis.Board3DPlay = (() => {
  const SIMPLE = {
    roll: "Roll the dice", buy: "Buy this district", pass: "Do not buy", jump: "Take the portal", stay: "Stay here",
    pay_exit: "Pay to leave the dungeon", use_rope: "Use the rope", drop: "Leave the auction", accept: "Accept",
    refuse: "Refuse", bankrupt: "Declare bankruptcy",
  };
  const ON_SQUARE = {
    build: "Build on", sell: "Sell a building on", mortgage: "Mortgage", unmortgage: "Lift the mortgage on",
    share_stall: "Ask for a shared stall on",
  };

  function actionLabel(action, board) {
    const [name, argument] = String(action).split(":");
    if (SIMPLE[name]) return SIMPLE[name];
    if (ON_SQUARE[name]) return `${ON_SQUARE[name]} ${board?.[Number(argument)]?.name ?? `square ${argument}`}`;
    if (name === "raise") return `Raise the auction by ${argument}`;
    if (name === "bid") return `Sealed bid: ${argument} gold`;
    if (name === "curse") return `Curse player ${argument}`;
    return String(action);
  }

  function humanSeat(tokens) {
    const entries = Object.entries(tokens || {});
    if (entries.length !== 1 || !Number.isSafeInteger(entries[0][1])) return null;
    return {token: entries[0][0], seat: entries[0][1]};
  }

  const storageKey = game => `traveler-quartet:seat:${game}`;

  return {actionLabel, humanSeat, storageKey};
})();
if (typeof module !== "undefined") module.exports = globalThis.Board3DPlay;

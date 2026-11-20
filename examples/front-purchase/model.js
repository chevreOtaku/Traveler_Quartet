/* A presentation-only selector over engine-generated public snapshots. No game rules. */
"use strict";
globalThis.PurchaseScene = (() => {
  function freeze(value) {
    if (value && typeof value === "object") {
      Object.values(value).forEach(freeze);
      Object.freeze(value);
    }
    return value;
  }
  function create(fixtures, initialMode = "player") {
    freeze(fixtures);
    let phase = "initial", mode = "player";
    function setMode(next) {
      if (!["player", "stream"].includes(next)) throw new Error("Unknown presentation mode");
      mode = next;
    }
    setMode(initialMode);
    return {
      get state() { return fixtures[phase]; },
      get phase() { return phase; },
      get mode() { return mode; },
      setMode,
      reset() { phase = "initial"; },
      select(action) {
        if (mode !== "player" || phase !== "initial" || !["buy", "pass"].includes(action)) return false;
        phase = action;
        return true;
      }
    };
  }
  return {create};
})();

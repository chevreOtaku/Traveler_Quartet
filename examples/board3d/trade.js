"use strict";
// A human proposes or answers a TRADE (D21) from the 3D page. This module lists what each side may hand over, writes
// the engine's contract and says a waiting offer in words. The ENGINE judges every contract: the page never decides
// which trade is good, nor whether to trade.
globalThis.Board3DTrade = (() => {
  const RULE = "What each side receives must be worth between half and double what it gives.";

  function townBuilt(board, town) {
    return board.some(square => square.town === town && square.buildings > 0);
  }

  function tradable(view, seat) {
    return view.board.filter(sq => sq.owner === seat && (sq.kind !== "district" || !townBuilt(view.board, sq.town)))
      .map(sq => sq.index);
  }

  const fields = side => [side.gold || 0, (side.squares || []).join(","), (side.cards || []).join(",")];

  function contract(kind, to, give, ask) {
    const head = kind === "counter" ? ["counter"] : ["offer", to];
    return [...head, ...fields(give), ...fields(ask)].join(":");
  }

  function forms(view) {
    const open = view.negotiations || [];
    const rivals = open.filter(n => n.startsWith("offer:")).map(n => Number(n.split(":")[1]));
    return [...(rivals.length ? [{kind: "offer", rivals}] : []), ...(open.includes("counter") ? [{kind: "counter", rivals: []}] : [])];
  }

  function items(view, gold, squares, cards) {
    const parts = gold ? [`${gold} gold`] : [];
    parts.push(...squares.map(i => view.board[i]?.name ?? `square ${i}`), ...cards.map(card => `card ${card}`));
    return parts.join(", ") || "nothing";
  }

  function offerWords(view) {
    const t = view.trade;
    if (!t) return "";
    const s = t.terms, who = seat => seat === view.me.seat ? "you" : `player ${seat}`;
    return `Player ${t.proposer} offers ${who(t.responder)} ${items(view, s.give_gold, s.give_squares, s.give_cards)} ` +
      `in exchange for ${items(view, s.ask_gold, s.ask_squares, s.ask_cards)}.`;
  }

  function gold(input) {
    const text = String(input.value).trim();
    return /^\d+$/.test(text) ? Number(text) : 0;
  }

  function node(make, tag, props = {}, children = []) {
    const element = Object.assign(make(tag), props);
    element.append(...children);
    return element;
  }

  function box(make, side, key, value, label) {
    const input = node(make, "input", {type: "checkbox", checked: false});
    input.dataset.side = side;
    input.dataset[key] = String(value);
    return {input, label: node(make, "label", {textContent: ` ${label}`}, [input])};
  }

  function sideBoxes(make, view, side, squares, cards) {
    return [...squares.map(i => box(make, side, "square", i, view.board[i]?.name ?? `square ${i}`)),
            ...cards.map(card => box(make, side, "card", card, `card ${card}`))];
  }

  function picked(boxes, key) {
    return boxes.filter(b => b.input.checked && b.input.dataset[key] !== undefined).map(b => b.input.dataset[key]);
  }

  function form(make, view, open, send) {
    const counter = open.kind === "counter";
    const rival = counter ? null : node(make, "select", {name: "rival"},
      open.rivals.map(p => node(make, "option", {value: String(p), textContent: `Player ${p}`})));
    if (rival) rival.value = String(open.rivals[0]);
    const giveGold = node(make, "input", {type: "number", min: "0", step: "1", value: "0", name: "give_gold"});
    const askGold = node(make, "input", {type: "number", min: "0", step: "1", value: "0", name: "ask_gold"});
    const gives = sideBoxes(make, view, "give", tradable(view, view.me.seat), view.me.cards || []);
    const askList = node(make, "div", {className: "trade-ask"});
    let asks = [];
    const other = () => counter ? view.trade.proposer : Number(rival.value);
    const showAsks = () => {
      asks = sideBoxes(make, view, "ask", tradable(view, other()), []);
      askList.replaceChildren(...asks.map(b => b.label));
    };
    showAsks();
    rival?.addEventListener("change", showAsks);
    const sendButton = node(make, "button", {type: "button", name: "send",
      textContent: counter ? "Send this counter-offer" : "Propose this trade"});
    sendButton.addEventListener("click", () => send(contract(open.kind, counter ? null : other(),
      {gold: gold(giveGold), squares: picked(gives, "square"), cards: picked(gives, "card")},
      {gold: gold(askGold), squares: picked(asks, "square"), cards: []})));
    const title = node(make, "summary", {textContent: counter ? "Counter-offer" : "Propose a trade"});
    return node(make, "details", {className: "trade"}, [title, ...(rival ? [node(make, "label", {textContent: "With "}, [rival])] : []),
      node(make, "p", {textContent: "You give gold "}, [giveGold]), ...gives.map(b => b.label),
      node(make, "p", {textContent: "You ask gold "}, [askGold]), askList,
      node(make, "p", {className: "trade-rule", textContent: RULE}), sendButton]);
  }

  return {RULE, tradable, contract, forms, offerWords, form};
})();
if (typeof module !== "undefined") module.exports = globalThis.Board3DTrade;

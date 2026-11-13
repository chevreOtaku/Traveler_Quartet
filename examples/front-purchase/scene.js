"use strict";
const get = id => document.getElementById(id);
const initialMode = new URLSearchParams(location.search).get("mode") === "stream" ? "stream" : "player";
const scene = PurchaseScene.create(PURCHASE_FIXTURES, initialMode);
function render() {
  const state = scene.state, square = state.board[1], stream = scene.mode === "stream";
  document.body.dataset.mode = scene.mode;
  document.body.dataset.phase = scene.phase;
  get("playerMode").setAttribute("aria-pressed", String(!stream));
  get("streamMode").setAttribute("aria-pressed", String(stream));
  get("arrivalLabel").textContent = stream ? "PLAYER 0 HAS ARRIVED" : "YOU HAVE ARRIVED";
  get("modeLabel").textContent = stream ? "STREAM VIEW" : "PLAYER VIEW";
  state.players.forEach(p => { get(`cash${p.seat}`).textContent = p.cash; });
  get("price").textContent = square.price;
  get("rent").textContent = square.rent;
  get("buyPrice").textContent = `${square.price} G`;
  get("propertyName").textContent = square.name;
  const owner = square.owner === null ? "Unowned" : `Player ${square.owner}`;
  get("ledgerOwner").textContent = owner;
  get("squareOwner").textContent = owner;
  get("ownerBadge").textContent = square.owner === null ? "FOR SALE" : "PLAYER 0";
  get("decision").hidden = stream || scene.phase !== "initial";
  get("spectatorNote").hidden = !stream || scene.phase !== "initial";
  get("result").hidden = scene.phase === "initial";
  get("again").hidden = stream;
  get("buy").disabled = stream || scene.phase !== "initial";
  get("pass").disabled = stream || scene.phase !== "initial";
  get("arrivalNote").textContent = scene.phase === "buy" ? "One small plot. The start of a very big plan." :
    scene.phase === "pass" ? "Passed on. The district now goes to auction." : "An unowned district. A modest opportunity.";
  get("resultLabel").textContent = scene.phase === "buy" ? "PURCHASE CONFIRMED / DEMO" : "PASSED / DEMO";
  get("resultTitle").textContent = scene.phase === "buy" ? "Your empire starts small." : "Someone else's cabbage.";
  get("resultText").textContent = scene.phase === "buy" ?
    `Player 0 owns Cabbage Row. Gold remaining: ${state.players[0].cash} G. This is the end of the purchase demo.` :
    "The engine has opened an auction. Bidding is outside this visual study.";
  get("footerState").textContent = scene.phase === "initial" ? "A purchase scene, not a live game." : "Engine-generated outcome. Demo ends here.";
}
function choose(action) {
  if (scene.select(action)) render();
}
get("buy").addEventListener("click", () => choose("buy"));
get("pass").addEventListener("click", () => choose("pass"));
get("playerMode").addEventListener("click", () => { scene.setMode("player"); render(); });
get("streamMode").addEventListener("click", () => { scene.setMode("stream"); render(); });
for (const id of ["reset", "again"]) get(id).addEventListener("click", () => { scene.reset(); render(); });
render();

import {createScene} from "./scene.js";

const element = id => document.getElementById(id);
const replay=element("replay"), detail=element("detail"), status=element("status");
const motion=matchMedia("(prefers-reduced-motion: reduce)");
const {movementSquares,motionFrame}=globalThis.Board3DMovement;
let stage, fixture, event, size, detailView=false, playing=false;

function updateMotionNote() {
  element("motion-note").textContent=motion.matches
    ? "Reduced motion: the merchant is placed directly at the destination."
    : "A small hop for each square. No animation while at rest.";
}
function complete() {
  playing=false; replay.disabled=false;
  status.textContent=`Arrived at ${fixture.after.view.board[event.data.to].name}.`;
}
function play() {
  if (!event || playing) return;
  playing=true; replay.disabled=true;
  stage.place(event.data.from);
  status.textContent=event.sentence;
  if (motion.matches || event.data.travel === "teleport") {
    stage.place(event.data.to); complete(); return;
  }
  let started;
  stage.animate(now=>{
    started ??= now;
    const frame=motionFrame(event,size,(now-started)/360,motion.matches);
    stage.pose(frame);
    if (frame.done) complete();
    return !frame.done;
  });
}
function validateFixture(data) {
  const moves=data.events.filter(row=>row.kind === "moved");
  if (moves.length !== 1) throw new Error("The fixture needs exactly one moved event");
  const move=moves[0], board=data.before.view.board;
  const route=movementSquares(move,board.length);
  if (move.data.travel !== "walk" || move.data.steps < 2 || move.data.steps > 8 ||
      route.length !== move.data.steps || board.length < 10 ||
      !board.every((square,index)=>square.index===index && typeof square.name === "string") ||
      data.after.revision !== data.before.revision+1 ||
      !data.events.every(row=>row.index>=data.before.log_length && row.index<data.after.log_length && row.revision===data.after.revision) ||
      data.before.view.players[move.player]?.position !== move.data.from ||
      data.after.view.players[move.player]?.position !== move.data.to)
    throw new Error("The public fixture does not match the single-walk study contract");
  return move;
}
async function load() {
  try {
    stage=createScene(element("viewport"),element("labels"));
    detail.addEventListener("click",()=>{
      detailView=!detailView; stage.setDetail(detailView);
      detail.setAttribute("aria-pressed",String(detailView));
      detail.textContent=detailView ? "Return to board" : "Inspect figurine";
      element("view-note").textContent=detailView ? "FIGURINE DETAIL / 60°" : "BOARD VIEW / 60°";
    });
    const response=await fetch("./fixture.json");
    if (!response.ok) throw new Error("fixture.json is missing; run python examples/board3d/make_fixture.py, then reload");
    fixture=await response.json();
    event=validateFixture(fixture); size=fixture.before.view.board.length;
    stage.setBoard(fixture.before.view.board,event.data.from);
    const route=movementSquares(event,size);
    element("move-title").textContent=`Player ${event.player} / ${event.data.steps} squares / engine revision ${fixture.after.revision}`;
    status.textContent=event.sentence;
    element("route").textContent=[event.data.from,...route].map(i=>String(i).padStart(2,"0")).join(" → ");
    element("event").textContent=JSON.stringify(event,null,2);
    for (let slot=0;slot<10;slot++) {
      const square=fixture.before.view.board[(event.data.from-1+slot+size)%size];
      const item=document.createElement("li"); item.textContent=`[${square.index}] ${square.name}`;
      element("squares").append(item);
    }
    replay.disabled=false; replay.addEventListener("click",play);
  } catch (error) {
    status.textContent=`Preview unavailable: ${error.message}`;
    if (!stage) detail.disabled=true;
    replay.disabled=true;
  }
}
motion.addEventListener("change",()=>{
  updateMotionNote();
  if (!playing || !motion.matches) return;
  stage.stop(); stage.place(event.data.to); complete();
});
updateMotionNote();
load();

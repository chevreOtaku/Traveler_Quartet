import {createScene} from "./scene.js";

const element=id=>document.getElementById(id);
const C=globalThis.Board3DClient,L=globalThis.Board3DLayout,M=globalThis.Board3DMovement;
const Cam=globalThis.Board3DCamera,P=globalThis.Board3DPlay;
const motion=matchMedia("(prefers-reduced-motion: reduce)");
const params=new URLSearchParams(location.search),fixtureMode=params.get("mode")==="fixture";
let stage,client,game=params.get("game"),fixture=null,timer=null,detailView=false,busy=false;
let activeMove=null,skip=false,board=null,seatKinds=[],player=null,playerRevision=null;
const HOP_MS={board:260,follow:380},FOLLOW_HOLD_MS=650;
const pause=ms=>new Promise(resolve=>setTimeout(resolve,ms));

function error(message="") {element("error").textContent=message;element("error").hidden=!message;}
function setBusy(value) {
  busy=value;
  for (const id of ["start","connect","replay"]) element(id).disabled=value;
  element("skip").disabled=!value;
}
function reset(snapshot,positions,replaying) {
  board=snapshot.view.board;seatKinds=snapshot.seats;
  stage.setBoard(board);stage.setPlayers(snapshot.view.players,positions,replaying);
  element("dice").textContent="-- / --";element("route").textContent="";
  element("move-title").textContent=replaying ? "Replaying the server's public journal" : "Public table";
  element("status").textContent=replaying ? "Starting the recorded journey." : "Public snapshot loaded.";
  element("squares").replaceChildren();
  for (const square of board) {
    const item=document.createElement("li");item.textContent=`[${square.index}] ${square.name}`;
    element("squares").append(item);
  }
}
function showSnapshot(snapshot) {
  seatKinds=snapshot.seats;
  stage.setPlayers(snapshot.view.players);stage.highlight(-1);
  element("dice").textContent=snapshot.view.last_dice.join(" / ");
  element("move-title").textContent=`Round ${snapshot.view.round} / revision ${snapshot.revision}`;
  element("status").textContent=snapshot.over ? "Game complete. Showing the confirmed public table." : "Following the public table.";
  const summary=snapshot.view.players.map(p=>`Player ${p.seat}: ${p.out?"out":`${p.cash} G, square ${p.position}`}`).join(" | ");
  element("summary").textContent=summary;
}
async function showEvent(row) {
  element("move-title").textContent=`Round ${row.round} / player ${row.player} / revision ${row.revision}`;
  element("status").textContent=row.sentence;element("event").textContent=JSON.stringify(row,null,2);
  element("summary").textContent="Public journal playback; balances appear at the confirmed snapshot.";
  if (row.kind==="rolled") element("dice").textContent=row.data.dice.join(" / ");
  if (row.kind==="bankrupt") stage.setOut(row.player);
  if (row.kind!=="moved") {
    if (!skip && !motion.matches) await new Promise(resolve=>setTimeout(resolve,65));
    return;
  }
  const route=M.movementSquares(row,40);
  stage.select(row.player);stage.highlight(row.data.to);
  element("seat").value=String(row.player);
  element("route").textContent=[row.data.from,...route,...(route.length?[]:[row.data.to])].map(i=>String(i).padStart(2,"0")).join(" > ");
  stage.place(row.player,row.data.from);
  if (skip || motion.matches || row.data.travel==="teleport") {stage.place(row.player,row.data.to);return;}
  const followed=Cam.followSeat(seatKinds,row,motion.matches||skip);
  if (followed!==null) following(followed);
  await walk(row,followed===null ? HOP_MS.board : HOP_MS.follow);
  if (followed!==null) {
    if (!skip) await pause(FOLLOW_HOLD_MS);
    following(null);
  }
}
function following(seat) {
  stage.setFollow(seat);
  element("board").classList.toggle("following",seat!==null);
}
function walk(row,hopMs) {
  return new Promise(resolve=>{
    let started;
    const finish=()=>{stage.stop();stage.place(row.player,row.data.to);activeMove=null;resolve();};
    activeMove=finish;
    stage.animate(now=>{
      started ??= now;
      const frame=M.motionFrame(row,40,(now-started)/hopMs,motion.matches||skip);
      stage.pose(row.player,frame);
      if (frame.done) {activeMove=null;resolve();}
      return !frame.done;
    });
  });
}
function authorized(path,options={}) {
  return fetch(`/games/${encodeURIComponent(game)}${path}`,{...options,
    headers:{...(options.headers||{}),"Authorization":`Bearer ${player.token}`}});
}
async function updatePanel() {
  const panel=element("play"),actions=element("actions");
  panel.hidden=!player;actions.replaceChildren();
  if (!player || !game) return;
  const response=await authorized("/view"),data=await response.json();
  if (!response.ok) throw new Error(data.error||"Your seat could not be read");
  playerRevision=data.revision;
  const legal=data.view.your_turn && !data.over ? data.view.legal_actions : [];
  element("play-title").textContent=data.over ? "Game over" :
    legal.length ? `Your turn, player ${player.seat}` : "The computers are playing";
  for (const action of legal) {
    const button=document.createElement("button");button.type="button";
    button.textContent=P.actionLabel(action,board);button.disabled=busy;
    button.addEventListener("click",()=>run(()=>play(action)));
    actions.append(button);
  }
}
async function play(action) {
  const response=await authorized("/act",{method:"POST",headers:{"Content-Type":"application/json"},
    body:JSON.stringify({action,expected_revision:playerRevision})});
  const data=await response.json();
  if (!response.ok) throw new Error(data.error||"The engine refused that action");
  await client.refresh();
}
function rememberSeat(id) {
  try {
    if (player) sessionStorage.setItem(P.storageKey(id),JSON.stringify(player));
    else player=JSON.parse(sessionStorage.getItem(P.storageKey(id))||"null");
  } catch {player=player||null;}
}
function schedule() {
  clearTimeout(timer);
  if (client?.snapshot && !client.snapshot.over) timer=setTimeout(()=>run(()=>client.refresh()),1500);
}
async function run(work) {
  if (busy) return;
  clearTimeout(timer);setBusy(true);skip=false;error();
  try {await work();}
  catch(e) {error(e.message+". Use Replay / retry to reconnect.");}
  finally {
    setBusy(false);schedule();
    updatePanel().catch(e=>error(e.message));
  }
}
async function replayFixture() {
  if (!fixture) {
    const response=await fetch("./fixture.json");
    if (!response.ok) throw new Error("Missing fixture.json; run make_fixture.py");
    fixture=await response.json();
  }
  C.validateSnapshot(fixture.before);C.validateSnapshot(fixture.after);
  const rows=C.windowRows(fixture.after,fixture.events,fixture.before.log_length,fixture.before.revision);
  const positions=C.rewind(fixture.after,rows);
  if (positions.some((p,i)=>p!==fixture.before.view.players[i].position)) throw new Error("Inconsistent fixture positions");
  reset(fixture.before,positions,true);
  for (const row of rows) await showEvent(row);
  showSnapshot(fixture.after);element("status").textContent="Recorded fixture move complete.";
}
async function connect(id,replay=false) {
  if (id!==game) player=null;
  game=id;rememberSeat(id);
  element("game").value=id;
  history.replaceState(null,"","?game="+encodeURIComponent(id));
  element("source").textContent="SERVER / PUBLIC JOURNAL";
  await client.connect(id,replay);
}
async function newGame() {
  const seed=Number(element("seed").value),rounds=Number(element("rounds").value);
  if (!Number.isSafeInteger(seed) || ![5,10,30].includes(rounds)) throw new Error("Choose an integer seed and a listed game length");
  const human=element("table").value==="human";
  const seats=human ? ["human","normal","normal","normal"] : ["normal","normal","normal","normal"];
  element("status").textContent=human ? "A table for you and three computers." :
    "The server is playing four computers. Their public journal will follow.";
  const response=await fetch("/games",{method:"POST",headers:{"Content-Type":"application/json"},
    body:JSON.stringify({seats,seed,rounds})});
  const data=await response.json();
  if (!response.ok) throw new Error(data.error||"Game creation failed");
  player=human ? P.humanSeat(data.tokens) : null;
  if (human && !player) throw new Error("The server gave no seat for you");
  game=data.game;rememberSeat(game);await connect(game,true);
}
function init() {
  try {
    stage=createScene(element("viewport"),element("labels"));
    for (const town of Object.values(L.towns)) {
      const label=document.createElement("span");label.style.setProperty("--seat",town.color);
      label.textContent=`T${town.number} / ${town.name}`;element("towns").append(label);
    }
    client=C.create({fetch:(...args)=>fetch(...args),onReset:reset,onEvent:showEvent,onSnapshot:showSnapshot,
      onResync:reason=>error(`Resynchronized to a fresh public snapshot: ${reason}. The damaged interval was skipped.`)});
    element("setup").hidden=fixtureMode;
    element("source").textContent=fixtureMode ? "FIXTURE / RECORDED MOVE" : "SERVER / PUBLIC JOURNAL";
    element("start-form").addEventListener("submit",event=>{event.preventDefault();run(newGame);});
    element("connect-form").addEventListener("submit",event=>{event.preventDefault();run(()=>connect(element("game").value.trim()));});
    element("replay").addEventListener("click",()=>run(()=>fixtureMode ? replayFixture() :
      game ? connect(game,true) : Promise.reject(new Error("Start or connect to a game first"))));
    element("skip").addEventListener("click",()=>{skip=true;activeMove?.();});
    element("seat").addEventListener("change",()=>stage.select(Number(element("seat").value)));
    element("detail").addEventListener("click",()=>{
      detailView=!detailView;stage.setDetail(detailView);element("board").classList.toggle("detail",detailView);
      element("detail").setAttribute("aria-pressed",String(detailView));
      element("detail").textContent=detailView ? "Return to board" : "Inspect figurine";
    });
    element("return").addEventListener("click",()=>element("detail").click());
    if (fixtureMode) run(replayFixture);
    else if (game) run(()=>connect(game,params.get("replay")==="1"));
    else {setBusy(false);element("status").textContent="Start four computers, or enter an existing game ID.";}
  } catch(e) {error(`3D preview unavailable: ${e.message}`);setBusy(true);}
}
function motionNote() {
  element("motion-note").textContent=motion.matches ? "Reduced motion: direct arrivals." : "One small hop per square. No rendering while at rest.";
  if (motion.matches) activeMove?.();
}
motion.addEventListener("change",motionNote);motionNote();init();

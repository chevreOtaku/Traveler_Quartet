"use strict";
const get=id=>document.getElementById(id);
BoardRender.mount();
let timer=null;
const params=new URLSearchParams(location.search),spectator=params.get("mode")==="stream";
function error(message) { get("error").textContent=message;get("error").hidden=!message;get("connection").textContent=message?"CHECK THE TABLE":"CONNECTED"; }
function remember(session) {
  try {sessionStorage.setItem("tq-seat:"+session.game,session.token);} catch {error("This tab cannot save its seat. Keep it open while playing.");}
  history.replaceState(null,"","?game="+encodeURIComponent(session.game));
  const href="?mode=stream&game="+encodeURIComponent(session.game);
  get("streamLink").href=href;get("streamLink").hidden=false;
}
const client=BoardClient.create({
  fetch:(...args)=>fetch(...args),
  onState:(data,publicOnly)=>{BoardRender.draw(data,publicOnly,play);get("connection").textContent="CONNECTED";},
  onEvents:BoardRender.events,onBusy:BoardRender.busy,onError:error,onSession:remember
});
function schedule() {
  clearTimeout(timer);
  if(client.game&&(!client.snapshot||!client.snapshot.over||client.pendingEvents)) timer=setTimeout(poll,1500);
}
async function poll() {
  try {await client.refresh();error("");} catch(e) {error("Refresh failed: "+e.message+". Retrying shortly.");}
  finally {schedule();}
}
async function play(action) {
  clearTimeout(timer);error("");
  try {if(await client.act(action,get("message").value)) get("message").value="";}
  catch(e) {error(e.message+" Your message has been kept. Check the table before trying again.");}
  finally {schedule();}
}
get("startForm").addEventListener("submit",async event=>{
  event.preventDefault();error("");
  const count=Number(get("count").value),seed=Number(get("seed").value),rounds=Number(get("rounds").value);
  if(!Number.isSafeInteger(seed)||![1,2,3].includes(count)||![5,10,30].includes(rounds)) {error("Choose a valid game length, opponents and integer seed.");return;}
  try {
    const seats=["remote",...Array.from({length:count},(_,i)=>get("bot"+(i+1)).value)];
    await client.newGame({seats,seed,rounds});
  } catch(e) {error("Cannot start: "+e.message);}
  finally {schedule();}
});
get("count").addEventListener("change",()=>{
  get("bot2Label").hidden=Number(get("count").value)<2;
  get("bot3Label").hidden=Number(get("count").value)<3;
});
get("tradeForm").addEventListener("submit",event=>{
  event.preventDefault();
  const fields=["giveGold","giveSquares","giveCards","askGold","askSquares","askCards"];
  play([get("recipient").value,...fields.map(id=>get(id).value.replace(/\s/g,""))].join(":"));
});
get("bidForm").addEventListener("submit",event=>{event.preventDefault();play(get("bid").value);});
get("new").addEventListener("click",()=>location.assign("/"));
async function resume() {
  const game=params.get("game");
  if(!game) {if(spectator){get("setup").hidden=true;error("Open a public-view link from an existing game.");}return;}
  if(spectator) {
    get("setup").hidden=true;
    try {await client.connect({game,spectator:true});} catch(e) {error("Cannot watch: "+e.message);}
    finally {schedule();}
    return;
  }
  let token=null;
  try {token=sessionStorage.getItem("tq-seat:"+game);} catch {error("This tab cannot read its saved seat.");}
  if(!token) {
    get("setup").hidden=true;get("missingSeat").hidden=false;
    get("watchLink").href="?mode=stream&game="+encodeURIComponent(game);return;
  }
  remember({game,token});
  try {await client.connect({game,token});} catch(e) {error("Cannot resume: "+e.message);}
  finally {schedule();}
}
resume();

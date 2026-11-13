"use strict";
globalThis.Board3DClient = (() => {
  const M=typeof module!=="undefined" ? require("./movement.js") : globalThis.Board3DMovement;
  const Cam=typeof module!=="undefined" ? require("./camera.js") : globalThis.Board3DCamera;
  const natural=n=>Number.isSafeInteger(n) && n>=0;
  function validateSnapshot(snapshot) {
    const v=snapshot?.view;
    if (!natural(snapshot?.revision) || !natural(snapshot?.log_length) || typeof snapshot.over!=="boolean" ||
        !Array.isArray(v?.board) || v.board.length!==40 ||
        !v.board.every((s,i)=>s.index===i && typeof s.name==="string") ||
        !Array.isArray(v.players) || v.players.length<2 || v.players.length>4 ||
        !v.players.every((p,i)=>p.seat===i && natural(p.position) && p.position<40) ||
        !Cam.validSeats(snapshot.seats,v.players.length))
      throw new Error("Invalid public snapshot");
    return snapshot;
  }
  function windowRows(snapshot,events,start,revision=0) {
    if (!Array.isArray(events) || !events.every(e=>natural(e?.index))) throw new Error("Invalid public journal");
    const rows=events.filter(e=>e.index>=start && e.index<snapshot.log_length);
    let prior=revision;
    rows.forEach((row,i)=>{
      if (row.index!==start+i || !natural(row.revision) || row.revision<=revision ||
          row.revision<prior || row.revision>snapshot.revision || typeof row.sentence!=="string")
        throw new Error("Public journal gap or invalid revision");
      prior=row.revision;
    });
    if (rows.length!==snapshot.log_length-start) throw new Error("Incomplete public journal");
    return rows;
  }
  function rewind(snapshot,rows) {
    const positions=snapshot.view.players.map(p=>p.position);
    for (const row of [...rows].reverse()) {
      if (row.kind!=="moved") continue;
      M.movementSquares(row,snapshot.view.board.length);
      if (!natural(row.player) || row.player>=positions.length || positions[row.player]!==row.data.to)
        throw new Error("Movement destination disagrees with public snapshot or journal");
      positions[row.player]=row.data.from;
    }
    return positions;
  }
  function create(options) {
    let game=null,snapshot=null,cursor=0,busy=false,history=false;
    const onReset=options.onReset||(()=>{}),onEvent=options.onEvent||(()=>{}),
      onSnapshot=options.onSnapshot||(()=>{}),onResync=options.onResync||(()=>{});
    async function request(suffix="") {
      const response=await options.fetch("/games/"+encodeURIComponent(game)+"/public"+suffix);
      const data=await response.json();
      if (!response.ok) throw new Error(data.error||`Public request refused (${response.status})`);
      return data;
    }
    function commit(data) {snapshot=data;cursor=data.log_length;onSnapshot(data);}
    async function resync(reason) {
      const fresh=validateSnapshot(await request());
      onReset(fresh,fresh.view.players.map(p=>p.position),false);
      commit(fresh);onResync(reason);
    }
    async function load() {
      const fresh=validateSnapshot(await request());
      if (!snapshot && !history) {
        onReset(fresh,fresh.view.players.map(p=>p.position),false);commit(fresh);return true;
      }
      let rows,positions;
      const start=snapshot ? cursor : 0;
      const payload=start===fresh.log_length ? {events:[]} :
        await request(`/events?since=${start}&until=${fresh.log_length}`);
      try {
        if (snapshot && (fresh.log_length<cursor || fresh.revision<snapshot.revision))
          throw new Error("Public journal moved backwards");
        rows=windowRows(fresh,payload.events,start,snapshot?.revision||0);
        positions=rewind(fresh,rows);
        if (snapshot && positions.some((p,i)=>p!==snapshot.view.players[i]?.position))
          throw new Error("Public journal does not continue the displayed positions");
      } catch(error) {await resync(error.message);return true;}
      if (!snapshot) onReset(fresh,positions,true);
      for (const row of rows) await onEvent(row);
      commit(fresh);return true;
    }
    async function locked(work) {
      if (busy) return false;
      busy=true;
      try {return await work();} finally {busy=false;}
    }
    return {
      get snapshot(){return snapshot;},get cursor(){return cursor;},get busy(){return busy;},
      connect(id,replayHistory=false) {
        return locked(async()=>{
          if (typeof id!=="string" || !id) throw new Error("A game ID is required");
          game=id;snapshot=null;cursor=0;history=replayHistory;return load();
        });
      },
      refresh(){return locked(load);}
    };
  }
  return {create,rewind,windowRows,validateSnapshot};
})();
if (typeof module!=="undefined") module.exports=globalThis.Board3DClient;

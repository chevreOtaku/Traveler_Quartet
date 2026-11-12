"use strict";
globalThis.BoardClient = (() => {
  const M=typeof module!=="undefined" ? require("./model.js") : globalThis.BoardModel;
  function create(options) {
    let game=null,token=null,spectator=false,snapshot=null,cursor=0,busy=false,pendingEvents=false;
    const onState=options.onState||(()=>{}),onEvents=options.onEvents||(()=>{}),
      onError=options.onError||(()=>{}),onBusy=options.onBusy||(()=>{});
    function headers() {
      return spectator ? {"Content-Type":"application/json"} :
        {"Content-Type":"application/json","Authorization":"Bearer "+token};
    }
    async function request(path,extra={}) {
      const response=await options.fetch(path,{headers:headers(),...extra});
      const data=await response.json();
      if (!response.ok) throw new Error(data.error||"Request refused ("+response.status+")");
      return data;
    }
    function path(kind) {
      return "/games/"+encodeURIComponent(game)+(spectator?"/public":"")+(kind==="view"?(spectator?"":"/view"):"/events");
    }
    function show(data) { snapshot=data; onState(data,spectator); }
    async function readEvents() {
      pendingEvents=true;
      const end=snapshot.log_length;
      if (!Number.isSafeInteger(end)||end<0) throw new Error("Invalid journal watermark");
      if (cursor>end) { cursor=0; onEvents([],true); }
      if (cursor===end) { pendingEvents=false; return; }
      const data=await request(path("events")+"?since="+cursor+"&until="+end);
      const rows=data.events.filter(e=>e.index>=cursor&&e.index<end);
      rows.forEach((e,i)=>{ if(e.index!==cursor+i) throw new Error("Journal gap: reconnect to resynchronize"); });
      if (rows.length!==end-cursor) throw new Error("Incomplete journal; retrying");
      onEvents(rows,false); cursor=end; pendingEvents=false;
    }
    async function load() { show(await request(path("view"))); await readEvents(); }
    async function locked(fn) {
      if (busy) return false;
      busy=true; onBusy(true);
      try { return await fn(); } finally { busy=false; onBusy(false); }
    }
    return {
      get game(){return game;},get snapshot(){return snapshot;},get cursor(){return cursor;},
      get busy(){return busy;},get pendingEvents(){return pendingEvents;},
      connect(config) {
        return locked(async()=>{
          game=config.game; spectator=Boolean(config.spectator); token=spectator?null:config.token;
          cursor=0; snapshot=null; onEvents([],true); await load(); return true;
        });
      },
      newGame(config) {
        return locked(async()=>{
          const data=await request("/games",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(config)});
          const entry=Object.entries(data.tokens).find(([,seat])=>seat===0);
          if (!entry) throw new Error("No player seat returned");
          game=data.game; token=entry[0]; spectator=false; cursor=0;
          if(options.onSession) options.onSession({game,token});
          onEvents([],true); await load(); return {game,token};
        });
      },
      refresh(){return locked(load);},
      act(action,message) {
        if (spectator||!M.allowed(snapshot,action)) return Promise.resolve(false);
        return locked(async()=>{
          const prior=M.questionKey(snapshot);
          const fresh=await request(path("view")); show(fresh);
          if (M.questionKey(fresh)!==prior) throw new Error("The table changed. Review your next move.");
          if (!M.allowed(fresh,action)) throw new Error("This action is no longer offered.");
          const body={action,message};
          if (Number.isSafeInteger(fresh.revision)) body.expected_revision=fresh.revision;
          show(await request("/games/"+encodeURIComponent(game)+"/act",{method:"POST",body:JSON.stringify(body)}));
          try { await readEvents(); } catch(error) { onError("Action accepted; "+error.message+". The journal will retry."); }
          return true;
        });
      }
    };
  }
  return {create};
})();
if (typeof module!=="undefined") module.exports=globalThis.BoardClient;

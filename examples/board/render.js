"use strict";
globalThis.BoardRender=(()=>{
  const M=BoardModel,get=id=>document.getElementById(id);
  let selected=0,latest=null,stream=false,lastPosition=null,actionKey=null;
  const tiles=new Map();
  function node(tag,text="",cls="") {
    const el=document.createElement(tag); el.textContent=text; el.className=cls; return el;
  }
  function seatName(seat) { return seat===null||seat===undefined ? "Unowned" : "Player "+seat; }
  function mount() {
    for(let i=0;i<40;i++) {
      const tile=node("button","","tile"); tile.type="button";
      const [r,c]=M.tilePosition(i); tile.style.gridRow=r; tile.style.gridColumn=c;
      tile.dataset.index=i; tile.addEventListener("click",()=>{selected=i;inspect();highlight();});
      tile.append(node("span",String(i).padStart(2,"0"),"tile-index"),node("span","","tile-name"),
        node("span","","tile-owner"),node("span","","tile-pins"));
      get("board").append(tile); tiles.set(i,tile);
    }
    get("mySquare").addEventListener("click",()=>{selected=latest.view.me.position;inspect();highlight();});
  }
  function highlight() {
    tiles.forEach((tile,index)=>tile.setAttribute("aria-pressed",String(index===selected)));
  }
  function paintBoard(view) {
    if(view.board.length!==40) throw new Error("This board requires the forty-square layout.");
    const players=M.players(view);
    view.board.forEach(s=>{
      const tile=tiles.get(s.index),town=M.towns[s.town];
      tile.style.setProperty("--town",town?town[1]:"#bdc5ae");
      tile.dataset.kind=s.kind; tile.dataset.owned=s.owner===null?"no":"yes";
      tile.children[1].textContent=s.name;
      tile.children[2].textContent=s.owner===null?(!["district","portal","utility"].includes(s.kind)?"":s.price+" G"):"P"+s.owner+(s.buildings>0?" / L"+s.buildings:"")+(s.mortgaged?" / M":"");
      tile.title="["+s.index+"] "+s.name+" - "+seatName(s.owner)+" - building level "+s.buildings;
      tile.setAttribute("aria-label",tile.title);
      tile.children[3].replaceChildren(...players.filter(p=>!p.out&&p.position===s.index).map(p=>{
        const pin=node("b",String(p.seat),"pin seat"+p.seat); pin.title=seatName(p.seat); return pin;
      }));
    });
    highlight();
  }
  function paintPlayers(view) {
    get("players").replaceChildren(...M.players(view).map(p=>{
      const el=node("article","","player"+(p.seat===view.actor?" is-acting":"")+(p.out?" is-out":""));
      const badge=node("span",String(p.seat),"player-seal seat"+p.seat),info=node("div");
      info.append(node("span",seatName(p.seat)+(view.me&&p.seat===view.me.seat?" / YOU":""),"player-name"),
        node("strong",p.cash+" G"));
      el.append(badge,info,node("span",p.out?"ELIMINATED":p.in_dungeon?"IN DUNGEON":"Worth "+p.net_worth+" G","player-worth"));
      return el;
    }));
    get("round").textContent="ROUND "+view.round+" / "+view.rounds;
    get("order").textContent="Order: "+view.order.map(p=>"P"+p).join(" > ");
    get("acting").textContent=view.actor===null?"The journey is over":seatName(view.actor)+" to answer";
    get("dice").replaceChildren(...view.last_dice.map(n=>node("span",n||"-","die")));
    get("double").textContent=view.doubles>0?"Double streak: "+view.doubles:"";
    get("jackpot").textContent="Table jackpot / "+view.jackpot+" G";
  }
  function inspect() {
    if(!latest) return;
    const view=latest.view,s=view.board[selected],town=M.towns[s.town];
    get("propertyName").textContent=s.name;
    get("squareKind").textContent=s.kind.replaceAll("_"," ").toUpperCase();
    get("squareNumber").textContent="No. "+String(s.index).padStart(2,"0");
    get("townName").textContent=town?town[0]:"Along the merchant's road";
    get("townName").style.color=town?town[1]:"#718169";
    get("ownership").textContent=seatName(s.owner)+(s.mortgaged?" / Mortgaged":"");
    get("price").textContent=!["district","portal","utility"].includes(s.kind)?"-":s.price+" G";
    get("rent").textContent=M.rentText(s);
    get("buildingInfo").textContent="Building level: "+s.buildings+(s.partner!==null&&s.partner!==undefined?" / Shared with player "+s.partner:"");
    const districts=town?view.board.filter(x=>x.town===s.town):[];
    get("townList").replaceChildren(...districts.map(d=>{
      const row=node("div","","town-row");
      row.append(node("span","["+d.index+"] "+d.name),node("b",seatName(d.owner)));
      return row;
    }));
    get("mySquare").hidden=stream||selected===view.me.position;
  }
  function contract(view) {
    get("contract").replaceChildren(); get("contract").hidden=!view.trade&&!view.auction;
    if(view.trade) {
      const t=view.trade;
      get("contract").append(node("strong",seatName(t.proposer)+" offers "+seatName(t.responder)));
      for(const [key,label] of [["give","Gives"],["ask","Asks"]]) {
        const terms=t.terms,parts=[terms[key+"_gold"]+" G"];
        terms[key+"_squares"].forEach(i=>parts.push("["+i+"] "+view.board[i].name));
        terms[key+"_cards"].forEach(c=>parts.push(c));
        get("contract").append(node("p",label+": "+parts.join(", ")));
      }
    }
    if(view.auction) get("contract").append(node("p","Auction: "+view.board[view.auction.square].name+" / "+view.auction.price+" G / leader: "+seatName(view.auction.leader)));
  }
  function controls(view,onAction) {
    const actions=view.legal_actions||[],bids=actions.filter(a=>a.startsWith("bid:"));
    get("actions").replaceChildren(...actions.filter(a=>!a.startsWith("bid:")).map(action=>{
      const b=node("button",M.actionLabel(action,view),action==="roll"||action==="buy"?"primary":"secondary");
      b.type="button"; b.addEventListener("click",()=>onAction(action)); return b;
    }));
    get("bidForm").hidden=!bids.length;
    get("bid").replaceChildren(...bids.map(a=>{const o=node("option",a.split(":")[1]+" G");o.value=a;return o;}));
    const choices=(view.negotiations||[]).filter(a=>a==="counter"||a.startsWith("offer:"));
    get("trade").hidden=!choices.length;
    get("recipient").replaceChildren(...choices.map(c=>{const o=node("option",c==="counter"?"Counter-offer":"Player "+c.split(":")[1]);o.value=c;return o;}));
  }
  function question(data,onAction) {
    const view=data.view;
    get("questionLabel").textContent=stream?"PUBLIC TABLE":data.over?"THE FINAL ACCOUNTS":"YOUR NEXT MOVE";
    get("questionTitle").textContent=data.over?"The road ends here.":stream?"At the table.":view.your_turn?
      ({roll:"Time to move.",buy:"An opportunity.",auction:"Going, going...",sealed:"Under sealed cover.",trade:"A deal on the table.",debt:"Settle your account.",jump:"Take the shortcut?"}[view.pending]||"Your decision."):"The others are deciding.";
    get("questionDetail").textContent=data.over?"Final ranking, as counted by the game.":stream?
      (view.actor===null?"":seatName(view.actor)+" must answer."):view.your_turn?
      "At ["+view.me.position+"] "+view.board[view.me.position].name+". Choose an action below.":"Watch the journal while the table moves on.";
    get("centerMessage").textContent=data.over?"Every road has an ending.":get("questionTitle").textContent;
    get("playerControls").hidden=stream||data.over;
    get("debt").hidden=!view.debt_context;
    if(view.debt_context) {const d=view.debt_context;get("debt").textContent=seatName(d.debtor)+" owes "+d.amount+" G to "+(typeof d.to==="number"?seatName(d.to):d.to)+".";}
    contract(view);
    const nextKey=M.questionKey(data);
    if(nextKey!==actionKey) { if(!stream) controls(view,onAction); actionKey=nextKey; }
    get("ranking").hidden=!data.over;
    get("ranking").replaceChildren(...(view.ranking||[]).map(p=>node("li",seatName(p.seat)+" / "+p.net_worth+" G")));
  }
  function satchel(data) {
    get("pockets").hidden=stream;
    if(stream) {get("hand").replaceChildren();get("textView").textContent="";return;}
    get("hand").replaceChildren(...(data.view.me.cards.length?data.view.me.cards.map(c=>node("span",c,"card-tag")):[node("p","No cards tucked away yet.","fine")]));
    get("textView").textContent=data.text||"";
  }
  function draw(data,spectator,onAction) {
    latest=data;stream=spectator;
    const position=stream?null:data.view.me.position;
    if(lastPosition!==position) {selected=position===null?data.view.players[0].position:position;lastPosition=position;}
    get("setup").hidden=true;get("game").hidden=false;get("new").hidden=stream;
    get("viewMode").textContent=stream?"PUBLIC VIEW / READ ONLY":"YOUR SEAT";
    paintBoard(data.view);paintPlayers(data.view);inspect();question(data,onAction);satchel(data);
  }
  function busy(value) {
    get("setupFields").disabled=value;get("tradeFields").disabled=value;
    const waiting=value||!latest||latest.over||stream||!latest.view.your_turn;
    get("message").disabled=waiting;
    get("playerControls").querySelectorAll("button,select,input").forEach(el=>{el.disabled=waiting;});
  }
  function events(rows,reset) {
    if(reset) get("events").replaceChildren();
    rows.forEach(e=>get("events").append(node("li","Round "+e.round+" / "+(e.sentence||e.kind))));
    while(get("events").children.length>100) get("events").firstElementChild.remove();
    get("journalCount").textContent="LAST "+get("events").children.length+" EVENTS";
  }
  return {mount,draw,busy,events};
})();

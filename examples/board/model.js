"use strict";
/* Presentation helpers only: no prices, dice, rent rules or movement simulation. */
globalThis.BoardModel = (() => {
  const towns = {
    brown:["Greenhorn Fields","#92734f"], light_blue:["Overtime Hollow","#77a5ac"],
    purple:["Three Altars","#9c8ba4"], orange:["Wildmark","#bb8855"],
    red:["Glimmerland","#b57668"], yellow:["Curtain Call","#c5ae5b"],
    green:["Wolfcoin","#77956d"], dark_blue:["Royal Ziggurat","#62788f"]
  };
  function tilePosition(index) {
    if (!Number.isInteger(index) || index < 0 || index >= 40) throw new Error("Unknown board square");
    const corners=[[10,10],[10,0],[0,0],[0,10]], directions=[[0,-1],[-1,0],[0,1],[1,0]];
    const side=Math.floor(index/10), step=index%10;
    return corners[side].map((v,k)=>v+directions[side][k]*step+1);
  }
  function players(view) { return view.players || [view.me,...view.others].sort((a,b)=>a.seat-b.seat); }
  function allowed(data,action) {
    if (!data || data.over || !data.view.your_turn) return false;
    const v=data.view;
    return v.legal_actions.includes(action) || (v.negotiations||[]).some(n=>action.startsWith(n+":"));
  }
  function questionKey(data) { return JSON.stringify([data.revision,data.log_length,data.view]); }
  function rentText(square) {
    if (square.rent_per_dice_point !== null && square.rent_per_dice_point !== undefined)
      return square.rent_per_dice_point+" G per dice point";
    return square.rent === null || square.rent === undefined ? "Not applicable" : square.rent+" G";
  }
  function actionLabel(action,view) {
    const [name,arg]=action.split(":"), square=view.board[Number(arg)];
    const names={roll:"Roll the dice",buy:"Buy "+view.board[view.me.position].name,
      pass:"Pass - open auction",drop:"Leave auction",accept:"Accept",refuse:"Refuse",
      jump:"Use the portal",stay:"Stay here",pay_exit:"Pay to leave dungeon",use_rope:"Use rope",bankrupt:"Declare bankruptcy"};
    if (names[action]) return names[action];
    if (name==="raise") return "Raise by "+arg+" G";
    if (name==="curse") return "Curse player "+arg;
    const verbs={build:"Build",sell:"Sell building",mortgage:"Mortgage",unmortgage:"Unmortgage",share_stall:"Share stall"};
    return verbs[name] && square ? verbs[name]+" - "+square.name : action;
  }
  return {towns,tilePosition,players,allowed,questionKey,rentText,actionLabel};
})();
if (typeof module !== "undefined") module.exports=globalThis.BoardModel;

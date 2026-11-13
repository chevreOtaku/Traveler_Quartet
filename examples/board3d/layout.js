"use strict";
globalThis.Board3DLayout = (() => {
  const PAWN_HEIGHT=.70, PAWN_WIDTH=.42;
  const seats=[
    {shape:"circle",color:"#216b83"}, {shape:"triangle",color:"#b85a39"},
    {shape:"square",color:"#69529b"}, {shape:"diamond",color:"#527634"}
  ];
  const towns={
    brown:{name:"Greenhorn Fields",color:"#96704c",number:1},
    light_blue:{name:"Overtime Hollow",color:"#64b6cd",number:2},
    purple:{name:"Three Altars",color:"#ad79bb",number:3},
    orange:{name:"Wildmark",color:"#e59749",number:4},
    red:{name:"Glimmerland",color:"#ce6762",number:5},
    yellow:{name:"Curtain Call",color:"#c6ac3f",number:6},
    green:{name:"Wolfcoin",color:"#6e9d74",number:7},
    dark_blue:{name:"Royal Ziggurat",color:"#566b9b",number:8}
  };
  function tilePosition(index) {
    if (!Number.isInteger(index) || index<0 || index>=40) throw new Error("Unknown board square");
    const side=Math.floor(index/10),step=index%10;
    const corners=[[5,5],[-5,5],[-5,-5],[5,-5]],directions=[[-1,0],[0,-1],[1,0],[0,1]];
    return corners[side].map((v,k)=>v+directions[side][k]*step);
  }
  function seatOffset(seat) {
    if (!Number.isInteger(seat) || seat<0 || seat>3) throw new Error("Unknown player seat");
    return [seat%2 ? .25 : -.25,seat<2 ? -.25 : .25];
  }
  return {PAWN_HEIGHT,PAWN_WIDTH,seats,towns,tilePosition,seatOffset};
})();
if (typeof module!=="undefined") module.exports=globalThis.Board3DLayout;

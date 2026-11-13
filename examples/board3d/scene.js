import * as THREE from "./vendor/three/three.module.js";
import {makeMerchant} from "./pawn.js";

const L=globalThis.Board3DLayout;
const material=(color,roughness=.65)=>new THREE.MeshStandardMaterial({color,roughness});

export function createScene(host,labelHost) {
  const scene=new THREE.Scene();
  scene.background=new THREE.Color("#e5e9dc");
  const renderer=new THREE.WebGLRenderer({antialias:true});
  renderer.setPixelRatio(Math.min(devicePixelRatio,2));
  renderer.shadowMap.enabled=true;renderer.shadowMap.type=THREE.PCFSoftShadowMap;
  renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=1.1;
  renderer.outputColorSpace=THREE.SRGBColorSpace;host.append(renderer.domElement);
  const boardCamera=new THREE.OrthographicCamera(-10,10,5,-5,.1,100);
  const detailCamera=new THREE.PerspectiveCamera(60,1,.01,100);
  const pawns=L.seats.map((_,seat)=>makeMerchant(seat));
  const present=pawns.map(()=>false);
  pawns.forEach(p=>{p.visible=false;scene.add(p);});
  const labels=[],tiles=[],positions=new Map();
  let detail=false,selected=0,requested=false,animation=null,frameCount=0;
  const svg=document.createElementNS("http://www.w3.org/2000/svg","svg");
  svg.classList.add("leaders");labelHost.append(svg);
  scene.add(new THREE.HemisphereLight("#f2f7ff","#afa38d",2));
  const sun=new THREE.DirectionalLight("#fff0d5",3.2);
  sun.position.set(-6,12,8);sun.castShadow=true;sun.shadow.mapSize.set(2048,2048);
  Object.assign(sun.shadow.camera,{left:-8,right:8,top:8,bottom:-8,near:.5,far:35});
  sun.shadow.normalBias=.012;sun.shadow.bias=-.0002;scene.add(sun);
  const fill=new THREE.DirectionalLight("#cee3ff",1.3);fill.position.set(8,6,-6);scene.add(fill);
  makeGround(scene);
  function invalidate() {
    if (requested || document.hidden) return;
    requested=true;requestAnimationFrame(draw);
  }
  function updateCamera() {
    const aspect=host.clientWidth/host.clientHeight;
    // Keep a 120 px callout band above and below, and room for the side names.
    const vertical=11*.56/(1-260/host.clientHeight);
    const extent=Math.max(vertical,11/(aspect-480/host.clientHeight))/2;
    boardCamera.left=-extent*aspect;boardCamera.right=extent*aspect;
    boardCamera.top=extent;boardCamera.bottom=-extent;
    boardCamera.position.set(0,15,22);boardCamera.lookAt(0,0,0);boardCamera.updateProjectionMatrix();
    const target=pawns[selected].position.clone().add(new THREE.Vector3(0,.35,0));
    detailCamera.aspect=aspect;
    detailCamera.position.copy(target).add(new THREE.Vector3(.28,.18,1.12));
    detailCamera.lookAt(target);detailCamera.updateProjectionMatrix();
    return detail ? detailCamera : boardCamera;
  }
  function draw(now) {
    requested=false;
    if (animation && !animation(now)) animation=null;
    pawns.forEach((pawn,seat)=>pawn.visible=present[seat] && (!detail || seat===selected));
    const camera=updateCamera();renderer.render(scene,camera);frameCount++;
    updateLabels(camera);
    if (animation) invalidate();
  }
  function updateLabels(camera) {
    const width=host.clientWidth,height=host.clientHeight;
    svg.style.display=detail ? "none" : "";
    for (const {element,point,line,index} of labels) {
      element.hidden=detail;
      const p=point.clone().project(camera),px=(p.x*.5+.5)*width,py=(-p.y*.5+.5)*height;
      const [x,z]=L.tilePosition(index);
      let left,top,ax,ay;
      if (Math.abs(z)===5) {
        const row=(x+5)%2;
        left=px-82;top=z<0 ? 12+row*62 : height-120+row*58;
        ax=px;ay=z<0 ? top+54 : top;
      } else {
        left=x<0 ? 14 : width-234;top=py-23;
        ax=x<0 ? left+220 : left;ay=py;
      }
      element.style.left=`${left}px`;element.style.top=`${top}px`;
      line.setAttribute("x1",px);line.setAttribute("y1",py);
      line.setAttribute("x2",ax);line.setAttribute("y2",ay);
    }
  }
  function resize() {
    renderer.setSize(host.clientWidth,host.clientHeight,false);invalidate();
  }
  function setBoard(board) {
    if (positions.size) return;
    if (board.length!==40) throw new Error("The board must have forty squares");
    for (const square of board) addTile(square);
    invalidate();
  }
  function addTile(square) {
    const [x,z]=L.tilePosition(square.index),town=L.towns[square.town];
    positions.set(square.index,new THREE.Vector3(x,.16,z));
    const tile=new THREE.Mesh(new THREE.BoxGeometry(.98,.16,.98),material(town ? "#f5ebd6" : "#e7dfcf"));
    tile.position.set(x,.08,z);tile.castShadow=true;tile.receiveShadow=true;scene.add(tile);tiles.push(tile);
    if (town) {
      const stripe=new THREE.Mesh(new THREE.BoxGeometry(.94,.018,.13),material(town.color));
      stripe.position.set(x,.17,z-.39);scene.add(stripe);
    }
    const number=makeTileNumber(square.index,town);
    number.position.set(x,.18,z);number.rotation.x=-Math.PI/2;scene.add(number);
    const element=document.createElement("span");element.className="tile-label";
    if (Math.abs(z)!==5) element.classList.add("side-label");
    element.style.setProperty("--town",town?.color||"#9b9587");
    const index=document.createElement("b");index.textContent=String(square.index).padStart(2,"0")+" ";
    element.append(index,document.createTextNode(square.name));labelHost.append(element);
    const line=document.createElementNS(svg.namespaceURI,"line");svg.append(line);
    labels.push({element,line,index:square.index,point:new THREE.Vector3(x,.17,z)});
  }
  function position(seat,index) {
    const point=positions.get(index);
    if (!point) throw new Error("Unknown movement square");
    const [x,z]=L.seatOffset(seat);return point.clone().add(new THREE.Vector3(x,0,z));
  }
  function place(seat,index) {pawns[seat].position.copy(position(seat,index));invalidate();}
  function pose(seat,frame) {
    pawns[seat].position.lerpVectors(position(seat,frame.from),position(seat,frame.to),frame.progress);
    pawns[seat].position.y+=frame.lift;
  }
  function setPlayers(players,locations=players.map(p=>p.position),replaying=false) {
    pawns.forEach((pawn,seat)=>{
      present[seat]=Boolean(players[seat]) && (replaying || !players[seat].out);
      if (players[seat]) place(seat,locations[seat]);
    });
  }
  new ResizeObserver(resize).observe(host);
  document.addEventListener("visibilitychange",invalidate);resize();
  return {setBoard,setPlayers,place,pose,invalidate,
    select(seat){L.seatOffset(seat);selected=seat;invalidate();},
    setDetail(value){detail=value;invalidate();},
    setOut(seat){present[seat]=false;invalidate();},
    highlight(index){tiles.forEach((t,i)=>t.material.emissive.set(i===index?"#514a21":"#000000"));invalidate();},
    animate(callback){animation=callback;invalidate();},stop(){animation=null;invalidate();},
    get frameCount(){return frameCount;}};
}

function makeTileNumber(index,town) {
  const canvas=document.createElement("canvas");canvas.width=128;canvas.height=128;
  const ctx=canvas.getContext("2d");
  ctx.fillStyle="#f7f0de";ctx.fillRect(0,0,128,128);
  ctx.fillStyle="#394e50";ctx.textAlign="center";ctx.font="bold 48px sans-serif";
  ctx.fillText(String(index).padStart(2,"0"),64,65);
  if (town) {ctx.fillStyle=town.color;ctx.font="bold 30px sans-serif";ctx.fillText(`T${town.number}`,64,103);}
  const texture=new THREE.CanvasTexture(canvas);texture.colorSpace=THREE.SRGBColorSpace;
  return new THREE.Mesh(new THREE.PlaneGeometry(.49,.49),new THREE.MeshStandardMaterial({map:texture,roughness:.8}));
}

function makeGround(scene) {
  const ground=new THREE.Mesh(new THREE.BoxGeometry(11.4,.28,11.4),material("#c6cdb6",1));
  ground.position.y=-.15;ground.receiveShadow=true;scene.add(ground);
  const palette=["#d5ddc7","#dce1cf","#ced8c1","#e0e3d3"];
  for (let i=0;i<4;i++) {
    const geometry=new THREE.BufferGeometry();
    const corners=[[-5.7,-5.7],[5.7,-5.7],[5.7,5.7],[-5.7,5.7]];
    const [ax,az]=corners[i],[bx,bz]=corners[(i+1)%4];
    geometry.setAttribute("position",new THREE.Float32BufferAttribute([0,.001,0,ax,.001,az,bx,.001,bz],3));
    geometry.computeVertexNormals();
    const facet=new THREE.Mesh(geometry,new THREE.MeshStandardMaterial({color:palette[i],roughness:1,side:THREE.DoubleSide}));
    facet.receiveShadow=true;scene.add(facet);
  }
}

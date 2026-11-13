import * as THREE from "./vendor/three/three.module.js";
import {makeMerchant} from "./pawn.js";

export function createScene(host, labelHost) {
  const scene = new THREE.Scene();
  const renderer = new THREE.WebGLRenderer({antialias:true,alpha:false});
  renderer.setPixelRatio(Math.min(devicePixelRatio,2));
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.15;
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  host.append(renderer.domElement);
  const camera = new THREE.PerspectiveCamera(60,1,.1,150);
  const pawn = makeMerchant();
  scene.add(pawn);
  const labels = [], positions = new Map();
  let detail = false, requested = false, animation = null, frameCount = 0;
  const target = new THREE.Vector3();
  const sky = document.createElement("canvas"); sky.width=2; sky.height=256;
  const context = sky.getContext("2d"), gradient = context.createLinearGradient(0,0,0,256);
  gradient.addColorStop(0,"#76b8e3"); gradient.addColorStop(.56,"#bee1ec"); gradient.addColorStop(1,"#ffd7bf");
  context.fillStyle=gradient; context.fillRect(0,0,2,256);
  scene.background = new THREE.CanvasTexture(sky);
  scene.background.colorSpace = THREE.SRGBColorSpace;
  scene.add(new THREE.HemisphereLight("#e5f6ff","#bc9b86",2.0));
  const sun = new THREE.DirectionalLight("#fff1da",3.5);
  sun.position.set(-6,12,8); sun.castShadow=true;
  sun.shadow.mapSize.set(2048,2048);
  Object.assign(sun.shadow.camera,{left:-17,right:17,top:12,bottom:-12,near:.5,far:40});
  sun.shadow.normalBias=.035; sun.shadow.bias=-.0002;
  scene.add(sun);
  const fill = new THREE.DirectionalLight("#c4deff",1.6);
  fill.position.set(8,6,-6); scene.add(fill);
  makeGround(scene);
  makeClouds(scene);
  function invalidate() {
    if (requested || document.hidden) return;
    requested=true;
    requestAnimationFrame(draw);
  }
  function draw(now) {
    requested=false;
    if (animation) {
      const keepGoing=animation(now);
      if (!keepGoing) animation=null;
    }
    updateCamera();
    renderer.render(scene,camera); frameCount++;
    updateLabels();
    if (animation) invalidate();
  }
  function updateCamera() {
    const aspect=camera.aspect;
    if (detail) {
      target.copy(pawn.position).add(new THREE.Vector3(0,1.6,0));
      camera.position.copy(target).add(new THREE.Vector3(1.3,1.1,Math.max(4.6,3.6/aspect)));
    } else {
      target.set(0,.3,.5);
      const distance=Math.max(8.5,22/aspect);
      camera.position.set(1,distance*.65,distance);
    }
    camera.lookAt(target);
  }
  function updateLabels() {
    for (const {element,point} of labels) {
      const p=point.clone().project(camera);
      element.hidden=detail || Math.abs(p.x)>1 || Math.abs(p.y)>1 || p.z>1;
      element.style.left=`${(p.x*.5+.5)*host.clientWidth}px`;
      element.style.top=`${(-p.y*.5+.5)*host.clientHeight}px`;
    }
  }
  function resize() {
    const width=host.clientWidth,height=host.clientHeight;
    renderer.setSize(width,height,false);
    camera.aspect=width/height; camera.updateProjectionMatrix(); invalidate();
  }
  function setBoard(board, origin) {
    if (positions.size) throw new Error("The study board is already loaded");
    const colors=["#ffdeb8","#b9dcd3","#dec8e8","#f2c1ad","#b6d8eb"];
    for (let slot=0;slot<10;slot++) {
      const index=(origin-1+slot+board.length)%board.length, square=board[index];
      const x=(slot-4.5)*2.25,z=.075*(slot-4.5)**2;
      positions.set(index,new THREE.Vector3(x,.18,z));
      const tile=new THREE.Mesh(new THREE.CylinderGeometry(1.04,1.08,.28,6),
        new THREE.MeshStandardMaterial({color:colors[slot%colors.length],roughness:.68,metalness:0,flatShading:true}));
      tile.position.set(x,0,z); tile.rotation.y=Math.PI/6;
      tile.receiveShadow=true; tile.castShadow=true; scene.add(tile);
      const element=document.createElement("span"); element.className="tile-label";
      element.textContent=`${square.index.toString().padStart(2,"0")} / ${square.name}`;
      labelHost.append(element);
      labels.push({element,point:new THREE.Vector3(x,.2,z+1.06)});
    }
    place(origin); invalidate();
  }
  function place(index) {
    const position=positions.get(index);
    if (!position) throw new Error("Movement leaves the displayed board section");
    pawn.position.copy(position); invalidate();
  }
  function pose(frame) {
    const from=positions.get(frame.from), to=positions.get(frame.to);
    if (!from || !to) throw new Error("Movement leaves the displayed board section");
    pawn.position.lerpVectors(from,to,frame.progress);
    pawn.position.y+=frame.lift;
  }
  new ResizeObserver(resize).observe(host);
  document.addEventListener("visibilitychange",()=>invalidate());
  resize();
  return {setBoard,place,pose,invalidate,
    setDetail(value) {detail=value; invalidate();},
    animate(callback) {animation=callback; invalidate();},
    stop() {animation=null; invalidate();},
    get frameCount() {return frameCount;}};
}

function makeGround(scene) {
  const vertices=[],colors=[];
  const palette=["#a4c9b4","#b0cfba","#bed5b9","#d0dcb7","#abc7b8","#b9d2bf"].map(c=>new THREE.Color(c));
  const count=28;
  for (let i=0;i<count;i++) {
    const a=i/count*Math.PI*2,b=(i+1)/count*Math.PI*2;
    const rim=theta=>[Math.cos(theta)*16,-.2+(Math.sin(theta*5)*.09),Math.sin(theta)*8];
    vertices.push(0,-.23,0,...rim(a),...rim(b));
    const c=palette[i%palette.length];
    colors.push(...c.toArray(),...c.toArray(),...c.toArray());
  }
  const geometry=new THREE.BufferGeometry();
  geometry.setAttribute("position",new THREE.Float32BufferAttribute(vertices,3));
  geometry.setAttribute("color",new THREE.Float32BufferAttribute(colors,3));
  geometry.computeVertexNormals();
  const ground=new THREE.Mesh(geometry,new THREE.MeshStandardMaterial({vertexColors:true,flatShading:true,
    roughness:1,side:THREE.DoubleSide}));
  ground.receiveShadow=true; scene.add(ground);
  const base=new THREE.Mesh(new THREE.CylinderGeometry(1,1,.7,28),
    new THREE.MeshStandardMaterial({color:"#c3b4a0",flatShading:true,roughness:1}));
  base.scale.set(16,1,8); base.position.y=-.65; scene.add(base);
}

function makeClouds(scene) {
  const material=new THREE.MeshStandardMaterial({color:"#fff5eb",roughness:.85});
  for (const [x,y,z,scale] of [[-9,7,-7,1.2],[1,8,-10,.85],[10,6,-8,1.1]]) {
    const cloud=new THREE.Group(); cloud.position.set(x,y,z); cloud.scale.setScalar(scale);
    for (const [dx,dy,r] of [[-1,0,.8],[0,.3,1],[1,0,.7]]) {
      const puff=new THREE.Mesh(new THREE.SphereGeometry(r,20,14),material);
      puff.position.set(dx,dy,0); puff.scale.set(1,.65,.7); cloud.add(puff);
    }
    scene.add(cloud);
  }
}

import * as THREE from "../../vendor/three/three.module.js";
import {MERCHANTS,makeMerchant} from "./merchants.js";

const studies = [
  ...MERCHANTS.map((merchant,i) => ({...merchant,index:i+1})),
  {...MERCHANTS.find(m => m.id === "dwarf-woman"),index:7,beard:true}
];
const notes = ["Swept hair / oat apron","Coiled bun / rose tunic","Silver crop / sage tunic",
  "Gathered hair / saffron tunic","Copper beard / broad apron","Twin coils / moss apron","Optional tied beard"];
const swatches = ["#317f87","#985367","#637f62","#d9a144","#a95832","#84618c","#84618c"];
const angles = {front:0,"three-quarter":-Math.PI/4,back:Math.PI,board:0};

function makeCard(study,i) {
  const article = document.createElement("article");
  article.className = "merchant" + (study.beard ? " alternative" : "");
  article.style.setProperty("--swatch",swatches[i]);
  const top = document.createElement("div");top.className = "card-top";
  const number = document.createElement("span");number.textContent = String(study.index).padStart(2,"0");
  const swatch = document.createElement("span");swatch.className = "swatch";top.append(number,swatch);
  const portrait = document.createElement("div");portrait.className = "portrait";
  portrait.role = "img";portrait.setAttribute("aria-label",study.label + (study.beard ? " with beard" : "") + ", enlarged 3D study");
  const caption = document.createElement("div");caption.className = "caption";
  const label = document.createElement("h2");label.textContent = study.label;
  const note = document.createElement("p");note.textContent = notes[i];caption.append(label,note);
  if (study.id === "dwarf-woman") {
    const variant = document.createElement("span");variant.className = "variant";
    variant.textContent = study.beard ? "B / With beard" : "A / Without beard";caption.append(variant);
  }
  const miniature = document.createElement("div");miniature.className = "miniature";
  miniature.role = "img";miniature.setAttribute("aria-label",study.label + ", board scale");
  const miniLabel = document.createElement("span");miniLabel.className = "mini-label";miniLabel.textContent = "Board scale / 1 square";
  article.append(top,portrait,caption,miniature,miniLabel);
  return {article,portrait,miniature};
}

function lighting(scene) {
  // Same values, directions and colour management as board3d/scene.js.
  scene.add(new THREE.HemisphereLight("#f2f7ff","#afa38d",2));
  const sun = new THREE.DirectionalLight("#fff0d5",3.2);
  sun.position.set(-6,12,8);sun.castShadow = true;sun.shadow.mapSize.set(512,512);
  Object.assign(sun.shadow.camera,{left:-1,right:1,top:1,bottom:-1,near:.5,far:35});
  sun.shadow.normalBias = .012;sun.shadow.bias = -.0002;scene.add(sun);
  const fill = new THREE.DirectionalLight("#cee3ff",1.3);fill.position.set(8,6,-6);scene.add(fill);
}

function makeStage(study,small) {
  const scene = new THREE.Scene();lighting(scene);
  const figure = makeMerchant(study.id,study.beard ? {beard:true} : {});scene.add(figure);
  const ground = new THREE.Mesh(new THREE.PlaneGeometry(200,200),
    new THREE.MeshStandardMaterial({color:small ? "#e5e9dc" : "#edf0e4",roughness:1}));
  ground.rotation.x = -Math.PI/2;ground.receiveShadow = true;ground.position.y = -.001;scene.add(ground);
  if (small) {
    const line = new THREE.LineLoop(new THREE.BufferGeometry().setFromPoints([
      new THREE.Vector3(-.49,0,-.49),new THREE.Vector3(.49,0,-.49),
      new THREE.Vector3(.49,0,.49),new THREE.Vector3(-.49,0,.49)
    ]),new THREE.LineBasicMaterial({color:"#b1baa6"}));
    scene.add(line);
  }
  return {scene,figure,camera:new THREE.OrthographicCamera(-1,1,1,-1,.01,100),small};
}

export function startGallery() {
  const canvas = document.querySelector("#render-layer"), status = document.querySelector("#status");
  const renderer = new THREE.WebGLRenderer({canvas,antialias:true,alpha:true});
  renderer.setPixelRatio(Math.min(devicePixelRatio,2));
  renderer.shadowMap.enabled = true;renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;renderer.toneMappingExposure = 1.1;
  renderer.outputColorSpace = THREE.SRGBColorSpace;renderer.autoClear = false;
  const shelf = document.querySelector("#shelf"), stages = [];
  studies.forEach((study,i) => {
    const card = makeCard(study,i);shelf.append(card.article);
    stages.push({...makeStage(study,false),element:card.portrait},
      {...makeStage(study,true),element:card.miniature});
  });
  let angle = "front", requested = false;

  function drawStage(stage) {
    const rect = stage.element.getBoundingClientRect();
    const clip = shelf.parentElement.getBoundingClientRect();
    const left = Math.max(rect.left,clip.left,0), right = Math.min(rect.right,clip.right,innerWidth);
    const top = Math.max(rect.top,0), bottom = Math.min(rect.bottom,innerHeight);
    if (right <= left || bottom <= top) return;
    const extent = stage.small ? rect.height/88 : 1.06;
    const aspect = rect.width/rect.height, camera = stage.camera;
    camera.left = -extent*aspect/2;camera.right = extent*aspect/2;
    camera.top = extent/2;camera.bottom = -extent/2;
    const target = new THREE.Vector3(0,stage.small ? .18 : .35,0);
    const board = stage.small || angle === "board";
    camera.position.copy(target).add(board ? new THREE.Vector3(0,15,22) : new THREE.Vector3(.03,.20,3));
    camera.lookAt(target);camera.updateProjectionMatrix();
    stage.figure.rotation.y = stage.small ? 0 : angles[angle];
    renderer.setViewport(rect.left,innerHeight-rect.bottom,rect.width,rect.height);
    renderer.setScissor(left,innerHeight-bottom,right-left,bottom-top);
    renderer.clear(true,true,true);renderer.render(stage.scene,camera);
  }
  function draw() {
    requested = false;
    renderer.setScissorTest(false);renderer.setClearColor(0,0);renderer.clear(true,true,true);
    renderer.setScissorTest(true);stages.forEach(drawStage);
    canvas.dataset.ready = "true";
  }
  function invalidate() {
    if (requested || document.hidden) return;
    requested = true;requestAnimationFrame(draw);
  }
  function resize() { renderer.setSize(innerWidth,innerHeight,false);invalidate(); }
  document.querySelectorAll("[data-angle]").forEach(button => button.addEventListener("click",() => {
    angle = button.dataset.angle;
    document.querySelectorAll("[data-angle]").forEach(b => b.setAttribute("aria-pressed",String(b === button)));
    invalidate();
  }));
  addEventListener("resize",resize);
  addEventListener("scroll",invalidate,{capture:true,passive:true});
  document.addEventListener("visibilitychange",invalidate);
  new ResizeObserver(invalidate).observe(shelf);
  status.textContent = "Six merchants + one beard variant. Choose an angle to inspect every sculpt.";
  resize();
}

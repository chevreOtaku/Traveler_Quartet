const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {pathToFileURL} = require('node:url');
const L = require('../examples/board3d/layout.js');
const fixture = require('../examples/board3d/fixture.json');
const dataURL=source=>'data:text/javascript;base64,'+Buffer.from(source).toString('base64');

class Element {
  constructor() {
    this.children=[];this.style={setProperty(){}};this.attributes={};
    this.classList={add:name=>{this.className=(this.className||'')+' '+name;}};
    this.namespaceURI='http://www.w3.org/2000/svg';
  }
  append(...children){this.children.push(...children);}
  setAttribute(key,value){this.attributes[key]=value;}
  getContext(){return {fillRect(){},fillText(){}};}
}

test('real scene projection keeps all forty callouts on screen, isolates detail and renders on demand', async t => {
  const frames=[];
  for (const name of ['document','ResizeObserver','requestAnimationFrame','devicePixelRatio','Board3DRenderer']) {
    const prior=globalThis[name];t.after(()=>{if(prior===undefined)delete globalThis[name];else globalThis[name]=prior;});
  }
  globalThis.devicePixelRatio=1;
  globalThis.requestAnimationFrame=fn=>frames.push(fn);
  globalThis.document={hidden:false,createElement:()=>new Element(),createElementNS:()=>new Element(),
    createTextNode:text=>({textContent:text}),addEventListener(){}};
  globalThis.ResizeObserver=class {observe(){}};
  let rendered;
  globalThis.Board3DRenderer=class {
    constructor(){this.domElement=new Element();this.shadowMap={};}
    setPixelRatio(){} setSize(){}
    render(scene,camera){scene.updateMatrixWorld();camera.updateMatrixWorld();rendered=scene;}
  };
  const three=pathToFileURL(path.resolve('examples/vendor/three/three.module.js')).href;
  const pawnSource=fs.readFileSync('examples/board3d/pawn.js','utf8').replace('./vendor/three/three.module.js',three);
  const source=fs.readFileSync('examples/board3d/scene.js','utf8')
    .replace('./vendor/three/three.module.js',three).replace('./pawn.js',dataURL(pawnSource))
    .replace('new THREE.WebGLRenderer','new globalThis.Board3DRenderer');
  const {createScene}=await import(dataURL(source));
  const host=new Element(),labels=new Element();host.clientWidth=1862;host.clientHeight=810;
  const stage=createScene(host,labels);
  stage.setBoard(fixture.before.view.board);stage.setPlayers(fixture.before.view.players,[0,0,0,0]);
  assert.equal(frames.length,1);frames.shift()(0);
  const names=labels.children.filter(e=>e.className?.includes('tile-label'));
  assert.equal(names.length,40);
  for (const label of names) {
    const width=label.className.includes('side-label')?220:164;
    const x=parseFloat(label.style.left),y=parseFloat(label.style.top);
    assert.ok(x>=0 && x+width<=host.clientWidth,`label x ${x}`);
    assert.ok(y>=0 && y+44<=host.clientHeight,`label y ${y}`);
  }
  const pawns=rendered.children.filter(p=>p.userData.shape);
  assert.equal(pawns.filter(p=>p.visible).length,4);
  assert.equal(new Set(pawns.map(p=>p.position.x+','+p.position.z)).size,4);
  assert.equal(frames.length,0);
  stage.select(3);stage.setDetail(true);frames.shift()(1);
  assert.ok(names.every(e=>e.hidden));assert.deepEqual(pawns.filter(p=>p.visible).map(p=>p.userData.seat),[3]);
  stage.setDetail(false);frames.shift()(2);
  assert.ok(names.every(e=>!e.hidden));assert.equal(frames.length,0);
  stage.animate(()=>false);frames.shift()(3);assert.equal(frames.length,0);
  host.clientWidth=1420;host.clientHeight=760;stage.invalidate();frames.shift()(4);
  assert.ok(names.every(e=>parseFloat(e.style.left)>=0));
  assert.ok(fs.readFileSync('examples/board3d/style.css','utf8').includes('font-size:18px'));
});

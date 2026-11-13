const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {pathToFileURL} = require('node:url');
const L = require('../examples/board3d/layout.js');

test('forty unique unit squares form four continuous sides with an empty centre', () => {
  const points = Array.from({length:40}, (_,i)=>L.tilePosition(i));
  assert.equal(new Set(points.map(JSON.stringify)).size,40);
  assert.deepEqual([0,10,20,30].map(L.tilePosition), [[5,5],[-5,5],[-5,-5],[5,-5]]);
  points.forEach(([x,z],i)=>{
    assert.ok(Math.abs(x)===5 || Math.abs(z)===5);
    const next=points[(i+1)%40];
    assert.equal(Math.abs(x-next[0])+Math.abs(z-next[1]),1);
  });
  for (const i of [-1,40,1.5]) assert.throws(()=>L.tilePosition(i));
});

test('four fixed envelopes fit on one tile without overlapping', () => {
  const slots=Array.from({length:4},(_,i)=>L.seatOffset(i));
  slots.forEach(([x,z],i)=>{
    assert.ok(Math.abs(x)+L.PAWN_WIDTH/2 <= .5);
    assert.ok(Math.abs(z)+L.PAWN_WIDTH/2 <= .5);
    slots.slice(i+1).forEach(([a,b])=>assert.ok(
      Math.abs(x-a)>=L.PAWN_WIDTH || Math.abs(z-b)>=L.PAWN_WIDTH));
  });
  assert.deepEqual(L.seats.map(s=>s.shape),['circle','triangle','square','diamond']);
  assert.equal(new Set(L.seats.map(s=>s.color)).size,4);
  assert.throws(()=>L.seatOffset(4));
});

test('actual merchant geometry including its numbered base fits the miniature envelope', async () => {
  const threeURL=pathToFileURL(path.resolve('examples/vendor/three/three.module.js')).href;
  const three=await import(threeURL);
  let source=fs.readFileSync('examples/board3d/pawn.js','utf8');
  source=source.replace('./vendor/three/three.module.js',threeURL)
    .replace('./layout.js',pathToFileURL(path.resolve('examples/board3d/layout.js')).href);
  const {makeMerchant}=await import('data:text/javascript;base64,'+Buffer.from(source).toString('base64'));
  for (let seat=0;seat<4;seat++) {
    const pawn=makeMerchant(seat),box=new three.Box3().setFromObject(pawn,true),size=box.getSize(new three.Vector3());
    assert.ok(Math.abs(size.y-.70)<.001, `height ${size.y}`);
    assert.ok(size.x<=.42001 && size.z<=.42001, `footprint ${size.x}, ${size.z}`);
    assert.ok(Math.abs(box.min.y)<.001);
    assert.equal(pawn.userData.seat,seat);
    assert.equal(pawn.userData.shape,L.seats[seat].shape);
  }
});

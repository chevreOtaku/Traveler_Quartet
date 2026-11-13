const {test} = require('node:test');
const assert = require('node:assert/strict');
const M = require('../examples/board3d/movement.js');
const moved = (from, to, steps, travel='walk', kind='dice') =>
  ({kind:'moved', player:0, data:{from, to, steps, travel, kind}});

test('forward movement uses every signed step, including wrap and long walks', () => {
  assert.deepEqual(M.movementSquares(moved(38, 2, 4), 40), [39,0,1,2]);
  const route = M.movementSquares(moved(3, 5, 42), 40);
  assert.equal(route.length, 42);
  assert.deepEqual(route.slice(0,3), [4,5,6]);
  assert.equal(route.at(-1), 5);
});

test('negative steps walk backwards even when a forward route would be shorter', () => {
  assert.deepEqual(M.movementSquares(moved(1,38,-3,'walk','card'),40), [0,39,38]);
  assert.equal(M.movementSquares(moved(1,2,-39,'walk','card'),40).length,39);
});

test('teleportation supplies no walking squares and no intermediate hop', () => {
  const event = moved(5,15,null,'teleport','portal');
  assert.deepEqual(M.movementSquares(event,40), []);
  assert.deepEqual(M.motionFrame(event,40,0,false), {from:15,to:15,progress:1,lift:0,done:true});
});

test('missing or inconsistent contracts fail explicitly; the front chooses no direction', () => {
  for (const event of [moved(1,8,undefined), moved(1,8,2), moved(1,8,null),
    moved(1,8,7,'flight'), moved(1,8,7,'teleport'), moved(40,2,2),
    {...moved(1,2,1),kind:'jumped'}, {kind:'moved',data:{from:1,to:2,steps:1,travel:'walk'}}]) {
    assert.throws(() => M.movementSquares(event,40), /movement/i);
  }
  assert.throws(() => M.movementSquares(moved(1,2,1),0), /movement/i);
});

test('one hop per square finishes exactly at the engine destination', () => {
  const event = moved(38,1,3);
  assert.deepEqual(M.motionFrame(event,40,0,false), {from:38,to:39,progress:0,lift:0,done:false});
  const half = M.motionFrame(event,40,0.5,false);
  assert.equal(half.from,38); assert.equal(half.to,39);
  assert.equal(half.progress,0.5); assert.ok(half.lift > 0);
  assert.equal(M.motionFrame(event,40,1,false).from,39);
  assert.deepEqual(M.motionFrame(event,40,3,false), {from:1,to:1,progress:1,lift:0,done:true});
});

test('reduced motion immediately places the pawn without a hop', () => {
  assert.deepEqual(M.motionFrame(moved(1,38,-3,'walk','card'),40,0,true),
    {from:38,to:38,progress:1,lift:0,done:true});
});

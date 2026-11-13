const {test} = require('node:test');
const assert = require('node:assert/strict');
const C = require('../examples/board3d/client.js');
const fixture = require('../examples/board3d/fixture.json');
const clone = data => structuredClone(data);
const reply = data => ({ok:true,json:async()=>clone(data)});
const moved = (index,revision,seat,from,to,steps) =>
  ({index,revision,kind:'moved',player:seat,data:{from,to,steps,travel:'walk',kind:'dice'},sentence:'A move'});
const snap = (revision=1,end=1,position=1) => {
  const data=clone(fixture.before); data.revision=revision; data.log_length=end;
  data.view.players.forEach(p=>p.position=0); data.view.players[0].position=position;
  return data;
};

test('snapshot then bounded public events, no token, ordered awaited playback then snapshot', async () => {
  const calls=[],seen=[],data=snap(3,3,3);
  let release;
  const gate=new Promise(resolve=>release=resolve);
  const client=C.create({fetch:async(url,options)=>{calls.push([url,options]);
    return reply(url.includes('/events')?{events:[moved(0,1,0,0,1,1),moved(1,2,0,1,2,1),moved(2,3,0,2,3,1)]}:data);},
    onReset:(_,positions)=>seen.push(['reset',positions[0]]),
    onEvent:async row=>{seen.push(row.index); if(row.index===0) await gate;},
    onSnapshot:s=>seen.push(['snapshot',s.revision])});
  const pending=client.connect('a/b',true);
  await new Promise(setImmediate);
  assert.deepEqual(seen,[['reset',0],0]);
  release(); await pending;
  assert.deepEqual(seen,[['reset',0],0,1,2,['snapshot',3]]);
  assert.deepEqual(calls.map(c=>c[0]),['/games/a%2Fb/public','/games/a%2Fb/public/events?since=0&until=3']);
  assert.ok(calls.every(([,options])=>!options || !options.headers?.Authorization));
  assert.equal(client.cursor,3);
});

test('fixture route can be reversed from its public destination without assuming Start', () => {
  const positions=C.rewind(fixture.after,fixture.events);
  assert.deepEqual(positions,fixture.before.view.players.map(p=>p.position));
  const broken=clone(fixture.after); broken.view.players[2].position=17;
  assert.throws(()=>C.rewind(broken,fixture.events),/destination/i);
});

test('connect existing game skips history; eventless revision refreshes; new moves only once', async () => {
  let data=snap(),rows=[],events=[];
  const client=C.create({fetch:async url=>reply(url.includes('/events')?{events:rows}:data),
    onEvent:async row=>events.push(row.index)});
  await client.connect('watch');
  data=snap(2,1); await client.refresh();
  assert.equal(client.snapshot.revision,2); assert.deepEqual(events,[]);
  data=snap(4,2,3); rows=[moved(1,4,0,1,3,2)];
  await client.refresh(); await client.refresh();
  assert.deepEqual(events,[1]); assert.equal(client.cursor,2);
});

test('gap, duplicate, reordered, bad revision or route triggers fresh snapshot resynchronization', async () => {
  const badWindows=[[],[moved(2,2,0,1,2,1)],
    [moved(1,2,0,1,2,1),moved(1,2,0,2,3,1)],
    [moved(1,4,0,1,2,1)], [moved(1,0,0,1,2,1)], [moved(1,2,0,7,2,1)]];
  for (const rows of badWindows) {
    let data=snap(),resets=[],errors=[],events=[];
    const client=C.create({fetch:async url=>reply(url.includes('/events')?{events:rows}:data),
      onReset:(_,positions)=>resets.push(positions),onResync:reason=>errors.push(reason),
      onEvent:row=>events.push(row.index)});
    await client.connect('g'); data=snap(3,2,2); await client.refresh();
    assert.equal(client.cursor,2); assert.deepEqual(events,[]);
    assert.equal(errors.length,1); assert.deepEqual(resets.at(-1),[2,0,0,0]);
  }
});

test('future events stay outside exclusive watermark and wrong arrival cannot animate', async () => {
  let data=snap(),rows=[],events=[];
  const client=C.create({fetch:async url=>reply(url.includes('/events')?{events:rows}:data),onEvent:row=>events.push(row.index)});
  await client.connect('g'); data=snap(2,2,2);
  rows=[moved(1,2,0,1,2,1),moved(2,3,0,2,3,1)]; await client.refresh();
  assert.deepEqual(events,[1]);
  data=snap(3,3,9); rows=[moved(2,3,0,2,3,1)]; await client.refresh();
  assert.deepEqual(events,[1]); assert.equal(client.cursor,3);
});

test('network failures preserve cursor for retry; concurrent refresh is serialized', async () => {
  let data=snap(),fail=false,calls=0;
  const client=C.create({fetch:async url=>{calls++;if(fail && url.includes('/events'))throw Error('offline');
    return reply(url.includes('/events')?{events:[moved(1,2,0,1,2,1)]}:data);}});
  await client.connect('g'); data=snap(2,2,2); fail=true;
  await assert.rejects(client.refresh(),/offline/); assert.equal(client.cursor,1);
  fail=false; const a=client.refresh(),b=client.refresh(); await Promise.all([a,b]);
  assert.equal(client.cursor,2); assert.equal(calls,5);
});

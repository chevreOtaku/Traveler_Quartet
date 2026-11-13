const {test}=require('node:test');
const assert=require('node:assert/strict');
const M=require('../examples/board/model.js');
const Client=require('../examples/board/client.js');
const snapshot=(n=0,revision=0)=>({view:{board:[],me:{seat:0,position:1},others:[],current:0,actor:0,pending:'buy',your_turn:true,legal_actions:['buy','pass'],negotiations:[]},over:false,log_length:n,revision});
function harness(spectator=false) {
  const calls=[],replies=[],events=[],states=[];
  const client=Client.create({fetch:async(path,options={})=>{
    calls.push({path,options}); const body=replies.shift();
    if(body instanceof Error) throw body;
    assert.ok(body,'unexpected request '+path);
    return {ok:true,json:async()=>body};
  },onState:s=>states.push(s),onEvents:(rows,reset)=>events.push({rows,reset})});
  return {client,calls,replies,events,states,spectator};
}
test('forty squares map uniquely around the perimeter including all corners',()=>{
  const cells=Array.from({length:40},(_,i)=>M.tilePosition(i));
  assert.equal(new Set(cells.map(String)).size,40);
  assert.deepEqual([cells[0],cells[10],cells[20],cells[30]],[[11,11],[11,1],[1,1],[1,11]]);
  assert.ok(cells.every(([r,c])=>r===1||r===11||c===1||c===11));
  assert.throws(()=>M.tilePosition(40));
});
test('public players never depend on a private seat; utility rent stays a multiplier',()=>{
  assert.deepEqual(M.players({players:[{seat:2}]}),[{seat:2}]);
  assert.equal(M.rentText({rent:null,rent_per_dice_point:4}),'4 G per dice point');
  assert.equal(M.allowed(snapshot(),'offer:1'),false);
  assert.equal(M.allowed(snapshot(),'buy'),true);
  assert.equal(M.allowed({...snapshot(),over:true},'buy'),false);
});
test('spectator only reads public endpoints and cannot act even if passed a token',async()=>{
  const h=harness(); h.replies.push(snapshot());
  await h.client.connect({game:'table',token:'secret',spectator:true});
  assert.equal(await h.client.act('buy','hello'),false);
  assert.equal(h.calls.length,1);
  assert.equal(h.calls[0].path,'/games/table/public');
  assert.equal(h.calls[0].options.headers.Authorization,undefined);
});
test('events beyond the snapshot watermark wait for the next snapshot and do not duplicate',async()=>{
  const h=harness(); h.replies.push(snapshot(1),{events:[{index:0,sentence:'first'},{index:1,sentence:'later'}]});
  await h.client.connect({game:'table',token:'secret'});
  assert.equal(h.client.cursor,1);
  assert.deepEqual(h.events.flatMap(e=>e.rows).map(e=>e.index),[0]);
  h.replies.push(snapshot(2,1),{events:[{index:1,sentence:'later'}]});
  await h.client.refresh();
  assert.equal(h.client.cursor,2);
  assert.deepEqual(h.events.flatMap(e=>e.rows).map(e=>e.index),[0,1]);
  assert.ok(h.calls.some(c=>c.path.includes('since=1&until=2')));
});
test('a changed question never receives the old click',async()=>{
  const h=harness(); h.replies.push(snapshot());
  await h.client.connect({game:'table',token:'secret'});
  const changed=snapshot(0,1); changed.view.me.position=3;
  h.replies.push(changed);
  await assert.rejects(h.client.act('buy','keep this'),/changed/);
  assert.equal(h.calls.filter(c=>c.options.method==='POST').length,0);
});
test('one legal action uses a header token and revision; it is never retried automatically',async()=>{
  const h=harness(); const s=snapshot();
  h.replies.push(s); await h.client.connect({game:'table',token:'secret'});
  const done={...snapshot(),over:true};
  h.replies.push(s,done);
  assert.equal(await h.client.act('buy','hello'),true);
  const posts=h.calls.filter(c=>c.options.method==='POST');
  assert.equal(posts.length,1);
  assert.equal(posts[0].options.headers.Authorization,'Bearer secret');
  assert.deepEqual(JSON.parse(posts[0].options.body),{action:'buy',message:'hello',expected_revision:0});
  assert.ok(h.calls.every(c=>!c.path.includes('secret')));
});
test('a failed final event read remains pending and can recover after game over',async()=>{
  const h=harness(); h.replies.push(snapshot());
  await h.client.connect({game:'table',token:'secret'});
  h.replies.push(snapshot(),{...snapshot(1,1),over:true},new Error('journal offline'));
  assert.equal(await h.client.act('buy','hello'),true);
  assert.equal(h.client.pendingEvents,true);
  h.replies.push({...snapshot(1,1),over:true},{events:[{index:0,sentence:'done'}]});
  await h.client.refresh();
  assert.equal(h.client.pendingEvents,false);
  assert.equal(h.client.cursor,1);
});

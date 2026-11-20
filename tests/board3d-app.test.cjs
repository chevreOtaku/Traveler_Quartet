const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const fixture = require('../examples/board3d/fixture.json');
const tick=()=>new Promise(setImmediate);

function page(search='',reduced=false,table='computers',mine={your_turn:true,legal_actions:['roll']},options={}) {
  const elements=new Map(),calls=[],places=[],poses=[],timers=[],follows=[];
  let animation=null;
  function element(id) {
    if (!elements.has(id)) {
      const made={value:'',children:[],handlers:{},style:{setProperty(){}},
        classList:{toggle(){}},setAttribute(){},append(...items){this.children.push(...items);},
        replaceChildren(...items){this.children=[...items];},addEventListener(kind,fn){this.handlers[kind]=fn;},
        click(){return this.handlers.click?.();}};
      const data={};Object.defineProperty(made,'dataset',{get:()=>data,enumerable:true});
      elements.set(id,made);
    }
    return elements.get(id);
  }
  const motion={matches:reduced,addEventListener(_,fn){this.change=fn;}};
  const snapshot=structuredClone(fixture.after);
  snapshot.revision=1;snapshot.log_length=1;snapshot.over=options.over ?? true;
  snapshot.view.players.forEach(p=>{p.position=0;p.out=false;});snapshot.view.players[0].position=1;
  const event={index:0,revision:1,round:1,kind:'moved',player:0,sentence:'player 0 walked three squares',
    data:{from:38,to:1,steps:3,travel:'walk',kind:'dice'}};
  const stage={setBoard(){},setPlayers(players,positions){if(positions)places.push([...positions]);},
    place:(seat,index)=>places.push([seat,index]),pose:(seat,frame)=>poses.push([seat,frame]),
    select(){},highlight(){},setOut(){},setDetail(){},setFollow:seat=>follows.push(seat),stop(){animation=null;},
    animate(fn){animation=fn;}};
  if (table==='human') snapshot.seats=['human','computer','computer','computer'];
  const seatView={view:mine,over:false,revision:1};
  const reply=url=>url.includes('fixture')?fixture:url==='/games'?{game:'real-id',tokens:table==='human'?{tok:0}:{}}:
    url.endsWith('/view')||url.endsWith('/act')?seatView:url.includes('/events')?{events:[event]}:snapshot;
  const context=vm.createContext({URLSearchParams,createScene:()=>stage,matchMedia:()=>motion,
    location:{search},history:{replaceState(){}},document:{getElementById:element,createElement:()=>element(Symbol())},
    sessionStorage:{store:{},getItem(k){return this.store[k]??null;},setItem(k,v){this.store[k]=v;}},
    clearTimeout(){},setTimeout:(fn,delay)=>{timers.push([fn,delay]);return timers.length;},
    fetch:async(url,init)=>{calls.push([url,init]);
      if (options.refuse && url.endsWith('/act')) return {ok:false,json:async()=>({error:options.refuse})};
      return {ok:true,json:async()=>structuredClone(reply(url))};}});
  for (const name of ['layout','movement','camera','play','trade','client']) vm.runInContext(fs.readFileSync(`examples/board3d/${name}.js`,'utf8'),context);
  vm.runInContext(fs.readFileSync('examples/board3d/app.js','utf8').replace(/^import .*;\r?\n/,''),context);
  element('seed').value='1';element('rounds').value='5';element('table').value=table;
  return {element,calls,places,poses,motion,timers,snapshot,follows,
    frame(now){if(animation && !animation(now))animation=null;},
    submit:id=>element(id).handlers.submit({preventDefault(){}})};
}

test('page creates four computers and plays the real public route before the final snapshot', async () => {
  const p=page();p.submit('start-form');await tick();
  assert.equal(p.element('start').disabled,true);
  assert.deepEqual(JSON.parse(p.calls[0][1].body),{seats:['normal','normal','normal','normal'],seed:1,rounds:5});
  assert.deepEqual(p.calls.slice(1).map(c=>c[0]),['/games/real-id/public','/games/real-id/public/events?since=0&until=1']);
  assert.deepEqual(p.places[0],[38,0,0,0]);
  p.frame(0);p.frame(260);p.frame(520);p.frame(780);await tick();
  assert.deepEqual(p.poses.map(([,f])=>f.to),[39,0,1,1]);
  assert.equal(p.element('start').disabled,false);
  assert.match(p.element('status').textContent,/Game complete/);
  assert.equal(p.timers.length,0);
  assert.ok(p.calls.every(([url,options])=>!url.includes('/view') && !url.includes('/act') && !options?.headers?.Authorization));
  assert.equal(p.element('towns').children.length,8);
  assert.equal(p.element('squares').children.length,40);
});

test('a table without a human never moves the camera', async () => {
  const p=page();p.submit('start-form');await tick();
  p.frame(0);p.frame(260);p.frame(520);p.frame(780);await tick();
  assert.deepEqual(p.follows,[]);
});

test('with a human: the camera follows the human pawn, then returns; the seat acts with its token', async () => {
  const p=page('',false,'human');p.submit('start-form');await tick();
  assert.deepEqual(JSON.parse(p.calls[0][1].body).seats,['human','normal','normal','normal']);
  assert.deepEqual(p.follows,[0]);
  p.frame(0);p.frame(380);p.frame(760);p.frame(1140);await tick();
  const hold=p.timers.find(([,delay])=>delay===650);
  assert.ok(hold,'a short hold at the arrival before the camera goes back');
  hold[0]();await tick();await tick();
  assert.deepEqual(p.follows,[0,null]);
  const view=p.calls.find(([url])=>url.endsWith('/view'));
  assert.equal(view[1].headers.Authorization,'Bearer tok');
  const [button]=p.element('actions').children;
  assert.equal(button.textContent,'Roll the dice');
  button.handlers.click();await tick();
  const act=p.calls.find(([url])=>url.endsWith('/act'));
  assert.deepEqual(JSON.parse(act[1].body),{action:'roll',expected_revision:1});
  assert.equal(act[1].headers.Authorization,'Bearer tok');
  assert.ok(p.calls.every(([url])=>!url.includes('tok')),'the token never goes in a URL');
});

function tradeView(extra) {
  const board=fixture.after.view.board.map(sq=>({...sq,owner:null,buildings:0}));
  board[1].owner=0;board[3].owner=1;
  return {your_turn:true,me:{seat:0,cash:500,cards:[]},board,...extra};
}
const all=node=>[node,...(node.children||[]).flatMap(all)];

test('with a human: an open negotiation gives a trade form whose contract goes to the engine', async () => {
  const p=page('',true,'human',tradeView({legal_actions:['roll'],negotiations:['offer:1']}));
  p.submit('start-form');await tick();await tick();
  const nodes=p.element('actions').children.flatMap(all);
  assert.equal(nodes.filter(n=>n.className==='trade').length,1);
  nodes.find(n=>n.name==='give_gold').value='40';
  nodes.find(n=>n.type==='checkbox' && n.dataset.side==='ask').checked=true;
  nodes.find(n=>n.name==='send').handlers.click();await tick();
  const act=p.calls.find(([url])=>url.endsWith('/act'));
  assert.deepEqual(JSON.parse(act[1].body),{action:'offer:1:40:::0:3:',expected_revision:1});
});

test('with a human: an offer waiting for an answer is said in words before Accept and Refuse', async () => {
  const trade={proposer:1,responder:0,counters:0,terms:{give_gold:45,give_squares:[],give_cards:[],ask_gold:0,
    ask_squares:[1],ask_cards:[]}};
  const v=tradeView({legal_actions:['accept','refuse'],negotiations:['counter'],trade});
  const p=page('',true,'human',v);p.submit('start-form');await tick();await tick();
  const [words,accept,refuse,form]=p.element('actions').children;
  assert.equal(words.textContent,`Player 1 offers you 45 gold in exchange for ${v.board[1].name}.`);
  assert.deepEqual([accept.textContent,refuse.textContent],['Accept','Refuse']);
  assert.equal(form.className,'trade');
});

test('with a human: the periodic refresh keeps what the human is typing in the trade form', async () => {
  const p=page('',true,'human',tradeView({legal_actions:['roll'],negotiations:['offer:1']}),{over:false});
  p.submit('start-form');await tick();await tick();
  const form=p.element('actions').children.find(n=>n.className==='trade');
  const nodes=all(form);
  nodes.find(n=>n.name==='give_gold').value='40';
  nodes.find(n=>n.type==='checkbox' && n.dataset.side==='ask').checked=true;
  const refresh=p.timers.findLast(([,delay])=>delay===1500);
  assert.ok(refresh,'the table refreshes itself');
  refresh[0]();for (let i=0;i<6;i++) await tick();
  assert.equal(p.element('actions').children.find(n=>n.className==='trade'),form,'the same form, not a new empty one');
  nodes.find(n=>n.name==='send').handlers.click();await tick();
  const act=p.calls.find(([url])=>url.endsWith('/act'));
  assert.equal(JSON.parse(act[1].body).action,'offer:1:40:::0:3:');
});

test('with a human: a refused offer stays said after the next refresh', async () => {
  const refuse="'offer:1:0:::0::' is not a legal contract now";
  const p=page('',true,'human',tradeView({legal_actions:['roll'],negotiations:['offer:1']}),{over:false,refuse});
  p.submit('start-form');for (let i=0;i<6;i++) await tick();
  all(p.element('actions').children.find(n=>n.className==='trade')).find(n=>n.name==='send').handlers.click();
  for (let i=0;i<4;i++) await tick();
  assert.ok(p.calls.some(([url])=>url.endsWith('/act')),'the offer was sent');
  assert.match(p.element('error').textContent,/not a legal contract/);
  p.timers.findLast(([,delay])=>delay===1500)[0]();for (let i=0;i<6;i++) await tick();
  assert.match(p.element('error').textContent,/not a legal contract/);
});

test('with a human: no trade form when it is not the human turn', async () => {
  const p=page('',true,'human',tradeView({your_turn:false,legal_actions:[],negotiations:['offer:1']}));
  p.submit('start-form');await tick();await tick();
  assert.deepEqual(p.element('actions').children,[]);
});

test('with a human but reduced motion: no camera move at all', async () => {
  const p=page('',true,'human');p.submit('start-form');await tick();
  assert.deepEqual(p.follows,[]);
});

test('fixture mode uses no server and reduced motion places every merchant directly', async () => {
  const p=page('?mode=fixture',true);await tick();
  assert.deepEqual(p.calls.map(c=>c[0]),['./fixture.json']);
  assert.equal(p.element('setup').hidden,true);
  assert.equal(p.poses.length,0);
  assert.ok(p.places.some(([seat,index])=>seat===2 && index===4));
  assert.match(p.element('status').textContent,/fixture move complete/);
});

test('motion preference change and Go to latest both settle an active hop', async () => {
  for (const preference of [true,false]) {
    const p=page();p.submit('start-form');await tick();p.frame(0);p.frame(130);
    assert.ok(p.poses.at(-1)[1].lift>0);
    if(preference){p.motion.matches=true;p.motion.change();}else p.element('skip').click();
    await tick();
    assert.deepEqual(p.places.at(-1),[0,1]);
    assert.equal(p.element('start').disabled,false);
    assert.match(p.element('status').textContent,/Game complete/);
  }
});

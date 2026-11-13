const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const fixture = require('../examples/board3d/fixture.json');
const tick=()=>new Promise(setImmediate);

function page(search='',reduced=false) {
  const elements=new Map(),calls=[],places=[],poses=[],timers=[];
  let animation=null;
  function element(id) {
    if (!elements.has(id)) elements.set(id,{value:'',children:[],handlers:{},style:{setProperty(){}},
      classList:{toggle(){}},setAttribute(){},append(...items){this.children.push(...items);},
      replaceChildren(){this.children=[];},addEventListener(kind,fn){this.handlers[kind]=fn;},
      click(){return this.handlers.click?.();}});
    return elements.get(id);
  }
  const motion={matches:reduced,addEventListener(_,fn){this.change=fn;}};
  const snapshot=structuredClone(fixture.after);
  snapshot.revision=1;snapshot.log_length=1;snapshot.over=true;
  snapshot.view.players.forEach(p=>{p.position=0;p.out=false;});snapshot.view.players[0].position=1;
  const event={index:0,revision:1,round:1,kind:'moved',player:0,sentence:'player 0 walked three squares',
    data:{from:38,to:1,steps:3,travel:'walk',kind:'dice'}};
  const stage={setBoard(){},setPlayers(players,positions){if(positions)places.push([...positions]);},
    place:(seat,index)=>places.push([seat,index]),pose:(seat,frame)=>poses.push([seat,frame]),
    select(){},highlight(){},setOut(){},setDetail(){},stop(){animation=null;},
    animate(fn){animation=fn;}};
  const context=vm.createContext({URLSearchParams,createScene:()=>stage,matchMedia:()=>motion,
    location:{search},history:{replaceState(){}},document:{getElementById:element,createElement:()=>element(Symbol())},
    clearTimeout(){},setTimeout:(fn,delay)=>{timers.push([fn,delay]);return timers.length;},
    fetch:async(url,options)=>{calls.push([url,options]);return {ok:true,json:async()=>structuredClone(
      url.includes('fixture')?fixture:url==='/games'?{game:'real-id',tokens:{}}:
        url.includes('/events')?{events:[event]}:snapshot)};}});
  for (const name of ['layout','movement','client']) vm.runInContext(fs.readFileSync(`examples/board3d/${name}.js`,'utf8'),context);
  vm.runInContext(fs.readFileSync('examples/board3d/app.js','utf8').replace(/^import .*;\r?\n/,''),context);
  element('seed').value='1';element('rounds').value='5';
  return {element,calls,places,poses,motion,timers,snapshot,
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

// Browser logic with a small DOM substitute; no external test library.
const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

function browser() {
  const elements = new Map();
  function element(id = '') {
    return {id, value: '', textContent: '', hidden: false, disabled: false, children: [],
      handlers: {}, addEventListener(type, fn) { this.handlers[type] = fn; },
      append(...children) { this.children.push(...children); },
      replaceChildren(...children) { this.children = children; }};
  }
  const document = {getElementById(id) {
    if (!elements.has(id)) elements.set(id, element(id));
    return elements.get(id);
  }, createElement: () => element()};
  const calls = [], replies = [], timers = [];
  const context = vm.createContext({document, location: {reload() {}},
    setTimeout(fn, ms) { timers.push({fn, ms}); return timers.length; }, clearTimeout() {},
    fetch: async (path, options = {}) => {
      calls.push({path, options});
      const next = replies.shift();
      if (next instanceof Error) throw next;
      assert.ok(next, `Unexpected request: ${path}`);
      return {ok: next.status === undefined || next.status < 400, status: next.status || 200,
        json: async () => next.body};
    }});
  const html = fs.readFileSync('src/traveler_quartet/web/index.html', 'utf8');
  vm.runInContext(html.match(/<script>([\s\S]*?)<\/script>/)[1], context);
  return {get: document.getElementById, calls, replies, timers,
    run: expression => vm.runInContext(expression, context)};
}

const seen = (over = false, negotiations = ['offer:1']) => ({text: '<unsafe table message>', over,
  view: {your_turn: !over, legal_actions: over ? [] : ['roll', 'buy'], negotiations}});

async function start(b) {
  b.get('count').value = '3'; b.get('seed').value = '7';
  for (let n = 1; n <= 3; n++) b.get(`bot${n}`).value = 'normal';
  b.replies.push({body: {game: 'table', tokens: {'secret-token': 0}}},
    {body: seen()}, {body: {events: [{index: 0, round: 1, kind: 'said', player: 0, data: {text: '<hello>'}}]}});
  await b.run('startGame()');
}

test('one human and three computers; token in headers, text stays text', async () => {
  const b = browser(); await start(b);
  assert.deepEqual(JSON.parse(b.calls[0].options.body), {seats: ['remote','normal','normal','normal'], seed: 7});
  assert.equal(b.calls[1].options.headers.Authorization, 'Bearer secret-token');
  assert.ok(b.calls.every(c => !c.path.includes('secret-token')));
  assert.equal(b.get('state').textContent, '<unsafe table message>');
  assert.deepEqual(b.get('actions').children.map(c => c.textContent), ['roll', 'buy']);
  assert.equal(b.timers.at(-1).ms, 1500);
});

test('events append from the last consumed index, including after a network failure', async () => {
  const b = browser(); await start(b);
  const first = b.get('log').textContent;
  b.replies.push({body: seen()}, new Error('offline'));
  await b.run('poll()');
  assert.equal(b.get('log').textContent, first);
  b.replies.push({body: seen()}, {body: {events: [
    {index: 0, kind: 'said'}, {index: 1, kind: 'rolled'}]}});
  await b.run('poll()');
  assert.ok(b.calls.at(-1).path.endsWith('since=1'));
  assert.equal(b.get('log').textContent.split('"index":0').length, 2);
  assert.match(b.get('log').textContent, /rolled/);
});

test('trade form builds full offers and counter-offers, never a bare template', () => {
  const b = browser();
  b.get('recipient').value = 'offer:2';
  b.get('giveGold').value = '40'; b.get('giveSquares').value = '1, 3';
  b.get('giveCards').value = 'rope'; b.get('askGold').value = '0';
  b.get('askSquares').value = '6'; b.get('askCards').value = '';
  assert.equal(b.run('tradeAction()'), 'offer:2:40:1,3:rope:0:6:');
  b.get('recipient').value = 'counter';
  assert.equal(b.run('tradeAction()'), 'counter:40:1,3:rope:0:6:');
});

test('actions carry the message; game over removes actions and stops polling', async () => {
  const b = browser(); await start(b);
  b.get('message').value = 'good luck';
  b.replies.push({body: seen(true, [])}, {body: {events: []}});
  const timers = b.timers.length;
  await b.run('play("buy")');
  const call = b.calls.find(c => c.path.endsWith('/act'));
  assert.deepEqual(JSON.parse(call.options.body), {action: 'buy', message: 'good luck'});
  assert.equal(b.get('actions').children.length, 0);
  assert.equal(b.get('trade').hidden, true);
  assert.equal(b.get('message').value, '');
  assert.equal(b.timers.length, timers);
});

test('a refused action preserves the message and shows the server error', async () => {
  const b = browser(); await start(b); b.get('message').value = 'keep me';
  b.replies.push({status: 400, body: {error: 'not legal now'}}, {body: seen()}, {body: {events: []}});
  await b.run('play("buy")');
  assert.equal(b.get('message').value, 'keep me');
  assert.match(b.get('error').textContent, /not legal now/);
});

test('a failed final journal read is retried even when the game is over', async () => {
  const b = browser(); await start(b);
  b.replies.push({body: seen(true, [])}, new Error('journal offline'));
  const timers = b.timers.length;
  await b.run('play("buy")');
  assert.equal(b.timers.length, timers + 1);
  b.replies.push({body: seen(true, [])}, {body: {events: [{index: 1, kind: 'game_over'}]}});
  await b.run('poll()');
  assert.match(b.get('log').textContent, /game_over/);
  assert.equal(b.timers.length, timers + 1);
});

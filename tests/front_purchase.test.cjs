const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
function model(mode = 'player') {
  const ctx = vm.createContext({});
  vm.runInContext(fs.readFileSync('examples/front-purchase/fixtures.js', 'utf8'), ctx);
  vm.runInContext(fs.readFileSync('examples/front-purchase/model.js', 'utf8'), ctx);
  return vm.runInContext(`PurchaseScene.create(PURCHASE_FIXTURES, "${mode}")`, ctx);
}
test('buy selects a confirmed snapshot once; it never deducts twice', () => {
  const m = model();
  assert.equal(m.state.board[1].owner, null);
  assert.equal(m.select('buy'), true);
  assert.equal(m.state.board[1].owner, 0);
  const cash = m.state.players[0].cash;
  assert.equal(m.select('buy'), false);
  assert.equal(m.select('pass'), false);
  assert.equal(m.state.players[0].cash, cash);
});
test('stream is read-only, even when select is called directly', () => {
  const m = model('stream');
  assert.equal(m.select('buy'), false);
  assert.equal(m.phase, 'initial');
  assert.equal(m.state.board[1].owner, null);
  m.setMode('player');
  assert.equal(m.select('pass'), true);
  assert.equal(m.state.pending, 'auction');
  assert.equal(m.state.board[1].owner, null);
});
test('mode switches preserve the scene; reset restores the public fixture', () => {
  const m = model();
  m.select('buy'); m.setMode('stream');
  assert.equal(m.phase, 'buy');
  assert.equal(m.state.board[1].owner, 0);
  m.reset();
  assert.equal(m.mode, 'stream');
  assert.equal(m.phase, 'initial');
  assert.equal(m.state.board[1].owner, null);
  assert.equal(m.select('bid:55'), false);
  assert.throws(() => m.setMode('invalid'));
});
test('presentation cannot mutate fixture state or leak private player fields', () => {
  const m = model();
  assert.ok(Object.isFrozen(m.state.board[1]));
  for (const p of m.state.players) assert.equal('cards' in p, false);
  for (const key of ['seed', 'decks', 'legal_actions', 'tokens', 'me']) assert.equal(key in m.state, false);
});

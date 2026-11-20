const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {pathToFileURL} = require('node:url');

const threeURL = pathToFileURL(path.resolve('examples/vendor/three/three.module.js')).href;
const THREE = import(threeURL);
const art = (async () => {
  const source = fs.readFileSync('examples/board3d/art/merchants.js', 'utf8')
    .replace('../../vendor/three/three.module.js', threeURL);
  return import('data:text/javascript;base64,' + Buffer.from(source).toString('base64'));
})();

function meshes(group) {
  const result = [];
  group.traverse(part => { if (part.isMesh) result.push(part); });
  return result;
}

test('catalogue contains exactly the six ordinary merchants', async () => {
  const {MERCHANTS} = await art;
  assert.equal(MERCHANTS.length, 6);
  assert.equal(new Set(MERCHANTS.map(m => m.id)).size, 6);
  assert.deepEqual(MERCHANTS.map(m => [m.people, m.gender]).sort(),
    ['human', 'elf', 'dwarf'].flatMap(p => ['male', 'female'].map(g => [p, g])).sort());
  for (const entry of MERCHANTS) assert.ok(entry.label.length > 3);
});

test('all seven sculpts have grounded feet, half-height heads and a seat-free .70 by .42 envelope', async () => {
  const {MERCHANTS, makeMerchant} = await art;
  const {Box3, Vector3, Group} = await THREE;
  const figures = MERCHANTS.map(m => makeMerchant(m.id));
  figures.push(makeMerchant('dwarf-woman', {beard: true}));
  for (const figure of figures) {
    assert.ok(figure instanceof Group);
    const bounds = new Box3().setFromObject(figure, true);
    const size = bounds.getSize(new Vector3());
    assert.ok(Math.abs(bounds.min.y) < 1e-6, `${figure.name}: grounded`);
    assert.ok(Math.abs(size.y - .70) < 1e-6, `${figure.name}: height ${size.y}`);
    assert.ok(size.x <= .420001 && size.z <= .420001, `${figure.name}: footprint ${size.toArray()}`);
    assert.ok(Math.abs(bounds.min.x + bounds.max.x) < 1e-6);
    assert.ok(Math.abs(bounds.min.z + bounds.max.z) < 1e-6);
    const head = new Box3().setFromObject(figure.getObjectByName('head'), true);
    assert.ok(head.getSize(new Vector3()).y / size.y >= .43);
    for (const name of ['apron', 'satchel', 'left-eye', 'right-eye', 'hair', 'ears']) {
      assert.ok(figure.getObjectByName(name), `${figure.name}: ${name}`);
    }
    assert.equal(figure.userData.seat, undefined);
    assert.equal(figure.getObjectByName('base'), undefined);
    for (const mesh of meshes(figure)) {
      assert.ok(mesh.castShadow && mesh.receiveShadow);
      assert.ok(mesh.material.isMeshPhysicalMaterial);
      assert.ok(mesh.material.roughness <= .4 && mesh.material.clearcoat > 0);
      assert.equal(mesh.material.map, null, 'all features are original primitives');
    }
  }
});

test('bearded dwarf woman is an explicit extra sculpt; female default has no beard', async () => {
  const {makeMerchant} = await art;
  const plain = makeMerchant('dwarf-woman');
  const bearded = makeMerchant('dwarf-woman', {beard: true});
  assert.equal(plain.getObjectByName('beard'), undefined);
  assert.ok(bearded.getObjectByName('beard'));
  assert.ok(makeMerchant('dwarf-man').getObjectByName('beard'));
  assert.equal(plain.userData.beard, false);
  assert.equal(bearded.userData.beard, true);
  assert.ok(meshes(bearded).length > meshes(plain).length);
});

test('sculpts share GPU resources while instances keep independent transforms', async () => {
  const {MERCHANTS, makeMerchant} = await art;
  const first = makeMerchant('human-man'), second = makeMerchant('human-man');
  const firstMesh = meshes(first), secondMesh = meshes(second);
  firstMesh.forEach((mesh, i) => {
    assert.equal(mesh.geometry, secondMesh[i].geometry);
    assert.equal(mesh.material, secondMesh[i].material);
    assert.notEqual(mesh, secondMesh[i]);
  });
  first.position.x = 8;
  assert.equal(second.position.x, 0);
  const all = MERCHANTS.flatMap(m => meshes(makeMerchant(m.id)));
  assert.ok(new Set(all.map(m => m.geometry)).size < 24, 'pooled primitives');
  assert.ok(new Set(all.map(m => m.material)).size < 60, 'pooled palette');
  const hairSignatures = MERCHANTS.map(m => JSON.stringify(makeMerchant(m.id)
    .getObjectByName('hair').children.map(p => [p.position.toArray(), p.scale.toArray(), p.rotation.toArray()])));
  assert.equal(new Set(hairSignatures).size, 6, 'six sculpted hairstyles, not only recolours');
});

test('integration mistakes fail explicitly', async () => {
  const {makeMerchant} = await art;
  assert.throws(() => makeMerchant('wizard'), /merchant/i);
  assert.throws(() => makeMerchant(0), /merchant/i);
  assert.throws(() => makeMerchant('human-man', null), /options/i);
  assert.throws(() => makeMerchant('dwarf-woman', {beard: 'yes'}), /beard/i);
  assert.throws(() => makeMerchant('human-woman', {beard: true}), /beard/i);
});

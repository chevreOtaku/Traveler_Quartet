import * as THREE from "../../vendor/three/three.module.js";

// Original toy sculpts. +Z is the face; modelling units are normalized at the end.
export const MERCHANTS = Object.freeze([
  {id:"human-man", people:"human", gender:"male", label:"Human man"},
  {id:"human-woman", people:"human", gender:"female", label:"Human woman"},
  {id:"elf-man", people:"elf", gender:"male", label:"Elf man"},
  {id:"elf-woman", people:"elf", gender:"female", label:"Elf woman"},
  {id:"dwarf-man", people:"dwarf", gender:"male", label:"Dwarf man"},
  {id:"dwarf-woman", people:"dwarf", gender:"female", label:"Dwarf woman"}
].map(Object.freeze));

const looks = {
  "human-man": {skin:"#bc805b", hair:"#302a32", cloth:"#317f87", apron:"#f2d8ac", iris:"#b37536"},
  "human-woman": {skin:"#f1bb99", hair:"#864039", cloth:"#985367", apron:"#efd5b6", iris:"#668e78"},
  "elf-man": {skin:"#ead2ac", hair:"#d6e3d2", cloth:"#637f62", apron:"#f2e5bf", iris:"#408b93"},
  "elf-woman": {skin:"#98674f", hair:"#3d334f", cloth:"#d9a144", apron:"#8db6aa", iris:"#b289b5"},
  "dwarf-man": {skin:"#e4a77f", hair:"#a95832", cloth:"#cf9948", apron:"#477d7d", iris:"#6b8e82"},
  "dwarf-woman": {skin:"#cf9772", hair:"#673b32", cloth:"#84618c", apron:"#9aab7d", iris:"#a47643"}
};
const palette = {ink:"#292835", white:"#fff8e9", blush:"#d67f77", leather:"#925d3c",
  flap:"#bf8b59", brass:"#e6b85e", boot:"#49404a", sole:"#302e38"};
const geometries = {
  ball:new THREE.SphereGeometry(1,32,20),
  cylinder:new THREE.CylinderGeometry(1,1,1,32),
  skirt:new THREE.CylinderGeometry(.70,1,1,40),
  cone:new THREE.ConeGeometry(1,1,32),
  ring:new THREE.TorusGeometry(1,.075,10,40)
};
const materials = new Map(), curves = new Map();

function material(color, roughness=.28) {
  const key = color + roughness;
  if (!materials.has(key)) materials.set(key, new THREE.MeshPhysicalMaterial({
    color, roughness, metalness:0, clearcoat:.85, clearcoatRoughness:.16
  }));
  return materials.get(key);
}

function group(parent, name) {
  const result = new THREE.Group();result.name = name;parent.add(result);return result;
}

function part(parent, name, geometry, color, position, scale, rotation=0) {
  const result = new THREE.Mesh(geometry, material(color));
  result.name = name;result.position.set(...position);result.scale.set(...scale);
  result.rotation.z = rotation;result.castShadow = true;result.receiveShadow = true;
  parent.add(result);return result;
}

const ball = (parent, name, color, position, scale, rotation=0) =>
  part(parent,name,geometries.ball,color,position,scale,rotation);

function stroke(parent, name, color, points, radius) {
  const key = JSON.stringify([points,radius]);
  if (!curves.has(key)) curves.set(key,new THREE.TubeGeometry(new THREE.CatmullRomCurve3(
    points.map(p => new THREE.Vector3(...p))),20,radius,8,false));
  return part(parent,name,curves.get(key),color,[0,0,0],[1,1,1]);
}

function makeEye(parent, side, colors) {
  const eye = group(parent,side < 0 ? "left-eye" : "right-eye");
  eye.position.set(side*.335,2.36,.575);eye.rotation.y = side*.38;
  const glow = "#" + new THREE.Color(colors.iris).lerp(new THREE.Color(palette.white),.48).getHexString();
  // Shallow lenses follow the cheek's curvature, including in three-quarter view.
  ball(eye,"eye-white",palette.white,[0,0,0],[.281,.342,.080]);
  ball(eye,"eye-rim",palette.ink,[0,.007,.053],[.249,.306,.042]);
  ball(eye,"iris",colors.iris,[0,-.038,.091],[.204,.244,.023]);
  ball(eye,"iris-light",glow,[0,-.135,.111],[.175,.106,.014]);
  // A pale lower crescent and two strong reflections survive at board scale.
  ball(eye,"iris-crescent",glow,[0,-.17,.119],[.115,.048,.010]);
  ball(eye,"pupil",palette.ink,[0,.055,.114],[.117,.161,.012]);
  ball(eye,"large-reflection",palette.white,[-.066,.133,.128],[.083,.056,.010],-.2);
  ball(eye,"small-reflection",palette.white,[.094,-.08,.127],[.033,.035,.009]);
  ball(eye,"brow",colors.hair,[0,.427,-.05],[.175,.033,.025],side*-.12);
}

function makeEars(parent, colors, people) {
  const ears = group(parent,"ears");
  for (const side of [-1,1]) {
    if (people === "elf") {
      const ear = part(ears,"pointed-ear",geometries.cone,colors.skin,
        [side*.86,2.40,-.005],[.145,.36,.17],side*-.99);
      ball(ears,"ear-fold",palette.blush,[side*.865,2.40,.095],[.065,.13,.035],side*-.99);
      ear.rotation.x = -.14;
    } else {
      ball(ears,"round-ear",colors.skin,[side*.84,2.31,-.005],[.14,.205,.145]);
      ball(ears,"ear-fold",palette.blush,[side*.90,2.31,.091],[.055,.106,.032]);
    }
  }
}

function makeFace(parent, colors, people) {
  ball(parent,"neck",colors.skin,[0,1.62,0],[.15,.18,.16]);
  const head = ball(parent,"head",colors.skin,[0,2.37,0],[people === "dwarf" ? .91 : .85,.82,.665]);
  makeEars(parent,colors,people);
  makeEye(parent,-1,colors);makeEye(parent,1,colors);
  for (const side of [-1,1]) {
    ball(parent,"cheek",palette.blush,[side*.587,2.091,.519],[.116,.047,.027]);
  }
  ball(parent,"nose",colors.skin,[0,2.13,.664],[people === "dwarf" ? .115 : .065,.065,.078]);
  stroke(parent,"smile",palette.ink,[[-.084,2.015,.606],[0,1.978,.647],[.084,2.015,.606]],.017);
  return head;
}

function makeHair(parent, id, colors) {
  const hair = group(parent,"hair");
  ball(hair,"hair-cap",colors.hair,[0,2.64,-.145],[.89,.731,.647]);
  hairstyles[id](hair,colors);
  return hair;
}

function lock(parent, colors, position, scale, rotation=0) {
  return ball(parent,"hair-lock",colors.hair,position,scale,rotation);
}

const hairstyles = {
  "human-man"(hair,c) {
    lock(hair,c,[-.47,2.96,.35],[.36,.29,.29],-.5);
    lock(hair,c,[-.06,3.10,.29],[.43,.24,.31],-.25);
    lock(hair,c,[.39,3.06,.26],[.36,.23,.29],.32);
    lock(hair,c,[-.71,2.66,.16],[.15,.31,.23],-.15);
    lock(hair,c,[.73,2.69,.12],[.13,.27,.22],.12);
    lock(hair,c,[-.29,3.31,-.08],[.33,.16,.31],-.3);
  },
  "human-woman"(hair,c) {
    lock(hair,c,[-.45,2.96,.37],[.34,.30,.26],-.55);
    lock(hair,c,[.12,3.06,.32],[.39,.24,.28],.3);
    lock(hair,c,[.65,2.66,.07],[.21,.48,.33],.12);
    lock(hair,c,[-.69,2.65,.08],[.20,.48,.30],-.12);
    lock(hair,c,[.36,3.26,-.25],[.34,.32,.33],-.2);
    ball(hair,"bun-ribbon",c.cloth,[.37,3.24,.015],[.31,.048,.07],-.3);
    lock(hair,c,[0,2.15,-.49],[.68,.48,.26]);
  },
  "elf-man"(hair,c) {
    lock(hair,c,[-.42,3.00,.35],[.39,.30,.28],-.5);
    lock(hair,c,[-.06,2.98,.48],[.24,.38,.19],-.42);
    lock(hair,c,[.32,3.15,.26],[.40,.20,.30],.25);
    lock(hair,c,[.67,2.76,.14],[.16,.32,.23],.17);
    lock(hair,c,[-.64,2.73,.09],[.15,.34,.23],-.16);
    lock(hair,c,[0,2.34,-.58],[.64,.50,.18]);
    lock(hair,c,[.12,3.34,-.12],[.34,.13,.29],.2);
  },
  "elf-woman"(hair,c) {
    lock(hair,c,[-.38,3.04,.33],[.37,.25,.28],-.42);
    lock(hair,c,[.24,3.07,.32],[.36,.25,.28],.42);
    lock(hair,c,[-.67,2.68,.12],[.16,.39,.24],-.08);
    lock(hair,c,[.67,2.68,.12],[.16,.39,.24],.08);
    lock(hair,c,[.16,3.29,-.36],[.39,.32,.29]);
    lock(hair,c,[.28,2.57,-.57],[.42,.68,.28],-.18);
    ball(hair,"ponytail-tie",c.cloth,[.26,2.95,-.59],[.28,.064,.24]);
    ball(hair,"hair-bead",palette.brass,[-.60,2.72,.33],[.065,.065,.038]);
  },
  "dwarf-man"(hair,c) {
    lock(hair,c,[-.52,3.00,.26],[.31,.25,.33],-.3);
    lock(hair,c,[-.13,3.14,.25],[.35,.25,.34],-.2);
    lock(hair,c,[.29,3.12,.24],[.34,.25,.33],.3);
    lock(hair,c,[.61,2.96,.20],[.26,.28,.30],.4);
    lock(hair,c,[-.78,2.54,-.01],[.19,.34,.25]);
    lock(hair,c,[.78,2.54,-.01],[.19,.34,.25]);
  },
  "dwarf-woman"(hair,c) {
    lock(hair,c,[-.46,3.00,.29],[.31,.28,.30],-.45);
    lock(hair,c,[0,3.10,.31],[.31,.24,.30]);
    lock(hair,c,[.44,3.00,.29],[.31,.28,.30],.45);
    for (const side of [-1,1]) {
      lock(hair,c,[side*.70,2.92,-.17],[.28,.32,.30],side*.3);
      lock(hair,c,[side*.78,2.12,-.11],[.18,.38,.25],side*.14);
      ball(hair,"braid-band",palette.brass,[side*.79,1.96,.02],[.15,.051,.17],side*.14);
    }
  }
};

function makeClothes(parent, colors, people) {
  const stout = people === "dwarf", width = stout ? .57 : .45;
  const hem = stout ? .56 : .65;
  for (const side of [-1,1]) {
    ball(parent,"trouser",colors.cloth,[side*.245,.39,0],[stout ? .21 : .17,.24,.18]);
    ball(parent,"shoe-sole",palette.sole,[side*.25,.095,.087],[.235,.095,.30]);
    ball(parent,"shoe",palette.boot,[side*.25,.18,.10],[.23,.14,.29]);
    ball(parent,"shoe-tab",palette.flap,[side*.25,.254,.20],[.12,.031,.085]);
    const sleeve = ball(parent,"sleeve",colors.cloth,[side*(width+.08),1.16,0],[.19,.36,.23],side*.16);
    sleeve.rotation.x = -.11;
    ball(parent,"hand",colors.skin,[side*(width+.12),.87,.15],[.16,.17,.17]);
  }
  part(parent,"tunic",geometries.skirt,colors.cloth,[0,1.05,0],[width,.95,.35]);
  ball(parent,"collar",palette.white,[0,1.50,.06],[.26,.095,.24]);
  for (const side of [-1,1]) {
    ball(parent,"collar-fold",colors.apron,[side*.13,1.43,.30],[.105,.15,.04],side*-.35);
  }
  const apron = group(parent,"apron");
  ball(apron,"apron-skirt",colors.apron,[0,hem+.27,.302],[width*.77,.39,.118]);
  ball(apron,"apron-bib",colors.apron,[0,1.265,.292],[.23,.255,.093]);
  for (const side of [-1,1]) {
    ball(apron,"apron-strap",colors.apron,[side*.215,1.40,.21],[.043,.22,.07],side*-.08);
  }
  part(apron,"waist-tie",geometries.cylinder,colors.apron,[0,1.065,0],[width*.91,.063,.35]);
  ball(apron,"patch-pocket",colors.cloth,[-.065,.91,.416],[.19,.115,.031]);
  ball(apron,"pocket-seam",colors.apron,[-.065,1.002,.438],[.16,.013,.018]);
  // A small rolled parcel makes the trade readable without any weapon or armour.
  const parcel = part(parent,"wrapped-parcel",geometries.cylinder,palette.white,
    [-width-.06,.92,.26],[.066,.36,.066],-.20);
  parcel.rotation.x = .24;
  ball(parent,"parcel-string",palette.flap,[-width-.06,.92,.315],[.071,.025,.023],-.20);
}

function makeSatchel(parent) {
  const bag = group(parent,"satchel");
  stroke(bag,"shoulder-strap",palette.leather,
    [[-.34,1.49,.23],[-.12,1.25,.405],[.16,1.00,.43],[.46,.76,.26]],.037);
  stroke(bag,"back-strap",palette.leather,
    [[-.34,1.49,-.17],[-.07,1.25,-.35],[.23,1.00,-.35],[.46,.76,-.12]],.037);
  ball(bag,"bag-body",palette.leather,[.47,.73,.19],[.23,.25,.17]);
  ball(bag,"bag-flap",palette.flap,[.47,.825,.323],[.219,.118,.055]);
  ball(bag,"buckle",palette.brass,[.47,.745,.375],[.043,.052,.021]);
}

function makeBeard(parent, colors, gender) {
  const beard = group(parent,"beard"), small = gender === "female";
  ball(beard,"beard-mass",colors.hair,[0,1.91,.29],[small ? .43 : .56,small ? .32 : .42,.36]);
  for (const side of [-1,1]) {
    ball(beard,"beard-cheek",colors.hair,[side*(small ? .36 : .46),2.00,.25],[.18,.29,.29],side*-.24);
    ball(beard,"moustache",colors.hair,[side*.15,2.036,.65],[.19,.081,.067],side*.18);
  }
  ball(beard,"beard-tip",colors.hair,[0,small ? 1.67 : 1.57,.34],[.20,.20,.21]);
  ball(beard,"beard-tie",palette.brass,[0,small ? 1.65 : 1.55,.515],[.12,.038,.028]);
}

export function makeMerchant(id, options = {}) {
  const entry = MERCHANTS.find(m => m.id === id);
  if (!entry) throw new Error("Unknown merchant id: " + id);
  if (!options || typeof options !== "object" || Array.isArray(options)) throw new TypeError("Invalid merchant options");
  if (options.beard !== undefined && typeof options.beard !== "boolean") throw new TypeError("beard must be boolean");
  if (options.beard !== undefined && id !== "dwarf-woman") throw new Error("beard option is for dwarf-woman only");
  const beard = id === "dwarf-man" || (id === "dwarf-woman" && options.beard === true);
  const result = new THREE.Group();result.name = id;
  const sculpt = group(result,"sculpt"), colors = looks[id];
  makeClothes(sculpt,colors,entry.people);makeSatchel(sculpt);
  makeFace(sculpt,colors,entry.people);makeHair(sculpt,id,colors);
  if (beard) makeBeard(sculpt,colors,entry.gender);
  const bounds = new THREE.Box3().setFromObject(sculpt,true);
  const scale = .70 / (bounds.max.y-bounds.min.y);
  sculpt.scale.setScalar(scale);
  sculpt.position.set(-(bounds.max.x+bounds.min.x)*scale/2,-bounds.min.y*scale,
    -(bounds.max.z+bounds.min.z)*scale/2);
  result.userData = {merchantId:id,people:entry.people,gender:entry.gender,beard};
  return result;
}

import * as THREE from "./vendor/three/three.module.js";

// Original merchant, built only from smooth primitives. The face points towards +Z.
export function makeMerchant(seat=0) {
  const {PAWN_HEIGHT,PAWN_WIDTH,seats}=globalThis.Board3DLayout;
  if (!Number.isInteger(seat) || !seats[seat]) throw new Error("Unknown player seat");
  const pawn = new THREE.Group();
  const material = (color, roughness=0.24) => new THREE.MeshStandardMaterial({color, roughness, metalness:0});
  const skin = material("#edb68e"), hair = material("#693936");
  const teal = material("#228e95"), cream = material("#ffdfaa"), leather = material("#ae693e");
  const dark = material("#302e43",0.18), iris = material("#c27432",0.16);
  const white = material("#fff9ec",0.16), blush = material("#df867c",0.38);
  function mesh(geometry, mat, position, scale=[1,1,1], parent=pawn) {
    const part = new THREE.Mesh(geometry,mat);
    part.position.set(...position); part.scale.set(...scale);
    part.castShadow = true; part.receiveShadow = true;
    parent.add(part);
    return part;
  }
  const ball = (mat,pos,scale,parent) => mesh(new THREE.SphereGeometry(1,40,28),mat,pos,scale,parent);
  const tube = (points,radius,mat) => mesh(new THREE.TubeGeometry(
    new THREE.CatmullRomCurve3(points.map(p=>new THREE.Vector3(...p))),32,radius,10,false),mat,[0,0,0]);

  // Sculpting units only; the finished figure is normalized below, including its base.
  ball(skin,[0,2.25,0],[0.88,0.86,0.71]);
  ball(hair,[0,2.53,-0.16],[0.90,0.63,0.63]);
  for (const [x,y,z,s] of [[-.65,2.72,.32,.33],[-.38,2.92,.38,.31],[-.06,3.00,.32,.29],[.27,2.98,.25,.28],[.58,2.82,.25,.29]]) {
    const lock = ball(hair,[x,y,z],[s,s*.65,s*.72]);
    lock.rotation.z = -.4;
  }
  for (const side of [-1,1]) {
    ball(skin,[side*.86,2.18,0],[.15,.21,.15]);
    ball(hair,[side*.76,2.50,.14],[.17,.34,.22]);
    ball(white,[side*.35,2.28,.626],[.30,.38,.12]);
    ball(dark,[side*.35,2.28,.707],[.245,.315,.082]);
    ball(iris,[side*.35,2.20,.774],[.18,.17,.033]);
    ball(dark,[side*.35,2.32,.777],[.14,.19,.027]);
    ball(white,[side*.35-.065,2.43,.801],[.092,.062,.022]);
    ball(white,[side*.35+.09,2.20,.806],[.039,.036,.018]);
    ball(blush,[side*.56,1.99,.605],[.13,.055,.027]);
    ball(dark,[side*.30,.19,.13],[.25,.18,.34]);
    ball(cream,[side*.30,.41,0],[.17,.23,.19]);
    const arm = ball(teal,[side*.52,1.12,0],[.19,.36,.22]);
    arm.rotation.z = side*.3;
    ball(skin,[side*.63,.86,.06],[.18,.17,.19]);
  }
  mesh(new THREE.CylinderGeometry(.33,.51,.83,48),teal,[0,.98,0]);
  ball(cream,[0,.99,.365],[.35,.40,.14]);
  mesh(new THREE.TorusGeometry(.31,.035,12,48),cream,[0,1.39,0]).rotation.x = Math.PI/2;
  tube([[-.31,1.38,.28],[-.12,1.15,.48],[.19,.85,.47],[.44,.66,.24]],.043,leather);
  ball(leather,[.48,.73,.27],[.27,.28,.18]);
  ball(cream,[.48,.85,.41],[.25,.12,.045]);
  ball(material("#e7b64b"),[.48,.78,.466],[.052,.067,.025]);
  ball(skin,[0,2.06,.708],[.06,.055,.07]);
  tube([[-.09,1.95,.657],[0,1.92,.682],[.09,1.95,.657]],.018,dark);
  const result=new THREE.Group(),bounds=new THREE.Box3().setFromObject(pawn,true);
  const scale=(PAWN_HEIGHT-.10)/(bounds.max.y-bounds.min.y);
  pawn.scale.setScalar(scale);pawn.position.y=.10-bounds.min.y*scale;
  result.add(pawn);
  const segments=[64,3,4,4][seat];
  const base=new THREE.Mesh(new THREE.CylinderGeometry(PAWN_WIDTH/2,PAWN_WIDTH/2,.10,segments),
    material(seats[seat].color,.32));
  base.position.y=.05;
  if (seat===2) base.geometry.rotateY(Math.PI/4);
  base.castShadow=true;base.receiveShadow=true;result.add(base);
  // Raised numerals on the top of the base; the base outline is the seat's sign.
  const digits=[[[[-1,-1],[-1,1],[1,1],[1,-1],[-1,-1]]],[[[0,-1],[0,1]]],
    [[[-1,-1],[1,-1],[1,0],[-1,0],[-1,1],[1,1]]],
    [[[-1,-1],[1,-1],[1,1],[-1,1]],[[-1,0],[1,0]]]];
  for (const stroke of digits[seat]) {
    const points=stroke.map(([x,z])=>new THREE.Vector3(x*.025,.104,.10+z*.027));
    const curve=new THREE.CurvePath();
    points.slice(1).forEach((p,i)=>curve.add(new THREE.LineCurve3(points[i],p)));
    result.add(new THREE.Mesh(new THREE.TubeGeometry(curve,16,.007,6,false),white));
  }
  result.userData={seat,shape:seats[seat].shape};
  return result;
}

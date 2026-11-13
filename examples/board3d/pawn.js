import * as THREE from "./vendor/three/three.module.js";
import {makeMerchant as makeFigure} from "./art/merchants.js";

// The figure is ART (Codex, art/merchants.js); the base -- the seat's colour, shape and number -- is the board's.
// Provisional: which merchant stands at each seat, until each player picks one (an appearance_id, lot 3).
export const SEAT_MERCHANTS = Object.freeze(["human-man", "elf-woman", "dwarf-man", "human-woman"]);
const BASE_HEIGHT = .10;

export function makeMerchant(seat=0) {
  const {PAWN_HEIGHT,PAWN_WIDTH,seats}=globalThis.Board3DLayout;
  if (!Number.isInteger(seat) || !seats[seat]) throw new Error("Unknown player seat");
  const material=(color,roughness=.32)=>new THREE.MeshStandardMaterial({color,roughness,metalness:0});
  const result=new THREE.Group(),figure=makeFigure(SEAT_MERCHANTS[seat]);
  const height=new THREE.Box3().setFromObject(figure,true).max.y;
  figure.scale.setScalar((PAWN_HEIGHT-BASE_HEIGHT)/height);figure.position.y=BASE_HEIGHT;
  result.add(figure);
  const segments=[64,3,4,4][seat];
  const base=new THREE.Mesh(new THREE.CylinderGeometry(PAWN_WIDTH/2,PAWN_WIDTH/2,BASE_HEIGHT,segments),
    material(seats[seat].color));
  base.position.y=BASE_HEIGHT/2;
  if (seat===2) base.geometry.rotateY(Math.PI/4);
  base.castShadow=true;base.receiveShadow=true;result.add(base);
  // Raised numerals on the top of the base; the base outline is the seat's sign.
  const white=material("#fff9ec",.16);
  const digits=[[[[-1,-1],[-1,1],[1,1],[1,-1],[-1,-1]]],[[[0,-1],[0,1]]],
    [[[-1,-1],[1,-1],[1,0],[-1,0],[-1,1],[1,1]]],
    [[[-1,-1],[1,-1],[1,1],[-1,1]],[[-1,0],[1,0]]]];
  for (const stroke of digits[seat]) {
    const points=stroke.map(([x,z])=>new THREE.Vector3(x*.025,BASE_HEIGHT+.004,.10+z*.027));
    const curve=new THREE.CurvePath();
    points.slice(1).forEach((p,i)=>curve.add(new THREE.LineCurve3(points[i],p)));
    result.add(new THREE.Mesh(new THREE.TubeGeometry(curve,16,.007,6,false),white));
  }
  result.userData={seat,shape:seats[seat].shape,merchant:SEAT_MERCHANTS[seat]};
  return result;
}

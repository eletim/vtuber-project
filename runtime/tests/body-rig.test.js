import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {BodyRig} from '../web/body-rig.js';
import {neutral} from '../web/controls.js';
const model=JSON.parse(readFileSync(new URL('../model/model.json',import.meta.url)));
const weights=JSON.parse(readFileSync(new URL('../model/skinning.json',import.meta.url)));
const rig=()=>new BodyRig(model,weights);
const vertex=(r,x,y)=>Math.round(y/model.size[1]*model.mesh[1])*(model.mesh[0]+1)+Math.round(x/model.size[0]*model.mesh[0]);
function areas(r,positions){
 const [nx,ny]=model.mesh;let minimum=Infinity;
 const area=(a,b,c)=>((positions[b*2]-positions[a*2])*(positions[c*2+1]-positions[a*2+1])-(positions[b*2+1]-positions[a*2+1])*(positions[c*2]-positions[a*2]))*nx*ny;
 for(let y=0;y<ny;y++)for(let x=0;x<nx;x++){
  const a=y*(nx+1)+x,b=a+1,c=a+nx+1,d=c+1;minimum=Math.min(minimum,area(a,b,c),area(b,d,c));
 }
 return minimum;
}
test('neutral mesh preserves the original drawing; pelvis/base remains planted',()=>{
 const r=rig(),base=r.frame(neutral(),0);
 assert.deepEqual(base,r.rest);
 for(let i=0;i<180;i++)r.frame({...neutral(),ParamBodyAngleX:5,ParamAngleX:15},i/60);
 const bottom=vertex(r,543,1448)*2;
 assert.equal(r.positions[bottom],r.rest[bottom]);assert.equal(r.positions[bottom+1],r.rest[bottom+1]);
 const hand=vertex(r,125,1340)*2;
 const distance=Math.hypot((r.positions[hand]-r.rest[hand])*model.size[0],(r.positions[hand+1]-r.rest[hand+1])*model.size[1]);
 assert.ok(distance>10,'hands inherit the shoulder/body transform instead of being pinned at hip height');
});
test('head tilt keeps chest attached; arm springs follow torso with independent lag',()=>{
 const r=rig();r.frame(neutral(),0);
 const chest=vertex(r,543,700);
 r.frame({...neutral(),ParamAngleZ:8},.016);
 assert.equal(r.positions[chest*2],r.rest[chest*2]);
 const records=[];
 for(let i=1;i<=120;i++){
  r.frame({...neutral(),ParamBodyAngleX:i<40?5:-5},i/60);
  records.push({...r.pose,arms:[...r.pose.arms]});
 }
 assert.ok(records.some(p=>Math.abs(p.arms[0])>.05));
 assert.ok(records.every(p=>p.arms.every(a=>Math.abs(a)<1.16)));
 assert.ok(records.some((p,i)=>i>40&&p.body<0&&p.arms[0]>0),'arms should trail a reversal');
});
test('range extremes and reversals do not invert or collapse mesh triangles',()=>{
 const r=rig();let min=Infinity;
 for(let i=0;i<240;i++){
  const s=i%80<40?1:-1;
  const positions=r.frame({...neutral(),ParamAngleX:15*s,ParamAngleY:10*s,ParamAngleZ:8*s,ParamBodyAngleX:5*s,ParamBreath:i%2},i/60);
  min=Math.min(min,areas(r,positions));
 }
 assert.ok(min>.25,`minimum normalized triangle area ${min}`);
});

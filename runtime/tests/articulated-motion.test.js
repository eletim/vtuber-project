import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {BodyRig} from '../web/body-rig.js';
import {ArticulatedArm} from '../web/articulated-arm.js';
import {HairRig} from '../web/hair-rig.js';
import {neutral} from '../web/controls.js';
import {performancePose} from '../web/performance.js';
const model=JSON.parse(readFileSync(new URL('../model/model.json',import.meta.url))),weights=JSON.parse(readFileSync(new URL('../model/skinning.json',import.meta.url)));
const setup=()=>{const body=new BodyRig(model,weights);return{body,arm:new ArticulatedArm(model,body.rest),hair:new HairRig(model,body.rest)};};
test('cheek gesture keeps rigid bone lengths and never changes torso or skirt',()=>{
 const {body,arm}=setup(),baseline=new BodyRig(model,weights);let previous;
 for(let i=0;i<=100;i++){
  const p={...neutral(),ParamHandToCheek:i/100},time=i/60;body.frame(p,time,{ambient:false});baseline.frame(neutral(),time,{ambient:false});
  const torso=body.positionsByRole.torso.slice();arm.frame(p,time,body.pose,{snapArticulation:true});
  assert.deepEqual(body.positionsByRole.torso,torso);assert.deepEqual(torso,baseline.positionsByRole.torso);assert.deepEqual(body.positionsByRole.skirt,baseline.positionsByRole.skirt);
  const {elbow,wrist,shoulder}=arm.joints,d=Math.hypot(wrist[0]-elbow[0],wrist[1]-elbow[1]);
  assert.ok(Math.abs(d-Math.hypot(201,330))<1e-8);assert.deepEqual(shoulder,[353,510]);
  if(previous)assert.ok(Math.hypot(wrist[0]-previous[0],wrist[1]-previous[1])<12,'intermediate joints cannot jump');previous=wrist;
  for(const layer of model.bodyLayers.filter(l=>['forearm','hand','cuff'].includes(l.articulation?.joint))){
   const a=arm.geometry.get(layer.id),dx=(a[2]-a[0])*model.size[0],dy=(a[3]-a[1])*model.size[1];
   assert.ok(Math.abs(Math.hypot(dx,dy)-model.size[0]/model.mesh[0])<.001,'skin and hand are rotated, never stretched');
  }
 }
 assert.ok(Math.hypot(arm.joints.wrist[0]-476,arm.joints.wrist[1]-470)<1e-7);
});
test('arm spring raises and lowers continuously, settling back to rest',()=>{
 const {body,arm}=setup();body.frame(neutral(),0);arm.frame(neutral(),0,body.pose);let previous=0;
 for(let i=1;i<=120;i++){arm.frame({...neutral(),ParamHandToCheek:1},i/60,body.pose);assert.ok(arm.amount>=previous&&arm.amount<=1);previous=arm.amount;}
 assert.ok(arm.amount>.999);
 for(let i=121;i<=300;i++)arm.frame(neutral(),i/60,body.pose);
 assert.ok(arm.amount<.00001);
});
test('hair has fixed roots, distinct lag, and does not move the face surface',()=>{
 const {body,hair}=setup();let peak=0;
 for(let frame=0;frame<=240;frame++){
  body.frame(neutral(),frame/60);const before=body.positionsByRole.head.slice();hair.frame(neutral(),frame/60,before,body.pose);
  assert.deepEqual(body.positionsByRole.head,body.rest);
  for(const layer of model.bodyLayers.filter(l=>l.hairMotion)){
   const points=hair.geometry.get(layer.id);
   for(let i=0;i<points.length;i+=2){const y=body.rest[i+1]*model.size[1];if(y<=layer.hairMotion.rootY){assert.equal(points[i],before[i]);assert.equal(points[i+1],before[i+1]);}peak=Math.max(peak,Math.abs(points[i]-before[i])*model.size[0]);}
  }
 }
 assert.ok(peak>5&&peak<18);assert.ok(new Set([...hair.states.values()].map(s=>s.x.toFixed(3))).size>8);
});
test('thoughtful gesture raises, holds, and lowers the hand within six seconds',()=>{
 const p=time=>performancePose(neutral(),time,{enabled:true,emotion:'thoughtful',started_at:0,until:6});
 assert.equal(p(0).ParamHandToCheek,0);assert.ok(p(2).ParamHandToCheek>.99);assert.equal(p(5).ParamHandToCheek,0);
});

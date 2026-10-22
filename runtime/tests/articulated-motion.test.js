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
test('arm deformation keeps rigid bone lengths and never feeds back into torso or skirt',()=>{
 const {body,arm}=setup(),baseline=new BodyRig(model,weights);let previous;
 for(let i=0;i<=100;i++){
  const p={...neutral(),ParamHandToCheek:i/100},time=i/60;body.frame(neutral(),time,{ambient:false});baseline.frame(neutral(),time,{ambient:false});
  const torso=body.positionsByRole.torso.slice();arm.frame(p,time,body.pose,{snapArticulation:true});
  assert.deepEqual(body.positionsByRole.torso,torso);assert.deepEqual(torso,baseline.positionsByRole.torso);assert.deepEqual(body.positionsByRole.skirt,baseline.positionsByRole.skirt);
  const {elbow,wrist,shoulder}=arm.joints,d=Math.hypot(wrist[0]-elbow[0],wrist[1]-elbow[1]);
  assert.ok(Math.abs(Math.hypot(d,arm.joints.forearmDepth)-Math.hypot(201,330))<1e-8);assert.deepEqual(shoulder,[353,510]);
  if(previous)assert.ok(Math.hypot(wrist[0]-previous[0],wrist[1]-previous[1])<16,'continuous depth arc has bounded motion per 1% pose step');previous=wrist;
  assert.ok(arm.joints.projection>=Math.cos(1.095)-1e-10&&arm.joints.projection<=1);
  assert.ok(Math.abs(Math.hypot(elbow[0]-shoulder[0],elbow[1]-shoulder[1],arm.joints.upperDepth)-Math.hypot(78,290))<1e-8);

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
 assert.ok(peak>.1&&peak<3);assert.ok(new Set([...hair.states.values()].map(s=>s.x.toFixed(3))).size>8);
});

test('larger hair swing returns to its rest surface after motion stops',()=>{
 const {body,hair}=setup();body.frame(neutral(),0,{ambient:false});const head=body.positionsByRole.head;
 for(let i=0;i<=240;i++){body.frame({...neutral(),ParamBodyShiftX:Math.sin(i/25)},i/60);hair.frame(neutral(),i/60,body.positionsByRole.head,body.pose);}
 let peak=0;
 for(const points of hair.geometry.values())for(let i=0;i<points.length;i+=2)peak=Math.max(peak,Math.abs(points[i]-head[i])*model.size[0]);
 assert.ok(peak>5);
 for(let i=241;i<=720;i++){body.frame(neutral(),i/60,{ambient:false});hair.frame(neutral(),i/60,body.positionsByRole.head,body.pose,{ambient:false});}
 for(const points of hair.geometry.values())for(let i=0;i<points.length;i++)assert.ok(Math.abs(points[i]-head[i])<.000001);
});
test('thoughtful gesture raises, holds, and lowers the hand within six seconds',()=>{
 const p=time=>performancePose(neutral(),time,{enabled:true,emotion:'thoughtful',started_at:0,until:6});
 assert.equal(p(0).ParamHandToCheek,0);assert.ok(p(2).ParamHandToCheek>.99);assert.equal(p(5).ParamHandToCheek,0);
});

test('depth projection preserves forearm cross-section while narrowing its forward arc',()=>{
 const {body}=setup(),a=model.bodyLayers.find(l=>l.id==='left_raised_forearm').articulation,E=a.sourceElbow||model.articulatedArm.elbow,W=a.sourceWrist||model.articulatedArm.wristRaised,L=Math.hypot(W[0]-E[0],W[1]-E[1]),d=[(W[0]-E[0])/L,(W[1]-E[1])/L];
 const rest=new Float32Array([-20,20].flatMap(v=>[(E[0]+L*.45*d[0]-v*d[1])/1086,(E[1]+L*.45*d[1]+v*d[0])/1448]));
 const arm=new ArticulatedArm(model,rest);body.frame(neutral(),0);
 for(let f=0;f<=100;f++){arm.frame({...neutral(),ParamHandToCheek:f/100},f/60,body.pose,{snapArticulation:true});const v=arm.geometry.get('left_raised_forearm');assert.ok(Math.abs(Math.hypot((v[2]-v[0])*1086,(v[3]-v[1])*1448)-40)<.001);assert.ok(arm.joints.wrist[0]<550);}
});

test('projected distal hand cannot elongate the authored fingers',()=>{
 const {body}=setup(),a=model.bodyLayers.find(l=>l.id==='left_raised_forearm').articulation,E=a.sourceElbow||model.articulatedArm.elbow,W=a.sourceWrist||model.articulatedArm.wristRaised,L=Math.hypot(W[0]-E[0],W[1]-E[1]),d=[(W[0]-E[0])/L,(W[1]-E[1])/L];
 const rest=new Float32Array([80,150].flatMap(u=>[(W[0]+u*d[0])/1086,(W[1]+u*d[1])/1448]));const arm=new ArticulatedArm(model,rest);body.frame(neutral(),0);
 for(let f=0;f<=100;f++){arm.frame({...neutral(),ParamHandToCheek:f/100},f/60,body.pose,{snapArticulation:true});const v=arm.geometry.get('left_raised_hand');assert.ok(Math.hypot((v[2]-v[0])*1086,(v[3]-v[1])*1448)<=70.001);}
});

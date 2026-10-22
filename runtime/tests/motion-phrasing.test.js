import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {BodyRig} from '../web/body-rig.js';
import {ArticulatedArm} from '../web/articulated-arm.js';
import {HairRig} from '../web/hair-rig.js';
import {neutral} from '../web/controls.js';
const model=JSON.parse(readFileSync(new URL('../model/model.json',import.meta.url)));
const weights=JSON.parse(readFileSync(new URL('../model/skinning.json',import.meta.url)));

test('cheek response moves the head rigidly while the shared waist and skirt remain connected',()=>{
 const rig=new BodyRig(model,weights),base=new BodyRig(model,weights);
 const index=(x,y)=>(Math.round(y/1448*80)*61+Math.round(x/1086*60))*2;
 const a=index(450,200),b=index(630,200),distance=v=>Math.hypot((v[b]-v[a])*1086,(v[b+1]-v[a+1])*1448);
 let maxHead=0;
 for(let i=0;i<600;i++){
  const t=i/60,amount=t<1?0:t<4?1:0;
  rig.frame({...neutral(),ParamHandToCheek:amount},t,{ambient:false});base.frame(neutral(),t,{ambient:false});
  assert.deepEqual(rig.positionsByRole.skirt,base.positionsByRole.skirt,'no hand-driven hem or pelvis drift');
  assert.ok(Math.abs(distance(rig.positionsByRole.head)-distance(base.positionsByRole.head))<.001,'face cannot stretch');
  for(let row=54;row<=80;row++)for(let col=20;col<=40;col++){
   const j=(row*61+col)*2;assert.equal(rig.positionsByRole.abdomen[j],base.positionsByRole.abdomen[j]);assert.equal(rig.positionsByRole.abdomen[j+1],base.positionsByRole.abdomen[j+1]);
  }
  maxHead=Math.max(maxHead,Math.abs(rig.positionsByRole.head[a]-base.positionsByRole.head[a])*1086);
 }
 assert.ok(maxHead>8&&maxHead<30);assert.ok(rig.pose.approach<.00001,'neck settles after lowering');
});

test('lowering takes a continuous deeper arc, preserving opaque sleeve and bone length',()=>{
 const rig=new BodyRig(model,weights),arm=new ArticulatedArm(model,rig.rest);rig.frame(neutral(),0);
 let previous,largestStep=0,up,down;
 for(let i=0;i<=720;i++){
  const t=i/60,amount=t<2?0:t<4?(t-2)/2:t<5?1:t<7?(7-t)/2:0;
  arm.frame({...neutral(),ParamHandToCheek:amount},t,rig.pose);
  const j=arm.joints,d=Math.hypot(j.wrist[0]-j.elbow[0],j.wrist[1]-j.elbow[1]);
  assert.ok(Math.abs(Math.hypot(d,j.forearmDepth)-Math.hypot(201,330))<1e-7);
  assert.equal(arm.opacity(model.bodyLayers.find(l=>l.id==='left_raised_cuff')),1);
  if(previous)largestStep=Math.max(largestStep,Math.hypot(j.wrist[0]-previous[0],j.wrist[1]-previous[1]));previous=j.wrist;
  if(j.amount>.49&&j.amount<.51){if(t<4)up=j;else down=j;}
 }
 assert.ok(largestStep<15,`per 60Hz wrist step ${largestStep}`);
 assert.ok(down.returning>.5&&up.returning===0);assert.ok(down.projection<up.projection-.03,'return arc is deeper at the same lift');
 assert.ok(Math.abs(arm.amount)<1e-8);
});

test('hair cannot accumulate outward velocity at its limit and still settles after a stopped torso',()=>{
 const body=new BodyRig(model,weights),hair=new HairRig(model,body.rest);let peak=0;
 for(let i=0;i<900;i++){
  const t=i/60,p={...neutral(),ParamBodyShiftX:t<4?Math.sin(t*4):0};body.frame(p,t,{ambient:false});hair.frame(p,t,body.positionsByRole.head,body.pose,{ambient:false});
  for(const [id,s] of hair.states){if(id.startsWith('rear_')&&id.includes('outer')){peak=Math.max(peak,Math.abs(s.x));assert.ok(Math.abs(s.x)<=38);if(Math.abs(s.x)===38)assert.ok(s.x*s.v<=0);}}
 }
 assert.ok(peak>10);assert.ok([...hair.states.values()].every(s=>Math.abs(s.x)<.001));
});

import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {BodyRig,pelvisPoint} from '../web/body-rig.js';
import {ArticulatedArm} from '../web/articulated-arm.js';
import {neutral} from '../web/controls.js';
const m=JSON.parse(readFileSync(new URL('../model/model.json',import.meta.url))),w=JSON.parse(readFileSync(new URL('../model/skinning.json',import.meta.url)));
test('wrist correction is continuous across the hand-forearm seam and keeps visible mesh triangles positive',()=>{
 const r=new BodyRig(m,w),arm=new ArticulatedArm(m,r.rest);r.frame(neutral(),0);let minimum=Infinity;
 for(let f=0;f<=100;f++){
  arm.frame({...neutral(),ParamHandToCheek:f/100},f/60,r.pose,{snapArticulation:true});
  const hand=arm.geometry.get('left_raised_hand'),forearm=arm.geometry.get('left_raised_forearm');
  for(let row=25;row<=28;row++)for(let col=24;col<=27;col++){const i=(row*61+col)*2;assert.ok(Math.hypot((hand[i]-forearm[i])*1086,(hand[i+1]-forearm[i+1])*1448)<.001);}
  for(const [name,rect] of ['left_raised_hand','left_raised_forearm','left_raised_cuff'].map(id=>[id,m.bodyLayers.find(l=>l.id===id).rect])){
   const v=arm.geometry.get(name);for(let row=Math.floor(rect[1]/1448*80);row<=Math.ceil(rect[3]/1448*80);row++)for(let col=Math.floor(rect[0]/1086*60);col<=Math.ceil(rect[2]/1086*60);col++){
    const a=row*61+col,b=a+1,c=a+61;const area=((v[b*2]-v[a*2])*(v[c*2+1]-v[a*2+1])-(v[b*2+1]-v[a*2+1])*(v[c*2]-v[a*2]))*4800;minimum=Math.min(minimum,area);
   }
  }
 }
 assert.ok(minimum>.3,`visible arm surface minimum area ${minimum}`);assert.ok(Math.abs(arm.joints.wristRoll-(m.articulatedArm.forwardPosePaint?-Math.PI/3:0))<1e-10);
});
test('larger weight transfer moves pelvis and differentiates thighs without changing hip radii',()=>{
 const r=new BodyRig(m,w);let difference=0;
 for(let f=0;f<240;f++){
  r.frame({...neutral(),ParamBodyShiftX:1},f/60);difference=Math.max(difference,Math.abs(r.pose.legs[0]-r.pose.legs[1]));
  for(const [role,hx] of [['legLeft',400],['legRight',650]]){const hip=pelvisPoint(hx,1225,r.pose),v=r.positionsByRole[role];for(let row=73;row<=80;row++)for(let col=20;col<=42;col++){
   const i=(row*61+col)*2,original=Math.hypot(r.rest[i]*1086-hx,r.rest[i+1]*1448-1225),current=Math.hypot(v[i]*1086-hip[0],v[i+1]*1448-hip[1]);assert.ok(Math.abs(original-current)<.001);
  }}
 }
 assert.ok(r.pose.shift>47.9&&r.pose.shift<=48);assert.ok(difference>5);
});

test('one opaque cuff stays behind drape through lift and lowering without an alpha transition',()=>{
 const r=new BodyRig(m,w),arm=new ArticulatedArm(m,r.rest);r.frame(neutral(),0);
 const cuff=m.bodyLayers.find(l=>l.id==='left_raised_cuff'),old=m.bodyLayers.find(l=>l.id==='left_rest_cuff');
 assert.ok(m.bodyLayers.indexOf(cuff)<m.bodyLayers.findIndex(l=>l.id==='left_raised_drape'));
 let previous=null,maximumStep=0;
 for(let i=0;i<=400;i++){
  const amount=i<=200?i/200:(400-i)/200;
  arm.frame({...neutral(),ParamHandToCheek:amount},i/60,r.pose,{snapArticulation:true});
  assert.equal(arm.opacity(cuff),1);assert.equal(arm.opacity(old),0);
  const v=arm.geometry.get(cuff.id),index=(46*61+23)*2;
  if(previous)maximumStep=Math.max(maximumStep,Math.hypot((v[index]-previous[0])*1086,(v[index+1]-previous[1])*1448));
  previous=[v[index],v[index+1]];
 }
 assert.ok(maximumStep<12,`cuff step ${maximumStep}`);
});

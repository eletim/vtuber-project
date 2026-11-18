import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {BodyRig,pelvisPoint} from '../web/body-rig.js';
import {ArticulatedArm,palmProjection} from '../web/articulated-arm.js';
import {neutral} from '../web/controls.js';
const m=JSON.parse(readFileSync(new URL('../model/model.json',import.meta.url)));
const w=JSON.parse(readFileSync(new URL('../model/skinning.json',import.meta.url)));

test('palm projection carries thickness and finger crowns rather than uniform width scaling',()=>{
 assert.ok(palmProjection(35,0,.8).v>3,'palm crown moves in projected depth');
 const a=palmProjection(125,-15,.8),b=palmProjection(125,2,.8);
 assert.ok(Math.abs((b.v-a.v)-17*Math.cos(.8))>.1,'finger crowns do not share a flat plane');
 for(const yaw of [0,.4,.8])assert.equal(palmProjection(-70,12,yaw).v,12,'forearm attachment beyond twist remains fixed');
 assert.equal(palmProjection(125,20,0).v,20,'rest and cheek endpoints retain original painted view');
});

test('dense hand draw contains every triangle once, finite vertices and an opaque layer across the full arc',()=>{
 const r=new BodyRig(m,w),a=new ArticulatedArm(m,r.rest);r.frame(neutral(),0);let previous,maxStep=0;
 for(let i=0;i<=100;i++){
  a.frame({...neutral(),ParamHandToCheek:i/100},i/60,r.pose,{snapArticulation:true});
  const g=a.geometry.get('left_raised_hand_detail');assert.equal(g.length,49*49*2);
  assert.ok(g.every(Number.isFinite));assert.ok(a.handDrawIndices.every(x=>x<49*49));
  const triangles=[];for(let k=0;k<a.handDrawIndices.length;k+=3)triangles.push([...a.handDrawIndices.slice(k,k+3)].join(','));
  assert.equal(new Set(triangles).size,48*48*2,'sorting never loses or doubles a triangle');
  assert.equal(a.opacity(m.bodyLayers.find(l=>l.id==='left_raised_hand')),1);
  if(previous)for(let k=0;k<g.length;k+=2)maxStep=Math.max(maxStep,Math.hypot((g[k]-previous[k])*1086,(g[k+1]-previous[k+1])*1448));previous=g.slice();
 }
 assert.ok(maxStep<20,`maximum 1% hand pose step ${maxStep}`);
});

test('support height is shared by both hips and loading creates tilt without stretching their distance',()=>{
 const r=new BodyRig(m,w);let difference=0,height=0;
 for(let i=0;i<240;i++){
  r.frame({...neutral(),ParamBodyShiftX:1},i/60);
  const left=pelvisPoint(400,1225,r.pose),right=pelvisPoint(650,1225,r.pose);
  assert.ok(Math.abs(Math.hypot(right[0]-left[0],right[1]-left[1])-250)<1e-8);
  difference=Math.max(difference,Math.abs(right[1]-left[1]));height=Math.max(height,Math.abs(r.pose.supportHeight));
 }
 assert.ok(difference>23&&difference<26);assert.ok(height>5&&height<=5.5);
});

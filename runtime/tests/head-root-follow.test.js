import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {BodyRig} from '../web/body-rig.js';
import {HairRig} from '../web/hair-rig.js';
import {neutral} from '../web/controls.js';
import {performanceSequence} from '../web/performance-sequence.js';
const model=JSON.parse(readFileSync(new URL('../model/model.json',import.meta.url))),weights=JSON.parse(readFileSync(new URL('../model/skinning.json',import.meta.url)));
test('neck accepts the initial pose, but subsequent command changes have a continuous response',()=>{
 const r=new BodyRig(model,weights);r.frame({...neutral(),ParamAngleZ:4},0);assert.equal(r.pose.headCommands[2],4);
 r.frame({...neutral(),ParamAngleZ:-4},1/60);assert.ok(r.pose.headCommands[2]>3.8);
 for(let i=2;i<180;i++)r.frame({...neutral(),ParamAngleZ:-4},i/60);
 assert.ok(Math.abs(r.pose.headCommands[2]+4)<1e-7);
});
test('root sensors respond differently to rotation, and a still avatar generates no hair motion',()=>{
 const r=new BodyRig(model,weights),h=new HairRig(model,r.rest);let separate=0;
 for(let i=0;i<180;i++){
  const p={...neutral(),ParamAngleZ:i>60?5:0,ParamBodyShiftX:i>60?.8:0};r.frame(p,i/60);h.frame(p,i/60,r.positionsByRole.head,r.pose,{ambient:false});
  const left=h.states.get('rear_left_outer'),right=h.states.get('rear_right_outer');
  if(i<60){assert.equal(left.x,0);assert.equal(right.x,0)}
  separate=Math.max(separate,Math.abs(left.drive.ay-right.drive.ay));
  for(const s of h.states.values())assert.ok(Number.isFinite(s.x));
 }
 assert.ok(separate>10,'opposite roots no longer share one centre acceleration');
});
test('acting sequence overlaps hand preparation with happy settling and preserves large shifts',()=>{
 let low=0,high=0;
 for(let i=0;i<1110;i++){const s=performanceSequence(i/60);low=Math.min(low,s.parameters.ParamBodyShiftX);high=Math.max(high,s.parameters.ParamBodyShiftX)}
 const overlap=performanceSequence(9.2);assert.ok(overlap.performance.enabled&&overlap.parameters.ParamHandToCheek>0);
 assert.ok(low<-.85&&high>.85);assert.equal(performanceSequence(12).expression,'soft_smile');
 const end=performanceSequence(18.5);assert.equal(end.parameters.ParamHandToCheek,0);assert.equal(end.parameters.ParamBodyShiftX,0);
});

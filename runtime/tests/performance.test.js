import test from 'node:test';
import assert from 'node:assert/strict';
import {performancePose} from '../web/performance.js';
import {neutral,limits} from '../web/controls.js';
test('idle and speech gestures preserve mouth and remain inside pose limits',()=>{
 for(const emotion of ['neutral','happy','thoughtful','surprised'])for(let i=0;i<600;i++){
  const base=neutral();base.ParamMouthOpenY=(i%10)/10;
  const pose=performancePose(base,i/30,{enabled:true,emotion,started_at:0,until:0},base.ParamMouthOpenY);
  assert.equal(pose.ParamMouthOpenY,base.ParamMouthOpenY);
  for(const [key,[lo,hi]] of Object.entries(limits))assert.ok(pose[key]>=lo&&pose[key]<=hi);
 }
});
test('disabled motion preserves external commands; expired emotion returns idle',()=>{
 const base={...neutral(),ParamAngleX:12,ParamEyeLOpen:0};
 assert.deepEqual(performancePose(base,10,{enabled:false},1),base);
 assert.deepEqual(performancePose(base,10,{enabled:true,emotion:'thoughtful',started_at:0,until:9}),performancePose(base,10,{enabled:true,emotion:'neutral',started_at:0,until:9}));
 assert.equal(performancePose(base,10,{enabled:true,emotion:'happy'}).ParamEyeLOpen,0);
});

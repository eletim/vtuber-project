import test from 'node:test';import assert from 'node:assert/strict';
import {ActingController} from '../web/acting-controller.js';import {neutral} from '../web/controls.js';import {performanceSequence} from '../web/performance-sequence.js';
test('emotions keep head rigid and settle; thinking gaze precedes cheek contact',()=>{
 for(const v of ['joyful','thinking','surprised']){for(let i=0;i<=1110;i++){const s=performanceSequence(i/60,v);assert.equal(s.parameters.ParamAngleX,0);assert.equal(s.parameters.ParamAngleY,0);assert.ok(s.parameters.ParamHandToCheek<=.9);assert.ok(Math.abs(s.parameters.ParamBodyBounce)<=1);}for(const [k,value] of Object.entries(neutral()))assert.ok(Math.abs(performanceSequence(18.5,v).parameters[k]-value)<1e-12);}
 assert.ok(performanceSequence(1.2,'thinking').parameters.ParamEyeBallX<-.5);assert.equal(performanceSequence(1.2,'thinking').parameters.ParamHandToCheek,0);
 assert.equal(performanceSequence(2.7,'joyful').expression,'big_smile');assert.equal(performanceSequence(1,'surprised').expression,'surprised');assert.equal(performanceSequence(0,'surprised').expression,'neutral');assert.equal(performanceSequence(1.8,'thinking').parameters.ParamEyeLOpen,0);assert.equal(performanceSequence(3.6,'surprised').parameters.ParamEyeROpen,0);
});
test('new shared action blends from current sample; repeated snapshot and stop do not pop',()=>{
 const a=new ActingController(),p=neutral();a.sync({id:'joy',variant:'joyful',started_at:100},0,100);
 for(let n=0;n<=180;n++)a.frame(p,n/60);
 const before=a.frame(p,3);a.sync({id:'think',variant:'thinking',started_at:103},3,103);const next=a.frame(p,3);assert.deepEqual(next.pose,before.pose);
 let previous=next.pose;for(let n=181;n<240;n++){const r=a.frame(p,n/60);assert.ok(Math.abs(r.pose.ParamBodyShiftX-previous.ParamBodyShiftX)<.09);previous=r.pose;}
 const t=4,b=a.frame(p,t);a.sync({id:'think',variant:'thinking',started_at:103,stopped_at:104},t,104);assert.deepEqual(a.frame(p,t).pose,b.pose);
 for(let n=241;n<400;n++)a.frame(p,n/60);assert.equal(a.weight,0);
});

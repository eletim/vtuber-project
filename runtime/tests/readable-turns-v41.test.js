import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';import {BodyRig} from '../web/body-rig.js';import {neutral} from '../web/controls.js';import {performanceSequence} from '../web/performance-sequence.js';
const m=JSON.parse(readFileSync(new URL('../model/model.json',import.meta.url))),w=JSON.parse(readFileSync(new URL('../model/skinning.json',import.meta.url)));
test('shared acting phrase leads a distinct reversal and keeps cheek contact below full lift',()=>{
 let max=0,last=performanceSequence(0).parameters;for(let i=1;i<=1110;i++){const p=performanceSequence(i/60).parameters;assert.ok(Math.abs(p.ParamBodyShiftX-last.ParamBodyShiftX)<.06);assert.ok(Math.abs(p.ParamAngleX-last.ParamAngleX)<1.01);max=Math.max(max,p.ParamHandToCheek);last=p;}
 assert.ok(performanceSequence(2.5).parameters.ParamAngleX>-14);assert.ok(performanceSequence(2.5).parameters.ParamBodyShiftX<-.99);
 assert.equal(max,.965);assert.ok(performanceSequence(3.7).parameters.ParamBodyShiftX>.99);
});

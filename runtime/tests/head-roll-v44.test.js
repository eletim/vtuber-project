import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {BodyRig} from '../web/body-rig.js';
import {neutral} from '../web/controls.js';
const model=JSON.parse(readFileSync(new URL('../model/model.json',import.meta.url))),skin=JSON.parse(readFileSync(new URL('../model/skinning.json',import.meta.url)));
test('v44 whole head keeps all pairwise distances under roll/body/breath motion',()=>{
 const r=new BodyRig(model,skin),[w,h]=model.size;let max=0;
 const ids=[7*61+20,12*61+25,15*61+34,20*61+29,23*61+20];
 for(let f=0;f<600;f++){const t=f/60;r.frame({...neutral(),ParamAngleZ:8*Math.sin(t),ParamAngleX:15*Math.cos(t),ParamAngleY:10*Math.sin(t),ParamBodyShiftX:Math.sin(t*.7),ParamBodyAngleX:4*Math.sin(t*.5),ParamBreath:(1+Math.sin(t))/2},t);
 for(const a of ids)for(const b of ids){const d=(v)=>Math.hypot((v[a*2]-v[b*2])*w,(v[a*2+1]-v[b*2+1])*h);max=Math.max(max,Math.abs(d(r.rest)-d(r.positionsByRole.head)));}}
 assert.ok(max<.001,`maximum distance drift ${max}px`);console.log('rigid head maximum distance drift px',max);
});
test('v44 runtime cannot import angle artwork or apply facial warp',()=>{assert.equal(model.faceAngles,undefined);assert.equal(model.headMotion.mode,'rigid-2d-roll');const s=readFileSync(new URL('../web/renderer.js',import.meta.url),'utf8');assert.ok(!/face-angle-rig|paintNoseMaterial|faceAngleRig/.test(s));});

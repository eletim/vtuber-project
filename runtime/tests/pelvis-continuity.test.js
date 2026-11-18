import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {BodyRig} from '../web/body-rig.js';
import {neutral} from '../web/controls.js';
const m=JSON.parse(readFileSync(new URL('../model/model.json',import.meta.url))),w=JSON.parse(readFileSync(new URL('../model/skinning.json',import.meta.url)));
const index=(x,y)=>(Math.round(y/m.size[1]*m.mesh[1])*(m.mesh[0]+1)+Math.round(x/m.size[0]*m.mesh[0]))*2;
const distance=(a,i,j)=>Math.hypot((a[i]-a[j])*m.size[0],(a[i+1]-a[j+1])*m.size[1]);
test('bounce transports every attachment without stretching chest, waist or legs',()=>{
 const r=new BodyRig(m,w),a=index(540,580),b=index(540,995),la=index(500,1230),lb=index(500,1410);
 for(let f=0;f<240;f++){
  r.frame({...neutral(),ParamBodyBounce:Math.sin(f/20)},f/60);
  assert.ok(Math.abs(distance(r.positions,a,b)-distance(r.rest,a,b))<.001);
  assert.ok(Math.abs(distance(r.positionsByRole.root,la,lb)-distance(r.rest,la,lb))<.001);
  const row=Math.ceil(995/m.size[1]*m.mesh[1]);
  for(let x=0;x<=m.mesh[0];x++){const i=(row*(m.mesh[0]+1)+x)*2;for(const role of ['torso','skirt']){assert.equal(r.positionsByRole[role][i],r.positionsByRole.root[i]);assert.equal(r.positionsByRole[role][i+1],r.positionsByRole.root[i+1]);}}
 }
});
test('all waist attachment vertices stay coincident through mixed reversals and lower body follows',()=>{
 const r=new BodyRig(m,w),row=Math.ceil(995/m.size[1]*m.mesh[1]);let lowerMotion=0,maxLengthError=0;
 const a=index(540,580),b=index(540,995),leg=index(540,1320),restLength=distance(r.rest,a,b);
 for(let f=0;f<600;f++){
  r.frame({...neutral(),ParamBodyShiftX:Math.sin(f/30),ParamBodyAngleX:5*Math.sin(f/40),ParamBodyBounce:Math.sin(f/19)},f/60);
  for(let x=0;x<=m.mesh[0];x++){const i=(row*(m.mesh[0]+1)+x)*2;for(const role of ['torso','skirt']){assert.equal(r.positionsByRole[role][i],r.positionsByRole.root[i]);assert.equal(r.positionsByRole[role][i+1],r.positionsByRole.root[i+1]);}}
  maxLengthError=Math.max(maxLengthError,Math.abs(distance(r.positions,a,b)-restLength));
  lowerMotion=Math.max(lowerMotion,Math.abs(r.positionsByRole.root[leg]-r.rest[leg])*m.size[0]);
 }
 assert.ok(lowerMotion>20);// Off-axis chord ends 12px away from the lumbar pivot; its projection changes slightly under counter-rotation.
 assert.ok(maxLengthError<1.25,`chest to waist length error ${maxLengthError}`);
});

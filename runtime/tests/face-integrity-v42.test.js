import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';import {BodyRig} from '../web/body-rig.js';import {neutral} from '../web/controls.js';
const m=JSON.parse(readFileSync(new URL('../model/model.json',import.meta.url))),w=JSON.parse(readFileSync(new URL('../model/skinning.json',import.meta.url)));
test('frontal feature distances stay constant through yaw pitch and compound limits',()=>{
 const points=[[26,12],[34,12],[28,16],[32,16],[30,18]],dist=[];
 for(const x of [-15,-10,-5,0,5,10,15])for(const y of [-10,-5,0,5,10]){
  const r=new BodyRig(m,w);r.frame({...neutral(),ParamAngleX:x,ParamAngleY:y},0,{ambient:false});
  const p=points.map(([x,y])=>{const i=(y*61+x)*2;return[r.positionsByRole.head[i]*1086,r.positionsByRole.head[i+1]*1448]});
  const d=p.slice(1).map(q=>Math.hypot(q[0]-p[0][0],q[1]-p[0][1]));if(!dist.length)dist.push(...d);else d.forEach((v,i)=>assert.ok(Math.abs(v-dist[i])<.001,'portrait ratio changed: '+x+','+y));
 }
});

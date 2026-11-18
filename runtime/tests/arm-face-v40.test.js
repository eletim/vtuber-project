import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {ArticulatedArm} from '../web/articulated-arm.js';
import {BodyRig} from '../web/body-rig.js';
import {neutral} from '../web/controls.js';
const m=JSON.parse(readFileSync(new URL('../model/model.json',import.meta.url))),w=JSON.parse(readFileSync(new URL('../model/skinning.json',import.meta.url)));
test('forearm shaft remains straight during both trajectories; wrist shaping cannot bow its middle',()=>{
 const f=m.bodyLayers.find(l=>l.id==='left_raised_forearm'),a=f.articulation,points=[.1,.3,.5,.7].flatMap(t=>[(a.sourceElbow[0]+t*(a.sourceWrist[0]-a.sourceElbow[0]))/1086,(a.sourceElbow[1]+t*(a.sourceWrist[1]-a.sourceElbow[1]))/1448]);
 const rig=new BodyRig(m,w);rig.frame(neutral(),0);const arm=new ArticulatedArm({...m,bodyLayers:[f]},new Float32Array(points));
 for(let i=0;i<=400;i++){arm.frame({...neutral(),ParamHandToCheek:i<=200?i/200:(400-i)/200},i/60,rig.pose,{snapArticulation:true});const v=arm.geometry.get(f.id),p=Array.from({length:4},(_,j)=>[v[j*2]*1086,v[j*2+1]*1448]),dx=p[3][0]-p[0][0],dy=p[3][1]-p[0][1];
 for(const q of p.slice(1,3))assert.ok(Math.abs(dx*(q[1]-p[0][1])-dy*(q[0]-p[0][0]))/Math.hypot(dx,dy)<.001);
 assert.ok(Math.hypot(...arm.joints.surfaceWrist.map((x,j)=>x-arm.joints.wrist[j]))<25);
 }
});

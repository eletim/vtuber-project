import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {BodyRig} from '../web/body-rig.js';
import {ArticulatedArm} from '../web/articulated-arm.js';
import {neutral} from '../web/controls.js';
import {performancePose} from '../web/performance.js';
const m=JSON.parse(readFileSync(new URL('../model/model.json',import.meta.url))),w=JSON.parse(readFileSync(new URL('../model/skinning.json',import.meta.url)));
test('ribcage counterbalances the loaded pelvis and left/right thighs have distinct lag',()=>{
 const r=new BodyRig(m,w);let legDifference=0;
 for(let f=0;f<240;f++){r.frame({...neutral(),ParamBodyShiftX:1},f/60);legDifference=Math.max(legDifference,Math.abs(r.pose.legs[0]-r.pose.legs[1]));}
 assert.ok(r.pose.pelvisAngle>2);assert.ok(r.pose.body+r.pose.pelvisAngle<-.3,'net chest inclination opposes pelvis');assert.ok(legDifference>1);
 assert.notDeepEqual(r.positionsByRole.legLeft,r.positionsByRole.legRight);
});
test('independent chest-abdomen and abdomen-pelvis cut strips stay coincident; thigh roots stay under skirt',()=>{
 const r=new BodyRig(m,w);
 for(let f=0;f<480;f++){
  r.frame({...neutral(),ParamBodyShiftX:Math.sin(f/20),ParamBodyAngleX:5*Math.sin(f/31),ParamBodyBounce:Math.sin(f/17)},f/60);
  for(let i=0;i<r.rest.length;i+=2){const y=r.rest[i+1]*m.size[1];
   const pairs=[];if(y>=800&&y<=835)pairs.push(['chest','abdomen']);if(y>=965&&y<=1000)pairs.push(['abdomen','pelvis']);if(y<=1300)pairs.push(['legLeft','pelvis'],['legRight','pelvis']);
   for(const [a,b] of pairs)for(const j of [i,i+1])assert.ok(Math.abs(r.positionsByRole[a][j]-r.positionsByRole[b][j])*1448<.001,`${a}/${b} at ${y}`);
  }
 }
});
test('cloth trails the raised arm while wrist and forearm lengths remain rigid',()=>{
 const r=new BodyRig(m,w),arm=new ArticulatedArm(m,r.rest);let lag=0;
 for(let f=0;f<360;f++){
  const p={...neutral(),ParamHandToCheek:f<90?1:0};r.frame(p,f/60);arm.frame(p,f/60,r.pose);lag=Math.max(lag,Math.abs(arm.amount-arm.cloth));
  const {wrist,elbow}=arm.joints;assert.ok(Math.abs(Math.hypot(wrist[0]-elbow[0],wrist[1]-elbow[1])-Math.hypot(201,330))<1e-6);
 }
 assert.ok(lag>.1);assert.ok(arm.cloth<.00001);
});
test('happy gesture no longer opens both arms in phase',()=>{
 let difference=0;for(let f=0;f<240;f++){const p=performancePose(neutral(),f/60,{enabled:true,emotion:'happy',started_at:0});difference=Math.max(difference,Math.abs(p.ParamArmLOpen-p.ParamArmROpen));}assert.ok(difference>.1);
});

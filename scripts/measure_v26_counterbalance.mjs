import {readFileSync,writeFileSync} from 'node:fs';
import {BodyRig} from '../runtime/web/body-rig.js';
import {neutral} from '../runtime/web/controls.js';
const m=JSON.parse(readFileSync('runtime/model/model.json')),w=JSON.parse(readFileSync('runtime/model/skinning.json')),r=new BodyRig(m,w);
const index=(x,y)=>(Math.round(y/1448*80)*61+Math.round(x/1086*60))*2;
const c=index(555,580),a=index(555,810),b=index(555,995),dist=(v,i,j)=>Math.hypot((v[i]-v[j])*1086,(v[i+1]-v[j+1])*1448);
const result={maximumChestLengthChange:0,maximumChestWaistLengthChange:0,maximumLegAngleDifference:0,maximumPelvisAngle:0,maximumBodyAngle:0,maximumStepPixels:0};
let before=null;
for(let f=0;f<900;f++){const t=f/60,p={...neutral(),ParamBodyShiftX:Math.sin(t*1.7),ParamBodyAngleX:3*Math.sin(t*1.7),ParamBodyBounce:Math.sin(t*3)};r.frame(p,t);
 result.maximumChestLengthChange=Math.max(result.maximumChestLengthChange,Math.abs(dist(r.positionsByRole.chest,c,a)-dist(r.rest,c,a)));
 result.maximumChestWaistLengthChange=Math.max(result.maximumChestWaistLengthChange,Math.abs(dist(r.positions,c,b)-dist(r.rest,c,b)));
 result.maximumLegAngleDifference=Math.max(result.maximumLegAngleDifference,Math.abs(r.pose.legs[0]-r.pose.legs[1]));result.maximumPelvisAngle=Math.max(result.maximumPelvisAngle,Math.abs(r.pose.pelvisAngle));result.maximumBodyAngle=Math.max(result.maximumBodyAngle,Math.abs(r.pose.body));
 const points=['chest','pelvis','legLeft','legRight'].map(role=>[r.positionsByRole[role][b]*1086,r.positionsByRole[role][b+1]*1448]);if(before)points.forEach((q,i)=>result.maximumStepPixels=Math.max(result.maximumStepPixels,Math.hypot(q[0]-before[i][0],q[1]-before[i][1])));before=points;
}
writeFileSync('assets/parts/v26/counterbalance-metrics.json',JSON.stringify(result,null,2));console.log(result);

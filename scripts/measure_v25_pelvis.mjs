import {execFileSync} from 'node:child_process';
import {readFileSync,writeFileSync} from 'node:fs';
import {BodyRig as After} from '../runtime/web/body-rig.js';
import {neutral} from '../runtime/web/controls.js';
const old=execFileSync('git',['show','3da848cf3d58c9dc1d13c92ebab53c3ba82b1393:runtime/web/body-rig.js'],{encoding:'utf8'});
const {BodyRig:Before}=await import('data:text/javascript;base64,'+Buffer.from(old).toString('base64'));
const m=JSON.parse(readFileSync('runtime/model/model.json')),weights=JSON.parse(readFileSync('runtime/model/skinning.json'));
const idx=(x,y)=>(Math.round(y/m.size[1]*m.mesh[1])*(m.mesh[0]+1)+Math.round(x/m.size[0]*m.mesh[0]))*2;
const a=idx(540,580),b=idx(540,995),leg=idx(540,1320),dist=(v)=>Math.hypot((v[a]-v[b])*m.size[0],(v[a+1]-v[b+1])*m.size[1]);
const report={};
for(const [label,Type] of [['v24',Before],['v25',After]]){
 const r=new Type(m,weights),rest=dist(r.rest),result={maxChestWaistLengthChange:0,maxLegDisplacement:0,maxAttachmentSeparation:0};
 for(let f=0;f<=600;f++){
  const t=f/60,p={...neutral(),ParamBodyShiftX:Math.sin(t*2),ParamBodyAngleX:5*Math.sin(t*1.5),ParamBodyBounce:Math.sin(t*3)};r.frame(p,t);
  result.maxChestWaistLengthChange=Math.max(result.maxChestWaistLengthChange,Math.abs(dist(r.positions)-rest));
  const root=r.positionsByRole.root;result.maxLegDisplacement=Math.max(result.maxLegDisplacement,Math.hypot((root[leg]-r.rest[leg])*m.size[0],(root[leg+1]-r.rest[leg+1])*m.size[1]));
  const row=Math.ceil(995/m.size[1]*m.mesh[1]);for(let x=0;x<=m.mesh[0];x++){const i=(row*(m.mesh[0]+1)+x)*2;result.maxAttachmentSeparation=Math.max(result.maxAttachmentSeparation,Math.hypot((r.positions[i]-r.positionsByRole.skirt[i])*m.size[0],(r.positions[i+1]-r.positionsByRole.skirt[i+1])*m.size[1]));}
 }
 report[label]=result;
}
writeFileSync('assets/parts/v25/pelvis-metrics.json',JSON.stringify(report,null,2));console.log(report);

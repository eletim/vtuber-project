import {readFileSync,writeFileSync} from 'node:fs';import {execFileSync} from 'node:child_process';import {BodyRig} from '../runtime/web/body-rig.js';import {neutral} from '../runtime/web/controls.js';
const m=JSON.parse(readFileSync('runtime/model/model.json')),w=JSON.parse(readFileSync('runtime/model/skinning.json'));const report=[];
for(const [version,ref] of [['v39','58b73ac'],['v40','b7a01cf'],['v41','e3b7b78'],['v42',null]]){
 const C=ref?(await import('data:text/javascript;base64,'+Buffer.from(execFileSync('git',['show',ref+':runtime/web/body-rig.js'])).toString('base64'))).BodyRig:BodyRig;
 const base=new C(m,w);base.frame(neutral(),0);const baseline=base.positionsByRole.head;
 for(const [x,y] of [[-15,0],[15,0],[0,-10],[0,10],[-15,-10],[15,10]]){
  const r=new C(m,w);r.frame({...neutral(),ParamAngleX:x,ParamAngleY:y},0);const v=r.positionsByRole.head;const ratios=[];
  for(let row=11;row<=22;row++)for(let col=23;col<=36;col++){const a=(row*61+col)*2,b=a+2;const dist=q=>Math.hypot((q[b]-q[a])*1086,(q[b+1]-q[a+1])*1448);ratios.push(dist(v)/dist(baseline));}
  report.push({version,x,y,faceHorizontalEdgeScaleMin:Math.min(...ratios),faceHorizontalEdgeScaleMax:Math.max(...ratios)});
 }
}
writeFileSync('assets/parts/v42/face-metrics.json',JSON.stringify(report,null,2));console.log(JSON.stringify(report.filter(x=>x.x===15&&x.y===10)));

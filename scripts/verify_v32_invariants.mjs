import {readFileSync,writeFileSync} from 'node:fs';
import {execFileSync} from 'node:child_process';
import {pathToFileURL} from 'node:url';import {resolve} from 'node:path';
import {BodyRig} from '../runtime/web/body-rig.js';
import {ArticulatedArm} from '../runtime/web/articulated-arm.js';
import {neutral} from '../runtime/web/controls.js';
const baseline='23db0404b944b7e8fb4c98df466854d012319d95';
const src=execFileSync('git',['show',baseline+':runtime/web/articulated-arm.js'],{encoding:'utf8'}).replace("'./body-rig.js'",JSON.stringify(pathToFileURL(resolve('runtime/web/body-rig.js')).href));
const {ArticulatedArm:Old}=await import('data:text/javascript;base64,'+Buffer.from(src).toString('base64'));
const m=JSON.parse(readFileSync('runtime/model/model.json')),w=JSON.parse(readFileSync('runtime/model/skinning.json')),r=new BodyRig(m,w);r.frame(neutral(),0);
const arms=[new Old(m,r.rest),new ArticulatedArm(m,r.rest)],report={baseline,samples:[],newInvertedCells:0,invertedLocations:[],maximumClothVertexStep:0,cuffAlphaChanges:0,shoulderGeometryChanges:0};let previous;
for(let f=0;f<=1110;f++){
 const time=f/60,amount=time<10?0:time<12?(time-10)/2:time<13?1:time<15?(15-time)/2:0;
 for(const a of arms)a.frame({...neutral(),ParamHandToCheek:amount},time,r.pose);
 let minimum=1,maxStep=0;
 const vectors=arms.map(a=>a.geometry.get('left_raised_drape'));
 for(let row=35;row<54;row++)for(let col=9;col<30;col++){
  const j=(row*61+col)*2,k=j+2,l=j+122;
  const areas=vectors.map(v=>((v[k]-v[j])*(v[l+1]-v[j+1])-(v[k+1]-v[j+1])*(v[l]-v[j]))*4800);
  if(areas[0]>.0001&&areas[1]<-.0001){report.newInvertedCells++;report.invertedLocations.push({time,row,col,areas});}
  minimum=Math.min(minimum,areas[1]);if(previous)maxStep=Math.max(maxStep,Math.hypot((vectors[1][j]-previous[j])*1086,(vectors[1][j+1]-previous[j+1])*1448));
 }
 for(const layer of m.bodyLayers.filter(l=>l.id.includes('shoulder'))){const before=arms[0].geometry.get(layer.id),after=arms[1].geometry.get(layer.id);if(before&&after)for(let j=0;j<before.length;j++)if(before[j]!==after[j])report.shoulderGeometryChanges++}
 const cuff=m.bodyLayers.find(l=>l.id==='left_raised_cuff');if(arms[1].opacity(cuff)!==1)report.cuffAlphaChanges++;
 report.maximumClothVertexStep=Math.max(report.maximumClothVertexStep,maxStep);report.samples.push({time,amount:arms[1].amount,maxStep,cuffAlpha:arms[1].opacity(cuff),minimumSignedArea:minimum});previous=vectors[1].slice();
}
writeFileSync('assets/parts/v32/geometry-continuity.json',JSON.stringify(report,null,2));console.log(JSON.stringify({...report,invertedLocations:report.invertedLocations.length,samples:report.samples.length}));
// Tiny sign changes near pre-existing degenerate cloth cells are retained in
// the report for visual review, not silently discarded as a numeric pass.
if(report.shoulderGeometryChanges||report.cuffAlphaChanges)process.exitCode=1;

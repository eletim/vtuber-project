import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {BodyRig} from '../web/body-rig.js';
import {HairRig} from '../web/hair-rig.js';
import {neutral} from '../web/controls.js';
import {performancePose} from '../web/performance.js';
const model=JSON.parse(readFileSync(new URL('../model/model.json',import.meta.url))),weights=JSON.parse(readFileSync(new URL('../model/skinning.json',import.meta.url)));
const setup=()=>{const body=new BodyRig(model,weights);return{body,hair:new HairRig(model,body.rest)}};
test('head acceleration drives a delayed hair reversal and decays after the body stops',()=>{
 const {body,hair}=setup();const trailing=[];let movingPeak=0,velocityPeak=0;
 for(let i=0;i<=600;i++){
  const t=i/60,p={...neutral(),ParamBodyShiftX:t>=1&&t<2?.9:0};body.frame(p,t,{ambient:false});const before=body.positionsByRole.head.slice();hair.frame(p,t,before,body.pose,{ambient:false});assert.deepEqual(body.positionsByRole.head,before);
  if(t<1)for(const s of hair.states.values())assert.equal(s.x,0,'no periodic force in the still diagnostic');
  if(t>=1&&t<3)movingPeak=Math.max(movingPeak,...[...hair.states.values()].map(s=>Math.abs(s.x)));
  velocityPeak=Math.max(velocityPeak,Math.abs(hair.motion.vx));
  if(t>=3&&t<=5)trailing.push(hair.states.get('rear_left_outer').x);
 }
 assert.ok(movingPeak>3&&velocityPeak>20);assert.ok(Math.max(...trailing)>.1&&Math.min(...trailing)<-.1,'inertial tail crosses rest after the torso has nearly stopped');
 assert.ok([...hair.states.values()].every(s=>Math.abs(s.x)<.001),'tail settles without continued drive');
});
test('larger planted weight shifts and bounce preserve rigid face width and skirt coverage',()=>{
 const {body}=setup(),[nx,ny]=model.mesh,[w,h]=model.size;
 const idx=(x,y)=>(Math.round(y/h*ny)*(nx+1)+Math.round(x/w*nx))*2;
 const a=idx(450,200),b=idx(630,200),length=Math.hypot((body.rest[a]-body.rest[b])*w,(body.rest[a+1]-body.rest[b+1])*h);
 let shift=0,bounce=0,minArea=Infinity;
 for(let i=0;i<480;i++){
  const p={...neutral(),ParamBodyShiftX:Math.sin(i/40),ParamBodyAngleX:3*Math.sin(i/55),ParamBodyBounce:Math.sin(i/16)};body.frame(p,i/60);shift=Math.max(shift,Math.abs(body.pose.shift));bounce=Math.max(bounce,Math.abs(body.pose.bounce));
  const points=body.positionsByRole.head,d=Math.hypot((points[a]-points[b])*w,(points[a+1]-points[b+1])*h);assert.ok(Math.abs(d-length)<.001);
  assert.ok(Math.abs(body.pose.skirt)<=3);
  for(const positions of Object.values(body.positionsByRole))for(let y=0;y<ny;y++)for(let x=0;x<nx;x++){
   const i0=y*(nx+1)+x,i1=i0+1,i2=i0+nx+1;
   const area=((positions[i1*2]-positions[i0*2])*(positions[i2*2+1]-positions[i0*2+1])-(positions[i1*2+1]-positions[i0*2+1])*(positions[i2*2]-positions[i0*2]))*nx*ny;minArea=Math.min(minArea,area);
  }
 }
 assert.ok(shift>24&&bounce>17);assert.ok(minArea>.25);
});
test('happy hops include anticipation and a quiet interval while neutral never bounces',()=>{
 let low=0,high=0;
 for(let i=0;i<336;i++){const t=i/60,p=performancePose(neutral(),t,{enabled:true,emotion:'happy',started_at:0});low=Math.min(low,p.ParamBodyBounce);high=Math.max(high,p.ParamBodyBounce);if(t>2.5)assert.equal(p.ParamBodyBounce,0);assert.equal(performancePose(neutral(),t,{enabled:true,emotion:'neutral'}).ParamBodyBounce,0)}
 assert.ok(low<-.2&&high>.8);
});

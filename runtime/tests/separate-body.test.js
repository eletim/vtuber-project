import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {BodyRig,bodyRoles} from '../web/body-rig.js';
import {bodyLayers,bodyTextureRect,bodyTextureFile,bodySamplingPlan} from '../web/render-plan.js';
import {neutral,limits,smoothParameters} from '../web/controls.js';
const model=JSON.parse(readFileSync(new URL('../model/model.json',import.meta.url)));
const weights=JSON.parse(readFileSync(new URL('../model/skinning.json',import.meta.url)));
const make=()=>new BodyRig(model,weights);
const pixelDistance=(a,b)=>{let max=0;for(let i=0;i<a.length;i+=2)max=Math.max(max,Math.hypot((a[i]-b[i])*model.size[0],(a[i+1]-b[i+1])*model.size[1]));return max;};
function minimumArea(positions){
  const [nx,ny]=model.mesh;let minimum=Infinity;
  const area=(a,b,c)=>((positions[b*2]-positions[a*2])*(positions[c*2+1]-positions[a*2+1])-(positions[b*2+1]-positions[a*2+1])*(positions[c*2]-positions[a*2]))*nx*ny;
  for(let y=0;y<ny;y++)for(let x=0;x<nx;x++){const a=y*(nx+1)+x,b=a+1,c=a+nx+1,d=c+1;minimum=Math.min(minimum,area(a,b,c),area(b,d,c));}
  return minimum;
}

test('every render role has a distinct surface and exactly preserves rest geometry',()=>{
  const r=make(),frames=r.frames(neutral(),0,{ambient:false});
  assert.deepEqual(Object.keys(frames),bodyRoles);
  assert.equal(new Set(Object.values(frames).map(array=>array.buffer)).size,bodyRoles.length);
  for(const positions of Object.values(frames))assert.deepEqual(positions,r.rest);
  assert.equal(r.positions,frames.torso,'legacy return is explicitly torso, never a secretly combined warp');
});

test('isolated arm or skirt input changes only its own independent surface',()=>{
  for(const [control,role] of [['ParamArmLOpen','armLeft'],['ParamArmROpen','armRight'],['ParamSkirtSway','skirt']]){
    for(const sign of [-1,1]){
      const r=make(),baseline=make();
      for(let frame=0;frame<=180;frame++){
        const t=frame/60,pose={...neutral(),[control]:sign};
        r.frames(pose,t,{ambient:false});baseline.frames(neutral(),t,{ambient:false});
        for(const other of bodyRoles.filter(id=>id!==role))assert.deepEqual(r.positionsByRole[other],baseline.positionsByRole[other],`${control} contaminated ${other} at ${t}`);
      }
      assert.ok(pixelDistance(r.positionsByRole[role],baseline.positionsByRole[role])>(role==='skirt'?2.5:10),`${control} has independent motion within approved art coverage`);
    }
  }
});

test('torso never receives ambient hair sway and diagnostic neutral stays pixel-fixed',()=>{
  const r=make();r.frame(neutral(),0);
  for(let frame=1;frame<180;frame++){
    r.frame(neutral(),frame/60);
    assert.deepEqual(r.positionsByRole.torso,r.rest);
  }
  assert.deepEqual(r.positionsByRole.head,r.rest,'fixed face/crown no longer owns ambient hair sway');
  r.frame(neutral(),3,{ambient:false});assert.deepEqual(r.positionsByRole.head,r.rest);
});

test('skirt has a locked waist and delayed hem, then settles after interruption',()=>{
  const r=make();r.frame(neutral(),0,{ambient:false});
  const first=r.frames({...neutral(),ParamSkirtSway:1},1/60,{ambient:false}).skirt.slice();
  assert.ok(pixelDistance(first,r.rest)<.1,'skirt must ease in, not teleport to requested hem');
  for(let frame=2;frame<180;frame++)r.frame({...neutral(),ParamSkirtSway:1},frame/60,{ambient:false});
  assert.ok(r.pose.skirt>2.99&&r.pose.skirt<=3);
  for(let i=0;i<r.rest.length;i+=2)if(r.rest[i+1]*model.size[1]<=r.config.skirtTop+8){
    assert.equal(r.positionsByRole.skirt[i],r.rest[i]);assert.equal(r.positionsByRole.skirt[i+1],r.rest[i+1]);
  }
  for(let frame=180;frame<540;frame++)r.frame(neutral(),frame/60,{ambient:false});
  assert.ok(Math.abs(r.pose.skirt)<.00001);
  assert.ok(pixelDistance(r.positionsByRole.skirt,r.rest)<.001);
});

test('body motion drives skirt inertia but arms cannot drive it',()=>{
  const r=make();r.frame(neutral(),0,{ambient:false});
  let peak=0,lagObserved=false;
  for(let frame=1;frame<240;frame++){
    r.frame({...neutral(),ParamBodyAngleX:frame<60?5:0},frame/60,{ambient:false});
    peak=Math.max(peak,Math.abs(r.pose.skirt));
    if(frame>60&&Math.abs(r.pose.body)<1&&Math.abs(r.pose.skirt)>.1)lagObserved=true;
  }
  assert.ok(peak>.5);assert.ok(lagObserved,'hem should trail the upper-body response');
});

test('all independent surfaces retain positive triangles through extreme reversals',()=>{
  const r=make(),min=Object.fromEntries(bodyRoles.map(role=>[role,Infinity]));
  for(let i=0;i<480;i++){
    const sign=j=>Math.sin(i*(.11+j*.019))>=0?1:-1;
    const pose={...neutral(),ParamAngleX:15*sign(0),ParamAngleY:10*sign(1),ParamAngleZ:8*sign(2),ParamBodyAngleX:5*sign(3),ParamArmLOpen:sign(4),ParamArmROpen:sign(5),ParamShoulderY:sign(6),ParamBodyShiftX:sign(7),ParamBreath:(sign(8)+1)/2,ParamSkirtSway:sign(9)};
    const frames=r.frames(pose,i/60);
    for(const role of bodyRoles)min[role]=Math.min(min[role],minimumArea(frames[role]));
  }
  for(const [role,area] of Object.entries(min))assert.ok(area>.25,`${role}: minimum triangle area ${area}`);
});

test('skirt control defaults, smoothing, and draw-plan source coordinates are explicit',()=>{
  assert.deepEqual(limits.ParamSkirtSway,[-1,1,0]);
  assert.equal(neutral().ParamSkirtSway,0);
  assert.ok(smoothParameters(neutral(),{ParamSkirtSway:10},1).ParamSkirtSway<=1);
  const layer={id:'head',role:'head',file:'head.png',rect:[10,20,30,60],features:true,expressionFiles:{happy:'happy.png'}};
  const fixture={size:[100,200],bodyLayers:[layer]};
  assert.deepEqual(bodyLayers(fixture),[layer]);
  assert.deepEqual(bodyTextureRect(layer,fixture),[.1,.1,.2,.2]);
  assert.equal(bodyTextureFile(layer,{id:'happy'},fixture),'happy.png');
  assert.equal(bodyTextureFile(layer,{id:'neutral'},fixture),'head.png');
  assert.throws(()=>bodyLayers({...fixture,bodyLayers:[layer,layer]}),/invalid body layer/);
});

test('all 1024 settled control corners keep every render role non-inverting',()=>{
  const r=make(),clamp=(x,a,b)=>Math.min(b,Math.max(a,x));let minimum=Infinity;
  for(let bits=0;bits<1024;bits++){
    const sign=i=>(bits>>i)&1?1:-1;
    const p={...neutral(),ParamBodyAngleX:sign(0)*5,ParamAngleX:sign(1)*15,ParamAngleY:sign(2)*10,ParamAngleZ:sign(3)*8,ParamBreath:(sign(4)+1)/2,ParamArmLOpen:sign(5),ParamArmROpen:sign(6),ParamShoulderY:sign(7),ParamBodyShiftX:sign(8),ParamSkirtSway:sign(9)};
    r.body.x=clamp(p.ParamBodyAngleX*.8+p.ParamAngleX*.04,-4.6,4.6);r.body.v=0;
    for(let side=0;side<2;side++){
      const s=side===0?1:-1;
      r.arms[side].x=clamp(s*2.8*p[side===0?'ParamArmLOpen':'ParamArmROpen']+r.body.x*.09+s*(p.ParamBreath-.5)*.18,-3.2,3.2);r.arms[side].v=0;
      r.elbows[side].x=-r.arms[side].x*.35;r.elbows[side].v=0;
    }
    r.shoulder.x=p.ParamShoulderY*3;r.shoulder.v=0;r.shift.x=p.ParamBodyShiftX*36;r.shift.v=0;
    r.skirt.x=clamp(p.ParamSkirtSway*3-r.body.x*.65,-3,3);r.skirt.v=0;r.lastTime=0;
    for(const positions of Object.values(r.frames(p,0)))minimum=Math.min(minimum,minimumArea(positions));
  }
  assert.ok(minimum>.25,`all independent roles, settled normalized triangle area ${minimum}`);
});


test('seam-safe sampling resolves the complete avatar once within device texture limits',()=>{
  assert.deepEqual(bodySamplingPlan({},652,869,4096),{enabled:false,width:652,height:869,scale:1});
  assert.deepEqual(bodySamplingPlan({bodySampling:'coverage-2x'},652,869,4096),{enabled:true,width:1304,height:1738,scale:2});
  const limited=bodySamplingPlan({bodySampling:'coverage-2x'},652,869,1024);
  assert.ok(limited.width<=1024&&limited.height<=1024);assert.ok(limited.scale<2&&limited.scale>1);
});

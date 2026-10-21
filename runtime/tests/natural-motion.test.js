import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {BodyRig} from '../web/body-rig.js';
import {PerformanceMotion} from '../web/performance.js';
import {neutral,limits,smoothParameters} from '../web/controls.js';
const model=JSON.parse(readFileSync(new URL('../model/model.json',import.meta.url)));
const skinning=JSON.parse(readFileSync(new URL('../model/skinning.json',import.meta.url)));
const makeRig=()=>new BodyRig(model,skinning);
const state={enabled:true,emotion:'neutral',started_at:0,until:0};
const vertex=(x,y)=>Math.round(y/model.size[1]*model.mesh[1])*(model.mesh[0]+1)+Math.round(x/model.size[0]*model.mesh[0]);
const xy=(positions,x,y)=>{const i=vertex(x,y);return [positions[2*i]*model.size[0],positions[2*i+1]*model.size[1]];};
const distance=(a,b)=>Math.hypot(a[0]-b[0],a[1]-b[1]);
const subtract=(a,b)=>[a[0]-b[0],a[1]-b[1]];
function minimumArea(positions){
  const [nx,ny]=model.mesh;let minimum=Infinity;
  const area=(a,b,c)=>((positions[b*2]-positions[a*2])*(positions[c*2+1]-positions[a*2+1])-(positions[b*2+1]-positions[a*2+1])*(positions[c*2]-positions[a*2]))*nx*ny;
  for(let y=0;y<ny;y++)for(let x=0;x<nx;x++){
    const a=y*(nx+1)+x,b=a+1,c=a+nx+1,d=c+1;
    minimum=Math.min(minimum,area(a,b,c),area(b,d,c));
  }
  return minimum;
}

test('speech accents alternate sparsely, ease in/out and leave silent arms alone',()=>{
  const motion=new PerformanceMotion();let previous=neutral(),maxStep=0,peak=0,quiet=0,active=0;
  const sides=[];let count=0;
  for(let i=0;i<=1800;i++){
    const t=i/60,mouth=t>=2&&t<22?.45+.4*Math.sin(t*8)**2:0;
    const p=motion.frame({...neutral(),ParamMouthOpenY:mouth},t,state,mouth);
    assert.equal(p.ParamMouthOpenY,mouth,'motion must not fabricate lip sync');
    if(t<2||t>23){assert.equal(p.ParamArmLOpen,0);assert.equal(p.ParamArmROpen,0);assert.equal(p.ParamShoulderY,0);}
    if(t>=2&&t<22){if(motion.pose.accent>.02)active++;else quiet++;}
    for(const key of ['ParamArmLOpen','ParamArmROpen','ParamShoulderY'])maxStep=Math.max(maxStep,Math.abs(p[key]-previous[key]));
    peak=Math.max(peak,p.ParamArmLOpen,p.ParamArmROpen);
    if(motion.sequence!==count){sides.push(motion.gesture.side);count=motion.sequence;}
    for(const [key,[lo,hi]] of Object.entries(limits))assert.ok(p[key]>=lo&&p[key]<=hi,key);
    previous=p;
  }
  assert.ok(peak>.7&&peak<1,`visible bounded gesture peak ${peak}`);
  assert.ok(maxStep<.08,`maximum target step ${maxStep}`);
  assert.ok(count>=5&&count<=8,`not a gesture on every syllable: ${count}`);
  assert.ok(quiet>active,'more quiet time than arm-accent time');
  assert.ok(sides.every((s,i)=>i===0||s!==sides[i-1]),'lead arm alternates');
});

test('short audio spikes do not trigger arms; silence and changed speech settle them',()=>{
  const motion=new PerformanceMotion();
  for(let i=0;i<120;i++)motion.frame(neutral(),i/60,state,i===30?1:0);
  assert.equal(motion.sequence,0);
  let previous=0,maxStep=0;
  for(let i=120;i<360;i++){
    const t=i/60,mouth=t<2.8?.8:0;
    motion.frame(neutral(),t,{...state,started_at:t>=2.5?2.5:0},mouth);
    maxStep=Math.max(maxStep,Math.abs(motion.pose.accent-previous));previous=motion.pose.accent;
  }
  assert.ok(maxStep<.08,`interrupted accent step ${maxStep}`);
  assert.equal(motion.pose.accent,0);
});

test('disable and time discontinuities drop stale gestures without changing external commands',()=>{
  const motion=new PerformanceMotion(),base={...neutral(),ParamArmLOpen:.8,ParamArmROpen:-.4,ParamShoulderY:.3,ParamBodyShiftX:-.7};
  for(let i=0;i<40;i++)motion.frame(base,i/60,state,.8);
  assert.ok(motion.pose.accent>.2);
  assert.deepEqual(motion.frame(base,40/60,{enabled:false},1),base);
  assert.equal(motion.pose.accent,0);
  const first=motion.frame(base,41/60,state,.8);
  assert.equal(first.ParamArmLOpen,base.ParamArmLOpen);assert.equal(first.ParamArmROpen,base.ParamArmROpen);
  for(let i=42;i<80;i++)motion.frame(base,i/60,state,.8);
  for(const time of [100,0]){
    const p=motion.frame(base,time,state,.8);
    assert.equal(p.ParamArmLOpen,base.ParamArmLOpen);assert.equal(motion.pose.accent,0);
  }
  motion.reset();assert.equal(motion.sequence,0);assert.equal(motion.gesture,null);
});

test('new controls default safely for legacy clients, clamp and preserve disabled poses',()=>{
  const legacy={ParamAngleX:2,ParamAngleY:0,ParamAngleZ:0,ParamBodyAngleX:0,ParamBreath:.5,ParamEyeLOpen:1,ParamEyeROpen:1,ParamMouthOpenY:0};
  const smoothed=smoothParameters(legacy,{...legacy,ParamArmLOpen:200,ParamArmROpen:-200},1);
  assert.ok(Object.values(smoothed).every(Number.isFinite));
  assert.ok(smoothed.ParamArmLOpen<=1&&smoothed.ParamArmLOpen>.99);
  assert.ok(smoothed.ParamArmROpen>=-1&&smoothed.ParamArmROpen<-.99);
  assert.deepEqual(new PerformanceMotion().frame(legacy,0,{enabled:false},1),legacy);
  const rig=makeRig();rig.frame(legacy,0);rig.frame(legacy,.016);
  assert.ok([...rig.positions].every(Number.isFinite));
});

test('autonomous accents respect saturated manual limbs and use only remaining headroom',()=>{
  for(const sign of [-1,1]){
    const motion=new PerformanceMotion(),base={...neutral(),ParamArmLOpen:sign,ParamArmROpen:sign,ParamShoulderY:sign,ParamBodyShiftX:sign};
    for(let i=0;i<240;i++){
      const p=motion.frame(base,i/60,{...state,emotion:'happy'},.9);
      for(const key of ['ParamArmLOpen','ParamArmROpen','ParamShoulderY','ParamBodyShiftX'])assert.equal(p[key],base[key]);
    }
  }
});

test('all 512 settled control corners retain positive triangle area and a fixed pelvis',()=>{
  const r=makeRig(),clamp=(x,lo,hi)=>Math.min(hi,Math.max(lo,x));let min=Infinity;
  for(let bits=0;bits<512;bits++){
    const sign=i=>(bits>>i)&1?1:-1;
    const p={...neutral(),ParamBodyAngleX:sign(0)*5,ParamAngleX:sign(1)*15,ParamAngleY:sign(2)*10,ParamAngleZ:sign(3)*8,ParamBreath:(sign(4)+1)/2,ParamArmLOpen:sign(5),ParamArmROpen:sign(6),ParamShoulderY:sign(7),ParamBodyShiftX:sign(8)};
    // Set the analytically settled state rather than spend thousands of frames
    // warming up each corner. Reachable moving states are exercised below.
    r.body.x=clamp(p.ParamBodyAngleX*.8+p.ParamAngleX*.04,-4.6,4.6);r.body.v=0;
    for(let side=0;side<2;side++){
      const s=side===0?1:-1;
      r.arms[side].x=clamp(s*2.8*p[side===0?'ParamArmLOpen':'ParamArmROpen']+r.body.x*.09+s*(p.ParamBreath-.5)*.18,-3.2,3.2);r.arms[side].v=0;
      r.elbows[side].x=-r.arms[side].x*.35;r.elbows[side].v=0;
    }
    r.shoulder.x=p.ParamShoulderY*3;r.shoulder.v=0;r.shift.x=p.ParamBodyShiftX*4;r.shift.v=0;r.lastTime=0;
    const positions=r.frame(p,0);min=Math.min(min,minimumArea(positions));
    for(const y of [1390,1448])assert.deepEqual(xy(positions,543,y),xy(r.rest,543,y));
  }
  assert.ok(min>.25,`minimum normalized area ${min}`);
  assert.deepEqual(r.weights,skinning.weights,'runtime field must not mutate source ownership');
});

test('rapid multi-axis reversals keep every triangle oriented and limbs within their caps',()=>{
  const r=makeRig();let min=Infinity;
  for(let i=0;i<1800;i++){
    const s=j=>Math.sin(i*(.047+j*.013))>0?1:-1;
    const p={...neutral(),ParamBodyAngleX:s(0)*5,ParamAngleX:s(1)*15,ParamAngleY:s(2)*10,ParamAngleZ:s(3)*8,ParamBreath:(s(4)+1)/2,ParamArmLOpen:s(5),ParamArmROpen:s(6),ParamShoulderY:s(7),ParamBodyShiftX:s(8)};
    min=Math.min(min,minimumArea(r.frame(p,i/60)));
    assert.ok(r.pose.arms.every(x=>Math.abs(x)<=3.2));assert.ok(r.pose.elbows.every(x=>Math.abs(x)<=1.12));
    assert.ok(Math.abs(r.pose.shoulder)<=3);assert.ok(Math.abs(r.pose.shift)<=4);
  }
  assert.ok(min>.25,`minimum normalized area ${min}`);
});

function sequence(fps){
  const r=makeRig(),motion=new PerformanceMotion();let current=neutral();const samples=[];
  for(let i=0;i<=12*fps;i++){
    const t=i/fps,mouth=t>=1&&t<9?.5+.35*Math.sin(t*8)**2:0;
    const target=motion.frame({...neutral(),ParamMouthOpenY:mouth},t,state,mouth);
    current=smoothParameters(current,target,1/fps);r.frame(current,t);
    if(i%(fps/10)===0)samples.push({t,hand:xy(r.positions,125,1340),arms:[...r.pose.arms],shoulder:r.pose.shoulder});
  }
  return samples;
}
test('gesture speed and amplitude are consistent at 20, 30, 60 and 120 fps',()=>{
  const reference=sequence(120);
  for(const fps of [20,30,60]){
    const samples=sequence(fps);let max=0;
    samples.forEach((sample,i)=>{max=Math.max(max,distance(sample.hand,reference[i].hand));});
    assert.ok(max<3.6,`${fps} fps maximum hand difference ${max}px`);
    assert.ok(Math.max(...samples.flatMap(s=>s.arms.map(Math.abs)))>1.8);
  }
});

test('speech visibly moves hands relative to shoulders, stays smooth, then settles when disabled',()=>{
  const r=makeRig(),control=makeRig(),motion=new PerformanceMotion();let current=neutral(),baseline=neutral(),peak=0,maxStep=0,previous;
  for(let i=0;i<=420;i++){
    const t=i/60,enabled=t<3,mouth=t>=1&&enabled?.8:0;
    const pose=motion.frame(neutral(),t,{...state,enabled},mouth);
    current=smoothParameters(current,pose,1/60);
    baseline=smoothParameters(baseline,{...pose,ParamArmLOpen:0,ParamArmROpen:0},1/60);
    const positions=r.frame(current,t),plain=control.frame(baseline,t);
    const relative=subtract(xy(positions,125,1340),xy(positions,365,565));
    const relativePlain=subtract(xy(plain,125,1340),xy(plain,365,565));
    peak=Math.max(peak,distance(relative,relativePlain));
    const hand=xy(positions,125,1340);if(previous)maxStep=Math.max(maxStep,distance(hand,previous));previous=hand;
  }
  assert.ok(peak>20,`relative hand displacement ${peak}px must be visible, not just torso sway`);
  assert.ok(maxStep<3,`hand step ${maxStep}px at 60fps`);
  assert.ok(r.pose.arms.every(v=>Math.abs(v)<.001));
  assert.ok(Math.abs(r.pose.shoulder)<.001);assert.ok(Math.abs(r.pose.shift)<.001);
});

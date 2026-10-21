import fs from 'node:fs';import path from 'node:path';import {fileURLToPath} from 'node:url';import {BodyRig,bodyRoles} from './source/runtime/web/body-rig.js';import {neutral,smoothParameters} from './source/runtime/web/controls.js';
const d=path.dirname(fileURLToPath(import.meta.url)),out=path.join(d,'arm-extremes');fs.mkdirSync(out,{recursive:true});if(!fs.existsSync(path.join(out,'source')))fs.symlinkSync('../source',path.join(out,'source'),'dir');
const plan=JSON.parse(fs.readFileSync(path.join(d,'frames.json'))),model=JSON.parse(fs.readFileSync(path.join(d,'source/runtime/model/model.json'))),skin=JSON.parse(fs.readFileSync(path.join(d,'source/runtime/model',model.skinning)));
const cases=[['neutral',0,0],['left_out',1,0],['left_in',-1,0],['right_out',0,1],['right_in',0,-1],['both_out',1,1],['both_in',-1,-1]];
const fds=Object.fromEntries(bodyRoles.map(r=>[r,fs.openSync(path.join(out,`mesh-${r}.bin`),'w')])),frames=[];
for(const [i,[label,left,right]] of cases.entries()){
 const rig=new BodyRig(model,skin);let current={...neutral(),ParamBreath:.5},positions;
 for(let frame=0;frame<=120;frame++){const p={...neutral(),ParamBreath:.5,ParamArmLOpen:left,ParamArmROpen:right};current=smoothParameters(current,p,1/30);positions=rig.frames(current,frame/30,{ambient:false});}
 for(const role of bodyRoles){const v=positions[role];fs.writeSync(fds[role],Buffer.from(v.buffer,v.byteOffset,v.byteLength));}
 frames.push({...plan.frames[0],i,label,section:'static_full_range_arm_test',p:current,t:4,case:[left,right]});
}
for(const fd of Object.values(fds))fs.closeSync(fd);fs.writeFileSync(path.join(out,'mouth-frames.rgba'),'');fs.writeFileSync(path.join(out,'frames.json'),JSON.stringify({...plan,frames,reviewFrameIndices:frames.map(f=>f.i),method:'Each independent pose is settled for121 chronological30fps steps with all torso/head/breath/skirt inputs fixed; both arm signs and combined signs included.'}));console.log(out);

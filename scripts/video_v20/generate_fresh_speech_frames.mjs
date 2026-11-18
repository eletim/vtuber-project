import fs from 'node:fs';import path from 'node:path';import {fileURLToPath} from 'node:url';
import {BodyRig,bodyRoles} from './source/runtime/web/body-rig.js';
import {PerformanceMotion} from './source/runtime/web/performance.js';
import {neutral,smoothParameters,rmsMouth} from './source/runtime/web/controls.js';
import {ExpressionTransition,expressionParameters,featureOpening,expressionLabels,deformMouthPixels} from './source/runtime/web/expressions.js';
import {bodyLayers,bodyTextureFile,bodyTextureRect,bodySamplingPlan} from './source/runtime/web/render-plan.js';
const dir=path.dirname(fileURLToPath(import.meta.url)),root=path.join(dir,'source/runtime/model');
const model=JSON.parse(fs.readFileSync(path.join(root,'model.json'))),skin=JSON.parse(fs.readFileSync(path.join(root,model.skinning)));
if(!model.bodyLayers||model.bodyLayers.some(l=>l.id==='legacy'))throw Error('V19 requires explicit independent body layers.');
const layers=bodyLayers(model).map(l=>({...l,textureRect:bodyTextureRect(l,model)}));
const sampling=bodySamplingPlan(model,900,1200);
const fps=30,duration=15,voiceStarts=[1.5],audio=JSON.parse(fs.readFileSync(path.join(dir,'audio_samples.json'))),voiceDuration=audio.length/24000;
const ids=['neutral','soft_smile','big_smile','worried','surprised','bashful','displeased','thinking'];
const emotions={neutral:'neutral',soft_smile:'happy',big_smile:'happy',worried:'thoughtful',surprised:'surprised',bashful:'neutral',displeased:'neutral',thinking:'thoughtful'};
const rgbaManifest=JSON.parse(fs.readFileSync(path.join(dir,'rgba-manifest.json'))),rgbaInputs=new Map(),sizes=new Map();
function mouthInput(file){if(!rgbaInputs.has(file))rgbaInputs.set(file,new Uint8ClampedArray(fs.readFileSync(path.join(dir,'source-rgba',rgbaManifest[file].file))));return rgbaInputs.get(file);}
function pngSize(file){if(!sizes.has(file)){const b=fs.readFileSync(path.join(root,file));sizes.set(file,{width:b.readUInt32BE(16),height:b.readUInt32BE(20)});}return sizes.get(file);}
const expressions=new Map(model.expressions.map(e=>[e.id,{...e,parts:e.parts.map(p=>({...p,image:pngSize(p.file)}))}]));
for(const layer of layers)for(const id of ids){const file=bodyTextureFile(layer,expressions.get(id),model),size=pngSize(file);if(size.width!==layer.rect[2]-layer.rect[0]||size.height!==layer.rect[3]-layer.rect[1])throw Error('Layer crop/image mismatch '+file);}
const meshFD=Object.fromEntries(bodyRoles.map(r=>[r,fs.openSync(path.join(dir,`mesh-${r}.bin`),'w')]));const mouthFD=fs.openSync(path.join(dir,'mouth-frames.rgba'),'w');let mouthOffset=0;
function fixed(){const p=neutral();p.ParamBreath=.5;return p;}
const voiceStart=1.5,voiceEnd=voiceStart+voiceDuration;
let rig=new BodyRig(model,skin),motion=new PerformanceMotion(),current=fixed();const transition=new ExpressionTransition(),frames=[];
for(let i=0;i<fps*duration;i++){
 const t=i/fps,voice=t>=voiceStart&&t<voiceEnd,section=voice?'fresh_speech':t<voiceStart?'idle':'settle',natural=true,reset=i===0;
 const offset=voice?Math.round((t-voiceStart)*24000):0,samples=voice?audio.slice(Math.max(0,offset-512),Math.min(audio.length,offset+512)):[];
 const base=fixed();base.ParamMouthOpenY=voice?rmsMouth(samples):0;
 const requested=voice?'soft_smile':'neutral';
 const performance={enabled:voice,emotion:'happy',started_at:voiceStart,until:voiceEnd};
 let p=motion.frame(base,t,performance,base.ParamMouthOpenY);
 p.ParamBreath=.5+(voice?.35*Math.sin((t-voiceStart)/1.7):0);
 if((t>=5&&t<5.15)||(t>=9&&t<9.15))p.ParamEyeLOpen=p.ParamEyeROpen=0;
 const label=voice?'新しく作った声に合わせて話す':t<voiceStart?'再生前の待機':'話し終わって、待機へ';
 current=smoothParameters(current,p,1/fps);
 transition.request(requested,t);const expressionFrame=transition.update(t),active=expressions.get(expressionFrame.id),facePose=expressionParameters(current,active,expressionFrame.gate),draw=[];
 for(const part of active.parts){
  const opening=featureOpening(facePose[part.parameter],part.parameter.includes('Mouth'));if(part.state!==opening.state)continue;
  let warp=null;
  if(part.parameter==='ParamMouthOpenY'&&part.state==='open'&&opening.scale<.9999){
   const cp=active.parts.find(p=>p.parameter==='ParamMouthOpenY'&&p.state==='closed'),closed={pixels:mouthInput(cp.file),width:cp.image.width,height:cp.image.height,rect:cp.rect};
   const pixels=deformMouthPixels(mouthInput(part.file),part.image.width,part.image.height,part,opening.scale,active.id,closed),bytes=Buffer.from(pixels.buffer,pixels.byteOffset,pixels.byteLength);
   fs.writeSync(mouthFD,bytes);warp={offset:mouthOffset,length:bytes.length};mouthOffset+=bytes.length;
  }
  draw.push({name:part.name,file:part.file,rect:part.rect,width:part.image.width, height:part.image.height,opening,warp});
 }
 const positions=rig.frames(current,t,{ambient:natural});
 for(const role of bodyRoles){const v=positions[role];fs.writeSync(meshFD[role],Buffer.from(v.buffer,v.byteOffset,v.byteLength));}
 frames.push({i,t,section,label,reset,requested,expressionFrame,facePose,p:current,voice,voiceStart,ambient:natural,draw,layerFiles:layers.map(l=>bodyTextureFile(l,active,model)),rigPose:rig.pose});
}
for(const fd of Object.values(meshFD))fs.closeSync(fd);fs.closeSync(mouthFD);
fs.writeFileSync(path.join(dir,'frames.json'),JSON.stringify({fps,duration,voiceStarts,voiceDuration,ids,sampling,roles:bodyRoles,layers,frames,reviewFrameIndices:[0,44,60,90,150,210,270,330,360,390,449]}));
fs.writeFileSync(path.join(dir,'mesh-manifest.json'),JSON.stringify({roles:bodyRoles,vertices:(model.mesh[0]+1)*(model.mesh[1]+1),frames:frames.length,files:Object.fromEntries(bodyRoles.map(r=>[r,`mesh-${r}.bin`]))},null,2));
console.log(`Generated ${frames.length} chronological frames with ${bodyRoles.length} independently stored runtime role meshes; no shared full-body warp.`);

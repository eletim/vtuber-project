import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {BodyRig} from './source/runtime/web/body-rig.js';
import {PerformanceMotion} from './source/runtime/web/performance.js';
import {neutral,smoothParameters,rmsMouth} from './source/runtime/web/controls.js';
import {ExpressionTransition,expressionParameters,featureOpening,featureBands,expressionLabels,deformMouthPixels} from './source/runtime/web/expressions.js';
const dir=path.dirname(fileURLToPath(import.meta.url)),runtime=path.join(dir,'source/runtime'),modelDir=path.join(runtime,'model');
const model=JSON.parse(fs.readFileSync(path.join(modelDir,'model.json')));
if(!Array.isArray(model.expressions)||model.expressions.length<8)throw Error('Final eight-expression manifest not ready; refusing to render a partial source.');
const skin=JSON.parse(fs.readFileSync(path.join(modelDir,model.skinning))),audio=JSON.parse(fs.readFileSync(path.join(dir,'audio_samples.json')));
const fps=30,duration=42,ids=['neutral','soft_smile','big_smile','worried','surprised','bashful','displeased','thinking'];
const emotions={neutral:'neutral',soft_smile:'happy',big_smile:'happy',worried:'thoughtful',surprised:'surprised',bashful:'neutral',displeased:'neutral',thinking:'thoughtful'};
const rgbaManifest=JSON.parse(fs.readFileSync(path.join(dir,'rgba-manifest.json'))),rgbaInputs=new Map();
const warpFD=fs.openSync(path.join(dir,'mouth-frames.rgba'),'w');let warpOffset=0;
function mouthInput(file){if(!rgbaInputs.has(file))rgbaInputs.set(file,new Uint8ClampedArray(fs.readFileSync(path.join(dir,'source-rgba',rgbaManifest[file].file))));return rgbaInputs.get(file);}
const sizes=new Map();
function pngSize(file){if(!sizes.has(file)){const b=fs.readFileSync(path.join(modelDir,file));sizes.set(file,{width:b.readUInt32BE(16),height:b.readUInt32BE(20)});}return sizes.get(file);}
const expressions=new Map([['neutral',{id:'neutral',base:model.base,parts:model.parts,defaults:{}}]]);
for(const e of model.expressions)expressions.set(e.id,{...e,base:e.base||model.base,parts:(e.parts||model.parts).map(p=>({...p,image:pngSize(p.file)}))});
for(const id of ids)if(!expressions.has(id))throw Error('Missing '+id);
const motion=new PerformanceMotion(),rig=new BodyRig(model,skin),transition=new ExpressionTransition(),mesh=Buffer.alloc(fps*duration*rig.rest.length*4),frames=[];
let current=neutral();const voiceStarts=[.5,10.5,20.5,30.5],voiceDuration=audio.length/24000;
for(let i=0;i<fps*duration;i++){
 const t=i/fps,slot=Math.min(7,Math.floor(t/5)),requested=t>=40?'neutral':ids[slot],local=t-slot*5;
 const voiceStart=voiceStarts.find(start=>t>=start&&t<start+voiceDuration),voice=voiceStart!==undefined;
 const offset=voice?Math.round((t-voiceStart)*24000):0,samples=voice?audio.slice(Math.max(0,offset-512),Math.min(audio.length,offset+512)):[];
 const base=neutral();base.ParamMouthOpenY=voice?rmsMouth(samples):0;
 const emotion=emotions[requested],emotionStart=t>=40?40:slot*5;
 const performance={enabled:true,emotion,started_at:emotionStart,until:t>=40?0:slot*5+5};
 const p=motion.frame(base,t,performance,base.ParamMouthOpenY);
 const blink=(local>=1.2&&local<1.42)||(local>=3.5&&local<3.72);
 if(blink)p.ParamEyeLOpen=p.ParamEyeROpen=0;
 p.ParamBreath=.5+.5*Math.sin(t/1.7);current=smoothParameters(current,p,1/fps);
 transition.request(requested,t);const expressionFrame=transition.update(t),active=expressions.get(expressionFrame.id),facePose=expressionParameters(current,active,expressionFrame.gate);
 const draw=[];
 for(const part of active.parts){
  const opening=featureOpening(facePose[part.parameter],part.parameter.includes('Mouth'));
  if(part.state!==opening.state)continue;
  let warp=null;
  if(part.parameter==='ParamMouthOpenY'&&part.state==='open'&&opening.scale<.9999){
   const closedPart=active.parts.find(p=>p.parameter==='ParamMouthOpenY'&&p.state==='closed');
   const closed=closedPart?{pixels:mouthInput(closedPart.file),width:closedPart.image.width,height:closedPart.image.height,rect:closedPart.rect}:null;
   const pixels=deformMouthPixels(mouthInput(part.file),part.image.width,part.image.height,part,opening.scale,active.id,closed);
   const data=Buffer.from(pixels.buffer,pixels.byteOffset,pixels.byteLength);fs.writeSync(warpFD,data);warp={offset:warpOffset,length:data.length};warpOffset+=data.length;
  }
  draw.push({name:part.name,file:part.file,rect:part.rect,width:part.image.width,height:part.image.height,opening,warp,bands:warp?null:featureBands(part,opening.scale)});
 }
 const positions=rig.frame(current,t);Buffer.from(positions.buffer).copy(mesh,i*positions.length*4);
 frames.push({i,t,requested,label:expressionLabels[requested],voice,voiceStart,blink,expressionFrame,base:active.base,draw,p:current,facePose});
}
fs.closeSync(warpFD);
fs.writeFileSync(path.join(dir,'frames.json'),JSON.stringify({fps,duration,voiceStarts,voiceDuration,ids,frames}));fs.writeFileSync(path.join(dir,'mesh.bin'),mesh);
console.log(`Prepared ${frames.length} frames using current runtime ExpressionTransition/expressionParameters/featureOpening/deformMouthPixels and stateful PerformanceMotion/BodyRig functions.`);

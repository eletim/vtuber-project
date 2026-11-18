import fs from 'node:fs';
import {BodyRig} from './source/runtime/web/body-rig.js';
import {neutral} from './source/runtime/web/controls.js';
import {expressionParameters,featureOpening,featureBands,deformMouthPixels} from './source/runtime/web/expressions.js';
const dir=new URL('.',import.meta.url), runtime=new URL('source/runtime/',dir), modelDir=new URL('model/',runtime);
const model=JSON.parse(fs.readFileSync(new URL('model.json',modelDir))),skin=JSON.parse(fs.readFileSync(new URL(model.skinning,modelDir)));
const cache=new Map();fs.mkdirSync(new URL('review_textures/',modelDir),{recursive:true});
const expressions=model.expressions.map(e=>({...e,base:e.base||model.base,parts:(e.parts||model.parts).map(p=>{const b=fs.readFileSync(new URL(p.file,modelDir));return {...p,image:{width:b.readUInt32BE(16),height:b.readUInt32BE(20)}}})}));
const tilts=[-8,0,8],amounts=[0,.141,.15,.16,.20,.214,.25,.35,.65,1],frames=[],chunks=[];
for(const active of expressions) for(const tilt of tilts) for(const amount of amounts){
 const p={...neutral(),ParamMouthOpenY:amount,ParamAngleZ:tilt}, facePose=expressionParameters(p,active,1),draw=[];
 for(const part of active.parts){const opening=featureOpening(facePose[part.parameter],part.parameter.includes('Mouth'));if(part.state!==opening.state)continue;let file=part.file,bands=featureBands(part,opening.scale);
 if(part.parameter==='ParamMouthOpenY'&&part.state==='open'&&opening.scale<.9999){
  const key=active.id+'_'+amount.toFixed(3);file='review_textures/'+key+'.png';bands=null;
  if(!cache.has(key)){const shut=active.parts.find(p=>p.parameter==='ParamMouthOpenY'&&p.state==='closed');const raw=fs.readFileSync(new URL(part.file+'.rgba',modelDir)),cr=fs.readFileSync(new URL(shut.file+'.rgba',modelDir));const warped=deformMouthPixels(raw,part.image.width,part.image.height,part,opening.scale,active.id,{pixels:cr,width:shut.image.width,height:shut.image.height,rect:shut.rect});fs.writeFileSync(new URL(file+'.rgba',modelDir),warped);fs.writeFileSync(new URL(file+'.json',modelDir),JSON.stringify(part.image));cache.set(key,true);}
 }
 draw.push({name:part.name,file,rect:part.rect,width:part.image.width,height:part.image.height,opening,bands});}
 const rig=new BodyRig(model,skin),positions=rig.frame(p,0);chunks.push(Buffer.from(positions.buffer));frames.push({i:frames.length,requested:active.id,t:0,tilt,amount,base:active.base,p,facePose,draw});
}
fs.writeFileSync(new URL('grid.json',dir),JSON.stringify({fps:30,duration:frames.length/30,frames}));fs.writeFileSync(new URL('grid-mesh.bin',dir),Buffer.concat(chunks));console.log(`Generated ${frames.length} cases.`);

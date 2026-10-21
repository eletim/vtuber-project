import {bodyRoles} from './body-rig.js';

// Shared by the browser and offline renderer. Array order is the PSD's
// back-to-front occlusion order, not alphabetical role order.
export function bodyLayers(model){
  const layers=model.bodyLayers||[{id:'legacy',role:'torso',file:model.base,rect:[0,0,...model.size],features:true}];
  const ids=new Set();
  for(const layer of layers){
    if(typeof layer.id!=='string'||!layer.id||ids.has(layer.id)||!bodyRoles.includes(layer.role))throw Error(`invalid body layer ${layer.id}`);
    ids.add(layer.id);
    const [x0,y0,x1,y1]=layer.rect||[];
    if(![x0,y0,x1,y1].every(Number.isFinite)||x0<0||y0<0||x1<=x0||y1<=y0||x1>model.size[0]||y1>model.size[1])throw Error(`invalid body rectangle ${layer.id}`);
    if(typeof layer.file!=='string'||!layer.file)throw Error(`missing body texture ${layer.id}`);
    if(layer.articulation&&(!['upper','forearm','hand','cuff','drape'].includes(layer.articulation.joint)||layer.role!=='armLeft'))throw Error(`invalid arm articulation ${layer.id}`);
    if(layer.hairMotion){
      const h=layer.hairMotion;
      if(layer.features||layer.role!=='head'||!(h.tipY>h.rootY)||!(h.amplitude>0&&h.amplitude<=16)||!(h.speed>0))throw Error(`invalid hair strand ${layer.id}`);
    }
  }
  if(layers.filter(layer=>layer.features).length!==1)throw Error('exactly one body layer must own expression features');
  if(model.hairExport?.exclusiveOwnership&&!layers.find(layer=>layer.features).movingHairMask)throw Error('separated hair requires post-expression ownership mask');
  return layers;
}
export function bodyTextureFile(layer,expression,model){
  if(layer.id==='legacy')return expression.base||model.base;
  return layer.expressionFiles?.[expression.id]||layer.file;
}
export function bodyTextureRect(layer,model){
  const [x0,y0,x1,y1]=layer.rect,[w,h]=model.size;
  return [x0/w,y0/h,(x1-x0)/w,(y1-y0)/h];
}

// Adjacent separately cut parts must be sampled at the same subpixel locations
// before source-over. Resolve the assembled premultiplied surface once; filtering
// complementary alpha masks separately would make an opaque seam translucent.
export function bodySamplingPlan(model,width,height,maxSize=Infinity){
  const enabled=model.bodySampling==='coverage-2x';
  if(!enabled)return {enabled:false,width,height,scale:1};
  const scale=Math.min(2,maxSize/width,maxSize/height);
  return {enabled:true,width:Math.max(1,Math.floor(width*scale)),height:Math.max(1,Math.floor(height*scale)),scale};
}

import {clamp} from './controls.js';

export const expressionLabels = {
  neutral:'通常',soft_smile:'微笑み',big_smile:'にっこり',worried:'困り顔',
  surprised:'驚き',bashful:'照れ',displeased:'不満',thinking:'考え顔'
};
const ease = value => {const t=clamp(value);return t*t*(3-2*t);};

// One opaque face is visible at all times. Close the *local* eye/mouth features,
// change the authored drawing at the blink nadir, then reopen. A new request
// during closing replaces the pending target; during opening it smoothly closes
// from its current amount, rather than jumping or queuing stale expressions.
export class ExpressionTransition {
  constructor(id='neutral') {this.active=id;this.requested=id;this.phase='idle';this.gate=1;this.started=0;this.from=1;}
  request(id,time) {
    if(id===this.requested)return;
    this.update(time);
    this.requested=id;
    if(this.phase==='closing')return;
    if(this.phase==='hold'){this.active=id;return;}
    if(this.active===id&&this.phase==='idle')return;
    this.from=this.gate;this.started=time;this.phase='closing';
  }
  update(time) {
    if(this.phase==='closing'){
      const progress=(time-this.started)/.11;
      this.gate=this.from*(1-ease(progress));
      if(progress>=1){this.active=this.requested;this.phase='hold';this.started+=.11;this.gate=0;}
    }
    if(this.phase==='hold'&&time-this.started>=.045){this.phase='opening';this.started+=.045;}
    if(this.phase==='opening'){
      const progress=(time-this.started)/.17;this.gate=ease(progress);
      if(progress>=1){this.gate=1;this.phase='idle';}
    }
    return {id:this.active,requested:this.requested,gate:this.gate,phase:this.phase};
  }
}

// Eyes use the two authored opaque endpoints: their restoration patches include
// hair/brow pixels, so rectangular eye warps are deliberately not attempted.
// Mouth-only interpolation stays inside its clean core; no face opacity blend.
export function featureOpening(value, mouth=false) {
  const amount=clamp(Number.isFinite(value)?value:0);
  const threshold=mouth?.14:.4;
  return {state:amount>threshold?'open':'closed',scale:mouth&&amount>threshold?.06+.94*(amount-threshold)/(1-threshold):1};
}

export function expressionParameters(parameters,expression,gate=1) {
  const defaults=expression?.defaults||{};
  const pose={...parameters};
  // A smile painted with closed eyes stays closed by design; blinking and
  // mouth amplitude remain independent. Partial-eye defaults cap openness.
  for(const key of ['ParamEyeLOpen','ParamEyeROpen'])pose[key]=clamp(pose[key])*(defaults[key]??1)*gate;
  pose.ParamMouthOpenY=Math.max(clamp(pose.ParamMouthOpenY),defaults.ParamMouthOpenY||0)*gate;
  return pose;
}

// Legacy v15 strip metadata, retained for regression compatibility only.
// Production rendering must use deformMouthPixels, never these axis-aligned bands.
export function featureBands(part,scale) {
  const width=part.image.width,height=part.image.height;
  if(!part.motion||scale>=.9999)return null;
  const [x,y]=part.rect,[bx0,by0,bx1,by1]=part.motion.bounds;
  const x0=clamp(bx0-x,0,width),x1=clamp(bx1-x,x0,width);
  const y0=clamp(by0-y,0,height),y1=clamp(by1-y,y0,height);
  const anchor=clamp(part.motion.anchor[1]-y,y0,y1);
  // Invalid edge-touching metadata cannot supply restoration pixels. Keep the
  // opaque endpoint unchanged rather than stretching from an empty source band.
  if(x1<=x0||y1<=y0||y0<=0||y1>=height)return null;
  // Only the mouth reaches this warp. Its exterior stays stationary; zero-
  // source intervals reveal painted clean base instead of stretching skin.
  // At high zoom a slight skin-tone boundary can remain around the mouth core.
  return {x0,x1,source:[0,y0,y0,y1,y1,height],
    destination:[0,y0,anchor+(y0-anchor)*scale,anchor+(y1-anchor)*scale,y1,height]};
}

// Landmarks measured on the authored open-mouth PNGs, in PSD coordinates.
// The tangent follows the lip corners, not the screen's horizontal axis. The
// inner envelope contains all lip/cavity marks; the outer envelope contains
// only restoration skin and fades to an unmoving patch boundary.
const mouthProfiles = {
  neutral:    {corners:[[530,358],[580,350]],core:[32,-8,27],outer:[47,-26,43]},
  soft_smile: {corners:[[529,354],[577,348]],core:[30,-9,25],outer:[40,-24,36]},
  big_smile:  {corners:[[522,350],[585,338]],core:[36,-10,35],outer:[44,-23,43]},
  worried:   {corners:[[536,361],[573,357]],core:[25,-12,16],outer:[38,-26,32]},
  surprised: {corners:[[540,362],[565,357]],core:[20,-17,19],outer:[36,-30,33]},
  bashful:   {corners:[[529,354],[578,346]],core:[31,-9,26],outer:[41,-25,37]},
  displeased:{corners:[[535,367],[571,362]],core:[25,-22,14],outer:[38,-33,29]},
  thinking:  {corners:[[539,357],[565,354]],core:[20,-13,16],outer:[35,-27,31]}
};

// Closed-lip paths were measured independently: the old shared y=356 anchor
// did not describe any curved smile/frown reliably. These are geometry only,
// not replacement painted marks. Their correspondence prevents double lips.
const closedLipPaths = {
  neutral:[[532,363.5],[540,364],[550,363],[560,360.8],[571,357],[579,352.5]],
  soft_smile:[[530,357.5],[538,358],[548,356.8],[557,354.8],[563,353],[571,351.5],[579,349]],
  big_smile:[[523,350.5],[533,351.5],[544,350.5],[554,348.5],[564,345.7],[572,342.5],[582,338]],
  worried:[[538,361.5],[544,358.5],[552,355.5],[561,354],[566,354.5],[572,355.5]],
  surprised:[[541,357.5],[547,355.5],[550,355],[553,355],[559,356]],
  bashful:[[531,358.5],[539,359],[548,357.5],[560,355],[571,352.5],[579,349.5]],
  displeased:[[539,361],[544,357.5],[550,355],[557,354],[562,355.5],[566,356.5]],
  thinking:[[540,358],[544,355.5],[549,353],[555,352],[559,351.5],[563,351.5]]
};

export function mouthGeometry(part,expression='neutral') {
  if(!part.motion)return null;
  const profile=mouthProfiles[expression]||mouthProfiles.neutral;
  const [left,right]=profile.corners,dx=right[0]-left[0],dy=right[1]-left[1],length=Math.hypot(dx,dy);
  const origin=[(left[0]+right[0])/2,(left[1]+right[1])/2];
  const closure=(closedLipPaths[expression]||closedLipPaths.neutral).map(([x,y])=>[
    ((x-origin[0])*dx+(y-origin[1])*dy)/length,
    (-(x-origin[0])*dy+(y-origin[1])*dx)/length]);
  return {origin:[origin[0]-part.rect[0],origin[1]-part.rect[1]],closure,
    tangent:[dx/length,dy/length],normal:[-dy/length,dx/length],
    core:[-profile.core[0],profile.core[1],profile.core[0],profile.core[2]],
    outer:[-profile.outer[0],profile.outer[1],profile.outer[0],profile.outer[2]]};
}

function mouthNormalScale(u,geometry,scale) {
  const inner=geometry.core[2],outer=geometry.outer[2];
  return 1-(1-clamp(scale))*(1-ease((Math.abs(u)-inner)/(outer-inner)));
}

function mouthClosure(u,geometry) {
  const path=geometry.closure;
  let center=path[0][1];
  if(u>=path.at(-1)[0])center=path.at(-1)[1];
  else for(let i=0;i<path.length-1;i++)if(u>=path[i][0]&&u<path[i+1][0]){
    const mix=(u-path[i][0])/(path[i+1][0]-path[i][0]);
    center=path[i][1]*(1-mix)+path[i+1][1]*mix;break;
  }
  center=clamp(center,geometry.core[1]+1,geometry.core[3]-1);
  return center;
}

// Continuous, monotone normal-only map. The lip tangent is invariant, while
// the skin-only bands expand to meet the fixed exterior. There are no detached
// strips, transparent slits, duplicated corner fragments, or foldovers.
export function mouthPoint(geometry,x,y,scale,inverse=false) {
  const {origin,tangent:t,normal:n,core,outer}=geometry;
  const qx=x-origin[0],qy=y-origin[1],u=qx*t[0]+qy*t[1],v=qx*n[0]+qy*n[1];
  const s=Math.max(.001,mouthNormalScale(u,geometry,scale));
  const center=mouthClosure(u,geometry);
  const lower=center+(core[1]-center)*s,upper=center+(core[3]-center)*s;
  let mapped=v,ratio=1;
  const from=inverse?[outer[1],lower,upper,outer[3]]:[outer[1],core[1],core[3],outer[3]];
  const to=inverse?[outer[1],core[1],core[3],outer[3]]:[outer[1],lower,upper,outer[3]];
  for(let i=0;i<3;i++)if(v>=from[i]&&v<=from[i+1]){
    ratio=(to[i+1]-to[i])/(from[i+1]-from[i]);mapped=to[i]+(v-from[i])*ratio;break;
  }
  return {x:origin[0]+u*t[0]+mapped*n[0],y:origin[1]+u*t[1]+mapped*n[1],normalRatio:ratio};
}

// Near closure, use the actual closed lip with the deformed cavity
// collapsed onto that same measured curve, not a detached straight stripe.
// The narrow local morph ends before a visible cavity opens; never fade a face.
export function mouthBlend(scale) {
  return {scale:Math.max(.06,clamp(scale)),openWeight:ease((scale-.06)/.08)};
}

function samplePremultiplied(source,width,height,x,y,result) {
  const ix=Math.floor(x),iy=Math.floor(y),fx=x-ix,fy=y-iy;
  result.fill(0);
  for(let dy=0;dy<2;dy++)for(let dx=0;dx<2;dx++){
    const sx=ix+dx,sy=iy+dy;
    if(sx<0||sy<0||sx>=width||sy>=height)continue;
    const index=(sy*width+sx)*4,w=(dx?fx:1-fx)*(dy?fy:1-fy),a=source[index+3]/255;
    for(let c=0;c<3;c++)result[c]+=source[index+c]*a*w;
    result[3]+=a*w;
  }
}

// Fixed-size per-part cache only: no frame history or opening-value textures.
// Precompute coordinates/curve correspondence to avoid tens of thousands of
// temporary objects per video frame and the resulting garbage-collection stalls.
const mouthPixelMaps=new WeakMap();
function mouthPixelMap(part,width,height,expression,geometry) {
  let maps=mouthPixelMaps.get(part);
  if(!maps){maps=new Map();mouthPixelMaps.set(part,maps);}
  const key=expression+':'+width+':'+height;
  if(maps.has(key))return maps.get(key);
  const coordinates=new Float64Array(width*height*3),{origin,tangent:t,normal:n,core,outer}=geometry;
  for(let y=0;y<height;y++)for(let x=0;x<width;x++){
    const dx=x-origin[0],dy=y-origin[1],u=dx*t[0]+dy*t[1],at=(y*width+x)*3;
    coordinates[at]=dx*n[0]+dy*n[1];
    coordinates[at+1]=mouthClosure(u,geometry);
    coordinates[at+2]=1-ease((Math.abs(u)-core[2])/(outer[2]-core[2]));
  }
  // At most the eight supported expressions for any supplied part object.
  if(maps.size>=8)maps.delete(maps.keys().next().value);
  maps.set(key,coordinates);return coordinates;
}

// Shared with offline video: straight RGBA in/out, identical dimensions/rect.
// closed is optional {pixels,width,height,rect}. Coordinates and blending are
// kept here so the browser and offline renderer cannot diverge again.
export function deformMouthPixels(source,width,height,part,scale,expression='neutral',closed=null) {
  if(scale>=.9999)return new Uint8ClampedArray(source);
  const geometry=mouthGeometry(part,expression);
  if(!geometry)return new Uint8ClampedArray(source);
  const blend=closed?mouthBlend(scale):{scale:clamp(scale,.001,1),openWeight:1};
  const output=new Uint8ClampedArray(source.length),sample=new Float64Array(4),sum=new Float64Array(4),shut=new Float64Array(4);
  const n=geometry.normal,{core,outer}=geometry,coordinates=mouthPixelMap(part,width,height,expression,geometry);
  for(let y=0;y<height;y++)for(let x=0;x<width;x++){
    const pixel=y*width+x,index=pixel*4,v=coordinates[pixel*3],center=coordinates[pixel*3+1];
    const s=Math.max(.001,1-(1-blend.scale)*coordinates[pixel*3+2]);
    const lower=center+(core[1]-center)*s,upper=center+(core[3]-center)*s;
    let mappedV=v,normalRatio=1;
    if(v>=outer[1]&&v<=outer[3]){
      if(v<lower){normalRatio=(core[1]-outer[1])/(lower-outer[1]);mappedV=outer[1]+(v-outer[1])*normalRatio;}
      else if(v<=upper){normalRatio=1/s;mappedV=center+(v-center)*normalRatio;}
      else{normalRatio=(outer[3]-core[3])/(outer[3]-upper);mappedV=core[3]+(v-upper)*normalRatio;}
    }
    const mx=x+(mappedV-v)*n[0],my=y+(mappedV-v)*n[1];
    sum.fill(0);
    if(Math.abs(mx-x)<1e-8&&Math.abs(my-y)<1e-8&&Math.abs(normalRatio-1)<1e-8){
      const a=source[index+3]/255;sum[3]=a;
      for(let c=0;c<3;c++)sum[c]=source[index+c]*a;
    }else{
      // Area sampling along the minified normal, rather than one bilinear
      // point: dark corners and bright teeth cannot flicker between scanlines.
      const footprint=Math.max(1,normalRatio),samples=Math.min(32,Math.ceil(footprint));
      for(let k=0;k<samples;k++){
        const offset=((k+.5)/samples-.5)*Math.max(0,footprint-1);
        samplePremultiplied(source,width,height,mx+n[0]*offset,my+n[1]*offset,sample);
        for(let c=0;c<4;c++)sum[c]+=sample[c]/samples;
      }
    }
    if(closed&&blend.openWeight<1){
      samplePremultiplied(closed.pixels,closed.width,closed.height,x+part.rect[0]-closed.rect[0],y+part.rect[1]-closed.rect[1],shut);
      for(let c=0;c<4;c++)sum[c]=shut[c]*(1-blend.openWeight)+sum[c]*blend.openWeight;
    }
    const alpha=sum[3];output[index+3]=Math.round(alpha*255);
    if(alpha>0)for(let c=0;c<3;c++)output[index+c]=Math.round(sum[c]/alpha);
  }
  return output;
}

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

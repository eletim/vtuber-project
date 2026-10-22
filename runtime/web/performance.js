import {clamp} from './controls.js';
export const emotions=['neutral','happy','thoughtful','surprised'];
const ease=x=>{const u=clamp(x);return u*u*(3-2*u);};
const add=(pose,key,amount,lo=-1,hi=1)=>{
  const base=Number.isFinite(pose[key])?pose[key]:0;
  // An explicit full-range limb/posture command keeps authority. Automatic
  // accents use only its remaining headroom instead of fighting the operator.
  const room=lo===-1&&hi===1?1-clamp(Math.abs(base)):1;
  pose[key]=clamp(base+amount*room,lo,hi);
};
// Small additive movements preserve externally commanded poses and the existing drawing.
export function performancePose(base,time,performance={enabled:true},mouth=0){
  const pose={...base};
  if(!performance.enabled)return pose;
  const t=time,age=t-(performance.started_at||0);
  const emotion=(!performance.until||t<performance.until)?performance.emotion:'neutral';
  const speaking=clamp(mouth),pulse=Math.sin(t*4.1)*Math.sin(t*1.37);
  let x=1.7*Math.sin(t*.63)+.55*Math.sin(t*1.19),y=.65*Math.sin(t*.89),z=.85*Math.sin(t*.49),body=.5*Math.sin(t*.53);
  y+=speaking*1.6*pulse;z+=speaking*.7*Math.sin(t*1.8);
  const onset=Math.min(1,Math.max(0,age)*2.5),fade=performance.until?clamp((performance.until-t)*2):1;
  const weight=onset*fade;
  if(emotion==='happy'){
    z+=weight*1.8*Math.sin(age*1.7);body+=weight*2.1*Math.sin(age*1.7);
    add(pose,'ParamBodyShiftX',weight*.78*Math.sin(age*1.7));
    // Two anticipatory dips and hops, then a quiet pause. No perpetual jumping.
    const beat=Math.max(0,age)%5.6;
    const hop=a=>a<0||a>1.1?0:a<.3?-.5*Math.sin(Math.PI*a/.3):Math.sin(Math.PI*(a-.3)/.8);
    add(pose,'ParamBodyBounce',weight*(hop(beat)+.8*hop(beat-1.35)));
    add(pose,'ParamArmLOpen',weight*.35*(hop(beat)+.8*hop(beat-1.35)));
    add(pose,'ParamArmROpen',weight*.35*(hop(beat)+.8*hop(beat-1.35)));
  }
  if(emotion==='thoughtful'){z+=weight*3.1;x-=weight*2.2;y-=weight*.9;}
  if(emotion==='thoughtful'){
    const gesture=ease(age/1.1)*(1-ease((age-3.1)/1.5));
    pose.ParamHandToCheek=clamp((pose.ParamHandToCheek||0)+gesture*(1-(pose.ParamHandToCheek||0)));
  }
  if(emotion==='surprised'){y-=weight*1.5*Math.exp(-Math.max(0,age)*.9);z-=weight*1.1;}
  pose.ParamAngleX=clamp(pose.ParamAngleX+x,-15,15);
  pose.ParamAngleY=clamp(pose.ParamAngleY+y,-10,10);
  pose.ParamAngleZ=clamp(pose.ParamAngleZ+z,-8,8);
  pose.ParamBodyAngleX=clamp(pose.ParamBodyAngleX+body,-5,5);
  // A happy eye-close uses the existing authored closed-eye parts.
  if(emotion==='happy'&&age>=0&&age%3.6>3.18){pose.ParamEyeLOpen*=1-.95*weight;pose.ParamEyeROpen*=1-.95*weight;}
  return pose;
}

// One instance per avatar/session. Speech has an envelope and phrase cadence,
// not an arm sine-wave or a new movement for every syllable. The pure helper
// above remains available for existing callers that only need head motion.
export class PerformanceMotion {
  constructor(){this.reset();}
  reset(){
    this.lastTime=null;this.energy=0;this.lastVoice=-Infinity;this.speechStarted=null;
    this.nextGesture=0;this.sequence=0;this.gesture=null;this.epoch=null;
    this.pose={energy:0,speaking:false,accent:0,side:0,gestures:0};
  }
  frame(base,time,performance={enabled:true},mouth=0){
    const pose=performancePose(base,time,performance,mouth);
    if(!performance.enabled){this.reset();return pose;}
    const gap=this.lastTime===null?0:time-this.lastTime;
    // Background tabs, seeks and clock changes must not replay a stale gesture.
    if(gap<0||gap>.25)this.reset();
    const dt=this.lastTime===null?0:Math.min(.1,Math.max(0,time-this.lastTime));
    this.lastTime=time;
    const epoch=performance.started_at||0;
    if(this.epoch!==null&&Math.abs(epoch-this.epoch)>.1){
      if(this.gesture&&this.gesture.stop===null)this.gesture.stop=time;
      this.energy=0;this.lastVoice=-Infinity;this.speechStarted=null;this.nextGesture=time+.35;
    }
    this.epoch=epoch;
    const voice=Number.isFinite(mouth)?clamp(mouth):0;
    if(voice>.1){
      if(time-this.lastVoice>=.24)this.speechStarted=time;
      this.lastVoice=time;
    }
    this.energy+=(voice-this.energy)*(1-Math.exp(-dt/(voice>this.energy ? .09 : .2)));
    const speaking=time-this.lastVoice<.24;
    if(!speaking&&this.gesture&&this.gesture.stop===null)this.gesture.stop=time;
    const emotion=(!performance.until||time<performance.until)?performance.emotion:'neutral';
    if(speaking&&time-this.speechStarted>=.1&&this.energy>.12&&time>=this.nextGesture){
      const index=this.sequence++,side=index%2;
      this.gesture={start:time,stop:null,side,amplitude:(.64+.28*this.energy)*(emotion==='happy'?1.06:emotion==='thoughtful'?.78:1)};
      // Space accents across a sentence. An uninterrupted monologue gets at
      // most one gentle gesture every 2.8–3.6 seconds, alternating the lead arm.
      this.nextGesture=time+[2.8,3.4,3.05,3.6][index%4];
    }
    let accent=0,side=0;
    if(this.gesture){
      const gesture=this.gesture,age=time-gesture.start;
      const settle=gesture.stop===null?1:1-ease((time-gesture.stop)/.38);
      accent=gesture.amplitude*ease(age/.28)*(1-ease((age-.55)/.88))*settle;
      side=gesture.side;
      if(age>=1.43||settle<=0)this.gesture=null;
    }
    // Quiet weight shifts are deliberately much smaller than speaking accents.
    const idle=.08*Math.sin(time*.31)+.03*Math.sin(time*.17);
    add(pose,'ParamBodyShiftX',idle+(side===0?-.35:.35)*accent);
    add(pose,'ParamArmLOpen',accent*(side===0?1:.24));
    add(pose,'ParamArmROpen',accent*(side===1?1:.24));
    add(pose,'ParamShoulderY',.75*accent);
    add(pose,'ParamBodyAngleX',(side===0?-.62:.62)*accent,-5,5);
    this.pose={energy:this.energy,speaking,accent,side,gestures:this.sequence};
    return pose;
  }
}

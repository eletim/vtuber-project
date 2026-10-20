import {clamp} from './controls.js';
export const emotions=['neutral','happy','thoughtful','surprised'];
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
  if(emotion==='happy'){z+=weight*1.8*Math.sin(t*1.7);body+=weight*.6*Math.sin(t*1.7);y+=weight*.8*Math.sin(t*3.4);}
  if(emotion==='thoughtful'){z+=weight*3.1;x-=weight*2.2;y-=weight*.9;}
  if(emotion==='surprised'){y-=weight*1.5*Math.exp(-Math.max(0,age)*.9);z-=weight*1.1;}
  pose.ParamAngleX=clamp(pose.ParamAngleX+x,-15,15);
  pose.ParamAngleY=clamp(pose.ParamAngleY+y,-10,10);
  pose.ParamAngleZ=clamp(pose.ParamAngleZ+z,-8,8);
  pose.ParamBodyAngleX=clamp(pose.ParamBodyAngleX+body,-5,5);
  // A happy eye-close uses the existing authored closed-eye parts.
  if(emotion==='happy'&&age>=0&&age%3.6>3.18){pose.ParamEyeLOpen*=1-.95*weight;pose.ParamEyeROpen*=1-.95*weight;}
  return pose;
}

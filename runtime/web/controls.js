export const limits = {
  ParamAngleX: [-15,15,0], ParamAngleY: [-10,10,0], ParamAngleZ: [-8,8,0],
  ParamBodyAngleX: [-5,5,0], ParamEyeLOpen: [0,1,1], ParamEyeROpen: [0,1,1],
  ParamMouthOpenY: [0,1,0], ParamBreath: [0,1,.5]
};
export const neutral = () => Object.fromEntries(Object.entries(limits).map(([k,v])=>[k,v[2]]));
export const clamp = (x,lo=0,hi=1) => Math.min(hi, Math.max(lo,x));
export function faceParameters(result) {
  const b = Object.fromEntries((result.faceBlendshapes?.[0]?.categories || []).map(v=>[v.categoryName,v.score]));
  const l = result.faceLandmarks?.[0];
  if (!l?.[263] || !l?.[1] || !l?.[33]) return null;
  const left=l[33], right=l[263], nose=l[1];
  const width=Math.hypot(right.x-left.x,right.y-left.y);
  if(width<.03) return null;
  return {
    ParamEyeLOpen: clamp(1-(b.eyeBlinkLeft||0)*1.4),
    ParamEyeROpen: clamp(1-(b.eyeBlinkRight||0)*1.4),
    ParamMouthOpenY: clamp((b.jawOpen||0)*2.2),
    ParamAngleX: clamp((nose.x-(left.x+right.x)/2)/width*65,-15,15),
    ParamAngleY: clamp((nose.y-(left.y+right.y)/2)/width*50-16,-10,10),
    ParamAngleZ: clamp(-Math.atan2(right.y-left.y,right.x-left.x)*180/Math.PI,-8,8)
  };
}
export function rmsMouth(samples, noise=.012) {
  let energy=0;
  for(const value of samples) energy+=value*value;
  return clamp((Math.sqrt(energy/Math.max(samples.length,1))-noise)*9);
}
export function smoothParameters(current,target,dt) {
  const result={...current};
  for(const [key,[lo,hi,def]] of Object.entries(limits)) {
    const value=Number.isFinite(target[key])?clamp(target[key],lo,hi):def;
    const speed=key.includes('Eye')?35:key.includes('Mouth')?22:12;
    result[key]+=(value-result[key])*(1-Math.exp(-speed*dt));
  }
  return result;
}

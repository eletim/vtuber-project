import {neutral} from './controls.js';
const ease=x=>{x=Math.max(0,Math.min(1,x));return x*x*(3-2*x)};
const rise=(t,a,b)=>ease((t-a)/(b-a));
// An acting phrase, separate from the stop-and-settle diagnostic. All facial
// responses use accepted authored expressions and blink sprites.
export function performanceSequence(time,variant='original'){
 if(['curious','joyful','thinking','surprised'].includes(variant))return gestureSequence(time,variant);
 const t=Math.max(0,time),p=neutral();
 p.ParamBodyShiftX=-1*rise(t,1,2)+2*rise(t,2.65,3.55)-1*rise(t,4.7,5.8);
 p.ParamBodyAngleX=p.ParamBodyShiftX*2.7;
 p.ParamAngleX=-14*rise(t,.65,1.35)+28*rise(t,2.3,3.0)-14*rise(t,4.7,5.6)-1.4*rise(t,8.3,9.1)+1.4*rise(t,14.6,16.4);
 p.ParamAngleZ=-6*rise(t,.65,1.35)+12*rise(t,2.3,3.0)-6*rise(t,4.7,5.6);
 p.ParamAngleY=-6*rise(t,5,5.7)+11*rise(t,7,7.8)-5*rise(t,9,10);
 p.ParamHandToCheek=.965*rise(t,8.8,11.5)*(1-rise(t,13,15.8));
 // Residual loading settles during lowering instead of waiting for it to end.
 p.ParamBodyShiftX+=.16*rise(t,12.4,13.5)*(1-rise(t,15,17.5));
 for(const blink of [1.2,5.4,10.95,15.5]){const pulse=rise(t,blink,blink+.08)*(1-rise(t,blink+.13,blink+.25));p.ParamEyeLOpen*=1-pulse;p.ParamEyeROpen*=1-pulse}
 const happy=t>=5.5&&t<9.4;
 return {parameters:p,performance:{enabled:happy,emotion:'happy',started_at:5.5,until:9.4},expression:t>=5.5&&t<14.5?'soft_smile':'neutral'};
}

// Explicit variants share the existing 18.5s server epoch and smooth release.
function gestureSequence(time,variant){
 const t=Math.max(0,time),p=neutral(),pulse=(a,b,c,d)=>rise(t,a,b)*(1-rise(t,c,d));
 if(variant==='curious'||variant==='thinking'){
  p.ParamAngleZ=-6*pulse(.4,1.7,5.8,7.2)+4*pulse(7.4,8.8,13.5,15.6);
  p.ParamBodyShiftX=-.45*pulse(.8,2.3,6,8)+.28*pulse(8,10,14,16.8);
  p.ParamHandToCheek=.9*pulse(2.5,5.6,10.4,14.4);
  p.ParamBodyBounce=-.22*pulse(1.5,2.2,2.5,3.3)+.34*pulse(3,3.65,4,5.1);
  if(variant==='thinking'){
   p.ParamEyeBallX=-.62*pulse(.3,1.2,12.5,15.5);
   p.ParamEyeBallY=.2*pulse(.5,1.5,12,15.5);
  }
 }else if(variant==='surprised'){
  p.ParamBodyShiftX=-.42*pulse(.5,.95,2,4.4);
  p.ParamBodyBounce=-.3*pulse(.4,.85,1.6,3.7);
  p.ParamAngleZ=-3.2*pulse(.55,1.1,2.1,4.7);
  p.ParamShoulderY=.22*pulse(.45,.9,1.7,3.2);
 }else{
  p.ParamAngleZ=5.5*pulse(.5,1.5,3.7,5.2)-5*pulse(5.6,7.1,11.8,14.8);
  p.ParamBodyShiftX=.7*pulse(.7,2.2,4,5.6)-.55*pulse(5.9,7.4,11.8,14.8);
  p.ParamBodyBounce=-.35*pulse(1.1,1.7,1.9,2.25)+.9*pulse(2,2.55,2.8,3.35)+.7*pulse(3.35,3.8,4.05,4.65);
  p.ParamHandToCheek=.87*pulse(6.4,9.1,11.6,15.2);
 }
 p.ParamBodyAngleX=p.ParamBodyShiftX*2.4;
 for(const b of (variant==='surprised'?[3.5,8.2,15.8]:[1.7,5.1,10.6,15.8])){const v=pulse(b,b+.08,b+.14,b+.26);p.ParamEyeLOpen*=1-v;p.ParamEyeROpen*=1-v;}
 return {parameters:p,performance:{enabled:false,emotion:'neutral',started_at:0,until:0},expression:variant==='surprised'?(t>.4&&t<3.2?'surprised':t>=3.2&&t<5?'soft_smile':'neutral'):t>(variant==='curious'?2:.7)&&t<14?(['curious','thinking'].includes(variant)?'thinking':t>2.2&&t<4.7?'big_smile':'soft_smile'):'neutral'};
}

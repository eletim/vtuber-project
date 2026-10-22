import {pelvisPoint} from './body-rig.js';
const clamp=(x,a=0,b=1)=>Math.min(b,Math.max(a,x));
const smooth=(a,b,x)=>{const t=clamp((x-a)/(b-a));return t*t*(3-2*t);};
const rotate=(point,pivot,angle)=>{const c=Math.cos(angle),s=Math.sin(angle),x=point[0]-pivot[0],y=point[1]-pivot[1];return[pivot[0]+c*x-s*y,pivot[1]+s*x+c*y];};

// Bone lengths stay rigid; local wrist/cloth shaping never touches torso vertices.
// The painted raised bind pose follows the elbow/wrist hierarchy.
export class ArticulatedArm {
 constructor(model,rest){this.model=model;this.rest=rest;this.amount=0;this.velocity=0;this.last=null;this.geometry=new Map();this.cloth=0;this.clothVelocity=0;}
 frame(parameters,time,bodyPose,options={}){
  const config=this.model.articulatedArm;if(!config)return;
  const target=clamp(Number(parameters[config.parameter])||0),dt=this.last===null?0:clamp(time-this.last,0,.1);this.last=time;
  if(options.snapArticulation){this.amount=target;this.velocity=0;}
  else {const speed=7,offset=this.amount-target,c=this.velocity+speed*offset,e=Math.exp(-speed*dt);this.amount=target+(offset+c*dt)*e;this.velocity=(this.velocity-speed*c*dt)*e;}
  const clothTarget=this.amount;
  if(options.snapArticulation){this.cloth=clothTarget;this.clothVelocity=0;}
  else{const speed=9,offset=this.cloth-clothTarget,c=this.clothVelocity+speed*offset,e=Math.exp(-speed*dt);this.cloth=clothTarget+(offset+c*dt)*e;this.clothVelocity=(this.clothVelocity-speed*c*dt)*e;}
  const t=clamp(this.amount),[width,height]=this.model.size,S=config.shoulder,E=config.elbow,WR=config.wristRest,WU=config.wristRaised;
  const a0=Math.atan2(WR[1]-E[1],WR[0]-E[0]),a1=Math.atan2(WU[1]-E[1],WU[0]-E[0]),flex=(a1-a0)*(config.forwardPosePaint?(.55*Math.sin(Math.PI*smooth(0,1,t)/2)+.45*(t+.18*Math.sin(Math.PI*t))):t);
  const length=Math.hypot(WU[0]-E[0],WU[1]-E[1]);
  // Lowering relaxes into a slightly deeper route, continuously from velocity.
  const returning=Math.tanh(Math.max(0,-this.velocity)*2)*Math.sin(Math.PI*t)**2;
  const depthAngle=(1.095+.09*returning)*Math.sin(Math.PI*t)*(1+.3*Math.cos(Math.PI*t)**2),projection=Math.cos(depthAngle);
  const lift=Math.sin(Math.PI*t),projectedElbow=[E[0]+12*lift,E[1]-14*lift];
  const direction=[Math.cos(a0+flex),Math.sin(a0+flex)],normal=[-direction[1],direction[0]],bindDirection=[Math.cos(a1),Math.sin(a1)],bindNormal=[-bindDirection[1],bindDirection[0]];
  const W=[projectedElbow[0]+direction[0]*length*projection,projectedElbow[1]+direction[1]*length*projection];
  const upperLength=Math.hypot(E[0]-S[0],E[1]-S[1]),upperProjected=Math.hypot(projectedElbow[0]-S[0],projectedElbow[1]-S[1]);
  const upperBind=[(E[0]-S[0])/upperLength,(E[1]-S[1])/upperLength],upperAxis=[(projectedElbow[0]-S[0])/upperProjected,(projectedElbow[1]-S[1])/upperProjected];
  const projectUpper=q=>{const x=q[0]-S[0],y=q[1]-S[1],u=x*upperBind[0]+y*upperBind[1],v=-x*upperBind[1]+y*upperBind[0];return[S[0]+u*upperProjected/upperLength*upperAxis[0]-v*upperAxis[1],S[1]+u*upperProjected/upperLength*upperAxis[1]+v*upperAxis[0]];};
  // Integrate the projection scale along the palm: its derivative never exceeds
  // the original length, unlike multiplying position by a varying scale.
  const projectLength=u=>{const d=u-length,z=clamp((d-20)/55),integral=d<=20?0:d>=75?d-47.5:55*(z**3-.5*z**4);const handZ=clamp(d/20),handIntegral=d<=0?0:d>=20?d-10:20*(handZ**3-.5*handZ**4);return u*projection+(1-projection)*(config.forwardPosePaint?handIntegral:.9*integral);};
  const projectForearm=q=>{const x=q[0]-E[0],y=q[1]-E[1],u=x*bindDirection[0]+y*bindDirection[1],v=x*bindNormal[0]+y*bindNormal[1],along=projectLength(u);return[projectedElbow[0]+along*direction[0]+v*normal[0],projectedElbow[1]+along*direction[1]+v*normal[1]];};
  const projectHand=q=>projectForearm(q);
  const wristRoll=(config.forwardPosePaint?(-60*smooth(.35,1,t)-30*(1-smooth(0,.35,t))-22*Math.sin(Math.PI*t)**2+7*returning):26*Math.sin(Math.PI*t)**2)*Math.PI/180;
  // Correct the authored bent wrist over the palm-base transition, not a hinge.
  // The hand and the terminal forearm share exactly the same transform.
  const wristShape=point=>{
   const dir=[Math.cos(a1),Math.sin(a1)],along=(point[0]-WU[0])*dir[0]+(point[1]-WU[1])*dir[1];
   if(config.forwardPosePaint&&Math.abs(wristRoll)>1e-8){
    // A curved wrist centreline carries a rigid palm. Width follows its normal;
    // no position-dependent rotation stretches fingers or folds the wrist mesh.
    const v=-(point[0]-WU[0])*dir[1]+(point[1]-WU[1])*dir[0],span=160;
    let cx,cy,theta;
    if(along>=0){theta=wristRoll;cx=along*Math.cos(theta);cy=along*Math.sin(theta);}
    else if(along>=-span){theta=wristRoll*(along+span)/span;cx=span/wristRoll*(Math.sin(theta)-Math.sin(wristRoll));cy=span/wristRoll*(Math.cos(wristRoll)-Math.cos(theta));}
    else{theta=0;const fade=smooth(-length,-span,along);cx=along+fade*(span-span/wristRoll*Math.sin(wristRoll));cy=fade*span/wristRoll*(Math.cos(wristRoll)-1);}
    const u=cx-v*Math.sin(theta),n=cy+v*Math.cos(theta);
    return[WU[0]+u*dir[0]-n*dir[1],WU[1]+u*dir[1]+n*dir[0]];
   }
   return rotate(point,WU,wristRoll*smooth(-15,45,along));
  };
  const upperAngle=(bodyPose?.arms?.[0]||0)*Math.PI/180;
  const bodyAngle=(bodyPose?.body||0)*Math.PI/180,waist=this.model.bodyRig.waist;
  const parent=point=>{let q=rotate(point,S,upperAngle);q=rotate(q,waist,bodyAngle);return pelvisPoint(q[0],q[1]-(bodyPose?.shoulder||0)-(Number(parameters.ParamBreath??.5)-.5)*.7,bodyPose||{});};
  const blend=1;this.joints={shoulder:parent(S),elbow:parent(projectedElbow),wrist:parent(W),amount:t,returning,blend,flex,wristRoll,forearmDepth:length*Math.sin(depthAngle),projection,upperDepth:Math.sqrt(Math.max(0,upperLength**2-upperProjected**2))};
  for(const layer of this.model.bodyLayers){
   const a=layer.articulation;if(!a)continue;
   let positions=this.geometry.get(layer.id);if(!positions){positions=new Float32Array(this.rest.length);this.geometry.set(layer.id,positions);}
   for(let i=0;i<this.rest.length;i+=2){
    let q=[this.rest[i]*width,this.rest[i+1]*height];
    if(a.sourceElbow&&a.sourceWrist){
     const se=a.sourceElbow,sw=a.sourceWrist,sl=Math.hypot(sw[0]-se[0],sw[1]-se[1]),sd=[(sw[0]-se[0])/sl,(sw[1]-se[1])/sl],dx=q[0]-sw[0],dy=q[1]-sw[1],u=dx*sd[0]+dy*sd[1],v=-dx*sd[1]+dy*sd[0],along=a.joint==='cuff'?(-90-155*smooth(0,.4,t))+(u+70):u<0?u*length/sl:u*(config.extendedHandPose?.88:1);
     q=[WU[0]+along*bindDirection[0]+v*(config.extendedHandPose?1-.06*smooth(-25,10,u):1)*bindNormal[0],WU[1]+along*bindDirection[1]+v*(config.extendedHandPose?1-.06*smooth(-25,10,u):1)*bindNormal[1]];
    }
    if(a.joint==='forearm'||a.joint==='cuff'){
     if(a.joint==='cuff'){
      // Cloth bows at mid-flexion; pinned seam strips and rigid skin stay intact.
      const u=clamp((q[1]-565)/156),bell=Math.sin(Math.PI*u)**2;
      q=[q[0]-12*Math.sin(Math.PI*t)**2*bell,q[1]+5*Math.sin(Math.PI*t)**2*bell];
     }
     if(a.joint==='cuff'&&config.forwardPosePaint&&a.sourceWrist){
      const sl=Math.hypot(a.sourceWrist[0]-a.sourceElbow[0],a.sourceWrist[1]-a.sourceElbow[1]),u=-90-155*smooth(0,.4,t),center=[WU[0]+u*bindDirection[0],WU[1]+u*bindDirection[1]],mapped=wristShape(center),theta=wristRoll*clamp((u+160)/160);
      q=rotate(q,center,theta);q=[q[0]+mapped[0]-center[0],q[1]+mapped[1]-center[1]];q=projectForearm(q);
     }else q=projectForearm(a.poseWeight==='rest-cuff'?q:wristShape(q));
    }
    else if(a.joint==='hand')q=projectHand(wristShape(q));
    else if(a.joint==='upper')q=projectUpper(q);
    else if(a.joint==='drape'){
     // Cloth has its own cage: the upper attachment stays at the upper sleeve,
     // while the lower ruffles hang down. The skin/hand never use this map.
     const original=q,v=smooth(650,960,q[1]),drop=(1-clamp(this.cloth));
     const upper=projectUpper(q),hanging=[upper[0]-drop*133*v,upper[1]+drop*245*v];
     const cuffWeight=smooth(350,445,q[0])*(1-smooth(650,830,q[1]));
     const cuff=projectForearm(original);
     q=[hanging[0]*(1-cuffWeight)+cuff[0]*cuffWeight,hanging[1]*(1-cuffWeight)+cuff[1]*cuffWeight];
     // Opaque inner ruffle folds into the drape below the shoulder attachment.
     const innerFold=smooth(400,560,q[0])*smooth(600,680,q[1])*(1-smooth(850,1000,q[1]))*Math.sin(Math.PI*t)**2;
     q=[q[0]-75*innerFold,q[1]];
    }
    q=parent(q);positions[i]=q[0]/width;positions[i+1]=q[1]/height;
   }
  }
 }
 // One opaque cuff remains behind the drape. The archived down-facing paint
 // is retained in the PSD/model but never cross-faded through the clothing.
 opacity(layer){const pose=layer.articulation?.poseWeight;if(pose)return pose==='forward-cuff'?1:0;return layer.articulation?(layer.articulation.variant==='raised'?this.joints?.blend||0:1-(this.joints?.blend||0)):1;}
}

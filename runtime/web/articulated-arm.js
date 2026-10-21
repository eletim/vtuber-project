const clamp=(x,a=0,b=1)=>Math.min(b,Math.max(a,x));
const smooth=(a,b,x)=>{const t=clamp((x-a)/(b-a));return t*t*(3-2*t);};
const rotate=(point,pivot,angle)=>{const c=Math.cos(angle),s=Math.sin(angle),x=point[0]-pivot[0],y=point[1]-pivot[1];return[pivot[0]+c*x-s*y,pivot[1]+s*x+c*y];};

// Each limb is a rigid surface. Joint transforms never touch torso vertices.
// The painted raised bind pose follows the elbow/wrist hierarchy.
export class ArticulatedArm {
 constructor(model,rest){this.model=model;this.rest=rest;this.amount=0;this.velocity=0;this.last=null;this.geometry=new Map();}
 frame(parameters,time,bodyPose,options={}){
  const config=this.model.articulatedArm;if(!config)return;
  const target=clamp(Number(parameters[config.parameter])||0),dt=this.last===null?0:clamp(time-this.last,0,.1);this.last=time;
  if(options.snapArticulation){this.amount=target;this.velocity=0;}
  else {const speed=7,offset=this.amount-target,c=this.velocity+speed*offset,e=Math.exp(-speed*dt);this.amount=target+(offset+c*dt)*e;this.velocity=(this.velocity-speed*c*dt)*e;}
  const t=clamp(this.amount),[width,height]=this.model.size,S=config.shoulder,E=config.elbow,WR=config.wristRest,WU=config.wristRaised;
  const a0=Math.atan2(WR[1]-E[1],WR[0]-E[0]),a1=Math.atan2(WU[1]-E[1],WU[0]-E[0]),flex=(a1-a0)*t;
  const length=Math.hypot(WU[0]-E[0],WU[1]-E[1]);
  const W=[E[0]+Math.cos(a0+flex)*length,E[1]+Math.sin(a0+flex)*length];
  const upperAngle=(bodyPose?.arms?.[0]||0)*Math.PI/180;
  const bodyAngle=(bodyPose?.body||0)*Math.PI/180,waist=this.model.bodyRig.waist;
  const parent=point=>{let q=rotate(point,S,upperAngle);q=rotate(q,waist,bodyAngle);return[q[0]+(bodyPose?.shift||0),q[1]-(bodyPose?.shoulder||0)-(Number(parameters.ParamBreath??.5)-.5)*.7];};
  const blend=1;this.joints={shoulder:parent(S),elbow:parent(E),wrist:parent(W),amount:t,blend,flex};
  for(const layer of this.model.bodyLayers){
   const a=layer.articulation;if(!a)continue;
   let positions=this.geometry.get(layer.id);if(!positions){positions=new Float32Array(this.rest.length);this.geometry.set(layer.id,positions);}
   const raised=a.bind==='raised',bindW=raised?WU:WR,bindAngle=raised?a1:a0;
   for(let i=0;i<this.rest.length;i+=2){
    let q=[this.rest[i]*width,this.rest[i+1]*height];
    if(a.joint==='forearm'||a.joint==='cuff')q=rotate(q,E,a0+flex-bindAngle);
    else if(a.joint==='hand') {q=rotate(q,bindW,a0+flex-bindAngle);q=[q[0]+W[0]-bindW[0],q[1]+W[1]-bindW[1]];}
    else if(a.joint==='drape'){
     // Cloth has its own cage: the upper attachment stays at the upper sleeve,
     // while the lower ruffles hang down. The skin/hand never use this map.
     const original=q,v=smooth(650,960,q[1]),drop=(1-t);
     const hanging=[q[0]-drop*133*v,q[1]+drop*245*v];
     const cuffWeight=smooth(350,445,q[0])*(1-smooth(650,830,q[1]));
     const cuff=rotate(original,E,a0+flex-a1);
     q=[hanging[0]*(1-cuffWeight)+cuff[0]*cuffWeight,hanging[1]*(1-cuffWeight)+cuff[1]*cuffWeight];
    }
    q=parent(q);positions[i]=q[0]/width;positions[i+1]=q[1]/height;
   }
  }
 }
 opacity(layer){return layer.articulation?(layer.articulation.variant==='raised'?this.joints?.blend||0:1-(this.joints?.blend||0)):1;}
}

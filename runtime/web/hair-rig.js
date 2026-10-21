const clamp=(x,a=0,b=1)=>Math.max(a,Math.min(b,x));
const smooth=x=>{const t=clamp(x);return t*t*(3-2*t);};
export class HairRig {
 constructor(model,rest){this.model=model;this.rest=rest;this.geometry=new Map();this.states=new Map();this.last=null;this.first=null;}
 frame(p,time,head,bodyPose,options={}){
  if(this.first===null)this.first=time;const elapsed=time-this.first,dt=this.last===null?0:clamp(time-this.last,0,.1);this.last=time;
  const [w,h]=this.model.size;
  for(const layer of this.model.bodyLayers){const config=layer.hairMotion;if(!config)continue;
   let state=this.states.get(layer.id);if(!state){state={x:0,v:0};this.states.set(layer.id,state);}
   const drive=options.ambient===false?0:config.amplitude*(1-Math.exp(-Math.max(0,elapsed)*3))*(.75*Math.sin(elapsed*1.45+config.phase)+.25*Math.sin(elapsed*2.15+config.phase*1.3));
   const target=drive+(bodyPose?.body||0)*config.amplitude*.11+(Number(p.ParamAngleX)||0)*.075;
   const speed=config.speed,off=state.x-target,c=state.v+speed*off,e=Math.exp(-speed*dt);
   state.x=target+(off+c*dt)*e;state.v=(state.v-speed*c*dt)*e;
   let points=this.geometry.get(layer.id);if(!points){points=new Float32Array(head.length);this.geometry.set(layer.id,points);}
   for(let i=0;i<head.length;i+=2){const y=this.rest[i+1]*h,u=smooth((y-config.rootY)/(config.tipY-config.rootY));
    const delay=options.ambient===false?0:Math.sin(elapsed*1.45-u*.7+config.phase)-Math.sin(elapsed*1.45+config.phase);
    const dx=(state.x+config.amplitude*.18*delay)*u;
    points[i]=head[i]+dx/w;points[i+1]=head[i+1]+Math.abs(dx)*.045*u/h;
   }
  }
 }
}

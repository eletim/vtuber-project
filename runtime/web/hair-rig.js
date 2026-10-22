const clamp=(x,a=0,b=1)=>Math.max(a,Math.min(b,x));
const smooth=x=>{const t=clamp(x);return t*t*(3-2*t);};
function spring(state,key,target,omega,damping,dt){
 const velocity=key+'V',steps=Math.max(1,Math.ceil(dt*120)),h=dt/steps;
 for(let i=0;i<steps;i++){state[velocity]+=(omega*omega*(target-state[key])-2*damping*omega*state[velocity])*h;state[key]+=state[velocity]*h;}
}
// Two spring stages bend each existing authored strand. Motion is driven by
// measured head acceleration, not by a stronger independent sine wave.
export class HairRig {
 constructor(model,rest){this.model=model;this.rest=rest;this.geometry=new Map();this.states=new Map();this.last=null;this.first=null;this.sensor=null;this.motion={vx:0,vy:0,ax:0,ay:0};}
 frame(p,time,head,bodyPose,options={}){
  if(this.first===null)this.first=time;
  const gap=this.last===null?0:time-this.last,dt=clamp(gap,0,.1);this.last=time;
  const [w,h]=this.model.size,[nx,ny]=this.model.mesh;
  const index=(Math.round(350/h*ny)*(nx+1)+Math.round(540/w*nx))*2;
  const px=head[index]*w,py=head[index+1]*h;
  if(!this.sensor||gap<0||gap>.25)this.sensor={x:px,y:py,vx:0,vy:0};
  let vx=0,vy=0,ax=0,ay=0;
  if(dt>0){vx=clamp((px-this.sensor.x)/dt,-300,300);vy=clamp((py-this.sensor.y)/dt,-250,250);ax=clamp((vx-this.sensor.vx)/dt,-900,900);ay=clamp((vy-this.sensor.vy)/dt,-900,900);}
  this.sensor={x:px,y:py,vx,vy};this.motion={vx,vy,ax,ay};
  const elapsed=Math.max(0,time-this.first);
  for(const layer of this.model.bodyLayers){const config=layer.hairMotion;if(!config)continue;
   const rear=layer.id.startsWith('rear_'),bang=layer.id.startsWith('bang_'),left=layer.id.includes('left');
   const root=bang?config.rootY:Math.max(config.rootY,rear||layer.id==='side_left_outer'?560:460);
   const tip=layer.rect[3]-1,active=tip>root+10;
   const limit=bang?1.0:rear?(layer.id.includes('outer')?38:12):layer.id==='side_left_front'?20:12;
   let state=this.states.get(layer.id);if(!state){state={mid:0,midV:0,tail:0,tailV:0,vertical:0,verticalV:0,x:0,v:0};this.states.set(layer.id,state);}
   const inertia=(-ax*.07-vx*.09+(left?-1:1)*ay*.025)*(bang?.025:config.amplitude/12);
   const idle=options.ambient===false?0:config.amplitude*.09*(1-Math.exp(-elapsed*2))*Math.sin(elapsed*.85+config.phase);
   const target=active?clamp(inertia+idle,-limit,limit):0;
   const omega=config.speed*(rear?.8:1);
   spring(state,'mid',target*.45,omega*1.7,.9,dt);
   spring(state,'tail',target+state.mid*.25,omega,.52,dt);
   spring(state,'vertical',active?clamp(-ay*.014,-6,6):0,omega*.9,.68,dt);
   state.tail=clamp(state.tail,-limit,limit);state.x=state.tail;state.v=state.tailV;
   let points=this.geometry.get(layer.id);if(!points){points=new Float32Array(head.length);this.geometry.set(layer.id,points);}
   for(let i=0;i<head.length;i+=2){const y=this.rest[i+1]*h,u=active?smooth((y-root)/(tip-root)):0;
    const dx=state.mid*2*u*(1-u)+state.tail*u*u;
    points[i]=head[i]+dx/w;points[i+1]=head[i+1]+(state.vertical*u*u+Math.abs(dx)*.035*u)/h;
   }
  }
 }
}

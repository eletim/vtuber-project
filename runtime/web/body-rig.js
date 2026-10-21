const clamp=(x,lo,hi)=>Math.min(hi,Math.max(lo,x));
const smooth=(a,b,x)=>{const t=clamp((x-a)/(b-a),0,1);return t*t*(3-2*t);};
const radians=x=>x*Math.PI/180;
const value=(p,key,lo,hi)=>clamp(Number.isFinite(p[key])?p[key]:0,lo,hi);

// The PSD weights describe painted opacity, not a rigid limb volume. Moving
// their narrow alpha falloff bends fingers and can fold the transparent edge.
// Extend ownership through the transparent margin, then feather it smoothly.
// This is a runtime field only: neither the original weights nor art changes.
function armOwnership(weights,nx,ny,channel){
  const w=nx+1,h=ny+1,dilated=new Float32Array(w*h),out=new Float32Array(w*h);
  for(let y=0;y<h;y++)for(let x=0;x<w;x++){
    let peak=0;
    for(let dy=-4;dy<=4;dy++)for(let dx=-4;dx<=4;dx++){
      if(dx*dx+dy*dy>18)continue;
      peak=Math.max(peak,weights[clamp(y+dy,0,ny)*w+clamp(x+dx,0,nx)][channel]);
    }
    dilated[y*w+x]=peak;
  }
  const kernel=Array.from({length:13},(_,i)=>Math.exp(-(((i-6)/2.2)**2)/2));
  const total=kernel.reduce((a,b)=>a+b,0),horizontal=new Float32Array(w*h);
  for(let y=0;y<h;y++)for(let x=0;x<w;x++){
    for(let k=-6;k<=6;k++)horizontal[y*w+x]+=dilated[y*w+clamp(x+k,0,nx)]*kernel[k+6]/total;
  }
  for(let y=0;y<h;y++)for(let x=0;x<w;x++){
    for(let k=-6;k<=6;k++)out[y*w+x]+=horizontal[clamp(y+k,0,ny)*w+x]*kernel[k+6]/total;
  }
  return out;
}

class Spring {
  constructor(speed){this.x=0;this.v=0;this.speed=speed;}
  step(target,dt){
    // Exact critically damped response for a held target. No Euler step-size
    // dependence, overshoot on settling, or instability after a slow frame.
    const offset=this.x-target,c=this.v+this.speed*offset,e=Math.exp(-this.speed*dt);
    this.x=target+(offset+c*dt)*e;
    this.v=(this.v-this.speed*c*dt)*e;
    return this.x;
  }
}

// Pivots use the original PSD coordinate system. All transforms share the
// same surface, so shoulder/neck attachments cannot open transparent cracks.
export class BodyRig {
  constructor(model,skinning){
    this.size=model.size;this.mesh=model.mesh;this.weights=skinning.weights;
    const [nx,ny]=this.mesh;
    if(this.weights.length!==(nx+1)*(ny+1))throw Error('skinning grid size mismatch');
    this.rest=new Float32Array((nx+1)*(ny+1)*2);
    this.positions=new Float32Array(this.rest.length);
    let i=0;
    for(let y=0;y<=ny;y++)for(let x=0;x<=nx;x++){
      this.rest[i++]=x/nx;this.rest[i++]=y/ny;
    }
    this.body=new Spring(9);this.arms=[new Spring(6),new Spring(6)];
    this.elbows=[new Spring(5),new Spring(5)];
    this.shoulder=new Spring(8);this.shift=new Spring(6);
    this.armWeights=[armOwnership(this.weights,nx,ny,0),armOwnership(this.weights,nx,ny,1)];
    this.firstTime=null;this.lastTime=null;
  }
  frame(p,time){
    if(this.firstTime===null)this.firstTime=time;
    const elapsed=Math.max(0,time-this.firstTime);
    const dt=this.lastTime===null?0:clamp(time-this.lastTime,0,.1);this.lastTime=time;
    const bodyTarget=clamp(p.ParamBodyAngleX*.8+p.ParamAngleX*.04,-4.6,4.6);
    const body=this.body.step(bodyTarget,dt);
    const breath=clamp(p.ParamBreath,0,1)-.5;
    const shoulder=this.shoulder.step(value(p,'ParamShoulderY',-1,1)*3,dt);
    const shift=this.shift.step(value(p,'ParamBodyShiftX',-1,1)*4,dt);
    const armAngles=[],elbowAngles=[];
    for(let side=0;side<2;side++){
      const sign=side===0?1:-1;
      const lag=clamp(-this.body.v*.055+body*.09+sign*breath*.18,-1.15,1.15);
      const intent=sign*2.8*value(p,side===0?'ParamArmLOpen':'ParamArmROpen',-1,1);
      armAngles.push(radians(this.arms[side].step(clamp(lag+intent,-3.2,3.2),dt)));
      elbowAngles.push(radians(this.elbows[side].step(clamp(-this.arms[side].x*.35,-1.12,1.12),dt)));
    }
    const bodyAngle=radians(body),bc=Math.cos(bodyAngle),bs=Math.sin(bodyAngle);
    const headAngle=radians(p.ParamAngleZ),hc=Math.cos(headAngle),hs=Math.sin(headAngle);
    const [width,height]=this.size;
    for(let i=0;i<this.weights.length;i++){
      const x=this.rest[i*2]*width,y=this.rest[i*2+1]*height;
      const [, ,hair,armParent]=this.weights[i];
      const left=this.armWeights[0][i],right=this.armWeights[1][i];
      let px=x,py=y;
      // Distal bone first, followed by its parent shoulder.
      for(let side=0;side<2;side++){
        const weight=(side===0?left:right)*smooth(590,720,y);
        if(weight<.0001)continue;
        const shoulder=side===0?[365,565]:[780,585];
        const elbow=side===0?[275,935]:[850,955];
        let angle=elbowAngles[side]*weight*smooth(850,1080,y);
        let c=Math.cos(angle),s=Math.sin(angle),qx=px-elbow[0],qy=py-elbow[1];
        px=elbow[0]+c*qx-s*qy;py=elbow[1]+s*qx+c*qy;
        angle=armAngles[side]*weight;c=Math.cos(angle);s=Math.sin(angle);
        qx=px-shoulder[0];qy=py-shoulder[1];
        px=shoulder[0]+c*qx-s*qy;py=shoulder[1]+s*qx+c*qy;
      }
      // Neck blends into the shoulder line; chest no longer follows head tilt.
      const head=(1-smooth(430,565,y))*(1-smooth(230,380,Math.abs(x-540))),qx=px-540,qy=py-425;
      px+=(hc*qx-hs*qy-qx+p.ParamAngleX*.65)*head;
      py+=(hs*qx+hc*qy-qy+p.ParamAngleY*.35)*head;
      // Breathing is centered on the ribs and fades before the fixed waist.
      const chest=smooth(450,580,y)*(1-smooth(800,1000,y));
      const central=1-smooth(180,300,Math.abs(x-543));
      px+=(x-543)*breath*.002*chest*central;
      py-=breath*(.7*(1-smooth(570,950,y))+1.1*chest*central);
      // Hip/root stays planted. Upper body rotates around it as a hierarchy.
      const parent=Math.max(armParent,left,right);
      const torso=Math.max(1-smooth(1010,1370,y),parent),tx=px-543,ty=py-1000;
      px+=(bc*tx-bs*ty-tx)*torso;py+=(bs*tx+bc*ty-ty)*torso;
      px+=shift*torso;
      py-=shoulder*Math.max(1-smooth(650,1020,y),parent);
      // Sway belongs only to actual long-hair ownership, not sleeve/torso pixels.
      px+=hair*.55*(Math.sin(elapsed*1.6+y*.007)-Math.sin(y*.007));
      this.positions[i*2]=px/width;this.positions[i*2+1]=py/height;
    }
    this.pose={body,arms:this.arms.map(v=>v.x),elbows:this.elbows.map(v=>v.x),shoulder,shift};
    return this.positions;
  }
}

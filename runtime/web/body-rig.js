const clamp=(x,lo,hi)=>Math.min(hi,Math.max(lo,x));
const smooth=(a,b,x)=>{const t=clamp((x-a)/(b-a),0,1);return t*t*(3-2*t);};
const radians=x=>x*Math.PI/180;

class Spring {
  constructor(speed){this.x=0;this.v=0;this.speed=speed;}
  step(target,dt){
    const count=Math.max(1,Math.ceil(dt*120)),h=dt/count;
    for(let i=0;i<count;i++){
      this.v+=((target-this.x)*this.speed*this.speed-2*this.speed*this.v)*h;
      this.x+=this.v*h;
    }
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
    this.firstTime=null;this.lastTime=null;
  }
  frame(p,time){
    if(this.firstTime===null)this.firstTime=time;
    const elapsed=Math.max(0,time-this.firstTime);
    const dt=this.lastTime===null?0:clamp(time-this.lastTime,0,.05);this.lastTime=time;
    const bodyTarget=clamp(p.ParamBodyAngleX*.8+p.ParamAngleX*.04,-4.6,4.6);
    const body=this.body.step(bodyTarget,dt);
    const breath=clamp(p.ParamBreath,0,1)-.5;
    const armAngles=[],elbowAngles=[];
    for(let side=0;side<2;side++){
      const sign=side===0?1:-1;
      const lag=clamp(-this.body.v*.055+body*.09+sign*breath*.18,-1.15,1.15);
      armAngles.push(radians(this.arms[side].step(lag,dt)));
      elbowAngles.push(radians(this.elbows[side].step(-this.arms[side].x*.35,dt)));
    }
    const bodyAngle=radians(body),bc=Math.cos(bodyAngle),bs=Math.sin(bodyAngle);
    const headAngle=radians(p.ParamAngleZ),hc=Math.cos(headAngle),hs=Math.sin(headAngle);
    const [width,height]=this.size;
    for(let i=0;i<this.weights.length;i++){
      const x=this.rest[i*2]*width,y=this.rest[i*2+1]*height;
      const [left,right,hair,armParent]=this.weights[i];
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
      const torso=Math.max(1-smooth(1010,1370,y),armParent),tx=px-543,ty=py-1000;
      px+=(bc*tx-bs*ty-tx)*torso;py+=(bs*tx+bc*ty-ty)*torso;
      // Sway belongs only to actual long-hair ownership, not sleeve/torso pixels.
      px+=hair*.55*(Math.sin(elapsed*1.6+y*.007)-Math.sin(y*.007));
      this.positions[i*2]=px/width;this.positions[i*2+1]=py/height;
    }
    this.pose={body,arms:this.arms.map(v=>v.x),elbows:this.elbows.map(v=>v.x)};
    return this.positions;
  }
}

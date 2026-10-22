const clamp=(x,lo,hi)=>Math.min(hi,Math.max(lo,x));
const smooth=(a,b,x)=>{const t=clamp((x-a)/(b-a),0,1);return t*t*(3-2*t);};
const radians=x=>x*Math.PI/180;
const value=(p,key,lo,hi,fallback=0)=>clamp(Number.isFinite(p[key])?p[key]:fallback,lo,hi);

class Spring {
  constructor(speed){this.x=0;this.v=0;this.speed=speed;}
  step(target,dt){
    // Exact critically damped response for a held target, stable after a slow frame.
    const offset=this.x-target,c=this.v+this.speed*offset,e=Math.exp(-this.speed*dt);
    this.x=target+(offset+c*dt)*e;
    this.v=(this.v-this.speed*c*dt)*e;
    return this.x;
  }
}

// Shared pelvis parent used by every surface, including articulated limbs.
export function pelvisPoint(x,y,pose){
 const a=radians(pose.pelvisAngle||0),c=Math.cos(a),s=Math.sin(a),dx=x-555,dy=y-1100;
 return [555+c*dx-s*dy+(pose.shift||0),1100+s*dx+c*dy-(pose.bounce||0)];
}

export const bodyRoles=Object.freeze(['root','skirt','torso','armLeft','armRight','head','chest','abdomen','pelvis','legLeft','legRight']);

// Each role owns an independent surface. Texture alpha only controls coverage;
// it is never used as, or dilated into, a deformation field. Body art is exported
// from explicit PSD layers, including the hidden cloth underneath moving parts.
export class BodyRig {
  constructor(model,skinning){
    this.size=model.size;this.mesh=model.mesh;this.weights=skinning.weights;
    this.separateHair=Boolean(model.hairExport?.exclusiveOwnership);
    const [nx,ny]=this.mesh;
    if(this.weights.length!==(nx+1)*(ny+1))throw Error('skinning grid size mismatch');
    this.config={shoulders:[[365,520],[780,540]],elbows:[[275,935],[850,955]],waist:[543,995],skirtTop:995,skirtHem:1430,skirtRevealLimitPixels:3,...model.bodyRig};
    this.rest=new Float32Array((nx+1)*(ny+1)*2);
    let i=0;
    for(let y=0;y<=ny;y++)for(let x=0;x<=nx;x++){
      this.rest[i++]=x/nx;this.rest[i++]=y/ny;
    }
    this.positionsByRole=Object.fromEntries(bodyRoles.map(role=>[role,new Float32Array(this.rest)]));
    this.positions=this.positionsByRole.torso;
    this.body=new Spring(9);this.arms=[new Spring(6),new Spring(6)];
    this.elbows=[new Spring(5),new Spring(5)];
    this.shoulder=new Spring(8);this.shift=new Spring(6);this.skirt=new Spring(4.5);
    this.bounce=new Spring(11);this.headLag=new Spring(6);
    this.pelvis=new Spring(7);this.counterChest=new Spring(5.8);this.legs=[new Spring(6.5),new Spring(5.3)];
    this.firstTime=null;this.lastTime=null;
  }
  frame(p,time,options={}){
    if(this.firstTime===null)this.firstTime=time;
    const elapsed=Math.max(0,time-this.firstTime);
    const dt=this.lastTime===null?0:clamp(time-this.lastTime,0,.1);this.lastTime=time;
    const angleX=value(p,'ParamAngleX',-15,15),angleY=value(p,'ParamAngleY',-10,10);
    const bodyTarget=clamp(value(p,'ParamBodyAngleX',-5,5)*.8+angleX*.04,-4.6,4.6);
    const body=this.body.step(bodyTarget,dt);
    const breath=value(p,'ParamBreath',0,1,.5)-.5;
    const bounce=this.bounce.step(value(p,'ParamBodyBounce',-1,1)*6,dt);
    const shoulder=this.shoulder.step(value(p,'ParamShoulderY',-1,1)*.6,dt);
    const shift=this.shift.step(value(p,'ParamBodyShiftX',-1,1)*36,dt);
    const pelvisAngle=this.pelvis.step(clamp(shift/36*3.4-body*.12,-3.8,3.8),dt);
    // Ribcage balances the loaded hip with its own delayed angular response.
    const chestAngle=this.counterChest.step(clamp(-pelvisAngle*1.25+body*.28-this.shift.v*.009,-4.8,4.8),dt);
    const legAngles=this.legs.map((spring,side)=>spring.step(clamp(-pelvisAngle*.5+(side===0?1:-1)*(shift/36*2.8+bounce*.05),-4.8,4.8),dt));
    const headLag=this.headLag.step(clamp(-this.body.v*.09-body*.18,-2,2),dt);
    const armAngles=[],elbowAngles=[];
    for(let side=0;side<2;side++){
      const sign=side===0?1:-1;
      const lag=clamp(-this.counterChest.v*(side===0?.08:.055)+chestAngle*.09+sign*breath*.18,-1.15,1.15);
      const intent=sign*2.8*value(p,side===0?'ParamArmLOpen':'ParamArmROpen',-1,1);
      armAngles.push(radians(this.arms[side].step(clamp(lag+intent,-3.2,3.2),dt)));
      elbowAngles.push(radians(this.elbows[side].step(clamp(-this.arms[side].x*.35,-1.12,1.12),dt)));
    }
    // Delayed hem inertia follows the body, never an arm. The entire waist row
    // remains fixed relative to the pelvis parent, even under a full manual skirt command. The approved
    // hidden hem artwork supports at most three source pixels of reveal.
    const skirtLimit=clamp(this.config.skirtRevealLimitPixels,0,3);
    const skirtTarget=clamp(value(p,'ParamSkirtSway',-1,1)*skirtLimit-this.body.v*.4-this.shift.v*.25-this.bounce.v*.035-body*.65,-skirtLimit,skirtLimit);
    const skirt=this.skirt.step(skirtTarget,dt);
    const bodyAngle=radians(chestAngle),bc=Math.cos(bodyAngle),bs=Math.sin(bodyAngle);
    const headAngle=radians(clamp(value(p,'ParamAngleZ',-8,8)+headLag,-8,8)),hc=Math.cos(headAngle),hs=Math.sin(headAngle);
    const [width,height]=this.size,[wx,wy]=this.config.waist;
    const torso=this.positionsByRole.torso,headPositions=this.positionsByRole.head,skirtPositions=this.positionsByRole.skirt;
    for(let i=0;i<this.weights.length;i++){
      const x=this.rest[i*2]*width,y=this.rest[i*2+1]*height;
      const hair=this.weights[i][2];
      let px=x,py=y;
      // Preserve the v17/v18 face transform, independently of all limb inputs.
      const head=(1-smooth(430,565,y))*(1-smooth(230,380,Math.abs(x-540))),qx=x-540,qy=y-425;
      px+=(hc*qx-hs*qy-qx+angleX*.65)*head;
      py+=(hs*qx+hc*qy-qy+angleY*.35)*head;
      const chest=smooth(450,580,y)*(1-smooth(800,1000,y));
      const central=1-smooth(180,300,Math.abs(x-543));
      px+=(x-543)*breath*.002*chest*central;
      py-=breath*(.7*(1-smooth(570,950,y))+1.1*chest*central);
      const parent=1-smooth(840,960,y),tx=px-wx,ty=py-wy;
      px+=(bc*tx-bs*ty-tx)*parent;
      py+=(bs*tx+bc*ty-ty)*parent-shoulder*(1-smooth(650,wy,y));
      torso[i*2]=px/width;torso[i*2+1]=py/height;
      px+=(options.ambient===false||this.separateHair?0:hair)*.55*(Math.sin(elapsed*1.6+y*.007)-Math.sin(y*.007));
      headPositions[i*2]=px/width;headPositions[i*2+1]=py/height;
      const hem=smooth(this.config.skirtTop+8,this.config.skirtHem,y);
      skirtPositions[i*2]=(x+skirt*hem)/width;
      skirtPositions[i*2+1]=(y+Math.abs(skirt)*.06*hem)/height;
      for(let side=0;side<2;side++){
        const positions=this.positionsByRole[side===0?'armLeft':'armRight'];
        const anchor=this.config.shoulders[side],elbow=this.config.elbows[side];
        const attachment=smooth(anchor[1]-12,anchor[1]+110,y);
        px=x;py=y;
        // Elbow is local to its arm only. Broad smooth transition preserves
        // sleeve silhouette and hand shape without pulling adjacent clothes.
        let angle=elbowAngles[side]*smooth(elbow[1]-85,elbow[1]+145,y)*attachment;
        let c=Math.cos(angle),s=Math.sin(angle),ax=px-elbow[0],ay=py-elbow[1];
        px=elbow[0]+c*ax-s*ay;py=elbow[1]+s*ax+c*ay;
        angle=armAngles[side]*attachment;c=Math.cos(angle);s=Math.sin(angle);
        ax=px-anchor[0];ay=py-anchor[1];
        px=anchor[0]+c*ax-s*ay;py=anchor[1]+s*ax+c*ay;
        // Inherit the shoulder's complete body transform. No waist fade can
        // pin a low hand to the skirt, and no arm motion feeds back to torso.
        ax=px-wx;ay=py-wy;
        px=wx+bc*ax-bs*ay;
        py=wy+bs*ax+bc*ay-shoulder-breath*.7*(1-smooth(570,950,anchor[1]));
        positions[i*2]=px/width;positions[i*2+1]=py/height;
      }
    }
    this.pose={body:chestAngle,pelvisAngle,legs:legAngles,arms:this.arms.map(v=>v.x),elbows:this.elbows.map(v=>v.x),shoulder,shift,skirt,bounce,headLag};
    // One rigid pelvis parent transports torso, skirt and legs together. Bounce
    // is a translation of the complete skeleton, never a torso scale field.
    // Chest counter-rotation connects through abdomen into the pelvis attachment.
    this.positionsByRole.root.set(this.rest);
    this.positionsByRole.pelvis.set(this.rest);
    this.positionsByRole.abdomen.set(torso);
    this.positionsByRole.chest.set(torso);
    // Chest is rigid below its visible cut too; abdomen alone owns the short
    // lumbar transition. A 20px common strip on both cuts prevents cracks.
    for(let i=0;i<this.rest.length;i+=2){
      const x=this.rest[i]*width,y=this.rest[i+1]*height;
      if(y>=840){const ax=x-wx,ay=y-wy;this.positionsByRole.chest[i]=(wx+bc*ax-bs*ay)/width;this.positionsByRole.chest[i+1]=(wy+bs*ax+bc*ay-shoulder)/height;}
      for(let side=0;side<2;side++){
        const hip=[side===0?400:650,1225],u=smooth(1300,1440,y)*smooth(15,60,Math.abs(x-540)),a=radians(legAngles[side])*u,c=Math.cos(a),s=Math.sin(a),dx=x-hip[0],dy=y-hip[1],v=this.positionsByRole[side===0?'legLeft':'legRight'];
        v[i]=(hip[0]+c*dx-s*dy)/width;v[i+1]=(hip[1]+s*dx+c*dy)/height;
      }
    }
    for(const positions of Object.values(this.positionsByRole))for(let i=0;i<positions.length;i+=2){
      const q=pelvisPoint(positions[i]*width,positions[i+1]*height,this.pose);
      positions[i]=q[0]/width;positions[i+1]=q[1]/height;
    }
    // Legacy callers receive torso geometry. Multi-part callers must render
    // every independent positionsByRole surface in model.bodyLayers order.
    return this.positions;
  }
  frames(p,time,options={}){this.frame(p,time,options);return this.positionsByRole;}
}

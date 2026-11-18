const clamp=(x,lo,hi)=>Math.min(hi,Math.max(lo,x));
const smooth=(a,b,x)=>{const t=clamp((x-a)/(b-a),0,1);return t*t*(3-2*t);};
const radians=x=>x*Math.PI/180;
const value=(p,key,lo,hi,fallback=0)=>clamp(Number.isFinite(p[key])?p[key]:fallback,lo,hi);

class Spring {
  constructor(speed){this.x=0;this.v=0;this.speed=speed;}
  stepLinear(target,dt){
    // Exact response to the linearly varying command between two samples.
    // Larger pelvis travel must not magnify frame-rate-dependent endpoint holds.
    const previous=this.target??target;this.target=target;
    if(dt<=0)return this.x;
    const speed=this.speed,slope=(target-previous)/dt;
    const offset=this.x-previous+2*slope/speed,velocity=this.v-slope;
    const c=velocity+speed*offset,e=Math.exp(-speed*dt);
    this.x=target-2*slope/speed+(offset+c*dt)*e;
    this.v=slope+(velocity-speed*c*dt)*e;
    return this.x;
  }
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
 return [555+c*dx-s*dy+(pose.shift||0),1100+s*dx+c*dy-(pose.bounce||0)+(pose.supportHeight||0)];
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
    this.shoulder=new Spring(8);this.shift=new Spring(8);this.skirt=new Spring(4.5);
    this.bounce=new Spring(11);this.headLag=new Spring(6);
    this.headCommands=[new Spring(11),new Spring(11),new Spring(10)];
    this.pelvis=new Spring(12);this.counterChest=new Spring(4.2);this.cheek=new Spring(5.2);this.legs=[new Spring(6.5),new Spring(5.3)];
    this.firstTime=null;this.lastTime=null;
  }
  frame(p,time,options={}){
    const initializing=this.lastTime===null;
    if(this.firstTime===null)this.firstTime=time;
    const elapsed=Math.max(0,time-this.firstTime);
    const dt=this.lastTime===null?0:clamp(time-this.lastTime,0,.1);this.lastTime=time;
    // Intent leads the hand slightly; the neck keeps responding as the palm arrives.
    const cheek=this.cheek.step(value(p,'ParamHandToCheek',0,1),dt);
    const approach=smooth(.12,.9,cheek),contact=smooth(.62,1,cheek);
    // Head commands arrive through the neck instead of snapping at an emotion
    // boundary. This preserves the commanded end pose and the cheek response.
    const headCommands=this.headCommands.map((s,i)=>{const target=value(p,['ParamAngleX','ParamAngleY','ParamAngleZ'][i],[-15,-10,-8][i],[15,10,8][i]);if(initializing)s.x=target;return s.step(target,dt)});
    const angleX=clamp(headCommands[0]-2.2*approach,-15,15),angleY=clamp(headCommands[1]+.7*contact,-10,10);
    const bodyTarget=clamp(value(p,'ParamBodyAngleX',-5,5)*.8+value(p,'ParamAngleX',-15,15)*.04,-4.6,4.6);
    const body=this.body.step(bodyTarget,dt);
    const breath=value(p,'ParamBreath',0,1,.5)-.5;
    const bounce=this.bounce.step(value(p,'ParamBodyBounce',-1,1)*6,dt);
    const shoulder=this.shoulder.step(value(p,'ParamShoulderY',-1,1)*.6,dt);
    const shift=this.shift.stepLinear(value(p,'ParamBodyShiftX',-1,1)*72,dt);
    const pelvisAngle=this.pelvis.step(clamp(shift/72*5.6-body*.12,-5.9,5.9),dt);
    // Ribcage balances the loaded hip with its own delayed angular response.
    // Shared pelvis height follows loading rather than stretching either leg.
    const supportHeight=-5.5*smooth(0,1,Math.abs(shift)/72);
    const chestAngle=this.counterChest.step(clamp(-pelvisAngle*1.25+body*.28-this.shift.v*.012-.6*approach,-6,6),dt);
    const legAngles=this.legs.map((spring,side)=>spring.step(clamp(-pelvisAngle*.5+(side===0?1:-1)*(shift/72*4.5+bounce*.05),-6,6),dt));
    // React to the visible ribcage/pelvis rotation, not the raw body-control
    // spring (which is different from the counter-rotating chest surface).
    const headLag=this.headLag.step(clamp(-(this.counterChest.v+this.pelvis.v)*.055-(chestAngle+pelvisAngle)*.18,-2.3,2.3),dt);
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
    const headAngle=radians(clamp(headCommands[2]+headLag-2.8*approach-.7*contact,-8,8)),hc=Math.cos(headAngle),hs=Math.sin(headAngle);
    const [width,height]=this.size,[wx,wy]=this.config.waist;
    const torso=this.positionsByRole.torso,headPositions=this.positionsByRole.head,skirtPositions=this.positionsByRole.skirt;
    for(let i=0;i<this.weights.length;i++){
      const x=this.rest[i*2]*width,y=this.rest[i*2+1]*height;
      const hair=this.weights[i][2];
      let px=x,py=y;
      // Torso/neck retain their attachment field; head uses a rigid plane below.
      const head=(1-smooth(430,565,y))*(1-smooth(230,380,Math.abs(x-540))),qx=x-540,qy=y-425;
      px+=(hc*qx-hs*qy-qx)*head;
      py+=(hs*qx+hc*qy-qy)*head;
      const chest=smooth(450,580,y)*(1-smooth(800,1000,y));
      const central=1-smooth(180,300,Math.abs(x-543));
      px+=(x-543)*breath*.002*chest*central;
      py-=breath*(.7*(1-smooth(570,950,y))+1.1*chest*central);
      const parent=1-smooth(840,960,y),tx=px-wx,ty=py-wy;
      px+=(bc*tx-bs*ty-tx)*parent;
      py+=(bs*tx+bc*ty-ty)*parent-shoulder*(1-smooth(650,wy,y));
      torso[i*2]=px/width;torso[i*2+1]=py/height;
      // One rigid head roll, then rigid chest and pelvis transforms.
      // No yaw/pitch, per-feature displacement, depth or breathing scale.
      const hx=540+hc*qx-hs*qy,hy=425+hs*qx+hc*qy;
      const hdx=hx-wx,hdy=hy-wy;
      const rigidX=(wx+bc*hdx-bs*hdy)/width;
      const rigidY=(wy+bs*hdx+bc*hdy-shoulder-breath*.7)/height;
      // The legacy head texture includes neck/shoulder skin below the face.
      // Attach only that non-face region to the torso; all face pixels stay rigid.
      const neck=smooth(450,565+Math.max(0,Math.abs(x-540)-300)*.6,y);
      headPositions[i*2]=rigidX*(1-neck)+torso[i*2]*neck;
      headPositions[i*2+1]=rigidY*(1-neck)+torso[i*2+1]*neck;
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
        if(side===1){
          // Pin the authored inner sleeve cut to the torso's identical surface.
          // Independent elbow/shoulder lag grows across the outer sleeve width.
          const seam=[[489,731],[600,768],[700,791],[800,780],[900,765],[1000,795],[1050,820]];
          let inner=seam[0][1];for(let k=1;k<seam.length;k++)if(y>=seam[k-1][0]){const u=clamp((y-seam[k-1][0])/(seam[k][0]-seam[k-1][0]),0,1);inner=seam[k-1][1]+u*(seam[k][1]-seam[k-1][1]);}
          const pin=smooth(-120,-20,x-inner)*(1-smooth(0,90,x-inner))*smooth(440,490,y)*(1-smooth(760,830,y));
          px=px*(1-pin)+x*pin;py=py*(1-pin)+y*pin;
        }
        // Inherit the shoulder's complete body transform. No waist fade can
        // pin a low hand to the skirt, and no arm motion feeds back to torso.
        ax=px-wx;ay=py-wy;
        px=wx+bc*ax-bs*ay;
        py=wy+bs*ax+bc*ay-shoulder-breath*.7*(1-smooth(570,950,anchor[1]));
        positions[i*2]=px/width;positions[i*2+1]=py/height;
      }
    }
    this.pose={headCommands,supportHeight,cheek,approach,contact,body:chestAngle,pelvisAngle,legs:legAngles,arms:this.arms.map(v=>v.x),elbows:this.elbows.map(v=>v.x),shoulder,shift,skirt,bounce,headLag};
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

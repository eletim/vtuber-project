import {performanceSequence} from './performance-sequence.js';
import {PerformanceMotion} from './performance.js';

// A local, explicit performance overlay. The renderer and hair rig are never
// reset. Mouth/audio and externally owned expressions retain their authority.
export class ActingController {
  constructor(){this.weight=0;this.running=false;this.last=null;this.sample=null;this.motion=new PerformanceMotion();}
  start(time,variant='original'){
    if(this.running||this.weight>.001)return false;
    // A queued RAF timestamp may precede the click's performance.now().
    this.variant=['curious','joyful','thinking','surprised'].includes(variant)?variant:'original';this.started=time;this.running=true;this.last=null;this.sample=null;return true;
  }
  stop(){this.running=false;}
  sync(state,time,epoch){
    if(!state?.id){this.stop();return;}
    const resuming=!this.running;
    if(this.syncId!==state.id){
      this.switchFrom=this.sample;this.switchAt=time;
      this.variant=['curious','joyful','thinking','surprised'].includes(state.variant)?state.variant:'original';this.syncId=state.id;this.started=time-Math.max(0,epoch-state.started_at);
      this.running=true;this.last=null;this.motion=new PerformanceMotion();
    }
    // Repeated snapshots never rewind an existing performance or reset physics.
    if(state.stopped_at){
      const age=Math.max(0,state.stopped_at-state.started_at),s=performanceSequence(age,this.variant);
      if(!this.sample)this.sample={pose:this.motion.frame(s.parameters,age,s.performance,0),expression:s.expression};
      this.stop();
    }else {
      this.running=epoch-state.started_at<18.5;
      // A fresh authoritative snapshot can resume after a disconnected RAF gap.
      // Preserve the original epoch and blend weight; only discard the stale dt.
      if(this.running&&resuming&&(this.last===null||time-this.last>2||time<this.last))this.last=null;
    }
  }
  frame(base,time,{blocked=false,expression='neutral',expressionOwned=false}={}){
    const gap=this.last===null?0:time-this.last;
    if(blocked||gap<0||gap>2)this.stop();
    const dt=Math.max(0,Math.min(.1,gap));this.last=time;
    if(this.running){
      const age=Math.max(0,time-this.started);
      const sequence=performanceSequence(age,this.variant);
      const next={pose:this.motion.frame(sequence.parameters,age,sequence.performance,0),expression:sequence.expression};
      if(this.switchFrom){const u=Math.max(0,Math.min(1,(time-this.switchAt)/.6)),w=u*u*(3-2*u);for(const key of Object.keys(next.pose))next.pose[key]=this.switchFrom.pose[key]+(next.pose[key]-this.switchFrom.pose[key])*w;if(u<.5)next.expression=this.switchFrom.expression;if(u>=1)this.switchFrom=null;}
      this.sample=next;
      if(age>=18.5)this.stop();
    }
    this.weight+=(Number(this.running)-this.weight)*(1-Math.exp(-dt/.18));
    if(!this.running&&this.weight<.001){this.weight=0;this.sample=null;}
    const pose={...base};
    if(this.sample)for(const key of Object.keys(pose)){
      if(key==='ParamMouthOpenY'||key==='ParamBreath')continue;
      pose[key]+=(this.sample.pose[key]-pose[key])*this.weight;
    }
    return {pose,expression:!expressionOwned&&this.sample&&this.weight>.5?this.sample.expression:expression,running:this.running,weight:this.weight};
  }
}

export function mountActingControls(start,stop){
  const section=document.createElement('section');
  section.innerHTML='<h2>自然な演技</h2><p>プレビューと配信用画面で同じ演技を再生します。会話・音声・カメラ操作が優先されます。</p><label>しぐさ <select id="acting-variant"><option value="original">いつもの演技</option><option value="curious">首かしげ・頬添え</option><option value="thinking">考える：視線・首かしげ・頬添え</option><option value="surprised">驚く：身を引いて落ち着く</option><option value="joyful">うれしい弾み・頬添え</option></select></label><div class="row"><button id="acting-start">演技を再生</button><button id="acting-stop" disabled>演技を収める</button></div><p id="acting-status" role="status">待機中</p>';
  document.querySelector('aside').prepend(section);
  const begin=section.querySelector('#acting-start'),end=section.querySelector('#acting-stop'),status=section.querySelector('#acting-status');
  const selector=section.querySelector('#acting-variant');begin.onclick=()=>start(selector.value);end.onclick=stop;
  return state=>{begin.textContent=state.running?'このしぐさへ切替':'演技を再生';selector.disabled=state.blocked;begin.disabled=state.blocked||(!state.running&&state.weight>0);end.disabled=!state.running;status.textContent=state.blocked?'会話・音声・入力を優先中':state.running?'演技中':state.weight>0?'自然に収束中':'待機中';};
}

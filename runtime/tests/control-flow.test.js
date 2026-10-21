import test from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import {readFileSync} from 'node:fs';
import * as controls from '../web/controls.js';
import {PerformanceMotion} from '../web/performance.js';
import {expressionLabels} from '../web/expressions.js';

// Exercise the real UI handlers without WebGL, a media device, or wall-clock waits.
const source=readFileSync(new URL('../web/app.js',import.meta.url),'utf8')
  .replace(/^import .*;\n/gm,'')
  .replace(/^try\{await renderer\.load.*$/m,'');
const flush=()=>new Promise(resolve=>setImmediate(resolve));
function harness(){
  const elements=new Map(),requests=[],intervals=new Map(),timeouts=new Map(),sent=[],mediaRequests=[];
  let sequence=0,now=0,socket;
  let state={mode:'human',parameters:controls.neutral(),performance:{enabled:false,emotion:'neutral'},expression:{id:'neutral',owner:'idle'}};
  function element(id){
    if(!elements.has(id))elements.set(id,{
      value:'auto',checked:true,textContent:'',paused:true,ended:false,currentTime:0,files:[],listeners:{},
      classList:{toggle(){},add(){},remove(){}},append(){},
      addEventListener(type,callback){(this.listeners[type]||=[]).push(callback);},
      fire(type){for(const callback of this.listeners[type]||[])callback();},
      pause(){this.paused=true;},play(){this.paused=false;return Promise.resolve();},
      querySelector(){return{value:0,nextElementSibling:{value:0}};}
    });
    return elements.get(id);
  }
  const context=vm.createContext({
    ...controls,PerformanceMotion,expressionLabels,AvatarRenderer:class{},console,Date,URLSearchParams,
    URL:{createObjectURL:()=> 'blob:test',revokeObjectURL(){}},
    document:{getElementById:element,createElement:()=>element(`row${sequence++}`),body:element('body')},
    window:{addEventListener(){}},location:{protocol:'http:',host:'test',search:''},
    performance:{now:()=>now},
    navigator:{mediaDevices:{getUserMedia:()=>new Promise(resolve=>mediaRequests.push(resolve))}},
    AudioContext:class{
      resume(){}createAnalyser(){return{connect(){}};}
      createMediaStreamSource(){return{connect(){}};}
      createMediaElementSource(){return{connect(){}};}
    },
    WebSocket:class{
      constructor(){socket=this;this.readyState=1;}
      send(data){const message=JSON.parse(data);sent.push(message);if(message.source===state.mode){Object.assign(state.parameters,message.parameters);if(message.expression)state.expression={id:message.expression,owner:'manual'};emit({type:'state',...state});}}
    },
    fetch:(path,options)=>new Promise(resolve=>requests.push({path,body:JSON.parse(options.body),resolve})),
    setInterval:fn=>{const id=++sequence;intervals.set(id,fn);return id;},
    clearInterval:id=>intervals.delete(id),
    setTimeout:(fn,delay)=>{const id=++sequence;timeouts.set(id,{fn,at:now+delay});return id;},
    clearTimeout:id=>timeouts.delete(id),
    requestAnimationFrame(){},cancelAnimationFrame(){}
  });
  vm.runInContext(source+'\nconnect();',context);
  const emit=event=>socket.onmessage({data:JSON.stringify(event)});
  function publish(request){
    if(request.path==='/api/mode'){
      state={...state,mode:request.body.mode,parameters:controls.neutral(),expression:{id:'neutral',owner:'idle'}};
      emit({type:'cancel_speech'});
    }else if(request.path==='/api/performance'){
      state.performance={...state.performance,...request.body};
    }
    emit({type:'state',...state});
  }
  function respond(request){request.resolve({ok:true,json:async()=>({...state})});}
  function complete(request){publish(request);respond(request);}
  emit({type:'state',...state});
  return{element,requests,intervals,timeouts,sent,mediaRequests,emit,publish,respond,complete,
    motion:vm.runInContext('naturalMotion',context),
    prepareCamera:()=>vm.runInContext('landmarker={detectForVideo(){}};',context),
    slider:key=>vm.runInContext('sliders['+JSON.stringify(key)+']',context),
    disconnect:()=>{socket.readyState=3;socket.onclose();},
    advance:time=>{now=time;for(const callback of [...intervals.values()])callback();for(const [id,timer] of [...timeouts])if(timer.at<=now){timeouts.delete(id);timer.fn();}}};
}

for(const action of ['reset','human','disconnect'])test(`${action} clears speech accents and cannot revive an old gesture`,()=>{
  const h=harness();
  for(let i=0;i<40;i++)h.motion.frame(controls.neutral(),i/60,{enabled:true},.8);
  assert.ok(h.motion.pose.accent>.2);
  if(action==='disconnect')h.disconnect();else h.element(action).onclick();
  assert.equal(h.motion.gesture,null);assert.equal(h.motion.pose.accent,0);
  for(let i=40;i<100;i++){
    const pose=h.motion.frame(controls.neutral(),i/60,{enabled:action==='reset'},0);
    assert.equal(pose.ParamArmLOpen,0);assert.equal(pose.ParamArmROpen,0);
  }
});

test('gesture preview selects AI and enables disabled natural motion',async()=>{
  const h=harness();h.element('emotion').value='thoughtful';
  const action=h.element('gesture').onclick();
  assert.deepEqual(h.requests[0].body,{mode:'ai'});
  h.complete(h.requests[0]);await flush();
  assert.equal(h.requests[1].path,'/api/performance');
  assert.deepEqual(h.requests[1].body,{enabled:true,emotion:'thoughtful',duration:4});
  h.complete(h.requests[1]);await action;
  assert.equal(h.element('lively').checked,true);
});

test('an in-flight human control frame does not cancel an intended AI selection',async()=>{
  const h=harness();const demo=h.element('demo').onclick();
  h.emit({type:'state',mode:'human',parameters:controls.neutral(),performance:{enabled:false,emotion:'neutral'}});
  h.complete(h.requests[0]);await demo;
  assert.equal(h.intervals.size,1);
});

test('overlapping demo clicks share mode selection and start exactly one timer',async()=>{
  const h=harness();
  const first=h.element('demo').onclick(),second=h.element('demo').onclick();
  assert.equal(h.requests.length,1);
  // Actual server order: cancellation, shared state, then HTTP response.
  h.complete(h.requests[0]);await Promise.all([first,second]);
  assert.equal(h.intervals.size,1);
  h.advance(100);assert.equal(h.sent.length,1);
  h.advance(15000);assert.equal(h.intervals.size,0);
  assert.equal(h.sent.at(-1).parameters.ParamMouthOpenY,0);
});

for(const button of ['demo','gesture'])test(`${button} tolerates HTTP before WebSocket acknowledgment`,async()=>{
  const h=harness();const first=h.element(button).onclick(),latest=h.element(button).onclick();
  h.respond(h.requests[0]);await flush();
  assert.equal(h.intervals.size,0);assert.equal(h.requests.length,1);
  h.publish(h.requests[0]);await flush();
  if(button==='gesture'){
    assert.equal(h.requests.length,2);h.complete(h.requests[1]);
  }else assert.equal(h.intervals.size,1);
  await Promise.all([first,latest]);
});

test('a replacement gesture wins over a pending demo without a stray timer',async()=>{
  const h=harness();
  const demo=h.element('demo').onclick(),gesture=h.element('gesture').onclick();
  h.complete(h.requests[0]);await flush();
  assert.equal(h.intervals.size,0);
  assert.equal(h.requests.length,2);
  h.complete(h.requests[1]);await Promise.all([demo,gesture]);
  assert.equal(h.intervals.size,0);
});

for(const button of ['demo','gesture'])test(`human selection invalidates pending ${button}`,async()=>{
  const h=harness();const pending=h.element(button).onclick();
  // Mode has been broadcast, but its HTTP response remains in flight.
  h.publish(h.requests[0]);
  const human=h.element('human').onclick();h.complete(h.requests[1]);await human;
  h.respond(h.requests[0]);await pending;
  assert.equal(h.intervals.size,0);
  assert.equal(h.requests.filter(r=>r.path==='/api/performance').length,0);
});

test('cancellation after own mode reset invalidates a pending preview',async()=>{
  const h=harness();const gesture=h.element('gesture').onclick();
  h.publish(h.requests[0]);h.emit({type:'cancel_speech'});
  h.respond(h.requests[0]);await gesture;
  assert.equal(h.requests.length,1);
});

test('a running demo stops on human mode and never sends stale frames',async()=>{
  const h=harness();const demo=h.element('demo').onclick();
  h.complete(h.requests[0]);await demo;assert.equal(h.intervals.size,1);
  const human=h.element('human').onclick();h.complete(h.requests[1]);await human;
  h.advance(1000);assert.equal(h.intervals.size,0);assert.equal(h.sent.length,0);
});

test('disconnect invalidates a preview waiting for WebSocket acknowledgment',async()=>{
  const h=harness();const gesture=h.element('gesture').onclick();
  h.respond(h.requests[0]);await flush();h.disconnect();await gesture;
  assert.equal(h.requests.length,1);assert.equal(h.intervals.size,0);
  assert.match(h.element('status').textContent,/再接続/);
  // A reconnect's initial state must not revive the cancelled continuation.
  h.emit({type:'state',mode:'ai',parameters:controls.neutral(),performance:{enabled:false,emotion:'neutral'}});
  await flush();assert.equal(h.requests.length,1);
});

test('repeated blink restores the original eyes and ignores stale restoration',()=>{
  const h=harness();h.element('blink').onclick();
  const stale=[...h.timeouts.values()][0].fn;
  h.advance(100);h.element('blink').onclick();stale();
  assert.equal(h.sent.at(-1).parameters.ParamEyeLOpen,0);
  h.advance(400);
  assert.equal(h.sent.at(-1).parameters.ParamEyeLOpen,1);
  assert.equal(h.sent.at(-1).parameters.ParamEyeROpen,1);
});

test('reset cancels pending blink restoration',()=>{
  const h=harness();h.element('blink').onclick();h.element('reset').onclick();
  const count=h.sent.length;h.advance(400);assert.equal(h.sent.length,count);
});

const fakeStream=()=>{
  const track={readyState:'live',stop(){this.readyState='ended';}};
  return{getTracks:()=>[track]};
};
test('rapid microphone starts acquire one stream and mode switch stops it',async()=>{
  const h=harness();const first=h.element('microphone').onclick(),second=h.element('microphone').onclick();
  assert.equal(h.mediaRequests.length,1);
  const stream=fakeStream();h.mediaRequests[0](stream);await Promise.all([first,second]);
  const ai=h.element('ai').onclick();h.complete(h.requests[0]);await ai;
  assert.equal(stream.getTracks()[0].readyState,'ended');
});

test('microphone permission resolving after cancellation stops the late stream',async()=>{
  const h=harness();const pending=h.element('microphone').onclick();
  const ai=h.element('ai').onclick();h.complete(h.requests[0]);await ai;
  const stream=fakeStream();h.mediaRequests[0](stream);await pending;
  assert.equal(stream.getTracks()[0].readyState,'ended');
  assert.equal(h.element('microphone').textContent,'マイク開始');
});

test('microphone can intentionally switch from AI into human mode',async()=>{
  const h=harness();const ai=h.element('ai').onclick();h.complete(h.requests[0]);await ai;
  const mic=h.element('microphone').onclick();h.complete(h.requests[1]);await flush();
  assert.equal(h.mediaRequests.length,1);
  const stream=fakeStream();h.mediaRequests[0](stream);await mic;
  assert.equal(stream.getTracks()[0].readyState,'live');
  await h.element('microphone').onclick();assert.equal(stream.getTracks()[0].readyState,'ended');
});

test('microphone startup tolerates HTTP before human-mode WebSocket state',async()=>{
  const h=harness();const ai=h.element('ai').onclick();h.complete(h.requests[0]);await ai;
  const mic=h.element('microphone').onclick();h.respond(h.requests[1]);await flush();
  assert.equal(h.mediaRequests.length,0);
  h.publish(h.requests[1]);await flush();assert.equal(h.mediaRequests.length,1);
  const stream=fakeStream();h.mediaRequests[0](stream);await mic;
  assert.equal(stream.getTracks()[0].readyState,'live');
});

test('speech playback reports actual playing, pause, resume, and end with ordered sequences',async()=>{
  const h=harness();const ai=h.element('ai').onclick();h.complete(h.requests[0]);await ai;
  h.emit({type:'speech',play:true,text:'test',url:'/speech/test.wav',credit:'TEST',clip_id:'clip1',duration:3});
  const audio=h.element('audio');
  assert.equal(h.requests.length,1); // Synthesis itself must not start the emotion clock.
  audio.fire('playing');audio.currentTime=1;audio.paused=true;audio.fire('pause');
  audio.paused=false;audio.fire('playing');audio.currentTime=3;audio.paused=true;audio.ended=true;audio.fire('ended');
  const reports=h.requests.filter(r=>r.path==='/api/playback').map(r=>r.body);
  assert.deepEqual(reports.map(r=>r.state),['playing','paused','playing','ended']);
  assert.deepEqual(reports.map(r=>r.sequence),[1,2,3,4]);
  assert.deepEqual(reports.map(r=>r.position),[0,1,1,3]);
  assert.ok(reports.every(r=>r.clip_id==='clip1'));
  assert.equal(h.sent.at(-1).parameters.ParamMouthOpenY,0);
});

test('old queued pause/end events do not stop new playing speech',async()=>{
  const h=harness();const ai=h.element('ai').onclick();h.complete(h.requests[0]);await ai;
  h.emit({type:'speech',play:true,text:'old',url:'/old.wav',credit:'TEST',clip_id:'old'});
  h.emit({type:'cancel_speech'});
  h.emit({type:'speech',play:true,text:'new',url:'/new.wav',credit:'TEST',clip_id:'new'});
  const audio=h.element('audio');audio.fire('playing');
  const count=h.requests.length;audio.fire('pause');audio.fire('ended');
  assert.equal(h.requests.length,count);
  h.emit({type:'cancel_speech'});audio.fire('pause');
  assert.equal(h.requests.at(-1).body.clip_id,'new');
  assert.equal(h.requests.at(-1).body.state,'paused');
  assert.equal(h.element('subtitle').textContent,'');
});


test('eight-state picker keeps latest selection and reset explicitly returns neutral',()=>{
  const h=harness();
  for(const id of Object.keys(expressionLabels)){h.element('expression').value=id;h.element('expression').onchange();}
  assert.equal(h.sent.at(-1).expression,'thinking');
  assert.equal(h.sent.at(-1).source,'human');
  assert.equal(h.sent.at(-1).expression_duration,30);
  h.element('reset').onclick();assert.equal(h.sent.at(-1).expression,'neutral');
  assert.equal(h.element('expression').value,'neutral');
});

test('selected closed-eye smile is passed to speech across the AI mode reset',async()=>{
  const h=harness();h.element('expression').value='big_smile';h.element('expression').onchange();
  const pending=h.element('speak').onclick();h.complete(h.requests[0]);await flush();
  assert.equal(h.requests[1].path,'/api/speech');assert.equal(h.requests[1].body.expression,'big_smile');
  h.complete(h.requests[1]);await pending;
});

test('overlapping speech clicks share AI selection and only latest synthesizes',async()=>{
  const h=harness();const first=h.element('speak').onclick(),second=h.element('speak').onclick();
  assert.equal(h.requests.length,1);h.respond(h.requests[0]);await flush();assert.equal(h.requests.length,1);
  h.publish(h.requests[0]);await flush();assert.equal(h.requests.length,2);
  h.complete(h.requests[1]);await Promise.all([first,second]);
  assert.equal(h.requests.filter(request=>request.path==='/api/speech').length,1);
});

for(const button of ['speak','audiofile'])test(`human mode interrupts pending ${button} without stale playback`,async()=>{
  const h=harness();h.element('audiofile').files=[{name:'voice.wav'}];
  const pending=button==='speak'?h.element(button).onclick():h.element(button).onchange();
  h.publish(h.requests[0]);
  const human=h.element('human').onclick();h.complete(h.requests[1]);await human;
  h.respond(h.requests[0]);await pending;
  assert.equal(h.requests.length,2);assert.equal(h.element('audio').paused,true);
});

test('disconnected expression picker reports the problem instead of queueing stale state',()=>{
  const h=harness();h.disconnect();h.element('expression').value='worried';h.element('expression').onchange();
  assert.equal(h.sent.length,0);assert.match(h.element('status').textContent,/接続/);
});


test('disconnect clears selected face, stops audible speech and closes local mouth',async()=>{
  const h=harness();const ai=h.element('ai').onclick();h.complete(h.requests[0]);await ai;
  h.element('expression').value='surprised';h.element('expression').onchange();
  h.emit({type:'speech',play:true,text:'test',url:'/speech/test.wav',credit:'TEST',clip_id:'clip1'});
  assert.equal(h.element('audio').paused,false);
  h.disconnect();assert.equal(h.element('audio').paused,true);
  assert.equal(h.element('expression').value,'neutral');assert.equal(h.element('subtitle').textContent,'');
});


test('camera permission resolving after AI then human override cannot revive old tracking',async()=>{
  const h=harness();h.prepareCamera();const camera=h.element('camera').onclick();
  assert.equal(h.mediaRequests.length,1);
  const ai=h.element('ai').onclick();h.complete(h.requests[0]);await ai;
  const human=h.element('human').onclick();h.complete(h.requests[1]);await human;
  const stream=fakeStream();h.mediaRequests[0](stream);await camera;
  assert.equal(stream.getTracks()[0].readyState,'ended');assert.equal(h.element('video').srcObject,null);
});

test('camera startup waits for both mode acknowledgments and repeated clicks acquire one stream',async()=>{
  const h=harness();h.prepareCamera();const ai=h.element('ai').onclick();h.complete(h.requests[0]);await ai;
  const first=h.element('camera').onclick(),second=h.element('camera').onclick();
  assert.equal(h.requests.length,2);h.respond(h.requests[1]);await flush();assert.equal(h.mediaRequests.length,0);
  h.publish(h.requests[1]);await flush();assert.equal(h.mediaRequests.length,1);
  const stream=fakeStream();h.mediaRequests[0](stream);await Promise.all([first,second]);
  assert.equal(stream.getTracks()[0].readyState,'live');assert.equal(h.element('video').srcObject,stream);
});


test('new picker choice wins over an audiofile awaiting its AI-mode response',async()=>{
  const h=harness();h.element('expression').value='big_smile';h.element('expression').onchange();
  h.element('audiofile').files=[{name:'voice.wav'}];const pending=h.element('audiofile').onchange();
  h.publish(h.requests[0]);h.element('expression').value='thinking';h.element('expression').onchange();
  h.respond(h.requests[0]);await pending;
  assert.equal(h.sent.at(-1).expression,'thinking');assert.equal(h.requests.length,1);
  assert.equal(h.element('audio').paused,false);
});

test('manual eye change during blink cancels stale restoration and restores only the other eye',()=>{
  const h=harness();h.element('blink').onclick();const stale=[...h.timeouts.values()][0].fn;
  const input=h.slider('ParamEyeLOpen');input.value=.4;input.oninput();
  assert.equal(h.sent.at(-1).parameters.ParamEyeLOpen,.4);assert.equal(h.sent.at(-1).parameters.ParamEyeROpen,1);
  const count=h.sent.length;stale();h.advance(400);assert.equal(h.sent.length,count);
});


test('superseded speech responses do not overwrite the newer UI status',async()=>{
  for(const ok of [true,false]){
    const h=harness();const speech=h.element('speak').onclick();h.complete(h.requests[0]);await flush();
    const human=h.element('human').onclick();h.complete(h.requests[2]);await human;
    h.element('status').textContent='newer operation';
    h.requests[1].resolve({ok,status:409,json:async()=>({}),text:async()=> 'speech was superseded or cancelled'});
    await speech;assert.equal(h.element('status').textContent,'newer operation');
  }
});

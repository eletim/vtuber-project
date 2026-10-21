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
      value:'auto',checked:true,textContent:'',dataset:{},disabled:false,paused:true,ended:false,currentTime:0,playbackRate:1,readyState:4,seeking:false,error:null,src:'',files:[],listeners:{},
      classList:{toggle(){},add(){},remove(){}},append(){},
      addEventListener(type,callback){(this.listeners[type]||=[]).push(callback);},
      fire(type){for(const callback of this.listeners[type]||[])callback();},
      pause(){this.paused=true;},play(){this.paused=false;this.ended=false;return Promise.resolve();},
      removeAttribute(name){if(name==='src')this.src='';},load(){this.currentTime=0;this.ended=false;},
      querySelector(){return{value:0,nextElementSibling:{value:0}};}
    });
    return elements.get(id);
  }
  const context=vm.createContext({
    ...controls,PerformanceMotion,expressionLabels,AvatarRenderer:class{},console,Date,URLSearchParams,AbortController,
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
    fetch:(path,options={})=>new Promise((resolve,reject)=>{
      const request={path,body:options.body?JSON.parse(options.body):undefined,signal:options.signal,resolve,reject};
      requests.push(request);
      options.signal?.addEventListener('abort',()=>{if(!request.ignoreAbort)reject(options.signal.reason);});
    }),
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
      emit({type:'cancel_speech',reason:'mode_change'});
    }else if(request.path==='/api/performance'){
      state.performance={...state.performance,...request.body};
    }
    emit({type:'state',...state});
  }
  function respond(request){request.resolve({ok:true,json:async()=>({...state})});}
  function complete(request){publish(request);respond(request);}
  emit({type:'state',...state});
  return{element,requests,intervals,timeouts,sent,mediaRequests,emit,publish,respond,complete,
    reconnect:()=>{vm.runInContext('connect();',context);emit({type:'state',...state});},
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
    const human=h.element('human').onclick();h.complete(h.requests.findLast(request=>request.path==='/api/mode'));await human;
    h.element('status').textContent='newer operation';
    h.requests[1].resolve({ok,status:409,json:async()=>({}),text:async()=> 'speech was superseded or cancelled'});
    await speech;assert.equal(h.element('status').textContent,'newer operation');
  }
});


// v20: request-scoped text synthesis, real audio lifecycle, and engine health.
async function beginSynthesis(h,text='新しい文章です。'){
  h.element('speech').value=text;
  const pending=h.element('speak').onclick();
  h.complete(h.requests.findLast(request=>request.path==='/api/mode'));await flush();
  const request=h.requests.findLast(request=>request.path==='/api/speech');
  return{pending,request};
}
function speechEvent(request,overrides={}){
  return{type:'speech',play:true,text:request.body.text,request_id:request.body.request_id,url:'/speech/fresh.wav',clip_id:'fresh',credit:'VOICEVOX:雨晴はう',...overrides};
}
function resolveJSON(request,data){request.resolve({ok:true,json:async()=>data});}

for(const ordering of ['before-mode','http-first','ws-first'])test(`Stop ${ordering} prevents synthesis without requesting human mode`,async()=>{
  const h=harness();const pending=h.element('speak').onclick(),request=h.requests[0];
  if(ordering==='http-first')h.respond(request);
  if(ordering==='ws-first')h.publish(request);
  h.element('stop-speech').onclick();
  assert.equal(h.element('audio').paused,true);assert.equal(h.element('audio').src,'');
  assert.equal(h.element('stop-speech').disabled,true);
  h.complete(request);await pending;
  assert.equal(h.requests.filter(r=>r.path==='/api/speech').length,0);
  assert.ok(h.requests.filter(r=>r.path==='/api/mode').every(r=>r.body.mode==='ai'));
  assert.equal(h.element('audio-status').dataset.state,'stopped');
});

test('retry immediately after Stop shares the unfinished AI selection and only new text synthesizes',async()=>{
  const h=harness();const first=h.element('speak').onclick();
  h.element('stop-speech').onclick();h.element('speech').value='新しい発話';
  const latest=h.element('speak').onclick();
  assert.equal(h.requests.length,1);h.complete(h.requests[0]);await flush();
  assert.equal(h.requests.filter(r=>r.path==='/api/speech').length,1);
  const speech=h.requests.at(-1);assert.equal(speech.body.text,'新しい発話');
  resolveJSON(speech,{});await Promise.all([first,latest]);
});

for(const outcome of ['success','failure'])test(`Stop aborts pending synthesis and ignores late ${outcome} and its WS event`,async()=>{
  const h=harness();const {pending,request}=await beginSynthesis(h);
  request.ignoreAbort=true;h.element('stop-speech').onclick();
  assert.equal(request.signal.aborted,true);
  const cancellation=h.requests.find(r=>r.path==='/api/speech/cancel');
  assert.deepEqual(cancellation.body,{request_id:request.body.request_id});
  assert.equal(h.element('audio-status').dataset.state,'stopped');
  if(outcome==='success')resolveJSON(request,speechEvent(request));
  else request.resolve({ok:false,status:503,text:async()=> 'late failure'});
  await pending;h.emit(speechEvent(request));
  assert.equal(h.element('audio').src,'');assert.equal(h.element('subtitle').textContent,'');
  assert.equal(h.element('audio-status').dataset.state,'stopped');
  assert.equal(h.element('stop-speech').disabled,true);
});

test('own superseded broadcast preserves the pending request, followed by ready and playing feedback',async()=>{
  const h=harness();const {pending,request}=await beginSynthesis(h);
  assert.equal(h.element('audio-status').dataset.state,'generating');
  h.emit({type:'cancel_speech',reason:'superseded',request_id:request.body.request_id});
  assert.equal(request.signal.aborted,false);assert.equal(h.element('stop-speech').disabled,false);
  h.emit(speechEvent(request));assert.equal(h.element('audio-status').dataset.state,'ready');
  h.element('audio').fire('playing');assert.equal(h.element('audio-status').dataset.state,'playing');
  resolveJSON(request,speechEvent(request));await pending;
  assert.equal(h.element('audio-status').dataset.state,'playing');
  assert.match(h.element('audio-status').textContent,/入力文から生成/);
});

for(const phase of ['ready','playing'])test(`Stop clears a ${phase} generated source and late play rejection cannot restore it`,async()=>{
  const h=harness();const {pending,request}=await beginSynthesis(h);
  let rejectPlay;h.element('audio').play=function(){this.paused=false;return new Promise((_,reject)=>{rejectPlay=reject;});};
  h.emit(speechEvent(request));if(phase==='playing')h.element('audio').fire('playing');
  h.element('stop-speech').onclick();rejectPlay(Error('old autoplay failure'));await pending;await flush();
  assert.equal(h.element('audio').src,'');assert.equal(h.element('audio').paused,true);
  assert.equal(h.element('audio-status').dataset.state,'stopped');
  h.emit(speechEvent(request));h.element('audio').fire('playing');
  assert.equal(h.element('audio-status').dataset.state,'stopped');
});

test('new generation cannot be cancelled or overwritten by an old scoped response/event',async()=>{
  const h=harness();const old=await beginSynthesis(h,'古い文章');old.request.ignoreAbort=true;
  const latest=await beginSynthesis(h,'新しい文章');
  assert.equal(old.request.signal.aborted,true);
  assert.notEqual(old.request.body.request_id,latest.request.body.request_id);
  h.emit({type:'cancel_speech',reason:'stopped',request_id:old.request.body.request_id});
  h.emit({type:'cancel_speech',reason:'superseded',request_id:old.request.body.request_id});
  h.emit(speechEvent(old.request));
  assert.equal(h.element('audio').src,'');assert.equal(latest.request.signal.aborted,false);
  h.emit(speechEvent(latest.request,{clip_id:'latest',url:'/latest.wav'}));h.element('audio').fire('playing');
  resolveJSON(old.request,speechEvent(old.request));resolveJSON(latest.request,speechEvent(latest.request));
  await Promise.all([old.pending,latest.pending]);
  assert.equal(h.element('audio').src,'/latest.wav');assert.equal(h.element('subtitle').textContent,'新しい文章');
  assert.equal(h.element('audio-status').dataset.state,'playing');
});

for(const action of ['human','reset','disconnect'])test(`${action} cancels in-flight synthesis immediately and ignores late speech`,async()=>{
  const h=harness();const {pending,request}=await beginSynthesis(h);
  if(action==='disconnect')h.disconnect();else h.element(action).onclick();
  assert.equal(request.signal.aborted,true);await pending;
  h.emit(speechEvent(request));assert.equal(h.element('audio').paused,true);assert.equal(h.element('audio').src,'');
  assert.equal(h.element('audio-status').dataset.state,'stopped');
});

test('disconnect then reconnect allows a new request but never revives old speech',async()=>{
  const h=harness();const first=await beginSynthesis(h);h.disconnect();await first.pending;
  h.reconnect();const latest=await beginSynthesis(h,'接続後の新しい文章');
  h.emit(speechEvent(first.request));assert.equal(h.element('audio').src,'');
  h.emit(speechEvent(latest.request,{clip_id:'reconnected'}));resolveJSON(latest.request,{});await latest.pending;
  assert.equal(h.element('subtitle').textContent,'接続後の新しい文章');assert.equal(h.element('audio').paused,false);
});

test('synthesis errors show provider instructions, allow retry, and never fall back to a saved clip',async()=>{
  const h=harness();const first=await beginSynthesis(h);
  first.request.resolve({ok:false,status:503,text:async()=> 'VOICEVOXを起動してください。'});await first.pending;
  assert.match(h.element('audio-status').textContent,/VOICEVOXを起動してください/);
  assert.equal(h.element('audio-status').dataset.state,'error');assert.equal(h.element('audio').src,'');
  assert.equal(h.element('stop-speech').disabled,true);
  const latest=await beginSynthesis(h);h.emit(speechEvent(latest.request));resolveJSON(latest.request,{});await latest.pending;
  assert.equal(h.element('audio').paused,false);assert.equal(h.element('audio-status').dataset.state,'ready');
});

test('empty input is explained without switching mode or making a synthesis request',async()=>{
  const h=harness();h.element('speech').value='  ';await h.element('speak').onclick();
  assert.equal(h.requests.length,0);assert.equal(h.element('audio-status').dataset.state,'error');
});

test('uploaded audio is labeled as saved media, not generated speech, and Stop clears its source',async()=>{
  const h=harness();h.element('audiofile').files=[{name:'saved.wav'}];
  const pending=h.element('audiofile').onchange();h.complete(h.requests[0]);await pending;
  assert.match(h.element('audio-status').textContent,/保存済み音声ファイル/);
  assert.match(h.element('audio-status').textContent,/文章からの音声生成ではありません/);
  assert.equal(h.requests.filter(r=>r.path==='/api/speech').length,0);
  h.element('audio').fire('playing');assert.match(h.element('audio-status').textContent,/保存済み音声ファイル/);
  h.element('stop-speech').onclick();assert.equal(h.element('audio').src,'');
  assert.equal(h.requests.filter(r=>r.path==='/api/speech\/cancel').length,0);
});

test('a file replacing synthesis ignores its old generated event and never gains generated credit',async()=>{
  const h=harness();const first=await beginSynthesis(h);
  h.element('audiofile').files=[{name:'saved.wav'}];const file=h.element('audiofile').onchange();
  h.complete(h.requests.findLast(r=>r.path==='/api/mode'));await file;await first.pending;
  h.emit(speechEvent(first.request));assert.equal(h.element('audio').src,'blob:test');
  assert.match(h.element('audio-status').textContent,/保存済み音声ファイル/);
  assert.doesNotMatch(h.element('audio-status').textContent,/VOICEVOX/);
});

test('seeking, buffering, rate changes and audio failure report actual playback to the server',async()=>{
  const h=harness();const {pending,request}=await beginSynthesis(h);
  h.emit(speechEvent(request));resolveJSON(request,{});await pending;
  const audio=h.element('audio');audio.fire('playing');audio.currentTime=.5;audio.seeking=true;audio.fire('seeking');
  audio.currentTime=1;audio.seeking=false;audio.fire('seeked');audio.playbackRate=1.5;audio.fire('ratechange');
  audio.readyState=2;audio.fire('waiting');audio.readyState=4;audio.fire('playing');audio.error={code:3};audio.fire('error');
  const reports=h.requests.filter(r=>r.path==='/api/playback').map(r=>r.body);
  assert.deepEqual(reports.map(r=>r.state),['playing','paused','playing','playing','paused','playing','paused']);
  assert.equal(reports[3].playback_rate,1.5);assert.equal(reports[2].position,1);
  assert.deepEqual(reports.map(r=>r.sequence),[1,2,3,4,5,6,7]);
  assert.equal(h.element('audio-status').dataset.state,'error');
});

test('engine health check displays availability and stale checks cannot overwrite the latest result',async()=>{
  const h=harness();const old=h.element('check-voice').onclick(),first=h.requests[0];first.ignoreAbort=true;
  const latest=h.element('check-voice').onclick();assert.equal(first.signal.aborted,true);
  resolveJSON(h.requests[1],{available:true,provider:'VOICEVOX',credit:'VOICEVOX:雨晴はう',version:'1.0'});await latest;
  resolveJSON(first,{available:false,message:'old unavailable'});await old;
  assert.match(h.element('voice-status').textContent,/利用可能.*雨晴はう.*v1.0/);
  assert.doesNotMatch(h.element('voice-status').textContent,/old/);
  const unavailable=h.element('check-voice').onclick();resolveJSON(h.requests.at(-1),{available:false,message:'VOICEVOXを起動してください。'});await unavailable;
  assert.match(h.element('voice-status').textContent,/利用できません.*VOICEVOXを起動/);
});

test('failed engine health check offers a retry without changing speech state',async()=>{
  const h=harness();const check=h.element('check-voice').onclick();h.requests[0].reject(Error('offline'));await check;
  assert.match(h.element('voice-status').textContent,/確認できません/);
  const retry=h.element('check-voice').onclick();resolveJSON(h.requests[1],{available:true,credit:'VOICEVOX:雨晴はう'});await retry;
  assert.match(h.element('voice-status').textContent,/利用可能/);assert.equal(h.element('audio').src,'');
});


test('old queued error, waiting and seeking events do not pause healthy replacement audio',async()=>{
  const h=harness();const {pending,request}=await beginSynthesis(h);
  h.emit(speechEvent(request));resolveJSON(request,{});await pending;h.element('audio').fire('playing');
  const count=h.requests.length;
  for(const event of ['error','waiting','seeking'])h.element('audio').fire(event);
  assert.equal(h.requests.length,count);assert.equal(h.element('audio-status').dataset.state,'playing');
});

test('Stop is available while a saved file awaits AI-mode selection',async()=>{
  const h=harness();h.element('audiofile').files=[{name:'saved.wav'}];
  const pending=h.element('audiofile').onchange();assert.equal(h.element('stop-speech').disabled,false);
  h.element('stop-speech').onclick();h.complete(h.requests[0]);await pending;
  assert.equal(h.element('audio').src,'');assert.equal(h.element('stop-speech').disabled,true);
  assert.equal(h.element('audio-status').dataset.state,'stopped');
});

test('stale controller-disconnect cancellation does not stop a newer local synthesis',async()=>{
  const h=harness();const {pending,request}=await beginSynthesis(h);
  h.emit({type:'cancel_speech',reason:'controller_disconnected',request_id:'some-other-old-controller'});
  assert.equal(request.signal.aborted,false);
  h.emit(speechEvent(request));resolveJSON(request,{});await pending;
  assert.equal(h.element('audio').paused,false);
});


test('confirmed WS playback wins over a late HTTP transport error and duplicate speech event',async()=>{
  const h=harness();const {pending,request}=await beginSynthesis(h);
  h.emit(speechEvent(request));h.element('audio').fire('playing');h.element('audio').currentTime=1;
  const count=h.requests.length;h.emit(speechEvent(request));
  assert.equal(h.requests.length,count);assert.equal(h.element('audio').currentTime,1);
  request.reject(Error('HTTP response disconnected'));await pending;
  assert.equal(h.element('audio').paused,false);assert.equal(h.element('audio-status').dataset.state,'playing');
});


for(const name of ['NotAllowedError','NotSupportedError','NetworkError'])test(`${name} explains autoplay vs actual generated audio failure`,async()=>{
  const h=harness();const {pending,request}=await beginSynthesis(h);
  h.element('audio').play=()=>Promise.reject(Object.assign(Error('audio playback failed'),{name}));
  h.emit(speechEvent(request));resolveJSON(request,{});await pending;await flush();
  if(name==='NotAllowedError'){
    assert.equal(h.element('audio-status').dataset.state,'ready');assert.match(h.element('audio-status').textContent,/再生ボタン/);
  }else{
    assert.equal(h.element('audio-status').dataset.state,'error');assert.doesNotMatch(h.element('audio-status').textContent,/再生ボタン/);
  }
});

test('an audio decode error is not overwritten by later autoplay rejection advice',async()=>{
  const h=harness();const {pending,request}=await beginSynthesis(h);
  let rejectPlay;h.element('audio').play=()=>new Promise((_,reject)=>{rejectPlay=reject;});
  h.emit(speechEvent(request));const audio=h.element('audio');audio.error={code:3};audio.fire('error');
  rejectPlay(Object.assign(Error('not allowed'),{name:'NotAllowedError'}));resolveJSON(request,{});await pending;await flush();
  assert.equal(h.element('audio-status').dataset.state,'error');assert.doesNotMatch(h.element('audio-status').textContent,/再生ボタン/);
});


for(const reason of ['stopped','controller_disconnected'])test(`${reason} tombstones an external request before its delayed first speech event`,async()=>{
  const h=harness();const ai=h.element('ai').onclick();h.complete(h.requests[0]);await ai;
  const request_id='external-ai-client-utterance';
  h.emit({type:'cancel_speech',reason,request_id});
  h.emit({type:'state',mode:'ai',parameters:controls.neutral(),performance:{enabled:true,emotion:'neutral'},speech:{phase:'idle'}});
  h.emit({type:'speech',play:true,request_id,text:'cancelled external speech',clip_id:'late-external',url:'/late-external.wav',credit:'VOICEVOX:雨晴はう'});
  assert.equal(h.element('audio').src,'');assert.equal(h.element('audio').paused,true);
  assert.equal(h.element('subtitle').textContent,'');
  assert.equal(h.requests.filter(r=>r.path==='/api/playback').length,0);
});

test('tombstoning an unseen external stop neither cancels nor blocks a different new utterance',async()=>{
  const h=harness();const {pending,request}=await beginSynthesis(h);
  h.emit({type:'cancel_speech',reason:'stopped',request_id:'external-old'});
  assert.equal(request.signal.aborted,false);
  h.emit(speechEvent(request));resolveJSON(request,{});await pending;
  h.emit({type:'speech',play:true,request_id:'external-old',text:'late',clip_id:'late',url:'/late.wav',credit:'VOICEVOX:雨晴はう'});
  assert.equal(h.element('audio').src,'/speech/fresh.wav');assert.equal(h.element('audio').paused,false);
});

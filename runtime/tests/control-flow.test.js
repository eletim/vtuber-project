import test from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import {readFileSync} from 'node:fs';
import * as controls from '../web/controls.js';
import {performancePose} from '../web/performance.js';

// Exercise the real UI handlers without WebGL, a media device, or wall-clock waits.
const source=readFileSync(new URL('../web/app.js',import.meta.url),'utf8')
  .replace(/^import .*;\n/gm,'')
  .replace(/^try\{await renderer\.load.*$/m,'');
const flush=()=>new Promise(resolve=>setImmediate(resolve));
function harness(){
  const elements=new Map(),requests=[],intervals=new Map(),timeouts=new Map(),sent=[],mediaRequests=[];
  let sequence=0,now=0,socket;
  let state={mode:'human',parameters:controls.neutral(),performance:{enabled:false,emotion:'neutral'}};
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
    ...controls,performancePose,AvatarRenderer:class{},console,Date,URLSearchParams,
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
      send(data){const message=JSON.parse(data);sent.push(message);if(message.source===state.mode){Object.assign(state.parameters,message.parameters);emit({type:'state',...state});}}
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
      state={...state,mode:request.body.mode,parameters:controls.neutral()};
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
    disconnect:()=>{socket.readyState=3;socket.onclose();},
    advance:time=>{now=time;for(const callback of [...intervals.values()])callback();for(const [id,timer] of [...timeouts])if(timer.at<=now){timeouts.delete(id);timer.fn();}}};
}

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

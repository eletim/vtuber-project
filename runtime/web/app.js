import {performancePose} from './performance.js';
import {AvatarRenderer} from './renderer.js';
import {limits,neutral,faceParameters,rmsMouth,smoothParameters,clamp} from './controls.js';
const $=id=>document.getElementById(id);
const renderer=new AvatarRenderer();
let mode='human',target=neutral(),current=neutral(),ws,cameraStream,micStream,landmarker,tracking=false;
let cameraPending=false,audioContext,micAnalyser,fileAnalyser,fileSource,audioURL;
let manualBlink=0,blinkTimer,blinkRestore,blinkGeneration=0,lastFaceAt=0,frameStamp=0,lastSent=0;
let micRequest;
let activeSpeech;
let demoTimer,connectionTimer;
let motionAction,aiModeRequest;
let manualActive=false,performanceState={enabled:true,emotion:'neutral'};
const sliders={};
const names={ParamAngleX:'顔・左右',ParamAngleY:'顔・上下',ParamAngleZ:'顔・傾き',ParamBodyAngleX:'体・左右',ParamEyeLOpen:'左目',ParamEyeROpen:'右目',ParamMouthOpenY:'口の開き'};
const status=text=>$('status').textContent=text;
async function post(path,body){const r=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});if(!r.ok){const error=Error(await r.text());error.status=r.status;throw error;}return r.json();}
function report(error){console.error(error);status(error.message||String(error));}
function stopMotionAction(invalidateSelection=true){motionAction=null;clearInterval(demoTimer);demoTimer=undefined;if(invalidateSelection){aiModeRequest?.resolveState();aiModeRequest=null;}}
function beginMotionAction(){stopMotionAction(false);cancelSpeech();return motionAction={awaitingAI:true};}
async function selectAIForMotion(action){
  if(ws?.readyState!==1)throw Error('接続が切れています。再接続後にもう一度お試しください。');
  // Repeated clicks share the pending mode request, but only the latest action continues.
  if(!aiModeRequest){
    aiModeRequest={cancelExpected:true};
    aiModeRequest.statePromise=new Promise(resolve=>{aiModeRequest.resolveState=resolve;});
    aiModeRequest.promise=post('/api/mode',{mode:'ai'});
  }
  const request=aiModeRequest;
  // HTTP and WebSocket are independent transports: wait for both acknowledgments.
  try{await Promise.all([request.promise,request.statePromise]);}finally{if(aiModeRequest===request)aiModeRequest=null;}
  if(motionAction!==action)return false;
  action.awaitingAI=false;return true;
}
function send(parameters,source=mode){if(ws?.readyState===1)ws.send(JSON.stringify({source,parameters,ttl_ms:2000}));}
function connect(){
  ws=new WebSocket(`${location.protocol==='https:'?'wss':'ws'}://${location.host}/ws?role=${new URLSearchParams(location.search).has('overlay')?'overlay':'controller'}`);
  ws.onopen=()=>{$('connection').textContent='● 接続済み';};
  ws.onclose=()=>{if(motionAction)status('接続が切れたため操作を中止しました。再接続後にもう一度お試しください。');stopMotionAction();if(micRequest)stopMic();$('connection').textContent='再接続中…';connectionTimer=setTimeout(connect,1200);};
  ws.onmessage=({data})=>{
    const event=JSON.parse(data);
    if(event.type==='state'){
      const changed=mode!==event.mode;
      mode=event.mode;target={...event.parameters};performanceState={...event.performance};
      $('lively').checked=performanceState.enabled;
      const expectedAI=mode==='ai'&&motionAction?.awaitingAI;
      if(mode==='ai'&&aiModeRequest&&!aiModeRequest.cancelExpected)aiModeRequest.resolveState();
      if(mode==='human'&&micRequest?.awaitingHuman)micRequest.resolveState?.();
      if(changed&&!expectedAI)stopMotionAction();
      if(changed){manualActive=false;stopBlink();stopCamera();stopMic(!(mode==='human'&&micRequest?.awaitingHuman));cancelSpeech();$('audio').pause();}
      $('human').classList.toggle('selected',mode==='human');$('ai').classList.toggle('selected',mode==='ai');
      $('mode-label').textContent=mode==='human'?'人間操作':'AI操作';
      $('hint').textContent=mode==='human'?'スライダー・カメラ・マイクで動かせます。':'AIの指示・発話音声で動きます。';
      for(const [key,input] of Object.entries(sliders)){input.value=target[key];input.nextElementSibling.value=target[key].toFixed(2);}
    }
    if(event.type==='speech'&&mode==='ai'){
      $('subtitle').textContent=event.text;
      if(event.play)playSpeech(event).catch(report);
    }
    if(event.type==='cancel_speech'){
      if(aiModeRequest?.cancelExpected)aiModeRequest.cancelExpected=false;else stopMotionAction();
      cancelSpeech();
    }
    if(event.type==='error')status(event.message);
  };
}
for(const [key,label] of Object.entries(names)){
  const [min,max,def]=limits[key];const row=document.createElement('label');row.className='slider';
  row.innerHTML=`<span>${label}</span><input aria-label="${label}" type="range" min="${min}" max="${max}" step="0.01" value="${def}"><output>${def.toFixed(2)}</output>`;
  const input=row.querySelector('input');sliders[key]=input;
  input.oninput=()=>{manualActive=true;target[key]=Number(input.value);input.nextElementSibling.value=Number(input.value).toFixed(2);send({[key]:Number(input.value)});};
  $('sliders').append(row);
}
for(const next of ['human','ai'])$(next).onclick=()=>{stopMotionAction();stopBlink();if(micRequest)stopMic();return post('/api/mode',{mode:next}).catch(report);};
$('reset').onclick=()=>{stopBlink();manualActive=false;target=neutral();send(target);};
function stopBlink(){clearTimeout(blinkTimer);blinkGeneration++;blinkRestore=null;manualBlink=0;}
$('blink').onclick=()=>{
  manualBlink=performance.now()+220;
  const source=mode;
  if(!blinkRestore)blinkRestore={ParamEyeLOpen:target.ParamEyeLOpen,ParamEyeROpen:target.ParamEyeROpen};
  const eyes=blinkRestore,generation=++blinkGeneration;clearTimeout(blinkTimer);
  send({ParamEyeLOpen:0,ParamEyeROpen:0},source);
  blinkTimer=setTimeout(()=>{if(generation!==blinkGeneration)return;blinkRestore=null;if(mode===source)send(eyes,source);},220);
};

function stopCamera(){cameraStream?.getTracks().forEach(t=>t.stop());cameraStream=null;tracking=false;lastFaceAt=0;$('video').srcObject=null;$('video').hidden=true;$('camera').textContent='カメラ開始';updateTracking();}
function stopMic(invalidateRequest=true){if(invalidateRequest){micRequest?.resolveState?.();micRequest=null;}micStream?.getTracks().forEach(t=>t.stop());micStream=null;micAnalyser=null;$('microphone').textContent='マイク開始';updateTracking();}
function updateTracking(){$('tracking').textContent=`カメラ: ${tracking?'追跡中':'停止'} / マイク: ${micStream?'入力中':'停止'}`;}
function context(){audioContext ||= new AudioContext();audioContext.resume();return audioContext;}
$('camera').onclick=async()=>{
  if(cameraStream){stopCamera();send(neutral(),'human');return;}
  if(cameraPending)return;
  cameraPending=true;
  try {
    if(mode!=='human')await post('/api/mode',{mode:'human'});
    status('顔追跡モデルを読み込んでいます…');
    manualActive=false;
    if(!landmarker){
      const {FaceLandmarker,FilesetResolver}=await import('/vendor/vision_bundle.mjs');
      const files=await FilesetResolver.forVisionTasks('/vendor/wasm');
      landmarker=await FaceLandmarker.createFromOptions(files,{baseOptions:{modelAssetPath:'/vendor/face_landmarker.task'},runningMode:'VIDEO',numFaces:1,outputFaceBlendshapes:true});
    }
    cameraStream=await navigator.mediaDevices.getUserMedia({video:{width:640,height:480},audio:false});
    if(mode!=='human'){stopCamera();return;}
    $('video').srcObject=cameraStream;await $('video').play();$('video').hidden=false;
    tracking=true;$('camera').textContent='カメラ停止';updateTracking();status('顔の向き・目・口を追跡しています。');
  }catch(error){stopCamera();report(error);}finally{cameraPending=false;}
};
$('microphone').onclick=async()=>{
  if(micStream){stopMic();send({ParamMouthOpenY:0},'human');return;}
  if(micRequest)return;
  const request=micRequest={awaitingHuman:mode!=='human'};
  try {
    if(request.awaitingHuman){
      const statePromise=new Promise(resolve=>{request.resolveState=resolve;});
      await Promise.all([post('/api/mode',{mode:'human'}),statePromise]);
    }
    if(micRequest!==request)return;
    request.awaitingHuman=false;
    const stream=await navigator.mediaDevices.getUserMedia({audio:true,video:false});
    if(micRequest!==request||mode!=='human'){stream.getTracks().forEach(t=>t.stop());return;}
    micStream=stream;
    micAnalyser=context().createAnalyser();micAnalyser.fftSize=1024;
    context().createMediaStreamSource(micStream).connect(micAnalyser);
    $('microphone').textContent='マイク停止';updateTracking();
  }catch(error){if(micRequest===request){stopMic();report(error);}}
  finally{if(micRequest===request)micRequest=null;}
};
function reportPlayback(state,speech=activeSpeech,position=$('audio').currentTime){
  if(!speech?.clip_id)return;
  post('/api/playback',{clip_id:speech.clip_id,state,position,sequence:++speech.sequence})
    .catch(error=>{if(error.status!==409&&activeSpeech===speech)report(error);});
}
function cancelSpeech(){const speech=activeSpeech;activeSpeech=null;if(speech)reportPlayback('paused',speech);$('audio').pause();$('subtitle').textContent='';}
function prepareAudio(){
  if(!fileSource){fileSource=context().createMediaElementSource($('audio'));fileAnalyser=context().createAnalyser();fileAnalyser.fftSize=1024;fileSource.connect(fileAnalyser);fileAnalyser.connect(context().destination);}
}
async function playSpeech(event){
  prepareAudio();const speech=activeSpeech={clip_id:event.clip_id,sequence:0};$('audio').src=event.url;
  $('audio-status').textContent=event.credit+' · 実際の音量でリップシンク';
  try{await $('audio').play();}catch(e){if(activeSpeech===speech)$('audio-status').textContent=event.credit+' · 下の再生ボタンを押して音声を有効にしてください。';}
}
$('speak').onclick=async()=>{stopMotionAction();try{prepareAudio();await post('/api/mode',{mode:'ai'});status('音声を合成しています…');await post('/api/speech',{text:$('speech').value,emotion:$('emotion').value});status('音声を生成しました。');}catch(e){report(e);}};
$('lively').onchange=()=>post('/api/performance',{enabled:$('lively').checked}).catch(report);
$('gesture').onclick=async()=>{
  const action=beginMotionAction(),emotion=$('emotion').value==='auto'?'happy':$('emotion').value;
  try{
    if(!await selectAIForMotion(action))return;
    await post('/api/performance',{enabled:true,emotion,duration:4});
  }catch(error){if(motionAction===action)report(error);}
};
$('demo').onclick=async()=>{
  const action=beginMotionAction();
  try{
    if(!await selectAIForMotion(action))return;
    const start=performance.now();
    const timer=setInterval(()=>{const t=(performance.now()-start)/1000;
      if(motionAction!==action||mode!=='ai'||t>14){
        clearInterval(timer);if(demoTimer===timer)demoTimer=undefined;
        if(motionAction===action&&mode==='ai'){motionAction=null;send(neutral(),'ai');}
        return;
      }
      send({ParamAngleX:Math.sin(t)*10,ParamAngleZ:Math.sin(t*.7)*4,ParamBodyAngleX:Math.sin(t*.5)*2,ParamMouthOpenY:.4+.4*Math.sin(t*9)},'ai');
    },80);
    demoTimer=timer;
  }catch(error){if(motionAction===action)report(error);}
};
$('audio').addEventListener('playing',()=>{if(mode==='ai'&&!$('audio').paused)reportPlayback('playing');});
for(const event of ['pause','ended'])$('audio').addEventListener(event,()=>{
  if(event==='pause'&&!$('audio').paused||event==='ended'&&!$('audio').ended)return;
  if(mode==='ai'){target.ParamMouthOpenY=0;send({ParamMouthOpenY:0},'ai');reportPlayback(event==='pause'?'paused':'ended');}
});
$('audiofile').onchange=async()=>{
  const file=$('audiofile').files[0];if(!file)return;
  stopMotionAction();
  try{
    await post('/api/mode',{mode:'ai'});cancelSpeech();clearInterval(demoTimer);
    if(audioURL)URL.revokeObjectURL(audioURL);audioURL=URL.createObjectURL(file);$('audio').src=audioURL;
    prepareAudio();
    await $('audio').play();$('audio-status').textContent='音声の実際の音量で口を動かしています。';
  }catch(e){report(e);}
};
$('background').onchange=()=>{document.body.classList.remove('green','transparent');if($('background').value!=='studio')document.body.classList.add($('background').value);};
if(new URLSearchParams(location.search).has('overlay'))document.body.classList.add('overlay');
let last=0,lastTrack=0,frames=0,fpsTime=0;
const samples=new Float32Array(1024);
function tick(now){
  const dt=Math.min(.1,(now-last)/1000||.016);last=now;
  if(tracking&&$('video').readyState>=2&&now-lastTrack>70){
    try{
      const result=landmarker.detectForVideo($('video'),now);lastTrack=now;
      const face=faceParameters(result);
      if(face){Object.assign(target,face);lastFaceAt=now;}else if(now-lastFaceAt>700)Object.assign(target,neutral());
    }catch(e){stopCamera();report(e);}
  }
  let microphone=false;
  if(mode==='human'&&micAnalyser){micAnalyser.getFloatTimeDomainData(samples);target.ParamMouthOpenY=rmsMouth(samples);microphone=true;}
  if(mode==='ai'&&fileAnalyser&&!$('audio').paused){fileAnalyser.getFloatTimeDomainData(samples);target.ParamMouthOpenY=rmsMouth(samples);microphone=true;}
  if((tracking||microphone||manualActive)&&now-lastSent>(manualActive&&!tracking&&!microphone?700:90)){send(target);lastSent=now;}
  const pose=mode==='ai'?performancePose(target,Date.now()/1000,performanceState,target.ParamMouthOpenY):{...target};
  const phase=(now/1000)%4.7;const blink=$('autoblink').checked&&!tracking&&phase>4.48;
  if(blink||manualBlink>now)pose.ParamEyeLOpen=pose.ParamEyeROpen=0;
  pose.ParamBreath=.5+.5*Math.sin(now/1700);
  current=smoothParameters(current,pose,dt);renderer.render(current,now/1000);
  frames++;if(now-fpsTime>1000){$('fps').textContent=`${Math.round(frames*1000/(now-fpsTime))} FPS`;fpsTime=now;frames=0;}
  window.koma={mode,target:{...target},current:{...current},frames:renderer.frames,tracking,lastFaceAt,renderer,performance:performanceState};
  frameStamp=requestAnimationFrame(tick);
}
window.addEventListener('beforeunload',()=>{clearTimeout(connectionTimer);clearInterval(demoTimer);ws.onclose=null;ws.close();stopCamera();stopMic();cancelSpeech();landmarker?.close();audioContext?.close();if(audioURL)URL.revokeObjectURL(audioURL);cancelAnimationFrame(frameStamp);});
try{await renderer.load($('avatar'));connect();status('準備できました。');requestAnimationFrame(tick);}catch(error){report(error);}

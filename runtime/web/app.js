import {AvatarRenderer} from './renderer.js';
import {limits,neutral,faceParameters,rmsMouth,smoothParameters,clamp} from './controls.js';
const $=id=>document.getElementById(id);
const renderer=new AvatarRenderer();
let mode='human',target=neutral(),current=neutral(),ws,cameraStream,micStream,landmarker,tracking=false;
let cameraPending=false,audioContext,micAnalyser,fileAnalyser,fileSource,audioURL;
let manualBlink=0,lastFaceAt=0,frameStamp=0,lastSent=0;
let demoTimer,connectionTimer;
let manualActive=false;
const sliders={};
const names={ParamAngleX:'顔・左右',ParamAngleY:'顔・上下',ParamAngleZ:'顔・傾き',ParamBodyAngleX:'体・左右',ParamEyeLOpen:'左目',ParamEyeROpen:'右目',ParamMouthOpenY:'口の開き'};
const status=text=>$('status').textContent=text;
async function post(path,body){const r=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});if(!r.ok)throw Error(await r.text());return r.json();}
function report(error){console.error(error);status(error.message||String(error));}
function send(parameters,source=mode){if(ws?.readyState===1)ws.send(JSON.stringify({source,parameters,ttl_ms:2000}));}
function connect(){
  ws=new WebSocket(`${location.protocol==='https:'?'wss':'ws'}://${location.host}/ws?role=${new URLSearchParams(location.search).has('overlay')?'overlay':'controller'}`);
  ws.onopen=()=>{$('connection').textContent='● 接続済み';};
  ws.onclose=()=>{$('connection').textContent='再接続中…';connectionTimer=setTimeout(connect,1200);};
  ws.onmessage=({data})=>{
    const event=JSON.parse(data);
    if(event.type==='state'){
      const changed=mode!==event.mode;
      mode=event.mode;target={...event.parameters};
      if(changed){manualActive=false;stopCamera();stopMic();cancelSpeech();$('audio').pause();clearInterval(demoTimer);}
      $('human').classList.toggle('selected',mode==='human');$('ai').classList.toggle('selected',mode==='ai');
      $('mode-label').textContent=mode==='human'?'人間操作':'AI操作';
      $('hint').textContent=mode==='human'?'スライダー・カメラ・マイクで動かせます。':'AIの指示・発話音声で動きます。';
      for(const [key,input] of Object.entries(sliders)){input.value=target[key];input.nextElementSibling.value=target[key].toFixed(2);}
    }
    if(event.type==='speech'){
      $('subtitle').textContent=event.text;
      if(event.play)playSpeech(event).catch(report);
    }
    if(event.type==='cancel_speech')cancelSpeech();
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
for(const next of ['human','ai'])$(next).onclick=()=>post('/api/mode',{mode:next}).catch(report);
$('reset').onclick=()=>{manualActive=false;target=neutral();send(target);};
$('blink').onclick=()=>{
  manualBlink=performance.now()+220;
  const source=mode,eyes={ParamEyeLOpen:target.ParamEyeLOpen,ParamEyeROpen:target.ParamEyeROpen};
  send({ParamEyeLOpen:0,ParamEyeROpen:0},source);
  setTimeout(()=>{if(mode===source)send(eyes,source);},220);
};

function stopCamera(){cameraStream?.getTracks().forEach(t=>t.stop());cameraStream=null;tracking=false;lastFaceAt=0;$('video').srcObject=null;$('video').hidden=true;$('camera').textContent='カメラ開始';updateTracking();}
function stopMic(){micStream?.getTracks().forEach(t=>t.stop());micStream=null;micAnalyser=null;$('microphone').textContent='マイク開始';updateTracking();}
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
  try {
    if(mode!=='human')await post('/api/mode',{mode:'human'});
    micStream=await navigator.mediaDevices.getUserMedia({audio:true,video:false});
    if(mode!=='human'){stopMic();return;}
    micAnalyser=context().createAnalyser();micAnalyser.fftSize=1024;
    context().createMediaStreamSource(micStream).connect(micAnalyser);
    $('microphone').textContent='マイク停止';updateTracking();
  }catch(error){stopMic();report(error);}
};
function cancelSpeech(){$('audio').pause();$('subtitle').textContent='';}
function prepareAudio(){
  if(!fileSource){fileSource=context().createMediaElementSource($('audio'));fileAnalyser=context().createAnalyser();fileAnalyser.fftSize=1024;fileSource.connect(fileAnalyser);fileAnalyser.connect(context().destination);}
}
async function playSpeech(event){
  prepareAudio();$('audio').src=event.url;
  $('audio-status').textContent=event.credit+' · 実際の音量でリップシンク';
  try{await $('audio').play();}catch(e){$('audio-status').textContent=event.credit+' · 下の再生ボタンを押して音声を有効にしてください。';}
}
$('speak').onclick=async()=>{try{prepareAudio();clearInterval(demoTimer);await post('/api/mode',{mode:'ai'});status('音声を合成しています…');await post('/api/speech',{text:$('speech').value});status('音声を生成しました。');}catch(e){report(e);}};
$('demo').onclick=async()=>{
  $('audio').pause();cancelSpeech();clearInterval(demoTimer);await post('/api/mode',{mode:'ai'});const start=performance.now();
  demoTimer=setInterval(()=>{const t=(performance.now()-start)/1000;
    if(mode!=='ai'||t>14){clearInterval(demoTimer);send(neutral(),'ai');return;}
    send({ParamAngleX:Math.sin(t)*10,ParamAngleZ:Math.sin(t*.7)*4,ParamBodyAngleX:Math.sin(t*.5)*2,ParamMouthOpenY:.4+.4*Math.sin(t*9)},'ai');
  },80);
};
for(const event of ['pause','ended'])$('audio').addEventListener(event,()=>{if(mode==='ai'){target.ParamMouthOpenY=0;send({ParamMouthOpenY:0},'ai');}});
$('audiofile').onchange=async()=>{
  const file=$('audiofile').files[0];if(!file)return;
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
  const pose={...target};
  const phase=(now/1000)%4.7;const blink=$('autoblink').checked&&!tracking&&phase>4.48;
  if(blink||manualBlink>now)pose.ParamEyeLOpen=pose.ParamEyeROpen=0;
  pose.ParamBreath=.5+.5*Math.sin(now/1700);
  current=smoothParameters(current,pose,dt);renderer.render(current,now/1000);
  frames++;if(now-fpsTime>1000){$('fps').textContent=`${Math.round(frames*1000/(now-fpsTime))} FPS`;fpsTime=now;frames=0;}
  window.koma={mode,target:{...target},current:{...current},frames:renderer.frames,tracking,lastFaceAt,renderer};
  frameStamp=requestAnimationFrame(tick);
}
window.addEventListener('beforeunload',()=>{clearTimeout(connectionTimer);clearInterval(demoTimer);ws.onclose=null;ws.close();stopCamera();stopMic();cancelSpeech();landmarker?.close();audioContext?.close();if(audioURL)URL.revokeObjectURL(audioURL);cancelAnimationFrame(frameStamp);});
try{await renderer.load($('avatar'));connect();status('準備できました。');requestAnimationFrame(tick);}catch(error){report(error);}

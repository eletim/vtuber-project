import {PerformanceMotion} from './performance.js';
import {expressionLabels} from './expressions.js';
import {AvatarRenderer} from './renderer.js';
import {limits,neutral,faceParameters,rmsMouth,smoothParameters,clamp} from './controls.js';
const $=id=>document.getElementById(id);
const renderer=new AvatarRenderer();
const naturalMotion=new PerformanceMotion();
let mode='human',target=neutral(),current=neutral(),ws,cameraStream,micStream,landmarker,tracking=false;
let cameraRequest,audioContext,micAnalyser,fileAnalyser,fileSource,audioURL;
let manualBlink=0,blinkTimer,blinkRestore,blinkGeneration=0,lastFaceAt=0,frameStamp=0,lastSent=0;
let micRequest;
let activeSpeech,speechRequest,voiceCheck,conversationCheck,conversationClear,audioKind,audioFileName='';
let conversationConfig={available:false,max_input_chars:500};
let conversationRevision=0;
const speechClientId=`ui-${Date.now().toString(36)}-${Math.random().toString(36).slice(2)}-`;
let speechSequence=0;
const cancelledSpeechIds=new Set();
let demoTimer,connectionTimer;
let motionAction,aiModeRequest;
let expressionSelectionGeneration=0,mediaStatusGeneration=0;
let manualActive=false,performanceState={enabled:true,emotion:'neutral'},expressionState={id:'neutral',owner:'idle',until:0};
const sliders={};
const names={ParamAngleX:'顔・左右',ParamAngleY:'顔・上下',ParamAngleZ:'顔・傾き',ParamBodyAngleX:'体・左右',ParamArmLOpen:'画面左の腕',ParamArmROpen:'画面右の腕',ParamShoulderY:'肩・上下',ParamBodyShiftX:'姿勢・左右',ParamSkirtSway:'スカート・揺れ',ParamEyeLOpen:'左目',ParamEyeROpen:'右目',ParamMouthOpenY:'口の開き'};
const status=text=>$('status').textContent=text;
async function post(path,body,signal){const r=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body),signal});if(!r.ok){const error=Error(await r.text());error.status=r.status;throw error;}return r.json();}
function report(error){console.error(error);status(error.message||String(error));}
function stopMotionAction(invalidateSelection=true){motionAction=null;naturalMotion.reset();clearInterval(demoTimer);demoTimer=undefined;if(invalidateSelection){aiModeRequest?.resolveState();aiModeRequest?.controller.abort();aiModeRequest=null;}}
function beginMotionAction(){mediaStatusGeneration++;stopMotionAction(false);cancelSpeech({notify:true});return motionAction={awaitingAI:true};}
async function selectAIForMotion(action){
  if(ws?.readyState!==1)throw Error('接続が切れています。再接続後にもう一度お試しください。');
  // Repeated clicks share the pending mode request, but only the latest action continues.
  if(!aiModeRequest){
    aiModeRequest={cancelExpected:true,controller:new AbortController()};
    aiModeRequest.statePromise=new Promise(resolve=>{aiModeRequest.resolveState=resolve;});
    aiModeRequest.promise=post('/api/mode',{mode:'ai'},aiModeRequest.controller.signal);
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
  const socket=ws;
  ws.onopen=()=>{if(ws!==socket)return;$('connection').textContent='● 接続済み';checkVoice();checkConversation();};
  ws.onclose=()=>{
    if(ws!==socket)return;
    status('接続が切れたため操作を中止しました。再接続後にもう一度お試しください。');
    mediaStatusGeneration++;stopMotionAction();stopBlink();stopCamera();stopMic();cancelSpeech({notify:true});
    setAudioStatus('stopped','停止: 接続が切れました。再接続後に、もう一度「文章から音声を生成」を押してください。');
    voiceCheck?.controller.abort();voiceCheck=null;
    $('voice-status').dataset.state='unknown';$('voice-status').textContent='未確認: 再接続後に音声エンジンを確認します。';
    conversationCheck?.controller.abort();conversationCheck=null;conversationConfig.available=false;
    conversationClear?.controller.abort();
    $('conversation-send').disabled=true;
    $('conversation-engine-status').dataset.state='unknown';$('conversation-engine-status').textContent='未確認: 再接続後に会話モデルを確認します。';
    manualActive=false;target=neutral();expressionState={id:'neutral',owner:'idle',until:0};
    $('expression').value='neutral';$('expression-label').textContent=expressionLabels.neutral;
    $('connection').textContent='再接続中…';connectionTimer=setTimeout(connect,1200);
  };
  ws.onmessage=({data})=>{
    if(ws!==socket||socket.readyState!==1)return;
    const event=JSON.parse(data);
    if(event.type==='state'){
      const changed=mode!==event.mode;
      mode=event.mode;target={...event.parameters};performanceState={...event.performance};
      expressionState=event.expression||{id:'neutral',owner:'idle',until:0};
      $('expression').value=expressionState.id;
      $('expression-label').textContent=expressionLabels[expressionState.id]||expressionLabels.neutral;
      $('lively').checked=performanceState.enabled;
      const expectedAI=mode==='ai'&&motionAction?.awaitingAI;
      if(mode==='ai'&&aiModeRequest&&!aiModeRequest.cancelExpected)aiModeRequest.resolveState();
      if(mode==='human'&&micRequest?.awaitingHuman)micRequest.resolveState?.();
      if(mode==='human'&&cameraRequest?.awaitingHuman)cameraRequest.resolveState?.();
      if(changed&&!expectedAI)stopMotionAction();
      if(changed){manualActive=false;stopBlink();stopCamera(!(mode==='human'&&cameraRequest?.awaitingHuman));stopMic(!(mode==='human'&&micRequest?.awaitingHuman));cancelSpeech({invalidateRequest:!expectedAI});}
      $('human').classList.toggle('selected',mode==='human');$('ai').classList.toggle('selected',mode==='ai');
      $('mode-label').textContent=mode==='human'?'人間操作':'AI操作';
      $('hint').textContent=mode==='human'?'スライダー・カメラ・マイクで動かせます。':'AIの指示・発話音声で動きます。';
      for(const [key,input] of Object.entries(sliders)){input.value=target[key];input.nextElementSibling.value=target[key].toFixed(2);}
      const speech=event.speech;
      if(speech?.kind==='conversation'&&speechRequest?.kind==='conversation'&&speech.request_id===speechRequest.request_id&&!speechRequest.eventReceived&&!isStaleSpeech(speech.request_id)){
        if(speech.phase==='thinking')setAudioStatus('thinking','考え中: ローカルの会話モデルが返答を作っています…');
        if(speech.phase==='synthesizing')setAudioStatus('synthesizing','音声生成中: AIの返答を VOICEVOX で音声にしています…');
        if(speech.phase==='error')setAudioStatus('error','返答または音声を生成できませんでした。接続と設定を確認してください。');
      }
    }
    if(event.type==='speech'&&mode==='ai'){
      // A late HTTP response or WS event must never revive a stopped local request.
      if(isStaleSpeech(event.request_id))return;
      if(speechRequest&&event.request_id!==speechRequest.request_id)return;
      if(activeSpeech?.clip_id===event.clip_id)return;
      if(speechRequest)speechRequest.eventReceived=true;
      if(event.kind==='conversation'){
        conversationRevision++;
        $('conversation-user').textContent=event.user_text||speechRequest?.user_text||'';
        $('conversation-reply').textContent=event.text;
      }
      $('subtitle').textContent=event.text;
      if(event.play)playSpeech(event).catch(error=>{if(!isStaleSpeech(event.request_id)){cancelSpeech({notify:true});setAudioStatus('error',`再生できませんでした: ${error.message||String(error)}`,event.kind);}});
      else setAudioStatus('ready',`生成完了: ${event.kind==='conversation'?'AIの返答から':'入力文から'}作った音声を、別の操作画面で再生します。`,event.kind);
    }
    if(event.type==='cancel_speech'){
      const ownMode=(!event.reason||event.reason==='mode_change')&&aiModeRequest?.cancelExpected;
      const ownSynthesis=event.reason==='superseded'&&speechRequest?.request_id===event.request_id;
      if(ownMode)aiModeRequest.cancelExpected=false;
      if(ownMode||ownSynthesis){cancelSpeech({invalidateRequest:false});return;}
      if(['stopped','controller_disconnected','history_cleared'].includes(event.reason)&&event.request_id){
        const matchesCurrent=event.request_id===speechRequest?.request_id||event.request_id===activeSpeech?.request_id;
        // External clients can be stopped before their first speech event reaches us.
        rememberCancelledSpeech(event.request_id);
        if(!matchesCurrent)return;
      }else if(event.request_id&&isStaleSpeech(event.request_id))return;
      stopMotionAction();cancelSpeech();
    }
    if(event.type==='error')status(event.message);
  };
}
names.ParamHandToCheek='頬に手を添える';
for(const [key,label] of Object.entries(names)){
  const [min,max,def]=limits[key];const row=document.createElement('label');row.className='slider';
  row.innerHTML=`<span>${label}</span><input aria-label="${label}" type="range" min="${min}" max="${max}" step="0.01" value="${def}"><output>${def.toFixed(2)}</output>`;
  const input=row.querySelector('input');sliders[key]=input;
  input.oninput=()=>{
    manualActive=true;
    const restored=key.includes('Eye')&&blinkRestore?{...blinkRestore}:{};
    if(key.includes('Eye'))stopBlink();
    Object.assign(target,restored);target[key]=Number(input.value);
    input.nextElementSibling.value=Number(input.value).toFixed(2);send({...restored,[key]:Number(input.value)});
  };
  $('sliders').append(row);
}
for(const next of ['human','ai'])$(next).onclick=()=>{mediaStatusGeneration++;stopMotionAction();cancelSpeech({notify:true});stopBlink();if(micRequest)stopMic();if(cameraRequest)stopCamera();return post('/api/mode',{mode:next}).catch(report);};
function setExpression(id,duration=30){
  if(!Object.hasOwn(expressionLabels,id))throw Error('unknown expression');
  if(ws?.readyState!==1)throw Error('接続が切れています。');
  expressionSelectionGeneration++;
  ws.send(JSON.stringify({source:mode,expression:id,expression_duration:duration,parameters:{}}));
}
$('expression').onchange=()=>{try{setExpression($('expression').value);}catch(error){report(error);}};
$('reset').onclick=()=>{
  expressionSelectionGeneration++;mediaStatusGeneration++;stopMotionAction();cancelSpeech({notify:true});stopBlink();manualActive=false;target=neutral();
  if(ws?.readyState===1)ws.send(JSON.stringify({source:mode,parameters:target,expression:'neutral',expression_duration:30}));
};
function stopBlink(){clearTimeout(blinkTimer);blinkGeneration++;blinkRestore=null;manualBlink=0;}
$('blink').onclick=()=>{
  manualBlink=performance.now()+220;
  const source=mode;
  if(!blinkRestore)blinkRestore={ParamEyeLOpen:target.ParamEyeLOpen,ParamEyeROpen:target.ParamEyeROpen};
  const eyes=blinkRestore,generation=++blinkGeneration;clearTimeout(blinkTimer);
  send({ParamEyeLOpen:0,ParamEyeROpen:0},source);
  blinkTimer=setTimeout(()=>{if(generation!==blinkGeneration)return;blinkRestore=null;if(mode===source)send(eyes,source);},220);
};

function stopCamera(invalidateRequest=true){if(invalidateRequest){cameraRequest?.resolveState?.();cameraRequest=null;}cameraStream?.getTracks().forEach(t=>t.stop());cameraStream=null;tracking=false;lastFaceAt=0;$('video').srcObject=null;$('video').hidden=true;$('camera').textContent='カメラ開始';updateTracking();}
function stopMic(invalidateRequest=true){if(invalidateRequest){micRequest?.resolveState?.();micRequest=null;}micStream?.getTracks().forEach(t=>t.stop());micStream=null;micAnalyser=null;$('microphone').textContent='マイク開始';updateTracking();}
function updateTracking(){$('tracking').textContent=`カメラ: ${tracking?'追跡中':'停止'} / マイク: ${micStream?'入力中':'停止'}`;}
function context(){audioContext ||= new AudioContext();audioContext.resume();return audioContext;}
$('camera').onclick=async()=>{
  if(cameraStream){stopCamera();send(neutral(),'human');return;}
  if(cameraRequest)return;
  const request=cameraRequest={awaitingHuman:mode!=='human'};
  try {
    if(request.awaitingHuman){
      const statePromise=new Promise(resolve=>{request.resolveState=resolve;});
      await Promise.all([post('/api/mode',{mode:'human'}),statePromise]);
    }
    if(cameraRequest!==request)return;
    request.awaitingHuman=false;
    status('顔追跡モデルを読み込んでいます…');
    manualActive=false;
    if(!landmarker){
      const {FaceLandmarker,FilesetResolver}=await import('/vendor/vision_bundle.mjs');
      const files=await FilesetResolver.forVisionTasks('/vendor/wasm');
      landmarker=await FaceLandmarker.createFromOptions(files,{baseOptions:{modelAssetPath:'/vendor/face_landmarker.task'},runningMode:'VIDEO',numFaces:1,outputFaceBlendshapes:true});
    }
    if(cameraRequest!==request||mode!=='human')return;
    const stream=await navigator.mediaDevices.getUserMedia({video:{width:640,height:480},audio:false});
    if(cameraRequest!==request||mode!=='human'){stream.getTracks().forEach(track=>track.stop());return;}
    cameraStream=stream;$('video').srcObject=stream;await $('video').play();
    if(cameraRequest!==request||mode!=='human'){stream.getTracks().forEach(track=>track.stop());return;}
    $('video').hidden=false;
    tracking=true;$('camera').textContent='カメラ停止';updateTracking();status('顔の向き・目・口を追跡しています。');
  }catch(error){if(cameraRequest===request){stopCamera();report(error);}}
  finally{if(cameraRequest===request)cameraRequest=null;}
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
function setConversationStatus(phase,text){$('conversation-status').dataset.state=phase;$('conversation-status').textContent=text;}
function setAudioStatus(phase,text,kind=speechRequest?.kind||activeSpeech?.kind){
  $('audio-status').dataset.state=phase;$('audio-status').textContent=text;
  if(kind==='conversation')setConversationStatus(phase,text);
}
function updateSpeechStop(){
  $('stop-speech').disabled=!(speechRequest||activeSpeech||audioKind||motionAction?.kind==='file');
  $('stop-conversation').disabled=!(speechRequest?.kind==='conversation'||activeSpeech?.kind==='conversation');
}
function isStaleSpeech(id){return !!id&&(cancelledSpeechIds.has(id)||(id.startsWith(speechClientId)&&speechRequest?.request_id!==id));}
function rememberCancelledSpeech(id){
  if(!id)return;
  cancelledSpeechIds.add(id);
  if(cancelledSpeechIds.size>256)cancelledSpeechIds.delete(cancelledSpeechIds.values().next().value);
}
async function checkVoice(){
  voiceCheck?.controller.abort();
  const request=voiceCheck={controller:new AbortController()};
  $('voice-status').dataset.state='checking';$('voice-status').textContent='確認中: VOICEVOX に接続しています…';
  try{
    const response=await fetch('/api/voice',{signal:request.controller.signal});
    if(!response.ok)throw Error(await response.text());
    const voice=await response.json();if(voiceCheck!==request)return;
    $('voice-status').textContent=voice.available
      ?`利用可能: ${voice.credit||voice.provider||'VOICEVOX'}${voice.style?' / '+voice.style:''}${voice.version?' · v'+voice.version:''}`
      :`利用できません: ${voice.message||'VOICEVOX を起動してから、もう一度確認してください。'}`;
    $('voice-status').dataset.state=voice.available?'available':'unavailable';
  }catch(error){
    if(voiceCheck===request&&error.name!=='AbortError'){
      $('voice-status').dataset.state='unavailable';
      $('voice-status').textContent='確認できません: サーバーへの接続と VOICEVOX の起動を確認して、もう一度確認してください。';
    }
  }finally{if(voiceCheck===request)voiceCheck=null;}
}
$('check-voice').onclick=checkVoice;
async function checkConversation(){
  conversationCheck?.controller.abort();
  const request=conversationCheck={controller:new AbortController()};
  conversationConfig.available=false;$('conversation-send').disabled=true;
  $('conversation-engine-status').dataset.state='checking';$('conversation-engine-status').textContent='確認中: ローカルの会話モデルを確認しています…';
  try{
    const response=await fetch('/api/conversation',{signal:request.controller.signal});
    if(!response.ok)throw Error(await response.text());
    const config=await response.json();if(conversationCheck!==request)return;
    const available=config.configured===true&&config.available===true;
    const max=Number.isInteger(config.max_input_chars)&&config.max_input_chars>0?Math.min(500,config.max_input_chars):500;
    conversationConfig={...config,available,max_input_chars:max};$('conversation-input').maxLength=max;
    $('conversation-send').disabled=!available||!!conversationClear;
    $('conversation-engine-status').dataset.state=available?'available':config.configured?'unavailable':'unconfigured';
    $('conversation-engine-status').textContent=available
      ?`利用可能: ${config.provider||'ローカルモデル'}${config.model?' / '+config.model:''}（音声には VOICEVOX も必要です）`
      :`${config.configured?'利用できません':'未設定'}: ${config.message||'ローカルモデルの設定と起動を確認して、もう一度確認してください。'}`;
  }catch(error){
    if(conversationCheck===request&&error.name!=='AbortError'){
      $('conversation-engine-status').dataset.state='unavailable';
      $('conversation-engine-status').textContent='確認できません: サーバーへの接続とローカルモデルの設定・起動を確認して、もう一度確認してください。';
    }
  }finally{if(conversationCheck===request)conversationCheck=null;}
}
$('check-conversation').onclick=checkConversation;
$('conversation-send').disabled=true;$('stop-conversation').disabled=true;
function reportPlayback(state,speech=activeSpeech,position=$('audio').currentTime){
  if(!speech?.clip_id)return;
  post('/api/playback',{clip_id:speech.clip_id,state,position,sequence:++speech.sequence,playback_rate:$('audio').playbackRate||1})
    .catch(error=>{if(error.status!==409&&activeSpeech===speech)report(error);});
}
function clearSpeechAudio(){
  const speech=activeSpeech;activeSpeech=null;
  if(speech)reportPlayback('paused',speech);
  $('audio').pause();$('audio').removeAttribute('src');$('audio').load();
  audioKind=null;target.ParamMouthOpenY=0;$('subtitle').textContent='';
}
function cancelSpeech({invalidateRequest=true,notify=false}={}){
  const request=speechRequest,speech=activeSpeech,hadAudio=!!audioKind;
  const id=request?.request_id||speech?.request_id,kind=request?.kind||speech?.kind;
  if(invalidateRequest){
    speechRequest=null;request?.controller.abort();rememberCancelledSpeech(id);
    // Do not cancel some other controller's speech when only a local file was playing.
    if(notify&&(request?.posted||speech))post('/api/speech/cancel',id?{request_id:id}:{})
      .catch(()=>{}); // Local Stop is immediate, even when the server is unreachable.
  }
  clearSpeechAudio();updateSpeechStop();
  if(invalidateRequest&&(request||speech||hadAudio))setAudioStatus('stopped',kind==='conversation'?'停止: AIの返答生成と音声を止めました。もう一度話しかけると、新しい返答を生成します。':'停止: 音声を止めました。文章から新しく生成するか、音声ファイルを選んでください。',kind);
}
function prepareAudio(){
  if(!fileSource){fileSource=context().createMediaElementSource($('audio'));fileAnalyser=context().createAnalyser();fileAnalyser.fftSize=1024;fileSource.connect(fileAnalyser);fileAnalyser.connect(context().destination);}
}
async function playSpeech(event){
  clearSpeechAudio();prepareAudio();
  const speech=activeSpeech={clip_id:event.clip_id,request_id:event.request_id,kind:event.kind==='conversation'?'conversation':'text',credit:event.credit||'VOICEVOX',sequence:0};
  audioKind=speech.kind;$('subtitle').textContent=event.text;$('audio').src=event.url;updateSpeechStop();
  const origin=speech.kind==='conversation'?'AIの返答から':'入力文から';
  setAudioStatus('ready',`生成完了: ${origin}新しく生成した音声 · ${speech.credit}`);
  try{await $('audio').play();}catch(error){
    if(activeSpeech!==speech)return;
    if(error.name==='NotAllowedError'&&!$('audio').error)setAudioStatus('ready',`再生待ち: ${origin}生成済み · ${speech.credit}。音声プレーヤーの再生ボタンを押してください。`);
    else if(error.name==='AbortError'&&!$('audio').error)setAudioStatus('ready',`一時停止: ${origin}生成済み · ${speech.credit}`);
    else setAudioStatus('error',`再生エラー: 生成した音声を読み込めないか、音声形式に問題があります。接続を確認して、もう一度音声を生成してください。`);
  }
}
function stopSpeech(){
  const kind=speechRequest?.kind||activeSpeech?.kind;
  // Stop does not undo an already requested AI-mode switch. A quick retry shares its ack.
  mediaStatusGeneration++;stopMotionAction(false);cancelSpeech({notify:true});
  if(mode==='ai')send({ParamMouthOpenY:0},'ai');
  setAudioStatus('stopped',kind==='conversation'?'停止: AIの返答生成と音声を止めました。操作モードはそのままです。':'停止: 音声を止めました。操作モードはそのままです。',kind);
}
$('stop-speech').onclick=stopSpeech;$('stop-conversation').onclick=stopSpeech;
$('speak').onclick=async()=>{
  const text=$('speech').value.trim();
  if(!text){setAudioStatus('error','入力してください: 読み上げる文章を入力してから、音声を生成してください。','text');return;}
  if(text.length>2000){setAudioStatus('error','入力が長すぎます: 読み上げる文章は2000文字以内にしてください。','text');return;}
  const selected=expressionState.owner==='manual'?expressionState.id:undefined,action=beginMotionAction();
  const request=speechRequest={request_id:speechClientId+(++speechSequence),kind:'text',controller:new AbortController(),action,posted:false,eventReceived:false};
  updateSpeechStop();setAudioStatus('generating','生成準備中: AI操作へ切り替えています…');
  try{
    prepareAudio();if(!await selectAIForMotion(action)||speechRequest!==request)return;
    request.posted=true;setAudioStatus('generating','生成中: 入力した文章から VOICEVOX で新しく音声を作っています…');
    await post('/api/speech',{request_id:request.request_id,text,emotion:$('emotion').value,...(selected?{expression:selected}:{})},request.controller.signal);
    if(speechRequest!==request||mode!=='ai')return;
    if(!request.eventReceived)setAudioStatus('ready','生成完了: 音声の受信を待っています…');
  }catch(error){
    if(speechRequest!==request||error.name==='AbortError'||request.eventReceived)return;
    cancelSpeech();
    setAudioStatus(error.status===409?'stopped':'error',error.status===409?'停止: この発話はキャンセルされました。':`生成できませんでした: ${error.message||String(error)}`);
  }
};
$('conversation-send').onclick=async()=>{
  // The clear endpoint is global: do not race a new local question against it.
  if(conversationClear)return;
  if(!conversationConfig.available){setConversationStatus('error','会話モデルは未確認または利用できません。「会話モデルを確認」で状態を確認してください。');return;}
  const text=$('conversation-input').value.trim(),max=conversationConfig.max_input_chars;
  if(!text||text.length>max){setConversationStatus('error',!text?'入力してください: AIに話しかける文章を入力してください。':`入力が長すぎます: ${max}文字以内にしてください。`);return;}
  const action=beginMotionAction();
  const request=speechRequest={request_id:speechClientId+(++speechSequence),kind:'conversation',user_text:text,controller:new AbortController(),action,posted:false,eventReceived:false};
  conversationRevision++;
  $('conversation-user').textContent=text;$('conversation-reply').textContent='';
  updateSpeechStop();setAudioStatus('preparing','会話の準備中: AI操作へ切り替えています…');
  try{
    prepareAudio();if(!await selectAIForMotion(action)||speechRequest!==request)return;
    request.posted=true;setAudioStatus('thinking','考え中: ローカルの会話モデルが返答を作っています…');
    await post('/api/conversation',{request_id:request.request_id,text},request.controller.signal);
    if(speechRequest!==request||mode!=='ai')return;
    if(!request.eventReceived)setAudioStatus('ready','返答と音声の生成が完了しました。音声の受信を待っています…');
  }catch(error){
    if(speechRequest!==request||error.name==='AbortError'||request.eventReceived)return;
    cancelSpeech();
    setAudioStatus(error.status===409?'stopped':'error',error.status===409?'停止: この会話はキャンセルされました。':`返答または音声を生成できませんでした: ${error.message||String(error)}`,'conversation');
  }
};
$('clear-conversation').onclick=async()=>{
  if(conversationClear)return;
  if(speechRequest?.kind==='conversation'||activeSpeech?.kind==='conversation')stopSpeech();
  const request=conversationClear={controller:new AbortController(),revision:++conversationRevision};
  $('clear-conversation').disabled=true;$('conversation-send').disabled=true;
  setConversationStatus('clearing','消去中: 会話履歴の消去を確認しています…');
  try{
    const result=await post('/api/conversation/clear',{},request.controller.signal);
    if(request.controller.signal.aborted)throw Error('接続が切れたため、消去結果を確認できません。');
    if(result?.cleared!==true)throw Error('サーバーが履歴の消去を確認できませんでした。');
    if(conversationClear!==request||conversationRevision!==request.revision)return;
    $('conversation-user').textContent='';$('conversation-reply').textContent='';
    setConversationStatus('idle','会話履歴を消去しました。次の会話は新しく始めます。');
  }catch(error){
    if(conversationClear===request&&conversationRevision===request.revision)setConversationStatus('error','履歴の消去を確認できませんでした。会話の表示は残しています。接続を確認して、もう一度お試しください。');
  }finally{
    if(conversationClear===request){conversationClear=null;$('clear-conversation').disabled=false;$('conversation-send').disabled=!conversationConfig.available;}
  }
};
$('lively').onchange=()=>post('/api/performance',{enabled:$('lively').checked}).catch(report);
const cheekButton=document.createElement('button');cheekButton.id='cheek-gesture';cheekButton.textContent='頬に手を添えて戻す';
$('sliders').append(cheekButton);
cheekButton.onclick=async()=>{
  const action=beginMotionAction();
  try{if(!await selectAIForMotion(action))return;await post('/api/performance',{enabled:true,emotion:'thoughtful',duration:6});}
  catch(error){if(motionAction===action)report(error);}
};
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
function describeAudio(){return audioKind==='conversation'?`AIの返答から生成 · ${activeSpeech?.credit||'VOICEVOX'}`:audioKind==='text'?`入力文から生成 · ${activeSpeech?.credit||'VOICEVOX'}`:`保存済み音声ファイル · ${audioFileName}`;}
function playbackStarted(){
  if(mode!=='ai'||!audioKind||$('audio').paused||$('audio').seeking||$('audio').readyState<3||$('audio').error)return;
  reportPlayback('playing');setAudioStatus('playing',`再生中: ${describeAudio()} · 実際の音量でリップシンク`);
}
$('audio').addEventListener('playing',playbackStarted);
for(const event of ['seeked','ratechange'])$('audio').addEventListener(event,playbackStarted);
for(const event of ['pause','ended','waiting','seeking','error'])$('audio').addEventListener(event,()=>{
  const audio=$('audio');
  if(!audioKind||event==='pause'&&!audio.paused||event==='ended'&&!audio.ended||event==='error'&&!audio.error||event==='seeking'&&!audio.seeking||event==='waiting'&&audio.readyState>=3)return;
  if(mode==='ai'){
    target.ParamMouthOpenY=0;send({ParamMouthOpenY:0},'ai');reportPlayback(event==='ended'?'ended':'paused');
    const phase=event==='error'?'error':event==='ended'?'ended':'ready';
    const label=event==='error'?'再生エラー。もう一度生成するか、音声ファイルを選び直してください':event==='ended'?'再生完了':event==='pause'?'一時停止':'再生待ち';
    setAudioStatus(phase,`${label}: ${describeAudio()}`);
  }
});
$('audiofile').onchange=async()=>{
  const file=$('audiofile').files[0];if(!file)return;
  const selected=expressionState.owner==='manual'?expressionState.id:undefined,selection=expressionSelectionGeneration,action=beginMotionAction();
  action.kind='file';updateSpeechStop();
  setAudioStatus('ready',`再生準備中: 保存済み音声ファイル · ${file.name}（文章からの音声生成ではありません）`);
  try{
    if(!await selectAIForMotion(action))return;
    if(selected&&selection===expressionSelectionGeneration&&expressionState.owner!=='manual')setExpression(selected);
    if(motionAction!==action||mode!=='ai')return;
    if(audioURL)URL.revokeObjectURL(audioURL);audioURL=URL.createObjectURL(file);$('audio').src=audioURL;
    audioKind='file';audioFileName=file.name;updateSpeechStop();prepareAudio();
    await $('audio').play();if(motionAction===action)setAudioStatus('playing',`再生中: 保存済み音声ファイル · ${file.name}（文章からの音声生成ではありません）`);
  }catch(error){if(motionAction===action){setAudioStatus('error',`音声ファイルを再生できませんでした: ${error.message||String(error)}`);}}
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
  if(mode==='ai'&&fileAnalyser&&!$('audio').paused&&!$('audio').seeking&&!$('audio').error&&$('audio').readyState>=3){fileAnalyser.getFloatTimeDomainData(samples);target.ParamMouthOpenY=rmsMouth(samples);microphone=true;}
  if((tracking||microphone||manualActive)&&now-lastSent>(manualActive&&!tracking&&!microphone?700:90)){send(target);lastSent=now;}
  const pose=naturalMotion.frame(target,Date.now()/1000,{...performanceState,enabled:mode==='ai'&&performanceState.enabled},target.ParamMouthOpenY);
  const phase=(now/1000)%4.7;const blink=$('autoblink').checked&&!tracking&&phase>4.48;
  if(blink||manualBlink>now)pose.ParamEyeLOpen=pose.ParamEyeROpen=0;
  pose.ParamBreath=.5+.5*Math.sin(now/1700);
  const expression=expressionState.until&&Date.now()/1000>=expressionState.until?'neutral':expressionState.id;
  current=smoothParameters(current,pose,dt);renderer.render(current,now/1000,expression);
  frames++;if(now-fpsTime>1000){$('fps').textContent=`${Math.round(frames*1000/(now-fpsTime))} FPS`;fpsTime=now;frames=0;}
  window.koma={mode,target:{...target},current:{...current},frames:renderer.frames,tracking,lastFaceAt,renderer,performance:performanceState,naturalMotion,expression:{...expressionState},expressionFrame:renderer.expressionFrame,setExpression};
  frameStamp=requestAnimationFrame(tick);
}
window.addEventListener('beforeunload',()=>{clearTimeout(connectionTimer);clearInterval(demoTimer);voiceCheck?.controller.abort();conversationCheck?.controller.abort();conversationClear?.controller.abort();ws.onclose=null;ws.close();stopCamera();stopMic();cancelSpeech();landmarker?.close();audioContext?.close();if(audioURL)URL.revokeObjectURL(audioURL);cancelAnimationFrame(frameStamp);});
try{await renderer.load($('avatar'));connect();status('準備できました。');requestAnimationFrame(tick);}catch(error){report(error);}

// Requires the real official CPU engine; captures actual WebGL + generated speech.
import {createRequire} from 'node:module';
import {spawn} from 'node:child_process';
import {resolve,dirname} from 'node:path';
import {fileURLToPath} from 'node:url';
import {mkdir,writeFile} from 'node:fs/promises';
import assert from 'node:assert/strict';
const {chromium}=createRequire(import.meta.url)(process.env.PLAYWRIGHT_MODULE||'playwright');
const root=resolve(dirname(fileURLToPath(import.meta.url)),'../..');
const out=resolve(root,'assets/parts/v12');await mkdir(out,{recursive:true});
const engine=spawn(process.env.VOICEVOX_ENGINE,['--host','127.0.0.1','--port','50021','--cpu_num_threads','2']);
engine.stderr.on('data',d=>process.stderr.write(d));
const server=spawn('python',[resolve(root,'runtime/server.py'),'--port','18766']);
let browser;
async function wait(url){for(let i=0;i<300;i++){try{if((await fetch(url)).ok)return;}catch{}await new Promise(r=>setTimeout(r,200));}throw Error('startup timeout: '+url);}
const base='http://127.0.0.1:18766';
const post=async(path,body)=>{const r=await fetch(base+path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});assert.equal(r.status,200,await r.clone().text());return r.json();};
try{
 await wait('http://127.0.0.1:50021/version');await wait(base+'/api/state');
 browser=await chromium.launch({executablePath:process.env.CHROME_PATH,headless:true,args:['--no-sandbox','--enable-unsafe-swiftshader','--autoplay-policy=no-user-gesture-required']});
 const context=await browser.newContext({viewport:{width:1280,height:1000}});
 const page=await context.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto(base);await page.waitForFunction(()=>window.koma?.frames>5);
 const overlay=await context.newPage();await overlay.goto(base+'/?overlay=1');await overlay.waitForFunction(()=>window.koma?.frames>5);
 await page.bringToFront();await page.locator('#ai').click();
 const text='こんにちは、羽月こまです。今日は、声を出してお話しできるようになりました。一緒に楽しんでいきましょう。';
 await page.locator('#speech').fill(text);
 const response=page.waitForResponse(r=>r.url().endsWith('/api/speech')&&r.request().method()==='POST');
 await page.locator('#speak').click();const result=await response;assert.equal(result.status(),200,await result.text());const speech=await result.json();
 assert.equal(speech.playback_clients,1);
 const wav=await fetch(base+speech.url);await writeFile(resolve(out,'koma-free-voice.wav'),Buffer.from(await wav.arrayBuffer()));
 await page.waitForFunction(()=>!document.querySelector('#audio').paused&&window.koma.current.ParamMouthOpenY>.1);
 assert.equal(await overlay.locator('#audio').evaluate(a=>a.paused),true);
 await overlay.waitForFunction(()=>window.koma.current.ParamMouthOpenY>.1);
 const observed=[];
 for(let i=0;i<25;i++){observed.push(await page.evaluate(()=>({mouth:window.koma.current.ParamMouthOpenY,time:document.querySelector('#audio').currentTime})));await page.waitForTimeout(80);}
 assert.ok(Math.max(...observed.map(x=>x.mouth))-Math.min(...observed.map(x=>x.mouth))>.05);
 await page.screenshot({path:resolve(out,'free-voice-control.png'),fullPage:true});
 await page.locator('#audio').evaluate(a=>a.pause());await page.waitForFunction(()=>window.koma.current.ParamMouthOpenY<.05);
 // Capture deterministic time-sampled frames from the real rendered model using WAV RMS.
 const amplitudes=await page.evaluate(async url=>{
   const ac=new AudioContext();const b=await ac.decodeAudioData(await (await fetch(url)).arrayBuffer());const samples=b.getChannelData(0),fps=15;
   return Array.from({length:Math.ceil(b.duration*fps)},(_,i)=>{let sum=0,n=0;for(let j=Math.floor(i*b.sampleRate/fps);j<Math.min(samples.length,(i+1)*b.sampleRate/fps);j++){sum+=samples[j]*samples[j];n++;}return Math.min(1,Math.max(0,(Math.sqrt(sum/Math.max(1,n))-.008)*7));});
 },speech.url);
 const frames=resolve(root,'runtime/test-results/voice-frames');await mkdir(frames,{recursive:true});
 for(let i=0;i<amplitudes.length;i++){
  const data=await page.evaluate(({mouth,t})=>{const r=window.koma.renderer;r.render({...window.koma.current,ParamMouthOpenY:mouth,ParamEyeLOpen:t%4.7>4.48?0:1,ParamEyeROpen:t%4.7>4.48?0:1},t);return document.querySelector('#avatar').toDataURL().split(',')[1];},{mouth:amplitudes[i],t:i/15});
  await writeFile(resolve(frames,`${String(i).padStart(4,'0')}.png`),Buffer.from(data,'base64'));
 }
 const speaking=post('/api/speech',{text:'途中で人間操作に切り替えます。'});await speaking;
 await page.waitForFunction(()=>!document.querySelector('#audio').paused);
 await post('/api/mode',{mode:'human'});await page.waitForFunction(()=>document.querySelector('#audio').paused&&document.querySelector('#subtitle').textContent==='');
 assert.deepEqual(errors,[]);
 await writeFile(resolve(out,'voice-verification.json'),JSON.stringify({status:'PASS',engine:'VOICEVOX engine 0.25.2 CPU',credit:speech.credit,text,checks:['real Japanese WAV synthesis','single controller playback; overlay silent','real Web Audio RMS mouth motion','mouth state reaches overlay','pause closes mouth','mode switch cancels playback'],observed,frames:amplitudes.length},null,2)+'\n');
 console.log('PASS real VOICEVOX playback and lip sync; frames',amplitudes.length);
}finally{if(browser)await browser.close();server.kill();engine.kill();}

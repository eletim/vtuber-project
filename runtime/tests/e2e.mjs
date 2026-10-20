import {createRequire} from 'node:module';
import {spawn} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {resolve,dirname} from 'node:path';
import {mkdir,writeFile} from 'node:fs/promises';
import assert from 'node:assert/strict';
const require=createRequire(import.meta.url);
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const root=resolve(dirname(fileURLToPath(import.meta.url)),'../..');
const output=resolve(root,'runtime/test-results');await mkdir(output,{recursive:true});
const port=18766,base=`http://127.0.0.1:${port}`;
const server=spawn(process.env.PYTHON||'python',[resolve(root,'runtime/server.py'),'--port',String(port)],{cwd:root});
let browser;
const report={checks:[],errors:[],actual_camera_device_tested:false,actual_microphone_device_tested:false,tts_voice_output_verified:false};
const api=async(path,body)=>{const r=await fetch(base+path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});assert.equal(r.status,200,await r.clone().text());return r.json();};
try{
 for(let i=0;i<100;i++){try{if((await fetch(base+'/api/state')).ok)break;}catch{}await new Promise(r=>setTimeout(r,100));}
 const args=['--no-sandbox','--enable-unsafe-swiftshader','--autoplay-policy=no-user-gesture-required'];
 if(process.env.VIDEO_FIXTURE)args.push('--use-fake-device-for-media-stream','--use-fake-ui-for-media-stream',`--use-file-for-fake-video-capture=${process.env.VIDEO_FIXTURE}`);
 if(process.env.AUDIO_FIXTURE)args.push(`--use-file-for-fake-audio-capture=${process.env.AUDIO_FIXTURE}`);
 browser=await chromium.launch({headless:true,executablePath:process.env.CHROME_PATH||undefined,args});
 const context=await browser.newContext({viewport:{width:1380,height:1100},permissions:['camera','microphone']});
 const page=await context.newPage();page.on('pageerror',e=>report.errors.push(e.message));
 await page.goto(base);await page.waitForFunction(()=>window.koma?.frames>8);
 await page.locator('#autoblink').uncheck();
 const pixels=await page.evaluate(()=>{const gl=window.koma.renderer.gl;const p=new Uint8Array(gl.drawingBufferWidth*gl.drawingBufferHeight*4);gl.readPixels(0,0,gl.drawingBufferWidth,gl.drawingBufferHeight,gl.RGBA,gl.UNSIGNED_BYTE,p);return p.filter((v,i)=>i%4===3&&v>0).length;});
 assert.ok(pixels>30000,'avatar must contain visible pixels');
 report.checks.push('WebGL model loads and draws nonempty transparent output');
 await page.screenshot({path:resolve(output,'control-room.png'),fullPage:true});
 for(const [name,params] of Object.entries({normal:{ParamEyeLOpen:1,ParamEyeROpen:1,ParamMouthOpenY:1},eyes_closed:{ParamEyeLOpen:0,ParamEyeROpen:0,ParamMouthOpenY:1},mouth_closed:{ParamEyeLOpen:1,ParamEyeROpen:1,ParamMouthOpenY:0},both_closed:{ParamEyeLOpen:0,ParamEyeROpen:0,ParamMouthOpenY:0}})){
  await api('/api/control',{source:'human',parameters:params});await page.waitForTimeout(250);
  await page.locator('#avatar').screenshot({path:resolve(output,`expression_${name}.png`)});
 }
 report.checks.push('four expression endpoints rendered through human control API');
 const overlay=await context.newPage();await overlay.goto(base+'/?overlay=1');await overlay.waitForFunction(()=>window.koma?.frames>5);
 await page.locator('#blink').click();await overlay.waitForFunction(()=>window.koma.current.ParamEyeLOpen<.3);
 report.checks.push('manual blink reaches separate transparent overlay through shared control bus');
 await overlay.close();
 await page.locator('#ai').click();await page.waitForFunction(()=>window.koma.mode==='ai');
 await api('/api/control',{source:'ai',parameters:{ParamAngleX:12,ParamAngleZ:6,ParamMouthOpenY:.8}});
 await page.waitForFunction(()=>window.koma.current.ParamAngleX>10);
 const denied=await fetch(base+'/api/control',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({source:'human',parameters:{ParamAngleX:-10}})});assert.equal(denied.status,409);
 await page.locator('#avatar').screenshot({path:resolve(output,'ai-pose.png')});
 report.checks.push('external AI parameters drive model; inactive human input rejected');
 await mkdir(resolve(output,'motion'),{recursive:true});
 for(let i=0;i<24;i++){
  await api('/api/control',{source:'ai',parameters:{ParamAngleX:Math.sin(i/24*Math.PI*2)*14,ParamAngleZ:Math.sin(i/24*Math.PI*2)*7,ParamBodyAngleX:Math.sin(i/24*Math.PI*2)*3,ParamEyeLOpen:i===11?0:1,ParamEyeROpen:i===11?0:1,ParamMouthOpenY:i%6<3?1:0}});
  await page.waitForTimeout(130);
  const frame=await page.locator('#avatar').evaluate(c=>c.toDataURL('image/png').split(',')[1]);
  await writeFile(resolve(output,'motion',`${String(i).padStart(2,'0')}.png`),Buffer.from(frame,'base64'));
 }
 report.checks.push('24 actual WebGL frames captured while AI API changes pose and expression');
 if(process.env.AUDIO_FIXTURE){
  await page.locator('#audiofile').setInputFiles(process.env.AUDIO_FIXTURE);
  await page.waitForFunction(()=>window.koma.current.ParamMouthOpenY>.4,{},{timeout:15000});
  await page.locator('#audio').evaluate(a=>a.pause());
  await page.waitForFunction(()=>window.koma.current.ParamMouthOpenY<.05);
  report.checks.push('real Web Audio RMS from uploaded WAV opens mouth; pause closes it');
 }
 await page.locator('#human').click();await page.waitForFunction(()=>window.koma.mode==='human'&&Math.abs(window.koma.target.ParamAngleX)<.01);
 if(process.env.VIDEO_FIXTURE){
  await page.locator('#camera').click();await page.waitForFunction(()=>window.koma.tracking&&window.koma.lastFaceAt>0,{},{timeout:90000});
  await page.evaluate(()=>window.capturedCameraTrack=document.querySelector('#video').srcObject.getVideoTracks()[0]);
  await page.screenshot({path:resolve(output,'camera-tracking.png'),fullPage:true});
  report.checks.push('MediaPipe WASM detects a face from fake camera portrait video and publishes parameters');
  await page.locator('#ai').click();await page.waitForFunction(()=>window.koma.mode==='ai'&&!window.koma.tracking);
  assert.equal(await page.evaluate(()=>window.capturedCameraTrack.readyState),'ended');
  report.checks.push('switch to AI stops camera tracking');
 }
 if(process.env.AUDIO_FIXTURE){
  await page.locator('#human').click();await page.waitForFunction(()=>window.koma.mode==='human');
  await page.locator('#microphone').click();await page.waitForFunction(()=>window.koma.current.ParamMouthOpenY>.4,{},{timeout:20000});
  report.checks.push('fake microphone WAV traverses getUserMedia/Web Audio to mouth parameters');
  await page.locator('#ai').click();await page.waitForFunction(()=>window.koma.mode==='ai');
  await page.waitForFunction(()=>document.querySelector('#microphone').textContent==='マイク開始');
 }
 const invalidSpeech=await fetch(base+'/api/speech',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:''})});assert.equal(invalidSpeech.status,400);
 report.checks.push('empty speech rejected; real VOICEVOX playback covered separately by voice.e2e.mjs');
 await page.locator('#human').click();await page.waitForFunction(()=>document.querySelector('#subtitle').textContent==='');
 await page.setViewportSize({width:390,height:844});
 assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
 await page.screenshot({path:resolve(output,'mobile.png'),fullPage:true});
 report.checks.push('390px layout has no horizontal overflow');
 assert.deepEqual(report.errors,[]);
 report.status='PASS';
}catch(error){report.status='FAIL';report.failure=String(error);throw error;}
finally{await writeFile(resolve(output,'e2e.json'),JSON.stringify(report,null,2)+'\n');if(browser)await browser.close();server.kill();console.log(JSON.stringify(report,null,2));}

import {createRequire} from 'node:module';import {spawn} from 'node:child_process';import {mkdir,writeFile} from 'node:fs/promises';
import {muxCfr} from './cfr_mp4.mjs';
const require=createRequire(import.meta.url),{chromium}=require(process.env.PLAYWRIGHT_MODULE),out='assets/parts/v40/sync-review';await mkdir(out,{recursive:true});
const server=spawn(process.env.PYTHON,['runtime/server.py','--port','18780'],{windowsHide:true});let browser;const report={errors:[],samples:[],events:[]};
try{
 for(let i=0;i<100;i++){try{if((await fetch('http://127.0.0.1:18780/api/state')).ok)break}catch{}await new Promise(r=>setTimeout(r,100))}
 browser=await chromium.launch({headless:true,executablePath:process.env.CHROME_PATH,args:['--enable-unsafe-swiftshader']});
 const contexts=await Promise.all([browser.newContext(),browser.newContext()]);
 for(const c of contexts)await c.addInitScript(()=>{const W=window.WebSocket;window.WebSocket=class extends W{constructor(...args){super(...args);window.reviewSocket=this;}}});
 const a=await contexts[0].newPage(),b=await contexts[1].newPage();for(const p of [a,b])p.on('pageerror',e=>report.errors.push(e.message));
 await a.goto('http://127.0.0.1:18780');await a.waitForFunction(()=>window.koma?.frames>30);
 await a.locator('#acting-start').click();await a.waitForFunction(()=>koma.acting.running&&koma.acting.age>3);
 await a.evaluate(()=>{for(let i=0;i<8;i++)document.querySelector('#acting-start').onclick()});
 const first=await a.evaluate(()=>koma.acting.id);
 await b.goto('http://127.0.0.1:18780/?overlay=1');await b.waitForFunction(()=>window.koma?.acting.weight>.98);
 report.join=await Promise.all([a.evaluate(()=>koma.acting),b.evaluate(()=>koma.acting)]);
 if(report.join.some(s=>s.id!==first)||Math.abs(report.join[0].age-report.join[1].age)>.15)throw Error('Late join epoch mismatch');
 const encoder=await browser.newPage();await encoder.route('http://127.0.0.1:18780/encode',r=>r.fulfill({contentType:'text/html',body:'<!doctype html>'}));await encoder.goto('http://127.0.0.1:18780/encode');
 await encoder.evaluate(()=>{
  window.buffers=[[],[]];window.desc=[];window.encoders=[];window.encoderErrors=[];
  for(let k=0;k<2;k++){const e=new VideoEncoder({error:e=>encoderErrors.push(e.message),output:(chunk,meta)=>{const data=new Uint8Array(chunk.byteLength);chunk.copyTo(data);buffers[k].push({timestamp:chunk.timestamp,type:chunk.type,data:Array.from(data)});if(meta.decoderConfig?.description)desc[k]=Array.from(new Uint8Array(meta.decoderConfig.description))}});e.configure({codec:'avc1.420028',width:k?326:652,height:480,framerate:10,bitrate:3500000,avc:{format:'avc'},latencyMode:'realtime'});encoders.push(e)}
 });
 // The encoder is not an avatar controller: close its app socket immediately.
 await encoder.evaluate(()=>{window.reviewSocket?.close();});
 if(await a.locator('#acting-stop').isEnabled())await a.locator('#acting-stop').click();await Promise.all([a,b].map(p=>p.waitForFunction(()=>koma.acting.weight===0)));await a.waitForTimeout(1600);await a.locator('#acting-start').click();await a.waitForFunction(()=>koma.acting.running);
 const start=Date.now();
 for(let n=0;n<100;n++){
  if(n===10){await a.locator('#acting-stop').click();report.events.push({n,action:'stop'});}
  if(n===25){await a.locator('#acting-start').click();report.events.push({n,action:'restart'});}
  if(n===45){await a.locator('#ai').click();report.events.push({n,action:'AI mode'});}
  if(n===65){await a.locator('#human').click();await a.waitForFunction(()=>koma.mode==='human');await a.locator('#acting-start').click();report.events.push({n,action:'human/start'});}
  if(n===80){await b.evaluate(()=>reviewSocket.close());report.events.push({n,action:'overlay reconnect'});}
  const rows=await Promise.all([a,b].map(p=>p.evaluate(()=>(()=>{const c=document.createElement('canvas');c.width=326;c.height=435;c.getContext('2d').drawImage(document.querySelector('#avatar'),0,0,326,435);return {image:c.toDataURL('image/jpeg',.85),acting:{...koma.acting},pose:{...koma.current},frames:koma.frames}})())));
  if(n%20===0)console.log('sync frame '+n);
  report.samples.push({frame:n,wallSeconds:(Date.now()-start)/1000,states:rows.map(({image,...s})=>s)});
  await encoder.evaluate(async({rows,n})=>{const imgs=await Promise.all(rows.map(r=>new Promise(resolve=>{const im=new Image();im.onload=()=>resolve(im);im.src=r.image})));for(let k=0;k<2;k++){const c=document.createElement('canvas');c.width=k?326:652;c.height=480;const x=c.getContext('2d');x.fillStyle='#397e91';x.fillRect(0,0,c.width,c.height);for(let i=0;i<(k?1:2);i++){x.drawImage(imgs[k?1:i],i*326,45);x.fillStyle='white';x.font='13px sans-serif';x.fillText(k?'v40 overlay':i?'Overlay / separate context':'Control Room',i*326+12,25)}const f=new VideoFrame(c,{timestamp:n*100000,duration:100000});encoders[k].encode(f,{keyFrame:n%20===0});f.close();}}, {rows,n});
  const delay=start+(n+1)*100-Date.now();if(delay>0)await new Promise(r=>setTimeout(r,delay));
 }
 report.reconnected=await b.evaluate(()=>reviewSocket.readyState===1);if(!report.reconnected)throw Error('Overlay did not reconnect');
 await a.evaluate(async()=>{await fetch('/api/control',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({source:koma.mode,parameters:{ParamMouthOpenY:.65},expression:'worried'})})});
 await Promise.all([a,b].map(p=>p.waitForFunction(()=>koma.expression.id==='worried'&&koma.current.ParamMouthOpenY>.6)));
 report.mouthAndExpression=await Promise.all([a,b].map(p=>p.evaluate(()=>({mouth:koma.current.ParamMouthOpenY,expression:koma.expression.id}))));
 if(await a.locator('#acting-stop').isEnabled())await a.locator('#acting-stop').click();await Promise.all([a,b].map(p=>p.waitForFunction(()=>koma.acting.weight===0)));
 report.settled=true;await a.screenshot({path:out+'/controller.png'});await b.screenshot({path:out+'/overlay.png'});
 const result=await encoder.evaluate(async()=>{for(const e of encoders){await e.flush();e.close()}return{buffers,desc,errors:encoderErrors}});report.errors.push(...result.errors);
 for(let k=0;k<2;k++){const bytes=muxCfr({width:k?326:652,height:480,fps:10,description:Buffer.from(result.desc[k]),chunks:result.buffers[k].map(c=>({...c,data:Buffer.from(c.data)}))});await writeFile(out+(k?'/koma-v40-overlay-sample.mp4':'/koma-v40-two-context-sync.mp4'),bytes)}
 report.note='Live UI capture at nominal 10 samples/sec; actual wall times retained. Not fixed-dt rig simulation. Separate browser contexts share only the existing server WebSocket.';
 if(report.errors.length)throw Error('Browser errors');
}catch(e){report.errors.push(e.stack);process.exitCode=1}finally{await browser?.close();server.kill();await writeFile(out+'/report.json',JSON.stringify(report,null,2));console.log(JSON.stringify({errors:report.errors,join:report.join,reconnected:report.reconnected,settled:report.settled,frames:report.samples.length}));}

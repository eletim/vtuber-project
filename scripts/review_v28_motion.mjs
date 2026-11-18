import {createRequire} from 'node:module';
import {spawn,execFileSync} from 'node:child_process';
import {writeFile,mkdir} from 'node:fs/promises';
import {resolve} from 'node:path';
const require=createRequire(import.meta.url),{chromium}=require(process.env.PLAYWRIGHT_MODULE);
const out=resolve('assets/parts/v28/review');await mkdir(out,{recursive:true});
const revision='58cfe626d254cc4262749c75d612bb33637fcca9',cache=new Map();
const server=spawn(process.env.PYTHON,[resolve('runtime/server.py'),'--port','18772'],{cwd:process.cwd(),windowsHide:true});let browser;
const report={baseline:revision,errors:[],samples:[]};
try{
 for(let i=0;i<100;i++){try{if((await fetch('http://127.0.0.1:18772/api/state')).ok)break}catch{}await new Promise(r=>setTimeout(r,100))}
 browser=await chromium.launch({headless:true,executablePath:process.env.CHROME_PATH,args:['--enable-unsafe-swiftshader']});
 const page=await browser.newPage();page.on('pageerror',e=>report.errors.push(e.message));
 await page.route('**/v28-review',r=>r.fulfill({contentType:'text/html',body:'<!doctype html><canvas></canvas>'}));
 await page.route('**/baseline/*.js',r=>{const name=new URL(r.request().url()).pathname.split('/').at(-1);if(!cache.has(name)){let code=execFileSync('git',['show',`${revision}:runtime/web/${name}`],{encoding:'utf8'});if(name==='renderer.js')code=code.replace("fetch('/model/model.json')","fetch('/baseline-model.json')");if(name==='renderer.js')code=code.replace('position.x*2.-1.,1.-position.y*2.','(position.x*2.-1.)*.94,(1.-position.y*2.)*.94');cache.set(name,code)}return r.fulfill({contentType:'text/javascript',body:cache.get(name)})});
 await page.route('**/baseline-model.json',r=>r.fulfill({contentType:'application/json',body:execFileSync('git',['show',`${revision}:runtime/model/model.json`],{encoding:'utf8'})}));
 await page.goto('http://127.0.0.1:18772/v28-review');
 await page.evaluate(async()=>{
  const modules=await Promise.all([import('/baseline/renderer.js'),import('/web/renderer.js')]),performances=await Promise.all([import('/baseline/performance.js'),import('/web/performance.js')]),{neutral}=await import('/web/controls.js');
  window.neutral=neutral;window.pair=[];window.motions=performances.map(m=>new m.PerformanceMotion());
  for(const module of modules){const r=new module.AvatarRenderer(),c=document.createElement('canvas');c.width=1086;c.height=1448;await r.load(c);pair.push(r)}
  window.input=t=>{const p=neutral();if(t>=2&&t<3.2){p.ParamBodyShiftX=-.9;p.ParamBodyAngleX=-2.7}else if(t>=3.2&&t<4.4){p.ParamBodyShiftX=.9;p.ParamBodyAngleX=2.7}if(t>=10&&t<12)p.ParamHandToCheek=(t-10)/2;else if(t>=12&&t<13)p.ParamHandToCheek=1;else if(t>=13&&t<15)p.ParamHandToCheek=(15-t)/2;return p};
  window.draw=t=>{for(let i=0;i<2;i++){const active=t>=6&&t<9.2,base=input(t),p=active?motions[i].frame(base,t,{enabled:true,emotion:'happy',started_at:6,until:9.2}):base;pair[i].render(p,t,active?'soft_smile':'neutral',{ambient:false})}};
 });
 const times=[0,1.8,2.3,2.8,3.4,4,4.4,4.8,5.3,5.8,6.15,6.4,6.7,7.1,7.5,7.9,8.5,9.2,9.6,10,10.5,11,11.3,11.5,12,13,14,14.3,14.5,15,17,18];let last=-1;
 for(const time of times){
  const result=await page.evaluate(({last,time})=>{for(let frame=Math.max(0,last+1);frame<=Math.round(time*60);frame++)draw(frame/60);const r=pair[1];return{images:pair.map(r=>r.canvas.toDataURL().split(',')[1]),body:r.rig.pose,hair:Object.fromEntries([...r.hairRig.states.entries()].map(([k,v])=>[k,v.x])),motion:r.hairRig.motion};},{last,time});last=Math.round(time*60);
  for(let i=0;i<2;i++)await writeFile(resolve(out,`pose-v${27+i}-${time}.png`),Buffer.from(result.images[i],'base64'));delete result.images;report.samples.push({time,...result});
 }
 report.faces=await page.evaluate(()=>{let t=15;return [...pair[0].expressions.keys()].map(id=>{for(let f=0;f<12;f++){t+=.05;for(const r of pair)r.render(neutral(),t,id,{ambient:false})}const layers=pair.map(r=>r.layers.find(l=>l.features)),a=layers[0].ctx.getImageData(0,0,layers[0].paint.width,layers[0].paint.height).data,b=layers[1].ctx.getImageData(0,0,layers[1].paint.width,layers[1].paint.height).data;let diff=0,faceDiff=0;for(let i=0;i<a.length;i++)if(a[i]!==b[i]){diff++;const pixel=Math.floor(i/4),x=pixel%layers[0].paint.width+layers[0].rect[0],y=Math.floor(pixel/layers[0].paint.width)+layers[0].rect[1];if(x>=350&&x<=720&&y>=180&&y<=650)faceDiff++}return{expression:id,changedHeadTextureValues:diff,changedProtectedFaceValues:faceDiff}})});
 if(!process.env.PREVIEW_ONLY){
 const videos=await page.evaluate(async()=>{
  const [{BodyRig:B0},{BodyRig:B1},{HairRig:H0},{HairRig:H1},{ArticulatedArm:A0},{ArticulatedArm:A1}]=await Promise.all([import('/baseline/body-rig.js'),import('/web/body-rig.js'),import('/baseline/hair-rig.js'),import('/web/hair-rig.js'),import('/baseline/articulated-arm.js'),import('/web/articulated-arm.js')]);
  for(let i=0;i<2;i++){const r=pair[i],weights=await(await fetch('/model/'+r.model.skinning)).json();r.rig=new [B0,B1][i](r.model,weights);r.hairRig=new [H0,H1][i](r.model,r.rig.rest);r.articulatedArm=new [A0,A1][i](r.model,r.rig.rest);motions[i].reset()}
  const results=[];
  for(let kind=0;kind<2;kind++){
   for(let i=0;i<2;i++){const r=pair[i],weights=await(await fetch('/model/'+r.model.skinning)).json();r.rig=new [B0,B1][i](r.model,weights);r.hairRig=new [H0,H1][i](r.model,r.rig.rest);r.articulatedArm=new [A0,A1][i](r.model,r.rig.rest);motions[i].reset()}
   const c=document.createElement('canvas');c.width=kind?1620:1600;c.height=kind?780:620;const ctx=c.getContext('2d');
   function paint(t){draw(t);const label=t<2?'CALM':t<4.4?'WEIGHT SHIFT':t<6?'STOP + HAIR FOLLOW':t<9.2?'ANTICIPATION + HAPPY HOPS':t<10?'STOP + SETTLE':t<15?'HAND TO CHEEK + LOWER':'SETTLE';
    const columns=kind?3:4,cw=kind?540:400;
    for(let col=0;col<columns;col++){const x=col*cw,bg=kind?['white','black','#397e91'][col]:(col>=2?'black':'white'),black=bg==='black';ctx.fillStyle=bg;ctx.fillRect(x,0,cw,c.height);ctx.drawImage(pair[kind?1:col%2].canvas,x,45,cw,1448*cw/1086);ctx.fillStyle=black?'white':'#222';ctx.font='18px sans-serif';ctx.fillText(kind?'KOMA v28':col%2?'v28 depth + clean hair':'v27 baseline',x+8,23);ctx.font='13px sans-serif';ctx.fillText(label,x+8,42)}
   }
   paint(0);const chunks=[],stream=c.captureStream(30),rec=new MediaRecorder(stream,{mimeType:'video/mp4;codecs=avc1.42001E',videoBitsPerSecond:5500000});rec.ondataavailable=e=>{if(e.data.size)chunks.push(e.data)};const done=new Promise((r,j)=>{rec.onstop=r;rec.onerror=j});await new Promise(r=>{rec.onstart=r;rec.start()});
   const start=performance.now();await new Promise(resolve=>{function tick(){const t=(performance.now()-start)/1000;paint(t);if(t<18.5)requestAnimationFrame(tick);else resolve()}tick()});rec.stop();await done;stream.getTracks().forEach(t=>t.stop());
   results.push(await new Promise(r=>{const reader=new FileReader();reader.onload=()=>r(reader.result.split(',')[1]);reader.readAsDataURL(new Blob(chunks,{type:rec.mimeType}))}));
  }
  return results;
 });
 report.videos=[];
 for(let i=0;i<2;i++){const name=i?'koma-v28-motion-sample.mp4':'koma-v27-v28-motion-comparison.mp4';await writeFile(resolve(out,name),Buffer.from(videos[i],'base64'));const check=await page.evaluate(async data=>{const v=document.createElement('video');v.muted=true;v.src=URL.createObjectURL(new Blob([Uint8Array.from(atob(data),c=>c.charCodeAt(0))],{type:'video/mp4'}));await new Promise((r,j)=>{v.onloadeddata=r;v.onerror=j});const frames=[];for(const time of [0,2.8,4.8,6.7,7.9,10,11.3,12.5,14.3,17]){if(time)await new Promise(r=>{v.onseeked=r;v.currentTime=time});const c=document.createElement('canvas');c.width=v.videoWidth;c.height=v.videoHeight;c.getContext('2d').drawImage(v,0,0);frames.push({time,data:c.toDataURL().split(',')[1]})}return{width:v.videoWidth,height:v.videoHeight,duration:v.duration,frames}},videos[i]);for(const f of check.frames)await writeFile(resolve(out,`${i?'sample':'comparison'}-${f.time}.png`),Buffer.from(f.data,'base64'));check.frames=check.frames.map(f=>f.time);report.videos.push({file:name,bytes:Buffer.from(videos[i],'base64').length,...check})}
 }
}catch(e){report.errors.push(e.stack);process.exitCode=1}finally{if(browser)await browser.close();server.kill();await writeFile(resolve(out,'review.json'),JSON.stringify(report,null,2));console.log(JSON.stringify({errors:report.errors,videos:report.videos,faces:report.faces}))}

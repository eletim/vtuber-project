import {createRequire} from 'node:module';
import {spawn,execFileSync} from 'node:child_process';
import {writeFile,mkdir} from 'node:fs/promises';
import {resolve} from 'node:path';
const require=createRequire(import.meta.url),{chromium}=require(process.env.PLAYWRIGHT_MODULE);
const out=resolve('assets/parts/v25/review');await mkdir(out,{recursive:true});
const revision='3da848cf3d58c9dc1d13c92ebab53c3ba82b1393',cache=new Map();
const server=spawn(process.env.PYTHON,[resolve('runtime/server.py'),'--port','18772'],{cwd:process.cwd(),windowsHide:true});let browser;
const report={baseline:revision,errors:[],samples:[]};
try{
 for(let i=0;i<100;i++){try{if((await fetch('http://127.0.0.1:18772/api/state')).ok)break}catch{}await new Promise(r=>setTimeout(r,100))}
 browser=await chromium.launch({headless:true,executablePath:process.env.CHROME_PATH,args:['--enable-unsafe-swiftshader']});
 const page=await browser.newPage();page.on('pageerror',e=>report.errors.push(e.message));
 await page.route('**/v25-review',r=>r.fulfill({contentType:'text/html',body:'<!doctype html><canvas></canvas>'}));
 await page.route('**/baseline/*.js',r=>{const name=new URL(r.request().url()).pathname.split('/').at(-1);if(!cache.has(name)){let code=execFileSync('git',['show',`${revision}:runtime/web/${name}`],{encoding:'utf8'});if(name==='renderer.js')code=code.replace('position.x*2.-1.,1.-position.y*2.','(position.x*2.-1.)*.94,(1.-position.y*2.)*.94');cache.set(name,code)}return r.fulfill({contentType:'text/javascript',body:cache.get(name)})});
 await page.goto('http://127.0.0.1:18772/v25-review');
 await page.evaluate(async()=>{
  const modules=await Promise.all([import('/baseline/renderer.js'),import('/web/renderer.js')]),performances=await Promise.all([import('/baseline/performance.js'),import('/web/performance.js')]),{neutral}=await import('/web/controls.js');
  window.neutral=neutral;window.pair=[];window.motions=performances.map(m=>new m.PerformanceMotion());
  for(const module of modules){const r=new module.AvatarRenderer(),c=document.createElement('canvas');c.width=1086;c.height=1448;await r.load(c);pair.push(r)}
  window.input=t=>{const p=neutral();if(t>=2&&t<3.2){p.ParamBodyShiftX=-.9;p.ParamBodyAngleX=-2.7}else if(t>=3.2&&t<4.4){p.ParamBodyShiftX=.9;p.ParamBodyAngleX=2.7}return p};
  window.draw=t=>{for(let i=0;i<2;i++){const active=t>=6&&t<9.2,base=input(t),p=active?motions[i].frame(base,t,{enabled:true,emotion:'happy',started_at:6,until:9.2}):base;pair[i].render(p,t,active?'soft_smile':'neutral',{ambient:false})}};
 });
 const times=[0,1.8,2.3,2.8,3.4,4,4.4,4.8,5.3,5.8,6.15,6.4,6.7,7.1,7.5,7.9,8.5,9.2,9.6,10,11,12,13];let last=-1;
 for(const time of times){
  const result=await page.evaluate(({last,time})=>{for(let frame=Math.max(0,last+1);frame<=Math.round(time*60);frame++)draw(frame/60);const r=pair[1];return{images:pair.map(r=>r.canvas.toDataURL().split(',')[1]),body:r.rig.pose,hair:Object.fromEntries([...r.hairRig.states.entries()].map(([k,v])=>[k,v.x])),motion:r.hairRig.motion};},{last,time});last=Math.round(time*60);
  for(let i=0;i<2;i++)await writeFile(resolve(out,`pose-v${24+i}-${time}.png`),Buffer.from(result.images[i],'base64'));delete result.images;report.samples.push({time,...result});
 }
 report.faces=await page.evaluate(()=>{let t=15;return [...pair[0].expressions.keys()].map(id=>{for(let f=0;f<12;f++){t+=.05;for(const r of pair)r.render(neutral(),t,id,{ambient:false})}const layers=pair.map(r=>r.layers.find(l=>l.features)),a=layers[0].ctx.getImageData(0,0,layers[0].paint.width,layers[0].paint.height).data,b=layers[1].ctx.getImageData(0,0,layers[1].paint.width,layers[1].paint.height).data;let diff=0;for(let i=0;i<a.length;i++)if(a[i]!==b[i])diff++;return{expression:id,changedFaceValues:diff}})});
 const videos=await page.evaluate(async()=>{
  const [{BodyRig:B0},{BodyRig:B1},{HairRig:H0},{HairRig:H1},{ArticulatedArm:A0},{ArticulatedArm:A1}]=await Promise.all([import('/baseline/body-rig.js'),import('/web/body-rig.js'),import('/baseline/hair-rig.js'),import('/web/hair-rig.js'),import('/baseline/articulated-arm.js'),import('/web/articulated-arm.js')]);
  for(let i=0;i<2;i++){const r=pair[i],weights=await(await fetch('/model/'+r.model.skinning)).json();r.rig=new [B0,B1][i](r.model,weights);r.hairRig=new [H0,H1][i](r.model,r.rig.rest);r.articulatedArm=new [A0,A1][i](r.model,r.rig.rest);motions[i].reset()}
  const compare=document.createElement('canvas'),single=document.createElement('canvas');compare.width=1600;compare.height=620;single.width=1086;single.height=780;
  const cx=compare.getContext('2d'),sx=single.getContext('2d'),entries=[compare,single].map(c=>{const chunks=[],stream=c.captureStream(30),rec=new MediaRecorder(stream,{mimeType:'video/mp4;codecs=avc1.42001E',videoBitsPerSecond:5500000});rec.ondataavailable=e=>{if(e.data.size)chunks.push(e.data)};const done=new Promise((r,j)=>{rec.onstop=r;rec.onerror=j});return{chunks,stream,rec,done}});entries.forEach(e=>e.rec.start());
  const start=performance.now();await new Promise(resolve=>{function tick(){const t=(performance.now()-start)/1000;draw(t);const label=t<2?'CALM':t<4.4?'WEIGHT SHIFT':t<6?'STOP + HAIR FOLLOW':t<9.2?'ANTICIPATION + HAPPY HOPS':'STOP + SETTLE';
   for(let col=0;col<4;col++){const x=col*400,black=col>=2;cx.fillStyle=black?'black':'white';cx.fillRect(x,0,400,620);cx.drawImage(pair[col%2].canvas,x,45,400,1448*400/1086);cx.fillStyle=black?'white':'#222';cx.font='18px sans-serif';cx.fillText(col%2?'v25 body-driven hair':'v24 baseline',x+8,23);cx.font='13px sans-serif';cx.fillText(label,x+8,42)}
   for(let col=0;col<2;col++){const x=col*543,black=col===1;sx.fillStyle=black?'black':'white';sx.fillRect(x,0,543,780);sx.drawImage(pair[1].canvas,x,40,543,724);sx.fillStyle=black?'white':'#222';sx.font='16px sans-serif';sx.fillText('KOMA v25 / '+label,x+12,25)}
   if(t<13.5)requestAnimationFrame(tick);else resolve()}tick()});entries.forEach(e=>e.rec.stop());await Promise.all(entries.map(e=>e.done));
  return await Promise.all(entries.map(async e=>{e.stream.getTracks().forEach(t=>t.stop());return await new Promise(r=>{const reader=new FileReader();reader.onload=()=>r(reader.result.split(',')[1]);reader.readAsDataURL(new Blob(e.chunks,{type:e.rec.mimeType}))})}));
 });
 report.videos=[];
 for(let i=0;i<2;i++){const name=i?'koma-v25-motion-sample.mp4':'koma-v24-v25-motion-comparison.mp4';await writeFile(resolve(out,name),Buffer.from(videos[i],'base64'));const check=await page.evaluate(async data=>{const v=document.createElement('video');v.muted=true;v.src=URL.createObjectURL(new Blob([Uint8Array.from(atob(data),c=>c.charCodeAt(0))],{type:'video/mp4'}));await new Promise((r,j)=>{v.onloadeddata=r;v.onerror=j});const frames=[];for(const time of [0,2.8,4.8,6.7,7.9,10,12.5]){if(time)await new Promise(r=>{v.onseeked=r;v.currentTime=time});const c=document.createElement('canvas');c.width=v.videoWidth;c.height=v.videoHeight;c.getContext('2d').drawImage(v,0,0);frames.push({time,data:c.toDataURL().split(',')[1]})}return{width:v.videoWidth,height:v.videoHeight,duration:v.duration,frames}},videos[i]);for(const f of check.frames)await writeFile(resolve(out,`${i?'sample':'comparison'}-${f.time}.png`),Buffer.from(f.data,'base64'));check.frames=check.frames.map(f=>f.time);report.videos.push({file:name,bytes:Buffer.from(videos[i],'base64').length,...check})}
}catch(e){report.errors.push(e.stack);process.exitCode=1}finally{if(browser)await browser.close();server.kill();await writeFile(resolve(out,'review.json'),JSON.stringify(report,null,2));console.log(JSON.stringify({errors:report.errors,videos:report.videos,faces:report.faces}))}

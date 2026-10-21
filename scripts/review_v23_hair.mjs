import {createRequire} from 'node:module';
import {spawn,execFileSync} from 'node:child_process';
import {writeFile,mkdir} from 'node:fs/promises';
import {resolve} from 'node:path';
const require=createRequire(import.meta.url),{chromium}=require(process.env.PLAYWRIGHT_MODULE);
const root=process.cwd(),out=resolve('assets/parts/v23/review');await mkdir(out,{recursive:true});
const baseline=execFileSync('git',['show','d7d37e37647a114b13476176145ccce9b239d4e9:runtime/web/hair-rig.js'],{encoding:'utf8'});
const server=spawn(process.env.PYTHON,[resolve('runtime/server.py'),'--port','18771'],{cwd:root,windowsHide:true});let browser;
const report={errors:[],baseline:'d7d37e37647a114b13476176145ccce9b239d4e9',frames:[],peaks:{v22:{},v23:{}}};
try {
 for(let i=0;i<100;i++){try{if((await fetch('http://127.0.0.1:18771/api/state')).ok)break;}catch{}await new Promise(r=>setTimeout(r,100));}
 browser=await chromium.launch({headless:true,executablePath:process.env.CHROME_PATH,args:['--enable-unsafe-swiftshader']});
 const page=await browser.newPage();page.on('pageerror',e=>report.errors.push(e.message));
 await page.route('**/v23-review',route=>route.fulfill({contentType:'text/html',body:'<!doctype html><canvas></canvas>'}));
 await page.route('**/web/hair-rig-v22.js',route=>route.fulfill({contentType:'text/javascript',body:baseline}));
 await page.goto('http://127.0.0.1:18771/v23-review');
 await page.evaluate(async()=>{
  const {AvatarRenderer}=await import('/web/renderer.js'),{HairRig:OldHair}=await import('/web/hair-rig-v22.js'),{neutral}=await import('/web/controls.js');
  window.pose=neutral();window.pair=[];
  for(let i=0;i<2;i++){const r=new AvatarRenderer(),c=document.createElement('canvas');c.width=1086;c.height=1448;await r.load(c);if(!i)r.hairRig=new OldHair(r.model,r.rig.rest);pair.push(r)}
 });
 const metrics=await page.evaluate(()=>{const peaks=[{},{}];let rootDelta=0;for(let f=0;f<=600;f++){const t=f/60;for(let n=0;n<2;n++){const r=pair[n];r.render(pose,t,'neutral');for(const layer of r.model.bodyLayers.filter(l=>l.hairMotion)){const points=r.hairRig.geometry.get(layer.id),head=r.rig.positionsByRole.head;let peak=0;for(let i=0;i<points.length;i+=2){const dx=Math.abs(points[i]-head[i])*1086;peak=Math.max(peak,dx);if(r.rig.rest[i+1]*1448<=layer.hairMotion.rootY)rootDelta=Math.max(rootDelta,dx,Math.abs(points[i+1]-head[i+1])*1448)}peaks[n][layer.id]=Math.max(peaks[n][layer.id]||0,peak)}}}return{peaks,rootDelta}});
 report.peaks={v22:metrics.peaks[0],v23:metrics.peaks[1]};report.rootDelta=metrics.rootDelta;
 // Fresh instances give identical time origins for both versions.
 await page.evaluate(async()=>{const {HairRig}=await import('/web/hair-rig.js'),{HairRig:OldHair}=await import('/web/hair-rig-v22.js');pair[0].hairRig=new OldHair(pair[0].model,pair[0].rig.rest);pair[1].hairRig=new HairRig(pair[1].model,pair[1].rig.rest)});
 for(let frame=0;frame<=20;frame++){
  const data=await page.evaluate(frame=>{for(let f=Math.max(0,(frame-1)*30+1);f<=frame*30;f++){const t=f/60;for(const r of pair)r.render(pose,t,'neutral',{onlyRoles:['head']})}return pair.map(r=>r.canvas.toDataURL().split(',')[1])},frame);
  for(let n=0;n<2;n++)await writeFile(resolve(out,`head-v${22+n}-${frame.toString().padStart(2,'0')}.png`),Buffer.from(data[n],'base64'));
  report.frames.push(frame/2);
 }
 report.facePreservation=await page.evaluate(()=>{const rows=[];let t=12;for(const id of pair[0].expressions.keys()){for(let i=0;i<12;i++){t+=.05;for(const r of pair)r.render({...pose,ParamHandToCheek:.5},t,id)}const a=pair[0].layers.find(l=>l.features),b=pair[1].layers.find(l=>l.features),x=a.ctx.getImageData(0,0,a.paint.width,a.paint.height).data,y=b.ctx.getImageData(0,0,b.paint.width,b.paint.height).data;let changed=0;for(let i=0;i<x.length;i++)if(x[i]!==y[i])changed++;rows.push({expression:id,changedFaceTextureValues:changed})}return rows});
 const movie=await page.evaluate(async()=>{
  const {HairRig}=await import('/web/hair-rig.js'),{HairRig:OldHair}=await import('/web/hair-rig-v22.js');pair[0].hairRig=new OldHair(pair[0].model,pair[0].rig.rest);pair[1].hairRig=new HairRig(pair[1].model,pair[1].rig.rest);
  const canvas=document.createElement('canvas');canvas.width=1600;canvas.height=560;const ctx=canvas.getContext('2d'),stream=canvas.captureStream(30),mime='video/mp4;codecs=avc1.42001E';if(!MediaRecorder.isTypeSupported(mime))throw Error('MP4 encoder unavailable');
  const chunks=[],rec=new MediaRecorder(stream,{mimeType:mime,videoBitsPerSecond:6000000});rec.ondataavailable=e=>{if(e.data.size)chunks.push(e.data)};const done=new Promise((r,j)=>{rec.onstop=r;rec.onerror=j});rec.start();
  const start=performance.now();await new Promise(resolve=>{function frame(){const t=(performance.now()-start)/1000,p={...pose,ParamHandToCheek:t<1?0:t<5?1:0,ParamAngleZ:Math.sin(t*.7)*1.2,ParamBodyAngleX:Math.sin(t*.6)*.5};for(const r of pair)r.render(p,t,t<4?'neutral':t<7?'soft_smile':'thinking');
   for(let col=0;col<4;col++){const x=col*400,black=col>=2,r=pair[col%2];ctx.fillStyle=black?'black':'white';ctx.fillRect(x,0,400,560);ctx.drawImage(r.canvas,100,0,900,1100,x,36,400,1100*400/900);ctx.fillStyle=black?'white':'#333';ctx.font='20px sans-serif';ctx.fillText(col%2?'v23 stronger hair':'v22 original hair',x+10,25)}
   if(t<10)requestAnimationFrame(frame);else resolve()}frame()});rec.stop();await done;stream.getTracks().forEach(t=>t.stop());return await new Promise(r=>{const reader=new FileReader();reader.onload=()=>r({data:reader.result.split(',')[1],mime:rec.mimeType});reader.readAsDataURL(new Blob(chunks,{type:rec.mimeType}))});
 });
 const moviePath=resolve(out,'koma-v22-v23-hair-comparison.mp4');await writeFile(moviePath,Buffer.from(movie.data,'base64'));report.video={file:moviePath,mime:movie.mime,bytes:Buffer.from(movie.data,'base64').length};
 report.decode=await page.evaluate(async data=>{const v=document.createElement('video');v.muted=true;v.src=URL.createObjectURL(new Blob([Uint8Array.from(atob(data),c=>c.charCodeAt(0))],{type:'video/mp4'}));await new Promise((r,j)=>{v.onloadeddata=r;v.onerror=j});const frames=[];for(const t of [0,1,2,4,6,8,9.5]){if(t)await new Promise(r=>{v.onseeked=r;v.currentTime=t});const c=document.createElement('canvas');c.width=v.videoWidth;c.height=v.videoHeight;c.getContext('2d').drawImage(v,0,0);frames.push({time:v.currentTime,data:c.toDataURL().split(',')[1]})}return{width:v.videoWidth,height:v.videoHeight,duration:v.duration,frames}},movie.data);
 for(const f of report.decode.frames)await writeFile(resolve(out,`comparison-${f.time}.png`),Buffer.from(f.data,'base64'));report.decode.frames=report.decode.frames.map(f=>f.time);
}catch(e){report.errors.push(e.stack);process.exitCode=1}
finally{if(browser)await browser.close();server.kill();await writeFile(resolve(out,'review.json'),JSON.stringify(report,null,2));console.log(JSON.stringify(report))}

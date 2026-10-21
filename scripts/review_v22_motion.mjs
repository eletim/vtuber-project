import {createRequire} from 'node:module';
import {spawn} from 'node:child_process';
import {writeFile,mkdir,readFile} from 'node:fs/promises';
import {resolve} from 'node:path';
const require=createRequire(import.meta.url),{chromium}=require(process.env.PLAYWRIGHT_MODULE);
const root=process.cwd(),out=resolve(root,'assets/parts/v22/motion-review');await mkdir(out,{recursive:true});
const server=spawn(process.env.PYTHON,[resolve(root,'runtime/server.py'),'--port','18770'],{cwd:root,windowsHide:true});let browser;
const report=(process.env.AUDIT_ONLY||process.env.JOINT_ONLY)?JSON.parse(await readFile(resolve(out,'review.json'),'utf8')):{errors:[],poses:[]};
try {
 for(let i=0;i<100;i++){try{if((await fetch('http://127.0.0.1:18770/api/state')).ok)break;}catch{}await new Promise(r=>setTimeout(r,100));}
 browser=await chromium.launch({headless:true,executablePath:process.env.CHROME_PATH,args:['--enable-unsafe-swiftshader']});
 const page=await browser.newPage({viewport:{width:652,height:869},deviceScaleFactor:1});
 page.on('pageerror',e=>report.errors.push(e.message));
 await page.route('**/v22-review',route=>route.fulfill({contentType:'text/html',body:'<!doctype html><style>body{margin:0;background:white}canvas{display:block;width:652px;height:869px}</style><canvas id="avatar" width="1086" height="1448"></canvas>'}));
 await page.goto('http://127.0.0.1:18770/v22-review');
 await page.evaluate(async()=>{const {AvatarRenderer}=await import('/web/renderer.js');const {neutral}=await import('/web/controls.js');window.pose=neutral();window.r=new AvatarRenderer();await r.load(document.querySelector('canvas'));});
 if(process.env.JOINT_ONLY){
  report.isolatedArmFrames=[];
  for(let i=0;i<=20;i++){
   const amount=i/20,data=await page.evaluate(amount=>{r.render({...pose,ParamHandToCheek:amount},0,'neutral',{snapArticulation:true,ambient:false,onlyRoles:['armLeft']});return r.canvas.toDataURL().split(',')[1];},amount);
   const file=`arm-isolated-${i.toString().padStart(2,'0')}.png`;await writeFile(resolve(out,file),Buffer.from(data,'base64'));report.isolatedArmFrames.push({amount,file});
  }
  for(const time of [0,1,2,3,4]){
   const data=await page.evaluate(time=>{for(let t=r.hairRig.last??0;t<=time+.00001;t+=1/60)r.render(pose,t,'neutral',{onlyRoles:['head']});return r.canvas.toDataURL().split(',')[1];},time);
   await writeFile(resolve(out,`hair-alpha-${time}.png`),Buffer.from(data,'base64'));
  }
  const oldModel=await readFile(resolve(root,'assets/parts/v22/model-before-v22.json'),'utf8');
  await page.route('**/model/model.json',route=>route.fulfill({contentType:'application/json',body:oldModel}));
  const original=await page.evaluate(async()=>{const {AvatarRenderer}=await import('/web/renderer.js');const old=new AvatarRenderer(),c=document.createElement('canvas');c.width=1086;c.height=1448;await old.load(c);old.render(pose,0,'neutral',{ambient:false,onlyRoles:['head']});return c.toDataURL().split(',')[1];});
  await writeFile(resolve(out,'hair-alpha-v19-reference.png'),Buffer.from(original,'base64'));
 }else{
 if(!process.env.AUDIT_ONLY){
 for(const bg of ['white','black'])for(const amount of [0,.25,.5,.75,1]){
  const joints=await page.evaluate(({amount,bg})=>{document.body.style.background=bg;r.render({...pose,ParamHandToCheek:amount},0,'neutral',{snapArticulation:true,ambient:false});return r.articulatedArm.joints;},{amount,bg});
  await page.screenshot({path:resolve(out,`arm-${bg}-${amount}.png`)});report.poses.push({bg,amount,joints});
 }
 for(const time of [0,1,2,3,4]){
  await page.evaluate(time=>{document.body.style.background='white';for(let t=r.hairRig.last??0;t<=time;t+=1/60)r.render({...pose,ParamHandToCheek:1},t,'neutral',{snapArticulation:true});},time);
  await page.screenshot({path:resolve(out,`hair-${time}.png`)});
 }
 let clock=10;
 report.expressionCombinations=[];
 const expressionIds=await page.evaluate(()=>[...r.expressions.keys()]);
 for(const expression of expressionIds)for(const amount of [0,.5,1])for(const bg of ['white','black']){
  clock+=.6;
  await page.evaluate(({expression,amount,bg,clock})=>{document.body.style.background=bg;for(let i=0;i<=10;i++)r.render({...pose,ParamHandToCheek:amount},clock+i/20,expression,{snapArticulation:true});},{expression,amount,bg,clock});
  await page.screenshot({path:resolve(out,`expression-${expression}-${amount}-${bg}.png`)});
  report.expressionCombinations.push({expression,amount,bg});
 }
 const video=await page.evaluate(async()=>{
  const {AvatarRenderer}=await import('/web/renderer.js');r=new AvatarRenderer();await r.load(document.querySelector('#avatar'));
  const movie=document.createElement('canvas');movie.width=1304;movie.height=910;const ctx=movie.getContext('2d');
  const stream=movie.captureStream(30),chunks=[],recorder=new MediaRecorder(stream,{mimeType:'video/webm;codecs=vp9',videoBitsPerSecond:4500000});
  recorder.ondataavailable=e=>{if(e.data.size)chunks.push(e.data);};const stopped=new Promise(resolve=>recorder.onstop=resolve);recorder.start();
  const start=performance.now();
  await new Promise(resolve=>{function frame(){const t=(performance.now()-start)/1000;
   const target=t<1?0:t<5?1:0;
   r.render({...pose,ParamHandToCheek:target,ParamAngleZ:Math.sin(t*.7)*1.2,ParamBodyAngleX:Math.sin(t*.6)*.5},t,t<4?'neutral':t<7?'soft_smile':'thinking');
   ctx.fillStyle='white';ctx.fillRect(0,0,652,910);ctx.fillStyle='black';ctx.fillRect(652,0,652,910);
   ctx.drawImage(r.canvas,0,35,652,869);ctx.drawImage(r.canvas,652,35,652,869);
   ctx.font='18px sans-serif';ctx.fillStyle='#333';ctx.fillText('KOMA v22 / articulated arm + 12 hair strands',12,24);ctx.fillStyle='white';ctx.fillText('Actual headless Chrome / black background',666,24);
   if(t<11)requestAnimationFrame(frame);else resolve();}frame();});
  recorder.stop();await stopped;for(const track of stream.getTracks())track.stop();
  return await new Promise(resolve=>{const reader=new FileReader();reader.onload=()=>resolve(reader.result.split(',')[1]);reader.readAsDataURL(new Blob(chunks,{type:'video/webm'}));});
 });
 await writeFile(resolve(out,'koma-v22-arm-hair-motion.webm'),Buffer.from(video,'base64'));
 report.video={file:'koma-v22-arm-hair-motion.webm',seconds:11,actualBrowser:true,backgrounds:['white','black']};
 }
 const bind=await page.evaluate(async()=>{const {AvatarRenderer}=await import('/web/renderer.js');const bindRenderer=new AvatarRenderer(),canvas=document.createElement('canvas');canvas.width=1086;canvas.height=1448;await bindRenderer.load(canvas);bindRenderer.render({...pose,ParamHandToCheek:1},0,'neutral',{snapArticulation:true,ambient:false});return canvas.toDataURL().split(',')[1];});
 await writeFile(resolve(out,'browser-bind-pose.png'),Buffer.from(bind,'base64'));
 const originalModel=await readFile(resolve(root,'assets/parts/v22/model-before-v22.json'),'utf8');
 await page.route('**/model/model.json',route=>route.fulfill({contentType:'application/json',body:originalModel}));
 report.facePreservation=await page.evaluate(async()=>{
  const {AvatarRenderer}=await import('/web/renderer.js'),ref=new AvatarRenderer(),canvas=document.createElement('canvas');canvas.width=1086;canvas.height=1448;await ref.load(canvas);
  const rows=[];let t=30;
  for(const id of r.expressions.keys()){
   for(let i=0;i<12;i++){t+=.05;r.render(pose,t,id,{ambient:false});ref.render(pose,t,id,{ambient:false});}
   const current=r.layers.find(l=>l.features),old=ref.layers.find(l=>l.features);
   const regions={mouth:[461,314,617,424],leftEye:[450,280,530,325],rightEye:[580,250,650,290]},values={expression:id};
   for(const [name,[x0,y0,x1,y1]] of Object.entries(regions)){
    const a=current.ctx.getImageData(x0-current.rect[0],y0-current.rect[1],x1-x0,y1-y0).data,b=old.ctx.getImageData(x0-old.rect[0],y0-old.rect[1],x1-x0,y1-y0).data;
    let changed=0;for(let i=0;i<a.length;i++)if(a[i]!==b[i])changed++;values[name+'ChangedValues']=changed;
   }
   rows.push(values);
  }
  return rows;
 });
 await page.unroute('**/model/model.json');
 const app=await browser.newPage({viewport:{width:1380,height:1100}});app.on('pageerror',e=>report.errors.push(e.message));
 await app.goto('http://127.0.0.1:18770/');await app.waitForFunction(()=>window.koma?.frames>5);
 await app.locator('#cheek-gesture').click();
 await app.waitForFunction(()=>window.koma.renderer.articulatedArm.amount>.8,{},{timeout:12000});
 report.control={buttonRaises:true,mode:await app.evaluate(()=>window.koma.mode)};
 await app.locator('#reset').click();await app.waitForFunction(()=>window.koma.renderer.articulatedArm.amount<.01,{},{timeout:12000});report.control.resetLowers=true;await app.close();
 const painted=await page.evaluate(()=>r.layers.find(l=>l.features).paint.toDataURL().split(',')[1]);
 await writeFile(resolve(out,'face-painted-debug.png'),Buffer.from(painted,'base64'));
 const isolation=await page.evaluate(()=>{const all=r.layers;r.layers=all.filter(l=>l.features);r.render(pose,5,'neutral',{ambient:false});const data=r.canvas.toDataURL().split(',')[1];r.layers=all;return data;});
 await writeFile(resolve(out,'face-isolation-debug.png'),Buffer.from(isolation,'base64'));
 report.layers=await page.evaluate(()=>r.layers.map(l=>({id:l.id,rect:l.rect,hair:l.hairMotion})));
 report.accessoryAudit=await page.evaluate(()=>{const all=r.layers,result=[];for(let n=1;n<=all.length;n++){r.layers=all.slice(0,n);r.render({...pose,ParamHandToCheek:1},5,'neutral',{snapArticulation:true,ambient:false});const pixel=new Uint8Array(4);r.gl.readPixels(730,1448-220,1,1,r.gl.RGBA,r.gl.UNSIGNED_BYTE,pixel);result.push([all[n-1].id,...pixel]);}r.layers=all;return result;});
 }
}catch(e){report.errors.push(e.stack);process.exitCode=1;}
finally{if(browser)await browser.close();server.kill();await writeFile(resolve(out,'review.json'),JSON.stringify(report,null,2));console.log(JSON.stringify(report));}

import {createRequire} from 'node:module';
import {spawn,execFileSync} from 'node:child_process';
import {writeFile,mkdir} from 'node:fs/promises';
import {resolve} from 'node:path';
const require=createRequire(import.meta.url),{chromium}=require(process.env.PLAYWRIGHT_MODULE);
const acting=false;const out=resolve('assets/parts/v44/final-shoulder-probe');await mkdir(out,{recursive:true});
const revision='225fe5499ea8a81447b273a896516088d3943fae',cache=new Map();
const server=spawn(process.env.PYTHON,[resolve('runtime/server.py'),'--port','18781'],{cwd:process.cwd(),windowsHide:true});let browser;
const report={baseline:revision,scenario:'Same start time and camera; each version uses its own normal UI acting controller/sequence. Includes choreography and rig differences.',errors:[],samples:[]};
try{
 for(let i=0;i<100;i++){try{if((await fetch('http://127.0.0.1:18781/api/state')).ok)break}catch{}await new Promise(r=>setTimeout(r,100))}
 browser=await chromium.launch({headless:true,executablePath:process.env.CHROME_PATH,args:['--enable-unsafe-swiftshader']});
 const page=await browser.newPage();page.on('pageerror',e=>report.errors.push(e.message));
 await page.route('**/v44-review',r=>r.fulfill({contentType:'text/html',body:'<!doctype html><canvas></canvas>'}));
 await page.route('**/baseline/*.js',r=>{const name=new URL(r.request().url()).pathname.split('/').at(-1);if(!cache.has(name)){let code=execFileSync('git',['show',`${revision}:runtime/web/${name}`],{encoding:'utf8'});if(name==='renderer.js')code=code.replace("fetch('/model/model.json')","fetch('/baseline-model.json')");if(name==='renderer.js')code=code.replace('position.x*2.-1.,1.-position.y*2.','(position.x*2.-1.)*.94,(1.-position.y*2.)*.94');cache.set(name,code)}return r.fulfill({contentType:'text/javascript',body:cache.get(name)})});
 await page.route('**/baseline-model.json',r=>r.fulfill({contentType:'application/json',body:execFileSync('git',['show',`${revision}:runtime/model/model.json`],{encoding:'utf8'})}));
 await page.goto('http://127.0.0.1:18781/v44-review');
 await page.evaluate(async()=>{
  const modules=await Promise.all([import('/baseline/renderer.js'),import('/web/renderer.js')]),performances=await Promise.all([import('/baseline/performance.js'),import('/web/performance.js')]),{neutral}=await import('/web/controls.js');
  window.neutral=neutral;window.pair=[];window.motions=performances.map(m=>new m.PerformanceMotion());
  for(const module of modules){const r=new module.AvatarRenderer(),c=document.createElement('canvas');c.width=1086;c.height=1448;await r.load(c);pair.push(r)}
  window.input=t=>{const p=neutral();if(t>=2&&t<3.2){p.ParamBodyShiftX=-.9;p.ParamBodyAngleX=-2.7}else if(t>=3.2&&t<4.4){p.ParamBodyShiftX=.9;p.ParamBodyAngleX=2.7}if(t>=10&&t<12)p.ParamHandToCheek=(t-10)/2;else if(t>=12&&t<13)p.ParamHandToCheek=1;else if(t>=13&&t<15)p.ParamHandToCheek=(15-t)/2;return p};
  window.draw=(t,only=-1)=>{for(let i=0;i<2;i++){if(only>=0&&i!==only)continue;const active=t>=6&&t<9.2,base=input(t),p=active?motions[i].frame(base,t,{enabled:true,emotion:'happy',started_at:6,until:9.2}):base;pair[i].render(p,t,active?'soft_smile':'neutral',{ambient:false})}};
 });
 await page.evaluate(async()=>{
  const {performanceSequence}=await import('/web/performance-sequence.js'),{ActingController}=await import('/web/acting-controller.js');
  const controller=new ActingController();controller.start(0);const {ActingController:OldController}=await import('/baseline/acting-controller.js');const oldController=new OldController();oldController.start(0);
  window.draw=t=>{
   const live=controller.frame(neutral(),t);
   // Identical new controller inputs isolate the rig changes from choreography.
   const before=oldController.frame(neutral(),t);pair[0].render(before.pose,t,before.expression,{ambient:false});pair[1].render(live.pose,t,live.expression,{ambient:false});
  };
 });
 await page.evaluate(async()=>{
  window.encoders=[];window.encoded=[[],[]];window.descriptions=[];window.encodeErrors=[];window.audit=[];
  window.outputCanvases=[document.createElement('canvas'),document.createElement('canvas')];
  for(let kind=0;kind<2;kind++){
   const c=outputCanvases[kind];c.width=kind?1620:1600;c.height=kind?780:620;
   const encoder=new VideoEncoder({error:e=>encodeErrors.push(e.message),output:(chunk,meta)=>{const data=new Uint8Array(chunk.byteLength);chunk.copyTo(data);let s='';for(const byte of data)s+=String.fromCharCode(byte);encoded[kind].push({timestamp:chunk.timestamp,type:chunk.type,data:btoa(s)});if(meta.decoderConfig?.description)descriptions[kind]=Array.from(new Uint8Array(meta.decoderConfig.description));}});
   const config={codec:'avc1.420028',width:c.width,height:c.height,framerate:30,bitrate:4500000,latencyMode:'realtime',avc:{format:'avc'}};
   if(!(await VideoEncoder.isConfigSupported(config)).supported)throw Error('AVC encoding unavailable');encoder.configure(config);encoders.push(encoder);
  }
  window.captureFrame=async frame=>{
   // Both versions start at t=0 and integrate the same 1/60s input sequence.
   if(frame===0)draw(0);else{draw((frame*2-1)/60);draw(frame*2/60)}
   const t=frame/30;
   for(let kind=0;kind<2;kind++){
    const c=outputCanvases[kind],ctx=c.getContext('2d'),cw=kind?540:400;
    for(let col=0;col<(kind?3:4);col++){
     const bg=kind?['white','black','#397e91'][col]:(col>=2?'black':'white');ctx.fillStyle=bg;ctx.fillRect(col*cw,0,cw,c.height);ctx.drawImage(pair[kind?1:col%2].canvas,col*cw,45,cw,1448*cw/1086);
     ctx.fillStyle=bg==='black'?'white':'#222';ctx.font='18px sans-serif';ctx.fillText(kind?'KOMA v44 / full acting phrase':col%2?'v44 new acting':'v43 original acting',col*cw+8,23);ctx.font='13px sans-serif';ctx.fillText(`frame ${frame} / t=${t.toFixed(3)}s / 30 fps`,col*cw+8,42);
    }
    const videoFrame=new VideoFrame(c,{timestamp:Math.round(frame*1e6/30),duration:Math.round((frame+1)*1e6/30)-Math.round(frame*1e6/30)});encoders[kind].encode(videoFrame,{keyFrame:frame%60===0});videoFrame.close();
   }
   audit.push({frame,time:t,physicsStep:frame*2,versions:pair.map(r=>({armAmount:r.articulatedArm.amount,joints:r.articulatedArm.joints,body:r.rig.pose,cuffAlpha:r.articulatedArm.opacity(r.model.bodyLayers.find(l=>l.id==='left_raised_cuff')),hair:Object.fromEntries([...r.hairRig.states].map(([id,s])=>[id,s.x]))}))});
   while(encoders.some(e=>e.encodeQueueSize>4))await new Promise(r=>setTimeout(r,5));if(encodeErrors.length)throw Error(encodeErrors.join(';'));
  };
 });
 for(let start=0;start<90;start+=15){await page.evaluate(async start=>{for(let i=start;i<Math.min(start+15,90);i++)await captureFrame(i)},start);if([60,180,330,420,480].includes(start)){const png=await page.evaluate(()=>pair[1].canvas.toDataURL().split(',')[1]);await writeFile(resolve(out,'native-'+(start+14)+'.png'),Buffer.from(png,'base64'));}if(start%60===0)console.log('rendered '+Math.min(start+15,555)+'/555');}
 report.probeOnly=true;
}catch(e){report.errors.push(e.stack);process.exitCode=1}finally{if(browser)await browser.close();server.kill();await writeFile(resolve(out,'capture-report.json'),JSON.stringify(report,null,2));console.log(JSON.stringify({errors:report.errors,videos:report.videos}))}

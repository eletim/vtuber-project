import {createRequire} from 'node:module';
import {spawn,execFileSync} from 'node:child_process';
import {writeFile,mkdir} from 'node:fs/promises';
import {resolve} from 'node:path';
const require=createRequire(import.meta.url),{chromium}=require(process.env.PLAYWRIGHT_MODULE);
const probe=process.env.NATIVE_PROBE==='1';const out=resolve('assets/parts/v36/'+(probe?'probe-review':'native-review'));await mkdir(out,{recursive:true});
const revision='083379ad775a72ab1758025d42e1d8c195b88fa7',cache=new Map();
const server=spawn(process.env.PYTHON,[resolve('runtime/server.py'),'--port','18774'],{cwd:process.cwd(),windowsHide:true});let browser;
const report={baseline:revision,errors:[],samples:[]};
try{
 for(let i=0;i<100;i++){try{if((await fetch('http://127.0.0.1:18774/api/state')).ok)break}catch{}await new Promise(r=>setTimeout(r,100))}
 browser=await chromium.launch({headless:true,executablePath:process.env.CHROME_PATH,args:['--enable-unsafe-swiftshader']});
 const page=await browser.newPage();page.on('pageerror',e=>report.errors.push(e.message));
 await page.route('**/v36-review',r=>r.fulfill({contentType:'text/html',body:'<!doctype html><canvas></canvas>'}));
 await page.route('**/baseline/*.js',r=>{const name=new URL(r.request().url()).pathname.split('/').at(-1);if(!cache.has(name)){let code=execFileSync('git',['show',`${revision}:runtime/web/${name}`],{encoding:'utf8'});if(name==='renderer.js')code=code.replace("fetch('/model/model.json')","fetch('/baseline-model.json')");if(name==='renderer.js')code=code.replace('position.x*2.-1.,1.-position.y*2.','(position.x*2.-1.)*.94,(1.-position.y*2.)*.94');cache.set(name,code)}return r.fulfill({contentType:'text/javascript',body:cache.get(name)})});
 await page.route('**/baseline-model.json',r=>r.fulfill({contentType:'application/json',body:execFileSync('git',['show',`${revision}:runtime/model/model.json`],{encoding:'utf8'})}));
 await page.goto('http://127.0.0.1:18774/v36-review');
 await page.evaluate(async()=>{
  const modules=await Promise.all([import('/baseline/renderer.js'),import('/web/renderer.js')]),performances=await Promise.all([import('/baseline/performance.js'),import('/web/performance.js')]),{neutral}=await import('/web/controls.js');
  window.neutral=neutral;window.pair=[];window.motions=performances.map(m=>new m.PerformanceMotion());
  for(const module of modules){const r=new module.AvatarRenderer(),c=document.createElement('canvas');c.width=1086;c.height=1448;await r.load(c);pair.push(r)}
  window.input=t=>{const p=neutral();if(t>=2&&t<3.2){p.ParamBodyShiftX=-.9;p.ParamBodyAngleX=-2.7}else if(t>=3.2&&t<4.4){p.ParamBodyShiftX=.9;p.ParamBodyAngleX=2.7}if(t>=10&&t<12)p.ParamHandToCheek=(t-10)/2;else if(t>=12&&t<13)p.ParamHandToCheek=1;else if(t>=13&&t<15)p.ParamHandToCheek=(15-t)/2;return p};
  window.draw=(t,only=-1)=>{for(let i=0;i<2;i++){if(only>=0&&i!==only)continue;const active=t>=6&&t<9.2,base=input(t),p=active?motions[i].frame(base,t,{enabled:true,emotion:'happy',started_at:6,until:9.2}):base;pair[i].render(p,t,active?'soft_smile':'neutral',{ambient:false})}};
 });

 for(let frame=0;frame<=480;frame++){
  const image=await page.evaluate(([frame,probe])=>{
   if(frame===0)draw(0);else{draw((frame*2-1)/60);draw(frame*2/60)}
   if(frame<300||(probe&&![324,330,351,414,438,444].includes(frame)))return null;
   const c=document.createElement('canvas');c.width=1000;c.height=920;const ctx=c.getContext('2d');
   ctx.fillStyle='#397e91';ctx.fillRect(0,0,1000,920);
   for(let side=0;side<2;side++){ctx.drawImage(pair[side].canvas,150,400,500,900,side*500,20,500,900);ctx.fillStyle='white';ctx.font='15px sans-serif';ctx.fillText((side?'v36':'v35')+' native pixels / '+(frame/30).toFixed(3)+'s',side*500+5,16);}
   return c.toDataURL('image/png').split(',')[1];
  },[frame,probe]);
  if(image)await writeFile(resolve(out,`frame-${String(frame).padStart(4,'0')}.png`),Buffer.from(image,'base64'));
  if(frame%90===0)console.log('native '+frame+'/480');
 }
 report.frames=probe?6:181;report.range=[10,16];report.sourceCanvas=[1086,1448];report.crop=[150,400,500,900];report.rescaled=false;
}catch(e){report.errors.push(e.stack);process.exitCode=1}finally{if(browser)await browser.close();server.kill();await writeFile(resolve(out,'native-review.json'),JSON.stringify(report,null,2));console.log(JSON.stringify(report))}

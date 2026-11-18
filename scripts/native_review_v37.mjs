import {createRequire} from 'node:module';
import {spawn,execFileSync} from 'node:child_process';
import {writeFile,mkdir} from 'node:fs/promises';
import {resolve} from 'node:path';
const require=createRequire(import.meta.url),{chromium}=require(process.env.PLAYWRIGHT_MODULE);
const probe=process.env.NATIVE_PROBE==='1';const out=resolve('assets/parts/v37/'+(probe?'probe-review':'native-review'));await mkdir(out,{recursive:true});
const revision='a1d0cdb098182eaf5c6495d7a262500723066f2a',cache=new Map();
const server=spawn(process.env.PYTHON,[resolve('runtime/server.py'),'--port','18774'],{cwd:process.cwd(),windowsHide:true});let browser;
const report={baseline:revision,errors:[],samples:[]};
try{
 for(let i=0;i<100;i++){try{if((await fetch('http://127.0.0.1:18774/api/state')).ok)break}catch{}await new Promise(r=>setTimeout(r,100))}
 browser=await chromium.launch({headless:true,executablePath:process.env.CHROME_PATH,args:['--enable-unsafe-swiftshader']});
 const page=await browser.newPage();page.on('pageerror',e=>report.errors.push(e.message));
 await page.route('**/v37-review',r=>r.fulfill({contentType:'text/html',body:'<!doctype html><canvas></canvas>'}));
 await page.route('**/baseline/*.js',r=>{const name=new URL(r.request().url()).pathname.split('/').at(-1);if(!cache.has(name)){let code=execFileSync('git',['show',`${revision}:runtime/web/${name}`],{encoding:'utf8'});if(name==='renderer.js')code=code.replace("fetch('/model/model.json')","fetch('/baseline-model.json')");if(name==='renderer.js')code=code.replace('position.x*2.-1.,1.-position.y*2.','(position.x*2.-1.)*.94,(1.-position.y*2.)*.94');cache.set(name,code)}return r.fulfill({contentType:'text/javascript',body:cache.get(name)})});
 await page.route('**/baseline-model.json',r=>r.fulfill({contentType:'application/json',body:execFileSync('git',['show',`${revision}:runtime/model/model.json`],{encoding:'utf8'})}));
 await page.goto('http://127.0.0.1:18774/v37-review');
 await page.evaluate(async()=>{
  const modules=await Promise.all([import('/baseline/renderer.js'),import('/web/renderer.js')]),performances=await Promise.all([import('/baseline/performance.js'),import('/web/performance.js')]),{neutral}=await import('/web/controls.js');
  window.neutral=neutral;window.pair=[];window.motions=performances.map(m=>new m.PerformanceMotion());
  for(const module of modules){const r=new module.AvatarRenderer(),c=document.createElement('canvas');c.width=1086;c.height=1448;await r.load(c);pair.push(r)}
  window.input=t=>{const p=neutral();if(t>=2&&t<3.2){p.ParamBodyShiftX=-.9;p.ParamBodyAngleX=-2.7}else if(t>=3.2&&t<4.4){p.ParamBodyShiftX=.9;p.ParamBodyAngleX=2.7}if(t>=10&&t<12)p.ParamHandToCheek=(t-10)/2;else if(t>=12&&t<13)p.ParamHandToCheek=1;else if(t>=13&&t<15)p.ParamHandToCheek=(15-t)/2;return p};
  window.draw=(t,only=-1)=>{for(let i=0;i<2;i++){if(only>=0&&i!==only)continue;const active=t>=6&&t<9.2,base=input(t),p=active?motions[i].frame(base,t,{enabled:true,emotion:'happy',started_at:6,until:9.2}):base;pair[i].render(p,t,active?'soft_smile':'neutral',{ambient:false})}};
 });

 for(let frame=0;frame<=554;frame++){
  const image=await page.evaluate(([frame,probe])=>{
   if(frame===0)draw(0);else{draw((frame*2-1)/60);draw(frame*2/60)}
   if(!((frame>=66&&frame<=144)||(frame>=258&&frame<=306)||(frame>=348&&frame<=369)||(frame>=462&&frame<=498)))return null;
   const c=document.createElement('canvas');c.width=2172;c.height=1472;const ctx=c.getContext('2d');
   ctx.fillStyle='#397e91';ctx.fillRect(0,0,2172,1472);
   for(let side=0;side<2;side++){ctx.drawImage(pair[side].canvas,side*1086,24);ctx.fillStyle='white';ctx.font='15px sans-serif';ctx.fillText((side?'v37':'v36')+' native pixels / '+(frame/30).toFixed(3)+'s',side*1086+5,16);}
   return c.toDataURL('image/png').split(',')[1];
  },[frame,probe]);
  if(image)await writeFile(resolve(out,`frame-${String(frame).padStart(4,'0')}.png`),Buffer.from(image,'base64'));
  if(frame%90===0)console.log('native '+frame+'/480');
 }
 report.frames=187;report.ranges=[[2.2,4.8],[8.6,10.2],[11.6,12.3],[15.4,16.6]];report.sourceCanvas=[1086,1448];report.crop=[0,0,1086,1448];report.rescaled=false;
}catch(e){report.errors.push(e.stack);process.exitCode=1}finally{if(browser)await browser.close();server.kill();await writeFile(resolve(out,'native-review.json'),JSON.stringify(report,null,2));console.log(JSON.stringify(report))}

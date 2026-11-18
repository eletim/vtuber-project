import {createRequire} from 'node:module';
import {spawn,execFileSync} from 'node:child_process';
import {writeFile,mkdir} from 'node:fs/promises';
import {resolve} from 'node:path';
const require=createRequire(import.meta.url),{chromium}=require(process.env.PLAYWRIGHT_MODULE);
const probe=process.env.NATIVE_PROBE==='1';const out=resolve('assets/parts/v41/'+'acting-native');await mkdir(out,{recursive:true});
const revision='b7a01cf08839c2e504037efe3970ccc80c662ee5',cache=new Map();
const server=spawn(process.env.PYTHON,[resolve('runtime/server.py'),'--port','18782'],{cwd:process.cwd(),windowsHide:true});let browser;
const report={baseline:revision,errors:[],samples:[]};
try{
 for(let i=0;i<100;i++){try{if((await fetch('http://127.0.0.1:18782/api/state')).ok)break}catch{}await new Promise(r=>setTimeout(r,100))}
 browser=await chromium.launch({headless:true,executablePath:process.env.CHROME_PATH,args:['--enable-unsafe-swiftshader']});
 const page=await browser.newPage();page.on('pageerror',e=>report.errors.push(e.message));
 await page.route('**/v41-review',r=>r.fulfill({contentType:'text/html',body:'<!doctype html><canvas></canvas>'}));
 await page.route('**/baseline/*.js',r=>{const name=new URL(r.request().url()).pathname.split('/').at(-1);if(!cache.has(name)){let code=execFileSync('git',['show',`${revision}:runtime/web/${name}`],{encoding:'utf8'});if(name==='renderer.js')code=code.replace("fetch('/model/model.json')","fetch('/baseline-model.json')");if(name==='renderer.js')code=code.replace('position.x*2.-1.,1.-position.y*2.','(position.x*2.-1.)*.94,(1.-position.y*2.)*.94');cache.set(name,code)}return r.fulfill({contentType:'text/javascript',body:cache.get(name)})});
 await page.route('**/baseline-model.json',r=>r.fulfill({contentType:'application/json',body:execFileSync('git',['show',`${revision}:runtime/model/model.json`],{encoding:'utf8'})}));
 await page.goto('http://127.0.0.1:18782/v41-review');
 await page.evaluate(async()=>{
  const modules=await Promise.all([import('/baseline/renderer.js'),import('/web/renderer.js')]),performances=await Promise.all([import('/baseline/performance.js'),import('/web/performance.js')]),{neutral}=await import('/web/controls.js');
  window.neutral=neutral;window.pair=[];window.motions=performances.map(m=>new m.PerformanceMotion());
  for(const module of modules){const r=new module.AvatarRenderer(),c=document.createElement('canvas');c.width=1086;c.height=1448;await r.load(c);pair.push(r)}
  const {ActingController}=await import('/web/acting-controller.js');const controller=new ActingController();controller.start(0);
  window.draw=t=>{const live=controller.frame(neutral(),t);for(const r of pair)r.render(live.pose,t,live.expression,{ambient:false})};
 });

 for(let frame=0;frame<=554;frame++){
  const image=await page.evaluate(([frame,probe])=>{
   if(frame===0)draw(0);else{draw((frame*2-1)/60);draw(frame*2/60)}
   if(!(frame>=270&&frame<=480)&&![60,75,90,105,120,135,180,210,240,540].includes(frame))return null;
   const c=document.createElement('canvas');c.width=1200;c.height=974;const ctx=c.getContext('2d');
   ctx.fillStyle='#397e91';ctx.fillRect(0,0,1200,974);
   for(let side=0;side<2;side++){ctx.drawImage(pair[side].canvas,180,50,600,950,side*600,24,600,950);ctx.fillStyle='white';ctx.font='15px sans-serif';ctx.fillText((side?'v41':'v40')+' native pixels / '+(frame/30).toFixed(3)+'s',side*600+5,16);}
   return c.toDataURL('image/png').split(',')[1];
  },[frame,probe]);
  if(image)await writeFile(resolve(out,`frame-${String(frame).padStart(4,'0')}.png`),Buffer.from(image,'base64'));
  if(frame%90===0)console.log('native '+frame+'/554');
 }
 report.frames=221;report.ranges=[[9,16]];report.additionalFrames=[60,75,90,105,120,135,180,210,240,540];report.sourceCanvas=[1086,1448];report.crop=[180,50,600,950];report.rescaled=false;
}catch(e){report.errors.push(e.stack);process.exitCode=1}finally{if(browser)await browser.close();server.kill();await writeFile(resolve(out,'native-review.json'),JSON.stringify(report,null,2));console.log(JSON.stringify(report))}

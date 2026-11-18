import {createRequire} from 'node:module';
import {spawn,execFileSync} from 'node:child_process';
import {writeFile,mkdir} from 'node:fs/promises';
import {resolve} from 'node:path';
const require=createRequire(import.meta.url),{chromium}=require(process.env.PLAYWRIGHT_MODULE);
const out=resolve('assets/parts/v30/review');await mkdir(out,{recursive:true});
const revision='2122ed7ad066fab1805b370f1fb22aa19739b0f8',cache=new Map();
const server=spawn(process.env.PYTHON,[resolve('runtime/server.py'),'--port','18772'],{cwd:process.cwd(),windowsHide:true});let browser;
const report={baseline:revision,errors:[],samples:[]};
try{
 for(let i=0;i<100;i++){try{if((await fetch('http://127.0.0.1:18772/api/state')).ok)break}catch{}await new Promise(r=>setTimeout(r,100))}
 browser=await chromium.launch({headless:true,executablePath:process.env.CHROME_PATH,args:['--enable-unsafe-swiftshader']});
 const page=await browser.newPage();page.on('pageerror',e=>report.errors.push(e.message));
 await page.route('**/v30-review',r=>r.fulfill({contentType:'text/html',body:'<!doctype html><canvas></canvas>'}));
 await page.route('**/baseline/*.js',r=>{const name=new URL(r.request().url()).pathname.split('/').at(-1);if(!cache.has(name)){let code=execFileSync('git',['show',`${revision}:runtime/web/${name}`],{encoding:'utf8'});if(name==='renderer.js')code=code.replace("fetch('/model/model.json')","fetch('/baseline-model.json')");if(name==='renderer.js')code=code.replace('position.x*2.-1.,1.-position.y*2.','(position.x*2.-1.)*.94,(1.-position.y*2.)*.94');cache.set(name,code)}return r.fulfill({contentType:'text/javascript',body:cache.get(name)})});
 await page.route('**/baseline-model.json',r=>r.fulfill({contentType:'application/json',body:execFileSync('git',['show',`${revision}:runtime/model/model.json`],{encoding:'utf8'})}));
 await page.goto('http://127.0.0.1:18772/v30-review');
 await page.evaluate(async()=>{
  const modules=await Promise.all([import('/baseline/renderer.js'),import('/web/renderer.js')]),performances=await Promise.all([import('/baseline/performance.js'),import('/web/performance.js')]),{neutral}=await import('/web/controls.js');
  window.neutral=neutral;window.pair=[];window.motions=performances.map(m=>new m.PerformanceMotion());
  for(const module of modules){const r=new module.AvatarRenderer(),c=document.createElement('canvas');c.width=1086;c.height=1448;await r.load(c);pair.push(r)}
  window.input=t=>{const p=neutral();if(t>=2&&t<3.2){p.ParamBodyShiftX=-.9;p.ParamBodyAngleX=-2.7}else if(t>=3.2&&t<4.4){p.ParamBodyShiftX=.9;p.ParamBodyAngleX=2.7}if(t>=10&&t<12)p.ParamHandToCheek=(t-10)/2;else if(t>=12&&t<13)p.ParamHandToCheek=1;else if(t>=13&&t<15)p.ParamHandToCheek=(15-t)/2;return p};
  window.draw=t=>{for(let i=0;i<2;i++){const active=t>=6&&t<9.2,base=input(t),p=active?motions[i].frame(base,t,{enabled:true,emotion:'happy',started_at:6,until:9.2}):base;pair[i].render(p,t,active?'soft_smile':'neutral',{ambient:false})}};
 });

 for(const amount of [0,.2,.4,.5,.6,.8,1]){const data=await page.evaluate(amount=>{const p={...neutral(),ParamHandToCheek:amount};pair[1].render(p,1,'neutral',{ambient:false,snapArticulation:true});return pair[1].canvas.toDataURL().split(',')[1]},amount);await writeFile(resolve(out,`arm-${amount}.png`),Buffer.from(data,'base64'));}
}catch(e){report.errors.push(e.stack);process.exitCode=1}finally{if(browser)await browser.close();server.kill();console.log(report.errors)}

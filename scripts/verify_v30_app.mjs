import {createRequire} from 'node:module';import {spawn} from 'node:child_process';import {writeFile} from 'node:fs/promises';import {resolve} from 'node:path';
const require=createRequire(import.meta.url),{chromium}=require(process.env.PLAYWRIGHT_MODULE),out=resolve('assets/parts/v30/review');
const server=spawn(process.env.PYTHON,[resolve('runtime/server.py'),'--port','18773'],{cwd:process.cwd(),windowsHide:true});let browser;const report={errors:[]};
try{
 for(let i=0;i<100;i++){try{if((await fetch('http://127.0.0.1:18773/api/state')).ok)break}catch{}await new Promise(r=>setTimeout(r,100))}
 browser=await chromium.launch({headless:true,executablePath:process.env.CHROME_PATH,args:['--enable-unsafe-swiftshader']});const page=await browser.newPage();page.on('pageerror',e=>report.errors.push(e.message));
 await page.goto('http://127.0.0.1:18773/');await page.waitForFunction(()=>window.koma?.frames>3);await page.locator('#emotion').selectOption('happy');await page.locator('#gesture').click();
 report.happy=await page.evaluate(async()=>{let high=0,low=0,shift=0;const start=performance.now();await new Promise(r=>{function tick(){const p=koma.renderer.rig.pose;high=Math.max(high,p.bounce);low=Math.min(low,p.bounce);shift=Math.max(shift,Math.abs(p.shift));if(performance.now()-start<4200)requestAnimationFrame(tick);else r()}tick()});return{high,low,shift,mode:koma.mode}});
 if(report.happy.high<4||report.happy.low>=0)throw Error('Happy gesture did not show anticipation and hop in app');
 await page.locator('#reset').click();await page.waitForFunction(()=>Math.abs(koma.renderer.rig.pose.bounce)<.05&&Math.abs(koma.renderer.rig.pose.shift)<.1,{},{timeout:10000});report.reset=true;
 await page.route('**/pose-check',r=>r.fulfill({contentType:'text/html',body:'<canvas width="1086" height="1448"></canvas>'}));await page.goto('http://127.0.0.1:18773/pose-check');
 await page.evaluate(async()=>{const {AvatarRenderer}=await import('/web/renderer.js'),{neutral}=await import('/web/controls.js');window.r=new AvatarRenderer();await r.load(document.querySelector('canvas'));window.neutral=neutral});
 report.expressions=[];let clock=0;
 for(const expression of ['neutral','soft_smile','big_smile','worried','surprised','bashful','displeased','thinking'])for(const sign of [-1,1]){
  const data=await page.evaluate(({expression,sign,clock})=>{const p={...neutral(),ParamBodyShiftX:sign,ParamBodyAngleX:sign*3.5,ParamBodyBounce:sign,ParamHandToCheek:sign>0?1:0};for(let i=0;i<90;i++)r.render(p,clock+i/60,expression,{ambient:false});return r.canvas.toDataURL().split(',')[1]},{expression,sign,clock});clock+=1.5;
  const file=`extreme-${expression}-${sign}.png`;await writeFile(resolve(out,file),Buffer.from(data,'base64'));report.expressions.push({expression,sign,file});
 }
}catch(e){report.errors.push(e.stack);process.exitCode=1}finally{if(browser)await browser.close();server.kill();await writeFile(resolve(out,'app-verification.json'),JSON.stringify(report,null,2));console.log(JSON.stringify(report))}

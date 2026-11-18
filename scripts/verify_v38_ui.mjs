import {createRequire} from 'node:module';
import {spawn} from 'node:child_process';
import {mkdir,writeFile} from 'node:fs/promises';
const require=createRequire(import.meta.url),{chromium}=require(process.env.PLAYWRIGHT_MODULE);
const out='assets/parts/v38/ui-review';await mkdir(out,{recursive:true});
const server=spawn(process.env.PYTHON,['runtime/server.py','--port','18778'],{windowsHide:true});
let browser;const report={errors:[]};
try{
 for(let i=0;i<100;i++){try{if((await fetch('http://127.0.0.1:18778/api/state')).ok)break}catch{}await new Promise(r=>setTimeout(r,100))}
 browser=await chromium.launch({headless:true,executablePath:process.env.CHROME_PATH,args:['--enable-unsafe-swiftshader']});
 const page=await browser.newPage({viewport:{width:1440,height:1000}});page.on('pageerror',e=>report.errors.push(e.message));
 await page.goto('http://127.0.0.1:18778');await page.waitForFunction(()=>window.koma?.frames>3);
 await page.waitForTimeout(1500);await page.locator('#acting-start').click();
 report.startProbe=await page.evaluate(async()=>{const rows=[];for(let i=0;i<20;i++){rows.push({...koma.acting,frames:koma.frames});await new Promise(r=>setTimeout(r,100))}return rows});
 await page.waitForFunction(()=>koma.acting.weight>.95);
 report.started=await page.evaluate(()=>koma.acting);report.repeatDisabled=await page.locator('#acting-start').isDisabled();
 await page.locator('#expression').selectOption('worried');await page.waitForFunction(()=>koma.expression.id==='worried');
 report.manualExpression=await page.evaluate(()=>koma.expression.id);
 await page.waitForTimeout(3000);await page.screenshot({path:out+'/running.png'});
 await page.locator('#acting-stop').click();report.release=await page.evaluate(()=>koma.acting);
 await page.waitForFunction(()=>koma.acting.weight===0);report.stopped=true;
 await page.locator('#acting-start').click();await page.waitForFunction(()=>koma.acting.weight>.9);
 await page.locator('#ai').click();await page.waitForFunction(()=>koma.acting.weight===0&&koma.mode==='ai');report.modeSwitch=true;
 await page.locator('#human').click();await page.waitForFunction(()=>koma.mode==='human');
 await page.locator('#reset').click();await page.locator('#acting-start').click();
 report.complete=await page.evaluate(async()=>{
  const samples=[];const start=performance.now();
  await new Promise(resolve=>{function tick(){samples.push({time:(performance.now()-start)/1000,acting:{...koma.acting},pose:{...koma.renderer.rig.pose},current:{...koma.current}});if(performance.now()-start>20500)resolve();else requestAnimationFrame(tick)}tick()});return samples;
 });
 if(await page.evaluate(()=>koma.acting.weight!==0))throw Error('Phrase did not settle');
 await page.screenshot({path:out+'/settled.png'});
 if(!report.repeatDisabled||report.errors.length)throw Error('UI validation failed');
}catch(e){report.errors.push(e.stack);process.exitCode=1}finally{await browser?.close();server.kill();await writeFile(out+'/report.json',JSON.stringify(report,null,2));console.log(JSON.stringify({errors:report.errors,started:report.started,repeatDisabled:report.repeatDisabled,manualExpression:report.manualExpression,stopped:report.stopped,modeSwitch:report.modeSwitch,samples:report.complete?.length}));}

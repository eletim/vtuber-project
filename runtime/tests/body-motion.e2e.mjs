import {createRequire} from 'node:module';
import {spawn,execFileSync} from 'node:child_process';
import {readFile,mkdir,writeFile} from 'node:fs/promises';
import {resolve,dirname} from 'node:path';
import {fileURLToPath} from 'node:url';
import assert from 'node:assert/strict';
const require=createRequire(import.meta.url),{chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const root=resolve(dirname(fileURLToPath(import.meta.url)),'../..');
const out=resolve(root,'runtime/test-results/body-motion');await mkdir(out,{recursive:true});
const referenceBlob='7fa2cc317be671759a7e729ca02900c113d8d6f5';
const reference=execFileSync('git',['show',referenceBlob],{cwd:root,encoding:'utf8'});
const app=(await readFile(resolve(root,'runtime/web/app.js'),'utf8')).replace('frameStamp=requestAnimationFrame(tick);','frameStamp=0;');
const server=spawn(process.env.PYTHON||'python',[resolve(root,'runtime/server.py'),'--port','18768'],{cwd:root});
let browser;
const report={reference_renderer_blob:referenceBlob,warmup_frames:48,frames_per_version:48,errors:[],captures:'actual WebGL drawingBuffer frames with identical parameter/time input'};
try{
 for(let i=0;i<100;i++){try{if((await fetch('http://127.0.0.1:18768/api/state')).ok)break;}catch{}await new Promise(r=>setTimeout(r,100));}
 browser=await chromium.launch({headless:true,executablePath:process.env.CHROME_PATH||undefined,args:['--no-sandbox','--enable-unsafe-swiftshader']});
 for(const version of ['v10','v11']){
  const context=await browser.newContext();const page=await context.newPage();
  page.on('pageerror',e=>report.errors.push(e.message));
  await page.route('**/web/app.js',route=>route.fulfill({body:app,contentType:'text/javascript'}));
  if(version==='v10')await page.route('**/web/renderer.js',route=>route.fulfill({body:reference,contentType:'text/javascript'}));
  await page.goto('http://127.0.0.1:18768/?overlay=1');await page.waitForFunction(()=>window.koma?.frames>0);
  if(version==='v11')await page.evaluate(()=>{const r=window.koma.renderer;r.rig=new r.rig.constructor(r.model,{weights:r.rig.weights});});
  await mkdir(resolve(out,version),{recursive:true});
  for(let i=0;i<96;i++){
   const image=await page.evaluate(({i})=>{
    const t=i/20,phase=i/48*Math.PI*2;
    const pose={ParamAngleX:Math.sin(phase)*10,ParamAngleY:0,ParamAngleZ:Math.sin(phase)*6,ParamBodyAngleX:Math.sin(phase)*5,ParamEyeLOpen:1,ParamEyeROpen:1,ParamMouthOpenY:0,ParamBreath:.5+.35*Math.sin(phase*2)};
    window.koma.renderer.render(pose,t);
    if(i<48)return null;
    return document.querySelector('#avatar').toDataURL('image/png').split(',')[1];
   },{i});
   if(image)await writeFile(resolve(out,version,`${String(i-48).padStart(2,'0')}.png`),Buffer.from(image,'base64'));
  }
  if(version==='v11')report.final_pose=await page.evaluate(()=>window.koma.renderer.rig.pose);
  await context.close();
 }
 assert.deepEqual(report.errors,[]);report.status='PASS';
}finally{
 await writeFile(resolve(out,'report.json'),JSON.stringify(report,null,2)+'\n');
 if(browser)await browser.close();server.kill();console.log(JSON.stringify(report,null,2));
}

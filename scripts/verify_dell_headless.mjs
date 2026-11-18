import {createRequire} from 'node:module';
import {spawn} from 'node:child_process';
import {writeFile,mkdir} from 'node:fs/promises';
import {resolve} from 'node:path';
const require=createRequire(import.meta.url);
const {chromium}=require(process.env.PLAYWRIGHT_MODULE);
const root=process.cwd(),out=resolve(root,'assets/parts/v22/environment-review');
await mkdir(out,{recursive:true});
const server=spawn(process.env.PYTHON,[resolve(root,'runtime/server.py'),'--port','18769'],{cwd:root,windowsHide:true});
let browser;
const report={baseline:'b77f2fd6c6c4d1918615f0c6b14b59d2c38be6b4',new_motion_implemented:false,headless:true,errors:[],checks:[]};
try {
 for(let i=0;i<80;i++){try {if((await fetch('http://127.0.0.1:18769/api/state')).ok)break;}catch{}await new Promise(r=>setTimeout(r,100));}
 browser=await chromium.launch({headless:true,executablePath:process.env.CHROME_PATH,args:['--enable-unsafe-swiftshader','--autoplay-policy=no-user-gesture-required']});
 const page=await browser.newPage({viewport:{width:1100,height:1000}});
 page.on('pageerror',e=>report.errors.push(e.message));
 await page.goto('http://127.0.0.1:18769/?overlay=1');
 await page.waitForFunction(()=>window.koma?.frames>5);
 report.renderer=await page.evaluate(()=>({frames:window.koma.frames,layers:window.koma.renderer.layers.map(l=>l.id),webgl:!!window.koma.renderer.gl}));
 for(const bg of ['black','white']){
  await page.evaluate(bg=>document.body.style.background=bg,bg);
  await page.locator('#avatar').screenshot({path:resolve(out,`rest-${bg}.png`)});
 }
 report.checks.push('Restored v19 appearance loads in real headless Chrome; black/white baseline screenshots captured.');
 const clip=await page.evaluate(async()=>{
  const canvas=document.querySelector('#avatar'),stream=canvas.captureStream(24),chunks=[];
  const recorder=new MediaRecorder(stream,{mimeType:'video/webm;codecs=vp9',videoBitsPerSecond:2500000});
  const stopped=new Promise(resolve=>recorder.onstop=resolve);
  recorder.ondataavailable=e=>{if(e.data.size)chunks.push(e.data);};recorder.start();
  await new Promise(resolve=>setTimeout(resolve,4000));recorder.stop();await stopped;
  for(const track of stream.getTracks())track.stop();
  const blob=new Blob(chunks,{type:'video/webm'});
  return await new Promise(resolve=>{const reader=new FileReader();reader.onload=()=>resolve(reader.result.split(',')[1]);reader.readAsDataURL(blob);});
 });
 await writeFile(resolve(out,'RESTORED-v19-baseline-NOT-v22.webm'),Buffer.from(clip,'base64'));
 report.checks.push('Four-second real browser baseline recording; this is NOT new v22 motion.');
} catch(e) {report.errors.push(e.stack);process.exitCode=1;}
finally {if(browser)await browser.close();server.kill();await writeFile(resolve(out,'headless-report.json'),JSON.stringify(report,null,2));console.log(JSON.stringify(report,null,2));}

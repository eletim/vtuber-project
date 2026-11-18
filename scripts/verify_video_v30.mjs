import {createRequire} from 'node:module';
import {readFile,writeFile,mkdir} from 'node:fs/promises';
import {resolve} from 'node:path';
const require=createRequire(import.meta.url),{chromium}=require(process.env.PLAYWRIGHT_MODULE);
const out=resolve('assets/parts/v30/review/video-dense');await mkdir(out,{recursive:true});
const data=(await readFile('assets/parts/v30/review/koma-v30-motion-sample.mp4')).toString('base64');
const browser=await chromium.launch({headless:true,executablePath:process.env.CHROME_PATH});
try{
 const page=await browser.newPage();await page.setContent('<!doctype html><video muted></video>');
 await page.evaluate(async data=>{window.v=document.querySelector('video');v.src='data:video/mp4;base64,'+data;await new Promise((r,j)=>{v.onloadeddata=r;v.onerror=j})},data);
 const frames=[];
 for(let i=0;i<=72;i++){
  const time=9+i*.125;
  const result=await page.evaluate(async time=>{await new Promise(r=>{v.onseeked=r;v.currentTime=time});const c=document.createElement('canvas');c.width=v.videoWidth;c.height=v.videoHeight;c.getContext('2d').drawImage(v,0,0);return {time:v.currentTime,data:c.toDataURL('image/jpeg',.94).split(',')[1]}},time);
  const name=`video-${time.toFixed(3)}.jpg`;await writeFile(resolve(out,name),Buffer.from(result.data,'base64'));frames.push({requested:time,decoded:result.time,file:name});
 }
 await writeFile(resolve(out,'decode.json'),JSON.stringify({interval:[9,18],step:.125,frames,scenarioTime:'visible in each decoded frame; media timestamps may include capture-start offset'},null,2));
 console.log(JSON.stringify({frames:frames.length,first:frames[0],last:frames.at(-1)}));
}finally{await browser.close()}

import {createRequire} from 'node:module';
import {readFile,writeFile} from 'node:fs/promises';
import {resolve} from 'node:path';
const require=createRequire(import.meta.url),{chromium}=require(process.env.PLAYWRIGHT_MODULE),out=resolve('assets/parts/v22/motion-review');
const bytes=await readFile(resolve(out,'koma-v22-arm-hair-motion.webm'));
const browser=await chromium.launch({headless:true,executablePath:process.env.CHROME_PATH});
const report={bytes:bytes.length,decodedFrames:[],error:null};
try{
 const page=await browser.newPage();await page.setContent('<video id="video" muted preload="auto"></video><canvas id="frame"></canvas>');
 report.metadata=await page.evaluate(async b64=>{const bytes=Uint8Array.from(atob(b64),c=>c.charCodeAt(0)),video=document.querySelector('video');const ready=new Promise((resolve,reject)=>{video.onloadeddata=resolve;video.onerror=()=>reject(Error(video.error?.message||'decode error'));});video.src=URL.createObjectURL(new Blob([bytes],{type:'video/webm'}));await ready;return{width:video.videoWidth,height:video.videoHeight};},bytes.toString('base64'));
 for(const time of [0,1.2,1.4,1.6,2,3,5.2,5.4,5.6,6,10]){
  const frame=await page.evaluate(async time=>{const video=document.querySelector('video');if(Math.abs(video.currentTime-time)>.001){const seeked=new Promise(resolve=>video.onseeked=resolve);video.currentTime=time;await seeked;}const canvas=document.querySelector('canvas');canvas.width=video.videoWidth;canvas.height=video.videoHeight;canvas.getContext('2d').drawImage(video,0,0);return{time:video.currentTime,data:canvas.toDataURL().split(',')[1]};},time);
  await writeFile(resolve(out,`video-decoded-${time}.png`),Buffer.from(frame.data,'base64'));report.decodedFrames.push(frame.time);
 }
}catch(error){report.error=error.stack;process.exitCode=1;}
finally{await browser.close();await writeFile(resolve(out,'video-decode-verification.json'),JSON.stringify(report,null,2));console.log(JSON.stringify(report));}

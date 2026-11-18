import {createRequire} from 'node:module';
import {readFile,writeFile,mkdir} from 'node:fs/promises';
import {resolve} from 'node:path';
import {samples} from './mp4_samples.mjs';
const require=createRequire(import.meta.url),{chromium}=require(process.env.PLAYWRIGHT_MODULE);
const comparison=false;const out=resolve('assets/parts/v32/cfr-review/hair-frames');await mkdir(out,{recursive:true});
const bytes=await readFile('assets/parts/v32/cfr-review/'+(comparison?'koma-v31-v32-cfr-comparison.mp4':'koma-v32-cfr-motion-sample.mp4')),demux=samples(bytes);
const browser=await chromium.launch({headless:true,executablePath:process.env.CHROME_PATH});
try{
 const page=await browser.newPage();await page.route('https://koma-review.invalid/**',r=>r.fulfill({contentType:'text/html',body:'<!doctype html><video muted></video>'}));await page.goto('https://koma-review.invalid/');
 const report=await page.evaluate(async({data,demux})=>{
  const bytes=Uint8Array.from(atob(data),c=>c.charCodeAt(0));const errors=[];const frames=[];let previous=null;
  const c=document.createElement('canvas');c.width=540;c.height=260;const ctx=c.getContext('2d',{willReadFrequently:true});
  const crop=document.createElement('canvas');crop.width=315;crop.height=285;const cx=crop.getContext('2d');
  const decoder=new VideoDecoder({error:e=>errors.push(e.message),output:frame=>{
   ctx.drawImage(frame,0,0,c.width,c.height);const pixels=ctx.getImageData(0,0,c.width,c.height).data;let delta=0,armDelta=0,armN=0,max=0,changed=0;
   if(previous)for(let y=15;y<c.height;y++)for(let x=0;x<c.width;x++){const n=(y*c.width+x)*4;let d=0;for(let ch=0;ch<3;ch++)d+=Math.abs(pixels[n+ch]-previous[n+ch]);d/=3;delta+=d;max=Math.max(max,d);if(d>35)changed++;if(x>=20&&x<110&&y>=90&&y<195){armDelta+=d;armN++}}
   cx.clearRect(0,0,315,285);cx.drawImage(frame,50,60,420,380,0,0,315,285);
   frames.push({index:frames.length,time:frame.timestamp/1e6,meanDelta:delta/(c.width*(c.height-15)),armMeanDelta:armDelta/(armN||1),maxPixelDelta:max,changedOver35:changed,crop:crop.toDataURL('image/jpeg',.9).split(',')[1]});previous=pixels;frame.close();
  }});
  const config={codec:demux.codec,description:Uint8Array.from(atob(demux.description),c=>c.charCodeAt(0))};if(!(await VideoDecoder.isConfigSupported(config)).supported)throw Error('AVC decoder unavailable');decoder.configure(config);
  for(const sample of demux.samples){decoder.decode(new EncodedVideoChunk({...sample,data:bytes.subarray(sample.offset,sample.offset+sample.size)}));while(decoder.decodeQueueSize>12)await new Promise(r=>setTimeout(r,5))}
  await decoder.flush();decoder.close();
  return {errors,codec:demux.codec,encodedSamples:demux.samples.length,decodedFrames:frames.length,allEncodedSamplesDecoded:frames.length===demux.samples.length,frames,playback:{quality:'not repeated: see sample-frames'}};
 },{data:bytes.toString('base64'),demux});
 for(const frame of report.frames){const name=`frame-${String(frame.index).padStart(4,'0')}-${frame.time.toFixed(3)}.jpg`;await writeFile(resolve(out,name),Buffer.from(frame.crop,'base64'));delete frame.crop;frame.file=name}
 report.highestArmChanges=[...report.frames].filter(f=>f.time>9&&f.time<17).sort((a,b)=>b.armMeanDelta-a.armMeanDelta).slice(0,12);
 report.timestampMismatches=report.frames.filter((f,i)=>Math.abs(f.time-Math.round(i*1e6/30)/1e6)>0.000001).map(f=>f.index);report.expectedFrames=555;if(report.decodedFrames!==555||report.timestampMismatches.length)throw Error('Decoded fixed timestamps do not match rendered frames');
 report.note='All encoded samples decoded for hair-region review. Playback evidence is in sample-frames/temporal-report.json; playback was not repeated in this crop extraction.';
 await writeFile(resolve(out,'temporal-report.json'),JSON.stringify(report,null,2));console.log(JSON.stringify({errors:report.errors,encoded:report.encodedSamples,decoded:report.decodedFrames,playback:report.playback.quality,wallDuration:report.playback.wallDuration,top:report.highestArmChanges.slice(0,3)}));
}finally{await browser.close()}

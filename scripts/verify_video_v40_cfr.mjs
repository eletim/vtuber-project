import {createRequire} from 'node:module';
import {readFile,writeFile,mkdir} from 'node:fs/promises';
import {resolve} from 'node:path';
import {samples} from './mp4_samples.mjs';
const require=createRequire(import.meta.url),{chromium}=require(process.env.PLAYWRIGHT_MODULE);
const acting=process.env.CAPTURE_ACTING==='1',comparison=process.env.CFR_COMPARISON==='1';const out=resolve('assets/parts/v40/'+(acting?'acting-review/':'cfr-review/')+(comparison?'comparison-frames':'sample-frames'));await mkdir(out,{recursive:true});
const bytes=await readFile('assets/parts/v40/'+(acting?'acting-review/':'cfr-review/')+(acting?(comparison?'koma-v36-v37-acting-comparison.mp4':'koma-v37-acting-sample.mp4'):(comparison?'koma-v39-v40-cfr-comparison.mp4':'koma-v40-cfr-motion-sample.mp4'))),demux=samples(bytes);
const browser=await chromium.launch({headless:true,executablePath:process.env.CHROME_PATH});
try{
 const page=await browser.newPage();await page.route('https://koma-review.invalid/**',r=>r.fulfill({contentType:'text/html',body:'<!doctype html><video muted></video>'}));await page.goto('https://koma-review.invalid/');
 const report=await page.evaluate(async({data,demux})=>{
  const bytes=Uint8Array.from(atob(data),c=>c.charCodeAt(0));const errors=[];const frames=[];let previous=null;
  const c=document.createElement('canvas');c.width=540;c.height=260;const ctx=c.getContext('2d',{willReadFrequently:true});
  const crop=document.createElement('canvas');crop.width=250;crop.height=340;const cx=crop.getContext('2d');
  const full=document.createElement('canvas');full.width=810;full.height=390;const fullContext=full.getContext('2d');
  const decoder=new VideoDecoder({error:e=>errors.push(e.message),output:frame=>{
   ctx.drawImage(frame,0,0,c.width,c.height);const pixels=ctx.getImageData(0,0,c.width,c.height).data;let delta=0,armDelta=0,armN=0,max=0,changed=0;
   if(previous)for(let y=15;y<c.height;y++)for(let x=0;x<c.width;x++){const n=(y*c.width+x)*4;let d=0;for(let ch=0;ch<3;ch++)d+=Math.abs(pixels[n+ch]-previous[n+ch]);d/=3;delta+=d;max=Math.max(max,d);if(d>35)changed++;if(x>=20&&x<110&&y>=90&&y<195){armDelta+=d;armN++}}
   cx.clearRect(0,0,250,340);cx.drawImage(frame,65,275,250,340,0,0,250,340);
   let overview=null;if(frames.length%6===0||(frames.length>=300&&frames.length<=480&&frames.length%3===0)){fullContext.drawImage(frame,0,0,810,390);overview=full.toDataURL('image/jpeg',.94).split(',')[1];}
   frames.push({overview,index:frames.length,time:frame.timestamp/1e6,meanDelta:delta/(c.width*(c.height-15)),armMeanDelta:armDelta/(armN||1),maxPixelDelta:max,changedOver35:changed,crop:crop.toDataURL('image/jpeg',.9).split(',')[1]});previous=pixels;frame.close();
  }});
  const config={codec:demux.codec,description:Uint8Array.from(atob(demux.description),c=>c.charCodeAt(0))};if(!(await VideoDecoder.isConfigSupported(config)).supported)throw Error('AVC decoder unavailable');decoder.configure(config);
  for(const sample of demux.samples){decoder.decode(new EncodedVideoChunk({...sample,data:bytes.subarray(sample.offset,sample.offset+sample.size)}));while(decoder.decodeQueueSize>12)await new Promise(r=>setTimeout(r,5))}
  await decoder.flush();decoder.close();
  const v=document.querySelector('video');v.src=URL.createObjectURL(new Blob([bytes],{type:'video/mp4'}));await new Promise((r,j)=>{v.onloadeddata=r;v.onerror=j});v.playbackRate=1;
  const playback=[],start=performance.now();let done=false;const callback=(now,m)=>{playback.push({mediaTime:m.mediaTime,presentedFrames:m.presentedFrames,wallTime:(now-start)/1000});if(!done)v.requestVideoFrameCallback(callback)};
  v.requestVideoFrameCallback(callback);const ended=new Promise((r,j)=>{v.onended=()=>{done=true;r()};v.onerror=j});await v.play();await ended;
  return {errors,codec:demux.codec,encodedSamples:demux.samples.length,decodedFrames:frames.length,allEncodedSamplesDecoded:frames.length===demux.samples.length,frames,playback:{rate:1,duration:v.duration,wallDuration:(performance.now()-start)/1000,quality:v.getVideoPlaybackQuality().toJSON?.()||{totalVideoFrames:v.getVideoPlaybackQuality().totalVideoFrames,droppedVideoFrames:v.getVideoPlaybackQuality().droppedVideoFrames},callbacks:playback}};
 },{data:bytes.toString('base64'),demux});
 for(const frame of report.frames){const name=`frame-${String(frame.index).padStart(4,'0')}-${frame.time.toFixed(3)}.jpg`;await writeFile(resolve(out,name),Buffer.from(frame.crop,'base64'));delete frame.crop;frame.file=name;if(frame.overview){frame.overviewFile='overview-'+name;await writeFile(resolve(out,frame.overviewFile),Buffer.from(frame.overview,'base64'));}delete frame.overview;}
 report.highestArmChanges=[...report.frames].filter(f=>f.time>9&&f.time<17).sort((a,b)=>b.armMeanDelta-a.armMeanDelta).slice(0,12);
 report.timestampMismatches=report.frames.filter((f,i)=>Math.abs(f.time-Math.round(i*1e6/30)/1e6)>0.000001).map(f=>f.index);report.expectedFrames=555;if(report.decodedFrames!==555||report.timestampMismatches.length)throw Error('Decoded fixed timestamps do not match rendered frames');
 report.note='All encoded samples decoded with WebCodecs. Separate 1x HTMLVideoElement playback observed via requestVideoFrameCallback. MP4 has opaque backgrounds; alpha continuity is checked separately in the rig test.';
 await writeFile(resolve(out,'temporal-report.json'),JSON.stringify(report,null,2));console.log(JSON.stringify({errors:report.errors,encoded:report.encodedSamples,decoded:report.decodedFrames,playback:report.playback.quality,wallDuration:report.playback.wallDuration,top:report.highestArmChanges.slice(0,3)}));
}finally{await browser.close()}

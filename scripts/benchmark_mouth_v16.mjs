#!/usr/bin/env node
// Reproducible CPU-only mouth deformation microbenchmark. No native deps.
// Usage: node scripts/benchmark_mouth_v16.mjs [output.json]
// This does not measure browser frame rate, Canvas upload, or GPU rendering.
import assert from 'node:assert/strict';
import {readFileSync,writeFileSync,mkdirSync} from 'node:fs';
import {dirname,resolve} from 'node:path';
import {inflateSync} from 'node:zlib';
import {performance} from 'node:perf_hooks';
import {deformMouthPixels,featureOpening} from '../runtime/web/expressions.js';
const model=JSON.parse(readFileSync(new URL('../runtime/model/model.json',import.meta.url)));
function png(file){
  const buffer=readFileSync(new URL('../runtime/model/'+file,import.meta.url)),chunks=[];
  let width,height;
  for(let offset=8;offset<buffer.length;){
    const length=buffer.readUInt32BE(offset),type=buffer.toString('ascii',offset+4,offset+8),data=buffer.subarray(offset+8,offset+8+length);
    if(type==='IHDR'){width=data.readUInt32BE(0);height=data.readUInt32BE(4);assert.equal(data[8],8);assert.equal(data[9],6);assert.equal(data[12],0);}
    if(type==='IDAT')chunks.push(data);offset+=length+12;
  }
  const raw=inflateSync(Buffer.concat(chunks)),stride=width*4,pixels=new Uint8ClampedArray(stride*height);
  for(let y=0;y<height;y++){
    const filter=raw[y*(stride+1)];
    for(let x=0;x<stride;x++){
      const at=y*stride+x,a=x>=4?pixels[at-4]:0,b=y?pixels[at-stride]:0,c=y&&x>=4?pixels[at-stride-4]:0;
      let predictor=0;
      if(filter===1)predictor=a;
      if(filter===2)predictor=b;
      if(filter===3)predictor=Math.floor((a+b)/2);
      if(filter===4){const p=a+b-c,pa=Math.abs(p-a),pb=Math.abs(p-b),pc=Math.abs(p-c);predictor=pa<=pb&&pa<=pc?a:pb<=pc?b:c;}
      assert.ok(filter<=4);pixels[at]=(raw[y*(stride+1)+1+x]+predictor)&255;
    }
  }
  return {pixels,width,height};
}
const fixtures=model.expressions.map(expression=>{
  const part=expression.parts.find(p=>p.parameter==='ParamMouthOpenY'&&p.state==='open');
  const shut=expression.parts.find(p=>p.parameter==='ParamMouthOpenY'&&p.state==='closed');
  return {id:expression.id,part,...png(part.file),closed:{...png(shut.file),rect:shut.rect}};
});
const openings=[.141,.16,.2,.214,.25,.35,.65,1],warmupPasses=5,measuredPasses=20;
const all=[];
const percentile=(values,percent)=>values[Math.floor(values.length*percent)];
const perExpression=fixtures.map(f=>{
  const times=[];
  for(let pass=0;pass<warmupPasses+measuredPasses;pass++)for(const opening of openings){
    const scale=featureOpening(opening,true).scale,start=performance.now();
    deformMouthPixels(f.pixels,f.width,f.height,f.part,scale,f.id,f.closed);
    const duration=performance.now()-start;
    if(pass>=warmupPasses)times.push(duration);
  }
  times.sort((a,b)=>a-b);all.push(...times);
  return {id:f.id,width:f.width,height:f.height,samples:times.length,
    median_ms:percentile(times,.5),p95_ms:percentile(times,.95)};
});
all.sort((a,b)=>a-b);
const report={measurement:'Node CPU helper only; not browser FPS. Includes allocation and sampling, excludes Canvas/GPU/encoding. Concurrent workloads can affect timing.',
  node:process.version,warmupPasses,measuredPasses,openings,samples:all.length,
  median_ms:percentile(all,.5),p95_ms:percentile(all,.95),perExpression};
const json=JSON.stringify(report,null,2)+'\n';
if(process.argv[2]){const output=resolve(process.argv[2]);mkdirSync(dirname(output),{recursive:true});writeFileSync(output,json);}
process.stdout.write(json);

import test from 'node:test';import assert from 'node:assert/strict';
import {muxCfr} from './cfr_mp4.mjs';import {samples} from './mp4_samples.mjs';
test('all frame times and sample bytes survive exact 30fps mux without initial hold',()=>{
 const chunks=Array.from({length:555},(_,i)=>({timestamp:Math.round(i*1e6/30),type:i%60?'delta':'key',data:Buffer.from([0,0,0,1,i%256])}));
 const bytes=muxCfr({width:1620,height:780,description:Buffer.from([1,66,0,40,255,0,0]),chunks}),r=samples(bytes);
 assert.equal(r.samples.length,555);assert.equal(r.timescale,30000);
 r.samples.forEach((s,i)=>{assert.equal(s.timestamp,chunks[i].timestamp);assert.equal(s.duration,33333);assert.deepEqual(bytes.subarray(s.offset,s.offset+s.size),chunks[i].data)});
 assert.throws(()=>muxCfr({width:10,height:10,description:Buffer.alloc(7),chunks:chunks.slice(1)}),/timestamp/);
 assert.throws(()=>muxCfr({width:10,height:10,description:Buffer.alloc(7),chunks:[chunks[0],chunks[0]]}),/timestamp/);
});

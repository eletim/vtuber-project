import test from 'node:test';
import assert from 'node:assert/strict';
import {ActingController} from '../web/acting-controller.js';
import {neutral} from '../web/controls.js';
test('repeat start is idempotent, interruption releases continuously without resetting rig',()=>{
 const a=new ActingController(),p=neutral();a.start(0);
 for(let i=0;i<180;i++)a.frame(p,i/60);
 assert.equal(a.start(3),false);assert.equal(a.started,0);
 const before=a.frame(p,3);a.stop();const after=a.frame(p,3);
 assert.deepEqual(before.pose,after.pose);
 assert.equal(a.start(3),false);
 for(let i=181;i<300;i++)a.frame(p,i/60);
 assert.equal(a.weight,0);assert.equal(a.start(5),true);
});
test('speech mouth and explicit expressions win, blocking cancels, time gaps cannot replay',()=>{
 const a=new ActingController(),p={...neutral(),ParamMouthOpenY:.8};a.start(0);
 for(let i=0;i<400;i++)a.frame(p,i/60);
 const r=a.frame(p,400/60,{expression:'worried',expressionOwned:true});
 assert.equal(r.pose.ParamMouthOpenY,.8);assert.equal(r.expression,'worried');
 assert.equal(a.frame(p,401/60,{blocked:true}).running,false);
 const b=new ActingController();b.start(0);b.frame(p,0);assert.equal(b.frame(p,10).running,false);
});
test('a queued RAF just before the click timestamp does not cancel the start',()=>{
 const a=new ActingController();a.start(1.005);
 assert.equal(a.frame(neutral(),1).running,true);
 assert.equal(a.frame(neutral(),1.016).running,true);
 assert.ok(a.weight>0);
});
test('complete phrase settles back to live input and can restart',()=>{
 const a=new ActingController(),p={...neutral(),ParamAngleX:2};a.start(0);
 for(let i=0;i<1260;i++)a.frame(p,i/60);
 assert.equal(a.running,false);assert.equal(a.weight,0);assert.deepEqual(a.frame(p,21).pose,p);
 assert.equal(a.start(21),true);
});

test('shared epoch joins at current age and repeated snapshots do not restart; reconnect resumes',()=>{
 const a=new ActingController(),state={id:'one',started_at:100,stopped_at:0};
 a.sync(state,10,105);a.frame(neutral(),10);assert.equal(a.started,5);
 a.sync(state,10.5,105.5);assert.equal(a.started,5);
 a.stop();a.sync(state,11,106);assert.equal(a.running,true);
 a.sync({...state,stopped_at:106},11,106);assert.equal(a.running,false);
});

test('fresh reconnect snapshot resumes through a stale RAF gap without rewinding the epoch',()=>{
 const a=new ActingController(),state={id:'resume',started_at:100,stopped_at:0};
 a.sync(state,10,102);a.frame(neutral(),10);a.frame(neutral(),10.1);a.stop();
 const started=a.started,weight=a.weight;a.sync(state,14,106);
 const r=a.frame(neutral(),14);assert.equal(r.running,true);assert.equal(a.started,started);assert.equal(r.weight,weight);
 assert.equal(a.frame(neutral(),14.1).running,true);
});

test('repeated snapshots cannot prevent a blocked gesture from releasing',()=>{
 const a=new ActingController(),state={id:'blocked',started_at:100,stopped_at:0};a.sync(state,0,100);
 for(let i=0;i<60;i++)a.frame(neutral(),i/60);
 for(let i=60;i<240;i++){a.sync(state,i/60,100+i/60);a.frame(neutral(),i/60,{blocked:true});}
 assert.equal(a.running,false);assert.equal(a.weight,0);
});

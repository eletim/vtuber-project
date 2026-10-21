import test from 'node:test';
import assert from 'node:assert/strict';
import {ExpressionTransition,expressionParameters,expressionLabels,featureOpening,featureBands} from '../web/expressions.js';
import {AvatarRenderer} from '../web/renderer.js';
import {neutral} from '../web/controls.js';

test('all eight expressions change only while eyes and mouth are closed, without face blending',()=>{
  const transition=new ExpressionTransition();
  let time=0;
  for(const id of Object.keys(expressionLabels)){
    transition.request(id,time);
    for(let i=0;i<24;i++){
      const previous=transition.active,frame=transition.update(time+i/60);
      if(previous!==frame.id)assert.equal(frame.gate,0);
      assert.ok(frame.gate>=0&&frame.gate<=1);
    }
    time+=.4;
    assert.equal(transition.active,id);assert.equal(transition.phase,'idle');
  }
});

test('rapid replacement coalesces pending states and never gets stuck',()=>{
  const transition=new ExpressionTransition();
  transition.request('worried',0);transition.update(.04);
  const gate=transition.gate;
  transition.request('bashful',.04);assert.equal(transition.gate,gate);
  transition.request('thinking',.07);
  assert.equal(transition.update(.12).id,'thinking');
  assert.equal(transition.gate,0);
  transition.request('big_smile',.13);assert.equal(transition.active,'big_smile');
  transition.update(.22);const opening=transition.gate;
  transition.request('surprised',.22);assert.equal(transition.gate,opening);
  assert.equal(transition.update(.34).id,'surprised');
  assert.equal(transition.update(.6).phase,'idle');
  assert.equal(transition.gate,1);
  // A long suspended tab catches up instead of remaining half closed.
  transition.request('neutral',.61);assert.equal(transition.update(200).id,'neutral');
  assert.equal(transition.phase,'idle');
});

test('closed smile retains both eyes while lipsync amplitude remains independent',()=>{
  const face={defaults:{ParamEyeLOpen:0,ParamEyeROpen:0}};
  const pose=expressionParameters({...neutral(),ParamMouthOpenY:.8},face,1);
  assert.equal(pose.ParamEyeLOpen,0);assert.equal(pose.ParamEyeROpen,0);assert.equal(pose.ParamMouthOpenY,.8);
  assert.equal(expressionParameters({...pose,ParamMouthOpenY:0},face,1).ParamMouthOpenY,0);
  assert.equal(expressionParameters({...neutral(),ParamMouthOpenY:1},{},0).ParamMouthOpenY,0);
  const wink=expressionParameters({...neutral(),ParamEyeLOpen:0},{},1);
  assert.equal(wink.ParamEyeLOpen,0);assert.equal(wink.ParamEyeROpen,1);
});

test('feature warp preserves exact endpoints and fixed patch boundaries',()=>{
  const part={rect:[100,200,200,300],image:{width:100,height:100},motion:{bounds:[120,230,180,270],anchor:[150,250]}};
  for(const mouth of [false,true]){
    assert.deepEqual(featureOpening(0,mouth),{state:'closed',scale:1});
    assert.deepEqual(featureOpening(1,mouth),{state:'open',scale:1});
    assert.equal(featureBands(part,1),null);
    for(let i=1;i<100;i++){
      const {scale}=featureOpening(i/100,mouth),bands=featureBands(part,scale);
      if(!bands)continue;
      assert.equal(bands.destination[0],0);assert.equal(bands.destination.at(-1),100);
      assert.equal(bands.destination[1],30);assert.equal(bands.destination[4],70);
      assert.ok(Math.abs((bands.destination[2]+bands.destination[3])/2-50)<1e-10);
      assert.equal(bands.source[1],bands.source[2]);assert.equal(bands.source[3],bands.source[4]);
      for(let n=1;n<bands.destination.length;n++)assert.ok(bands.destination[n]>=bands.destination[n-1]);
    }
  }
});

test('renderer paints one opaque endpoint per feature and never fades a face',()=>{
  const calls=[];
  const ctx={save(){},restore(){},translate(){},clearRect(){},drawImage(...args){calls.push({alpha:this.globalAlpha,args});}};
  const part=(parameter,state)=>({name:parameter+'.'+state,parameter,state,rect:[0,0,50,50],image:{width:50,height:50}});
  const parts=['ParamEyeLOpen','ParamEyeROpen','ParamMouthOpenY'].flatMap(parameter=>['open','closed'].map(state=>part(parameter,state)));
  const renderer=new AvatarRenderer();
  Object.assign(renderer,{ctx,paint:{width:100,height:100},canvas:{width:100,height:100},
    model:{size:[100,100]},layers:[{id:'head',role:'head',file:'head.png',rect:[0,0,100,100],features:true,ctx,paint:{width:100,height:100},images:new Map(),image:{head:true}}],
    rig:{frames:()=>({head:new Float32Array()})},transition:new ExpressionTransition(),
    expressions:new Map([['neutral',{base:{neutral:true},parts}],['big_smile',{base:{smile:true},parts,defaults:{ParamEyeLOpen:0,ParamEyeROpen:0}}]]),
    gl:new Proxy({},{get:()=>()=>{}}),frames:0});
  for(let i=0;i<30;i++){
    calls.length=0;renderer.render({...neutral(),ParamMouthOpenY:1},i/60,'big_smile');
    assert.equal(calls.length,4);assert.ok(calls.every(call=>call.alpha===1));
    assert.equal(renderer.visibleParts.length,3);
    assert.equal(new Set(renderer.visibleParts.map(name=>name.split('.')[0])).size,3);
  }
  assert.deepEqual(renderer.visibleParts,['ParamEyeLOpen.closed','ParamEyeROpen.closed','ParamMouthOpenY.open']);
});


test('edge-touching metadata safely preserves the opaque endpoint',()=>{
  const part={rect:[0,0,100,100],image:{width:100,height:100},motion:{bounds:[10,0,90,100],anchor:[50,50]}};
  assert.equal(featureBands(part,.2),null);
});


test('eye interpolation always selects one unchanged authored endpoint, never warps brows or hair',()=>{
  for(let i=0;i<=100;i++){
    const value=i/100,eye=featureOpening(value,false);
    assert.equal(eye.scale,1);assert.equal(eye.state,value>.4?'open':'closed');
  }
  assert.ok(featureOpening(.65,true).scale<1,'mouth remains independently interpolated');
});

import test from 'node:test';
import assert from 'node:assert/strict';
import {AvatarRenderer} from '../web/renderer.js';
import {BodyRig} from '../web/body-rig.js';
import {ExpressionTransition} from '../web/expressions.js';
import {neutral} from '../web/controls.js';

function setup(){
  const calls=[],model={size:[1086,1448],mesh:[2,2]},rig=new BodyRig(model,{weights:Array.from({length:9},()=>[0,0,0,0])});
  const ctx={clearRect(){},save(){},restore(){},translate(){},drawImage(){}};
  const roles=['root','skirt','torso','armLeft','armRight','head'];
  const layers=roles.map((role,i)=>({id:role,role,file:`${role}.png`,rect:[0,0,1086,1448],features:role==='head',images:new Map(),image:{role},texture:{role},positionBuffer:{role},ctx,paint:{width:1086,height:1448}}));
  let buffer,texture,rect;
  const gl=new Proxy({
    bindBuffer(type,value){buffer=value;},bindTexture(type,value){texture=value;},
    bufferSubData(type,offset,positions){calls.push({type:'geometry',buffer,positions});},
    uniform4fv(location,value){rect=value;},
    drawElements(){calls.push({type:'draw',buffer,texture,rect});}
  },{get:(target,key)=>target[key]||(()=>{})});
  const renderer=new AvatarRenderer();Object.assign(renderer,{model,rig,layers,gl,canvas:{width:1086,height:1448},transition:new ExpressionTransition(),expressions:new Map([['neutral',{id:'neutral',parts:[]}]]),frames:0});
  return {renderer,calls,roles};
}

test('renderer issues ordered, distinct geometry/texture draw calls for all PSD layers',()=>{
  const {renderer,calls,roles}=setup();renderer.render(neutral(),0,'neutral',{ambient:false});
  const geometry=calls.filter(call=>call.type==='geometry'),draws=calls.filter(call=>call.type==='draw');
  assert.deepEqual(draws.map(call=>call.texture.role),roles);
  assert.equal(new Set(draws.map(call=>call.buffer)).size,roles.length);
  assert.equal(new Set(geometry.map(call=>call.positions.buffer)).size,roles.length);
  for(let i=0;i<roles.length;i++)assert.equal(geometry[i].positions,renderer.rig.positionsByRole[roles[i]]);
  assert.deepEqual(renderer.lastDraws.map(call=>call.role),roles);
});

test('diagnostic onlyRoles uses actual production surfaces and cannot draw omitted clothes',()=>{
  const {renderer,calls}=setup();renderer.render({...neutral(),ParamArmLOpen:1},0,'neutral',{ambient:false,onlyRoles:['torso']});
  assert.deepEqual(calls.filter(call=>call.type==='draw').map(call=>call.texture.role),['torso']);
  assert.deepEqual(renderer.lastDraws.map(call=>call.role),['torso']);
});


test('coverage resolve happens only after independently transformed layers are composited',()=>{
  const {renderer,calls,roles}=setup(),framebuffers=[];
  renderer.resolveFramebuffer={coverage:true};renderer.sampling={enabled:true,width:2172,height:2896};
  renderer.gl.bindFramebuffer=(type,value)=>framebuffers.push(value);
  renderer.gl.drawArrays=()=>calls.push({type:'resolve'});
  renderer.render(neutral(),0,'neutral',{ambient:false});
  assert.deepEqual(framebuffers,[renderer.resolveFramebuffer,null]);
  assert.equal(calls.filter(call=>call.type==='draw').length,roles.length);
  assert.equal(calls.filter(call=>call.type==='resolve').length,1);
  assert.equal(calls.at(-1).type,'resolve','no shared mesh is applied after assembly');
});

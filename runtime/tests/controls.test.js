import test from 'node:test';
import assert from 'node:assert/strict';
import {neutral,faceParameters,rmsMouth,smoothParameters} from '../web/controls.js';
test('face blendshapes preserve independent eyes and clamp jaw',()=>{
 const landmarks=Array.from({length:478},()=>({x:.5,y:.5}));
 landmarks[33]={x:.35,y:.4};landmarks[263]={x:.65,y:.4};landmarks[1]={x:.5,y:.5};
 const p=faceParameters({faceLandmarks:[landmarks],faceBlendshapes:[{categories:[{categoryName:'eyeBlinkLeft',score:1},{categoryName:'jawOpen',score:.9}]}]});
 assert.equal(p.ParamEyeLOpen,0);assert.equal(p.ParamEyeROpen,1);assert.equal(p.ParamMouthOpenY,1);
 assert.equal(faceParameters({faceLandmarks:[]}),null);
});
test('silence, audio signal and parameter interpolation',()=>{
 assert.equal(rmsMouth(new Float32Array(1024)),0);
 assert.ok(rmsMouth(new Float32Array(1024).fill(.12))>.9);
 const p=smoothParameters(neutral(),{...neutral(),ParamAngleX:200},1);
 assert.ok(p.ParamAngleX<=15&&p.ParamAngleX>14);
});

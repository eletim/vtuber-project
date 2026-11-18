import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {expressionLabels,expressionParameters,featureOpening,featureBands} from '../web/expressions.js';
import {neutral} from '../web/controls.js';
const root=new URL('../model/',import.meta.url);
const model=JSON.parse(readFileSync(new URL('model.json',root),'utf8'));
function pngSize(file){const data=readFileSync(new URL(file,root));assert.equal(data.subarray(1,4).toString(),'PNG');return[data.readUInt32BE(16),data.readUInt32BE(20)];}

test('v15 manifest has eight complete runtime expressions and original neutral textures',()=>{
  assert.deepEqual(model.expressions.map(item=>item.id),Object.keys(expressionLabels));
  const neutral=model.expressions.find(item=>item.id==='neutral');
  assert.equal(neutral.base,model.base);
  for(const expression of model.expressions){
    assert.deepEqual(pngSize(expression.base),model.size);
    assert.equal(expression.parts.length,6);
    assert.equal(expression.defaults.ParamMouthOpenY,0,'speech must be able to close every mouth');
    for(const parameter of ['ParamEyeLOpen','ParamEyeROpen','ParamMouthOpenY']){
      assert.deepEqual(expression.parts.filter(part=>part.parameter===parameter).map(part=>part.state).sort(),['closed','open']);
    }
    for(const part of expression.parts){
      const [width,height]=pngSize(part.file),[x0,y0,x1,y1]=part.rect;
      assert.deepEqual([width,height],[x1-x0,y1-y0]);
      assert.ok(x0>=0&&y0>=0&&x1<=model.size[0]&&y1<=model.size[1]);
      assert.ok(part.motion,'every part provides bounded local animation geometry');
      const [bx0,by0,bx1,by1]=part.motion.bounds,[ax,ay]=part.motion.anchor;
      assert.ok(bx0<bx1&&by0<by1&&ax>=bx0&&ax<=bx1&&ay>=by0&&ay<=by1);
      assert.ok(by0>y0&&by1<y1,`${expression.id}/${part.name}: motion needs stationary edge padding`);
    }
  }
  for(const part of neutral.parts)assert.equal(part.file,model.parts.find(original=>original.name===part.name).file);
});

test('all authored parts have continuous non-inverting local warp bands',()=>{
  for(const expression of model.expressions){
    for(const part of expression.parts){
      const [width,height]=pngSize(part.file),input={...part,image:{width,height}};
      for(let frame=0;frame<=100;frame++){
        const {scale}=featureOpening(frame/100,part.parameter==='ParamMouthOpenY');
        const bands=featureBands(input,scale);
        if(!bands)continue;
        assert.ok(bands.x0>=0&&bands.x1<=width&&bands.x0<bands.x1);
        for(const array of [bands.source,bands.destination]){
          assert.equal(array[0],0);assert.equal(array.at(-1),height);
          for(let index=1;index<array.length;index++)assert.ok(array[index]>=array[index-1]);
        }
      }
    }
  }
});

test('big smile stays closed while every expression has an independent mouth range',()=>{
  for(const expression of model.expressions){
    const closed=expressionParameters(neutral(),expression),open=expressionParameters({...neutral(),ParamMouthOpenY:1},expression);
    assert.equal(closed.ParamMouthOpenY,0);assert.equal(open.ParamMouthOpenY,1);
    assert.equal(open.ParamEyeLOpen,expression.id==='big_smile'?0:1);
    assert.equal(open.ParamEyeROpen,expression.id==='big_smile'?0:1);
  }
});

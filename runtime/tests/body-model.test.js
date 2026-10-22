import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {bodyLayers,bodyTextureFile} from '../web/render-plan.js';
const root=new URL('../model/',import.meta.url),model=JSON.parse(readFileSync(new URL('model.json',root)));
function pngSize(file){const data=readFileSync(new URL(file,root));assert.equal(data.subarray(1,4).toString(),'PNG');return[data.readUInt32BE(16),data.readUInt32BE(20)];}

test('v26 manifest loads explicit PSD layers for every separately rendered body role',()=>{
  assert.equal(model.format,'koma-part-mesh-3');
  const layers=bodyLayers(model);
  assert.deepEqual(new Set(layers.map(layer=>layer.role)),new Set(['legLeft','legRight','skirt','torso','armLeft','armRight','head','chest','abdomen','pelvis']));
  assert.ok(layers.length>=6);
  assert.match(model.source_psd,/v31\/koma_material_repair_v31\.psd$/);
  for(const layer of layers){
    assert.ok(layer.psdGroup,'every render layer points to its editable PSD group');
    assert.match(layer.file,/^body_v(?:19|22|26|28|29|30|31)\//);
    const [x0,y0,x1,y1]=layer.rect;
    for(const file of new Set([layer.file,...Object.values(layer.expressionFiles||{})]))assert.deepEqual(pngSize(file),[x1-x0,y1-y0],file);
  }
  const order=layers.map(layer=>layer.role);
  assert.ok(order.indexOf('legRight')<order.indexOf('skirt'),'skirt occludes articulated thighs');
  assert.ok(order.indexOf('skirt')<order.indexOf('torso'),'torso vest panels stay over skirt');
  assert.ok(order.indexOf('torso')<order.indexOf('armLeft'));
  assert.ok(order.indexOf('torso')<order.indexOf('armRight'));
});

test('only the head owns unchanged eye/mouth overlays and all eight head variants',()=>{
  const head=bodyLayers(model).find(layer=>layer.features);
  assert.equal(head.role,'head');
  assert.deepEqual(Object.keys(head.expressionFiles).sort(),model.expressions.map(expression=>expression.id).sort());
  const [x0,y0,x1,y1]=head.rect;
  for(const expression of model.expressions){
    assert.equal(bodyTextureFile(head,expression,model),head.expressionFiles[expression.id]);
    for(const part of expression.parts){
      const [px0,py0,px1,py1]=part.rect;
      assert.ok(px0>=x0&&py0>=y0&&px1<=x1&&py1<=y1,`${expression.id}/${part.name} is fully inside its head canvas`);
    }
  }
});

test('rig configuration respects approved limited under-hem coverage',()=>{
  assert.ok(model.bodyRig.skirtRevealLimitPixels>0&&model.bodyRig.skirtRevealLimitPixels<=3);
  assert.ok(model.bodyRig.skirtTop<model.bodyRig.skirtHem);
  assert.equal(model.bodyRig.shoulders.length,2);assert.equal(model.bodyRig.elbows.length,2);
});

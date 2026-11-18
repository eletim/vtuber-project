const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname, '../assets/parts/v14/Switch_Koma_Expression.jsx'),'utf8').replace(/^#target.*$/m,'');
function run(selected, {cancel=false, missing=false, noDocument=false}={}) {
  const folders=Array.from({length:7},(_,i)=>({name:`EXP 0${i+1} Test`,visible:true}));
  const original={};
  for (const part of ['eye_screen_left','eye_screen_right','mouth']) {
    original[part+'.open']={visible:false}; original[part+'.closed']={visible:true};
  }
  const alerts=[];
  const doc={layerSets:folders,artLayers:{getByName(name) { if(missing)throw Error('missing');return original[name];}}};
  function Window() {
    this.add=function(kind) {
      if(kind==='dropdownlist') {
        let choice={index:0};
        const picker={get selection(){return choice},set selection(value){choice=typeof value==='number'?{index:value}:value;}};
        this.picker=picker;return picker;
      }
      return {add(){return {}}};
    };
    this.show=function(){this.picker.selection=selected;return cancel?0:1;};
  }
  vm.runInNewContext(source,{app:{documents:noDocument?[]:[doc],activeDocument:doc},Window,alert:s=>alerts.push(s)});
  return {folders,original,alerts};
}
test('selector activates exactly one of eight expression states',()=>{
  for(let selected=0;selected<8;selected++) {
    const {folders,original,alerts}=run(selected);
    assert.equal(alerts.length,0);
    assert.deepEqual(folders.map(f=>f.visible),folders.map((_,i)=>i+1===selected));
    for(const [name,layer] of Object.entries(original))assert.equal(layer.visible,name.endsWith('.open'));
  }
});
test('selector cancel or missing original layer makes no changes',()=>{
  for(const options of [{cancel:true},{missing:true}]) {
    const {folders,original}=run(4,options);
    assert.ok(folders.every(f=>f.visible));
    for(const [name,layer] of Object.entries(original))assert.equal(layer.visible,name.endsWith('.closed'));
  }
});
test('selector reports when no document is open',()=>assert.equal(run(0,{noDocument:true}).alerts.length,1));

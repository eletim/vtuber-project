const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const source=fs.readFileSync(path.join(__dirname,'../assets/parts/v15/Switch_Koma_Expression.jsx'),'utf8').replace(/^#target.*$/m,'');
const ids=['soft_smile','big_smile','worried','surprised','bashful','displeased','thinking'];
function run(selected,{cancel=false,missing=false}={}){
 const folders=ids.map((id,i)=>({name:`EXP 0${i+1} ${id}`,visible:true,artLayers:[...['eye_screen_left','eye_screen_right','mouth'].flatMap(part=>['open','closed'].map(state=>({name:`${id}.${part}.${state}`,visible:false}))),{name:id+'.face_plate.brows_cheeks',visible:false}]}));
 const original={};for(const part of ['eye_screen_left','eye_screen_right','mouth'])for(const s of ['open','closed'])original[part+'.'+s]={visible:s==='closed'};
 const doc={layerSets:folders,artLayers:{getByName(n){if(missing)throw Error('missing');return original[n]}}};const alerts=[];
 function Window(){this.add=function(kind){if(kind==='dropdownlist'){let s={index:0};this.picker={get selection(){return s},set selection(v){s=typeof v==='number'?{index:v}:v}};return this.picker}return {add(){return {}}}};this.show=function(){this.picker.selection=selected;return cancel?0:1}};
 vm.runInNewContext(source,{app:{documents:[doc],activeDocument:doc},Window,alert:s=>alerts.push(s)});return {folders,original,alerts};
}
test('v15 selector restores one coherent face and its painted base',()=>{
 for(let selected=0;selected<8;selected++){
  const {folders,original,alerts}=run(selected);assert.equal(alerts.length,0);
  folders.forEach((folder,i)=>assert.equal(folder.visible,i+1===selected));
  for(const [n,p] of Object.entries(original))assert.equal(p.visible,n.endsWith('.open'));
  if(selected){const id=ids[selected-1];for(const p of folders[selected-1].artLayers){const [_,part,state]=p.name.split('.');if(part==='face_plate'){assert.equal(p.visible,true);continue;}const open=part==='mouth'?['big_smile','surprised'].includes(id):id!=='big_smile';assert.equal(p.visible,state==='open'?open:!open);}}
 }
});
test('v15 cancel and missing original preserve document state',()=>{
 for(const options of [{cancel:true},{missing:true}]){const r=run(4,options);assert.ok(r.folders.every(f=>f.visible));assert.ok(r.folders.every(f=>f.artLayers.every(p=>!p.visible)));}
});

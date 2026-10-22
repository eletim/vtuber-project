import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {AvatarRenderer} from '../web/renderer.js';
import {neutral} from '../web/controls.js';
const modelRoot=new URL('../model/',import.meta.url);

test('production renderer loads cropped textures and preserves independent draws across repeated FBO resolves',async()=>{
  const originals={document:globalThis.document,fetch:globalThis.fetch,Image:globalThis.Image};
  let number=0,currentTexture=null,currentBuffer=null,framebuffer=null,program=null;
  const draws=[],textureFilters=new Map(),attributes=new Map();
  const make=type=>({type,id:++number});
  const methods={
    createShader:()=>make('shader'),createProgram:()=>make('program'),createBuffer:()=>make('buffer'),createTexture:()=>make('texture'),createFramebuffer:()=>make('framebuffer'),
    getShaderParameter:()=>true,getProgramParameter:()=>true,
    getAttribLocation:(p,name)=>name==='position'?1:0,getUniformLocation:()=>make('uniform'),
    getParameter:name=>name==='MAX_VIEWPORT_DIMS'?[4096,4096]:4096,
    checkFramebufferStatus:()=> 'FRAMEBUFFER_COMPLETE',
    bindTexture:(type,texture)=>{currentTexture=texture;},
    texParameteri:(type,name,value)=>{if(!textureFilters.has(currentTexture))textureFilters.set(currentTexture,{});textureFilters.get(currentTexture)[name]=value;},
    bindBuffer:(type,buffer)=>{currentBuffer=buffer;},
    bindFramebuffer:(type,target)=>{framebuffer=target;},
    vertexAttribPointer:location=>attributes.set(location,currentBuffer),useProgram:value=>{program=value;},
    drawElements:()=>draws.push({type:'part',framebuffer,program,uv:attributes.get(0),position:attributes.get(1),texture:currentTexture}),
    drawArrays:()=>draws.push({type:'resolve',framebuffer,program,texture:currentTexture})
  };
  const gl=new Proxy(methods,{get:(target,key)=>key in target?target[key]:/^[A-Z_]+$/.test(key)?key:()=>{}});
  const canvas=()=>({width:0,height:0,getContext(){return{drawImage(){},clearRect(){},save(){},restore(){},translate(){},putImageData(){},getImageData:(x,y,w,h)=>({data:new Uint8ClampedArray(w*h*4)})};}});
  try{
    globalThis.document={createElement:canvas};
    globalThis.fetch=async path=>({json:async()=>JSON.parse(readFileSync(new URL(path.replace('/model/',''),modelRoot)))});
    globalThis.Image=class{
      set src(path){const data=readFileSync(new URL(path.replace('/model/',''),modelRoot));this.width=data.readUInt32BE(16);this.height=data.readUInt32BE(20);}
      async decode(){}
    };
    const renderer=new AvatarRenderer();await renderer.load({width:652,height:869,getContext:()=>gl});
    assert.deepEqual(renderer.sampling,{enabled:true,width:1304,height:1738,scale:2});
    const count=renderer.model.bodyLayers.length;
    assert.ok(count>=20);
    for(const layer of renderer.layers)assert.equal(textureFilters.get(layer.texture).TEXTURE_MIN_FILTER,layer.sampling==='linear'?'LINEAR':'NEAREST');
    assert.equal(textureFilters.get(renderer.resolveTexture).TEXTURE_MIN_FILTER,'LINEAR');
    for(let frame=0;frame<3;frame++)renderer.render(neutral(),frame/60,'neutral',{ambient:false});
    const visible=renderer.layers.filter(layer=>(renderer.articulatedArm?.opacity(layer)??1)>=.00001);
    const visibleCount=visible.length;
    assert.equal(draws.length,(visibleCount+1)*3,'visible independent parts plus one resolve per frame');
    for(let frame=0;frame<3;frame++){
      const batch=draws.slice(frame*(visibleCount+1),(frame+1)*(visibleCount+1)),parts=batch.slice(0,visibleCount),resolve=batch[visibleCount];
      assert.ok(parts.every(draw=>draw.framebuffer===renderer.resolveFramebuffer&&draw.program===renderer.program));
      assert.ok(parts.every((draw,i)=>draw.uv===(visible[i].id==='left_raised_hand'?renderer.handUvBuffer:renderer.uvBuffer)),'dense hand UV is isolated and common UV restored for other layers');
      assert.deepEqual(parts.map(draw=>draw.position),visible.map(layer=>layer.positionBuffer));
      assert.equal(resolve.type,'resolve');assert.equal(resolve.framebuffer,null);assert.equal(resolve.texture,renderer.resolveTexture);
    }
  }finally{for(const [key,value] of Object.entries(originals)){if(value===undefined)delete globalThis[key];else globalThis[key]=value;}}
});

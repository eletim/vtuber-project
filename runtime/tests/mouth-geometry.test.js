import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {inflateSync} from 'node:zlib';
import {mouthGeometry,mouthPoint,mouthBlend,deformMouthPixels,featureOpening} from '../web/expressions.js';
import {AvatarRenderer} from '../web/renderer.js';
import {BodyRig} from '../web/body-rig.js';
import {neutral} from '../web/controls.js';

const model=JSON.parse(readFileSync(new URL('../model/model.json',import.meta.url)));
const skinning=JSON.parse(readFileSync(new URL('../model/skinning.json',import.meta.url)));
// Small dependency-free decoder for the project's 8-bit RGBA fixture PNGs.
function png(file){
  const buffer=readFileSync(new URL('../model/'+file,import.meta.url)),chunks=[];
  let width,height;
  for(let offset=8;offset<buffer.length;){
    const length=buffer.readUInt32BE(offset),type=buffer.toString('ascii',offset+4,offset+8),data=buffer.subarray(offset+8,offset+8+length);
    if(type==='IHDR'){width=data.readUInt32BE(0);height=data.readUInt32BE(4);assert.equal(data[8],8);assert.equal(data[9],6);assert.equal(data[12],0);}
    if(type==='IDAT')chunks.push(data);offset+=length+12;
  }
  const raw=inflateSync(Buffer.concat(chunks)),stride=width*4,pixels=new Uint8ClampedArray(stride*height);
  for(let y=0;y<height;y++){
    const filter=raw[y*(stride+1)];
    for(let x=0;x<stride;x++){
      const at=y*stride+x,a=x>=4?pixels[at-4]:0,b=y?pixels[at-stride]:0,c=y&&x>=4?pixels[at-stride-4]:0;
      let predictor=0;
      if(filter===1)predictor=a;
      if(filter===2)predictor=b;
      if(filter===3)predictor=Math.floor((a+b)/2);
      if(filter===4){const p=a+b-c,pa=Math.abs(p-a),pb=Math.abs(p-b),pc=Math.abs(p-c);predictor=pa<=pb&&pa<=pc?a:pb<=pc?b:c;}
      assert.ok(filter<=4);pixels[at]=(raw[y*(stride+1)+1+x]+predictor)&255;
    }
  }
  return {pixels,width,height};
}
const mouths=model.expressions.map(expression=>{
  const part=expression.parts.find(p=>p.parameter==='ParamMouthOpenY'&&p.state==='open');
  const shut=expression.parts.find(p=>p.parameter==='ParamMouthOpenY'&&p.state==='closed');
  return {id:expression.id,part,source:png(part.file),closed:{...png(shut.file),rect:shut.rect}};
});
const close=(a,b,epsilon=1e-7)=>assert.ok(Math.abs(a-b)<epsilon,`${a} != ${b}`);

function localPoint(g,u,v){return {x:g.origin[0]+u*g.tangent[0]+v*g.normal[0],y:g.origin[1]+u*g.tangent[1]+v*g.normal[1]};}
function rotated(x,y,angle){const c=Math.cos(angle),s=Math.sin(angle);return {x:c*x-s*y,y:s*x+c*y};}

test('all eight mouth frames retain their authored slant and closed-lip curvature at both head tilts',()=>{
  for(const {id,part} of mouths){
    const g=mouthGeometry(part,id);
    assert.ok(g.tangent[1]<-.07,`${id}: must not substitute a horizontal lip axis`);
    for(const opening of [.141,.15,.16,.2,.214,.25,.35,.65,1]){
      const scale=featureOpening(opening,true).scale;
      for(const [u,v] of g.closure){
        const point=localPoint(g,u,v),mapped=mouthPoint(g,point.x,point.y,scale);
        close(mapped.x,point.x);close(mapped.y,point.y);
        for(const degrees of [-8,0,8]){
          const angle=degrees*Math.PI/180,a=rotated(point.x,point.y,angle),b=rotated(mapped.x,mapped.y,angle);
          close(a.x,b.x);close(a.y,b.y);
        }
      }
    }
  }
});

test('normal deformation is continuous, invertible, tangent preserving, and has a fixed exterior',()=>{
  for(const {id,part} of mouths){
    const g=mouthGeometry(part,id);
    for(const scale of [.06,.12,.25,.5,.8,1])for(let u=-55;u<=55;u+=5){
      let last=-Infinity;
      for(let v=-50;v<=50;v+=1){
        const p=localPoint(g,u,v),d=mouthPoint(g,p.x,p.y,scale),restored=mouthPoint(g,d.x,d.y,scale,true);
        close(restored.x,p.x);close(restored.y,p.y);
        close((d.x-g.origin[0])*g.tangent[0]+(d.y-g.origin[1])*g.tangent[1],u);
        const mappedV=(d.x-g.origin[0])*g.normal[0]+(d.y-g.origin[1])*g.normal[1];
        assert.ok(mappedV>last,`${id}: foldover at ${u},${v}`);last=mappedV;
        if(Math.abs(u)>=g.outer[2]||v<=g.outer[1]||v>=g.outer[3]){close(d.x,p.x);close(d.y,p.y);}
      }
    }
  }
});

test('full-open RGBA endpoints and input sources remain byte-exact for every expression',()=>{
  for(const {id,part,source,closed} of mouths){
    const original=source.pixels.slice();
    assert.deepEqual(deformMouthPixels(source.pixels,source.width,source.height,part,1,id,closed),source.pixels);
    for(const opening of [.141,.15,.16,.2,.214,.25,.35,.65]){
      const pixels=deformMouthPixels(source.pixels,source.width,source.height,part,featureOpening(opening,true).scale,id,closed);
      assert.equal(pixels.length,source.pixels.length);
    }
    assert.deepEqual(source.pixels,original);
  }
});

test('near closure uses the actual closed contour and has no detached dark second lip',()=>{
  assert.deepEqual(mouthBlend(.06),{scale:.06,openWeight:0});
  assert.equal(mouthBlend(.14).openWeight,1);
  for(const {id,part,source,closed} of mouths){
    const atClosure=deformMouthPixels(source.pixels,source.width,source.height,part,.06,id,closed);
    for(let y=0;y<source.height;y++)for(let x=0;x<source.width;x++){
      const cx=x+part.rect[0]-closed.rect[0],cy=y+part.rect[1]-closed.rect[1];
      if(cx<0||cy<0||cx>=closed.width||cy>=closed.height)continue;
      const a=(y*source.width+x)*4,b=(cy*closed.width+cx)*4;
      assert.deepEqual(atClosure.subarray(a,a+4),closed.pixels.subarray(b,b+4));
    }
    for(const opening of [.141,.15,.16,.18,.2,.214,.25]){
      const pixels=deformMouthPixels(source.pixels,source.width,source.height,part,featureOpening(opening,true).scale,id,closed);
      for(let x=540;x<=564;x++){
        const rows=[];
        for(let y=335;y<=377;y++){
          const at=((y-part.rect[1])*source.width+x-part.rect[0])*4;
          if(pixels[at+3]>240&&pixels[at+1]<175&&pixels[at]-pixels[at+1]>35)rows.push(y);
        }
        for(let i=1;i<rows.length;i++)assert.ok(rows[i]-rows[i-1]<=2,`${id} at ${opening}: detached lip at x${x}, rows ${rows}`);
      }
    }
  }
});

test('premultiplied resampling cannot turn transparent black RGB into a mouth halo',()=>{
  const {id,part,source}=mouths[0],pixels=new Uint8ClampedArray(source.pixels.length);
  for(let y=0;y<source.height;y++)for(let x=0;x<source.width;x++){
    const at=(y*source.width+x)*4,a=(x+y)%5?255:0;
    pixels[at]=a?220:0;pixels[at+1]=a?150:0;pixels[at+2]=a?130:0;pixels[at+3]=a;
  }
  for(const scale of [.06,.2,.5]){
    const result=deformMouthPixels(pixels,source.width,source.height,part,scale,id);
    for(let i=0;i<result.length;i+=4)if(result[i+3]>0){assert.equal(result[i],220);assert.equal(result[i+1],150);assert.equal(result[i+2],130);}
  }
});

test('strong normal minification averages details instead of picking a dark or white scanline',()=>{
  const {id,part,source}=mouths[0],g=mouthGeometry(part,id),pixels=new Uint8ClampedArray(source.pixels.length);
  for(let y=0;y<source.height;y++)for(let x=0;x<source.width;x++){
    const at=(y*source.width+x)*4,color=y%2?255:0;
    pixels[at]=pixels[at+1]=pixels[at+2]=color;pixels[at+3]=255;
  }
  const result=deformMouthPixels(pixels,source.width,source.height,part,.06,id);
  let tested=0;
  for(let y=0;y<source.height;y++)for(let x=0;x<source.width;x++){
    const mapped=mouthPoint(g,x,y,.06,true);
    if(mapped.normalRatio>10&&Math.abs(x-g.origin[0])<20){
      const value=result[(y*source.width+x)*4];assert.ok(value>90&&value<165,`aliased minification ${value}`);tested++;
    }
  }
  assert.ok(tested>30);
});

test('actual renderer drawPart consumes the shared warp once, without face alpha or strip overlays',()=>{
  const {id,part,source,closed}=mouths[2],calls=[],renderer=new AvatarRenderer();
  const previous=globalThis.ImageData;
  globalThis.ImageData=class {constructor(data,width,height){Object.assign(this,{data,width,height});}};
  try{
    const patch={},context={putImageData(data){calls.push(['pixels',data]);}};
    renderer.ctx={globalAlpha:1,drawImage(...args){calls.push(['draw',...args]);}};
    renderer.mouthPixels=new WeakMap([[part,{...source,closed,patch,context}]]);
    renderer.drawPart(part,.2,id);
    assert.equal(calls.length,2);assert.equal(calls[0][0],'pixels');
    assert.deepEqual(calls[0][1].data,deformMouthPixels(source.pixels,source.width,source.height,part,.2,id,closed));
    assert.deepEqual(calls[1],['draw',patch,...part.rect.slice(0,2)]);assert.equal(renderer.ctx.globalAlpha,1);
    calls.length=0;renderer.drawPart(part,1,id);assert.deepEqual(calls,[['draw',part.image,...part.rect.slice(0,2)]]);
  }finally{if(previous===undefined)delete globalThis.ImageData;else globalThis.ImageData=previous;}
});

test('mouth and neighboring face receive the same unchanged full head rotation at runtime extremes',()=>{
  for(const angle of [-8,8]){
    const rig=new BodyRig(model,skinning),positions=rig.frame({...neutral(),ParamAngleZ:angle},0);
    // Entire mouth and both eyes are inside the rigid head region, y<430.
    for(let y=12;y<=22;y++)for(let x=24;x<=34;x++){
      const index=y*(model.mesh[0]+1)+x,px=rig.rest[index*2]*model.size[0],py=rig.rest[index*2+1]*model.size[1];
      const expected=rotated(px-540,py-425,angle*Math.PI/180);
      close(positions[index*2]*model.size[0],expected.x+540,.0001);
      close(positions[index*2+1]*model.size[1],expected.y+425,.0001);
    }
  }
});

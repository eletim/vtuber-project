import test from 'node:test';
import assert from 'node:assert/strict';
import {handAngleMap,paintHandAngle} from '../web/hand-angle-material.js';
const w=163,h=155,d=Math.hypot(130,118),axis=[130/d,-118/d];
function patch(width,color){const a=new Uint8ClampedArray(w*h*4);for(let y=0;y<h;y++)for(let x=0;x<w;x++){
 const u=(x-27)*axis[0]+(y-127)*axis[1],v=-(x-27)*axis[1]+(y-127)*axis[0];
 if(u>-20&&u<155&&Math.abs(v)<width)a.set([...color,255],(y*w+x)*4);
}return a}
test('angle material moves a registered contour while keeping its interior opaque and wrist unchanged',()=>{
 const front=patch(24,[230,190,170]),side=patch(13,[240,200,180]),map=handAngleMap(front,side,w,h);
 assert.deepEqual(paintHandAngle(map,0),front);
 for(const t of [.1,.25,.5,.75,1]){
  const result=paintHandAngle(map,t);
  for(let y=0;y<h;y++)for(let x=0;x<w;x++){
   const k=(y*w+x)*4,u=(x-27)*axis[0]+(y-127)*axis[1],v=-(x-27)*axis[1]+(y-127)*axis[0];
   if(u<=0)assert.deepEqual(result.slice(k,k+4),front.slice(k,k+4),'proximal wrist is pinned');
   if(u>50&&u<135&&Math.abs(v)<8)assert.equal(result[k+3],255,'interior is not an opacity dissolve');
  }
 }
});

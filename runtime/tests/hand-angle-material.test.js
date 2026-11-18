import test from 'node:test';
import assert from 'node:assert/strict';
import {handAngleMap,paintHandAngle,alignedCoordinates} from '../web/hand-angle-material.js';
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
test('internal ink correspondence is monotone and transports a shifted crease as one line',()=>{
 const front=patch(24,[240,200,180]),side=patch(13,[240,200,180]);
 for(const [p,line] of [[front,-6],[side,2]])for(let y=0;y<h;y++)for(let x=0;x<w;x++){
  const u=(x-27)*axis[0]+(y-127)*axis[1],v=-(x-27)*axis[1]+(y-127)*axis[0],k=(y*w+x)*4;
  if(u>45&&u<140&&Math.abs(v-line)<1.6&&p[k+3])p.set([85,45,35,255],k);
 }
 const map=handAngleMap(front,side,w,h);
 for(const match of map.matches.filter(Boolean)){
  assert.equal(match[0],0);assert.equal(match.at(-1),1);
  for(let i=1;i<match.length;i++)assert.ok(match[i]>match[i-1],'no texture fold or reversed finger ordering');
 }
 const out=paintHandAngle(map,.5),profile=[];
 for(let v=-16;v<=16;v+=.5){const x=Math.round(27+100*axis[0]-v*axis[1]),y=Math.round(127+100*axis[1]+v*axis[0]);profile.push(out[(y*w+x)*4])}
 let runs=0,inside=false;for(const value of profile){if(value<150&&!inside)runs++;inside=value<150}
 assert.equal(runs,1,'a shifted crease remains one dark run instead of two faded strokes');
 assert.ok(Math.min(...profile)<120,'aligned ink retains contrast');
 for(const t of [.1,.5,.9])for(let f=0;f<=1;f+=.01){const [a,b]=alignedCoordinates(map.matches[170],f,t);assert.ok(Math.abs((1-t)*a+t*b-f)<1e-6)}
});

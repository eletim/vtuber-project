import test from 'node:test';import assert from 'node:assert/strict';import {eyeOpening,eyeAperture,paintEyeComponents} from '../web/eye-components.js';
test('authored half eye is not closed a second time by the expression cap',()=>{assert.equal(eyeOpening(.5,.5),1);assert.equal(eyeOpening(.25,.5),.5);assert.equal(eyeOpening(0,.5),0);assert.equal(eyeOpening(0,0),0)});
test('even a closed lash below the open corner never inverts the aperture',()=>{const m={upper:[[0,20],[10,10]],lower:[[0,20],[10,30]],closed:[[0,45],[10,25]]};for(let x=0;x<=10;x+=.2)for(let o=0;o<=1;o+=.01){const [a,b]=eyeAperture(m,x,o);assert.ok(b>=a-1e-8)}});

test('registered lid interpolation preserves colour across transparent patch padding',()=>{
 const w=60,h=70,original=new Uint8ClampedArray(w*h*4),closed=new Uint8ClampedArray(w*h*4),blank=new Uint8ClampedArray(w*h*4);
 for(let y=0;y<h;y++)for(let x=0;x<w;x++){let i=(y*w+x)*4;for(let k=0;k<3;k++){original[i+k]=200;closed[i+k]=200;}original[i+3]=x>5&&x<55&&y>4&&y<63?255:0;closed[i+3]=x>3&&x<57&&y>2&&y<66?255:0;}
 const eye={meta:{size:[w,h],upper:[[10,20],[50,20]],lower:[[10,40],[50,40]],closed:[[10,35],[50,35]],irisCenter:[30,30],irisRadius:[10,10],gazePixels:[5,4],authoredClosure:true},pixels:{original,'closed-reference':closed,'hair-foreground-mask':blank,'iris-completed':blank}};
 const saved=globalThis.ImageData;globalThis.ImageData=class{constructor(data){this.data=data}};let result;
 try{paintEyeComponents({putImageData:d=>result=d.data},eye,.4,0,0);for(let i=0;i<result.length;i+=4)if(result[i+3]>100)for(let k=0;k<3;k++)assert.ok(Math.abs(result[i+k]-200)<=2);}finally{globalThis.ImageData=saved;}
});

test('different authored upper-lash thicknesses register to one opaque ink band',()=>{
 const w=60,h=70,original=new Uint8ClampedArray(w*h*4),closed=new Uint8ClampedArray(w*h*4),blank=new Uint8ClampedArray(w*h*4);
 for(let y=0;y<h;y++)for(let x=0;x<w;x++){const i=(y*w+x)*4;for(let k=0;k<3;k++){original[i+k]=y>=11&&y<20?40:240;closed[i+k]=y>=31&&y<40?40:240;}original[i+3]=closed[i+3]=255;}
 const eye={meta:{size:[w,h],upper:[[10,20],[50,20]],lower:[[10,45],[50,45]],closed:[[10,40],[50,40]],irisCenter:[30,30],irisRadius:[10,10],gazePixels:[5,4],authoredClosure:true},pixels:{original,'closed-reference':closed,'hair-foreground-mask':blank,'iris-completed':blank}};
 const saved=globalThis.ImageData;globalThis.ImageData=class{constructor(data){this.data=data}};let result;
 try{paintEyeComponents({putImageData:d=>result=d.data},eye,.5,0,0);for(let y=22;y<=29;y++)for(let k=0;k<3;k++)assert.ok(result[(y*w+30)*4+k]<=42,'no separate diluted upper contour');}finally{globalThis.ImageData=saved;}
});

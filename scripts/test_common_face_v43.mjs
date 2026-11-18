import assert from 'node:assert/strict';
import {followHairGeometry} from '../assets/parts/v43/experiments/paired-skin.js';
globalThis.window={faceDirection:'right'};
const point=(x,y,t)=>{const r=followHairGeometry(new Float32Array([(x+235)/1086,(y+1)/1448]),t);return[r[0]*1086-235,r[1]*1448-1]};
let cases=0,minArea=Infinity,maxEyeError=0;
for(const direction of ['right','left','up','down']){window.faceDirection=direction;for(let i=0;i<=30;i++){const t=i/30;
for(const [cx,cy,sx,sy]of [[234,289,40,22],[375,262,34,22],[318,356,25,8]]){const c=point(cx,cy,t);for(const [x,y]of [[-sx,-sy],[sx,-sy],[sx,sy],[-sx,sy]]){const p=point(cx+x,cy+y,t);const error=Math.hypot(p[0]-c[0]-x,p[1]-c[1]-y);maxEyeError=Math.max(maxEyeError,error);assert.ok(error<.02,`${direction} feature control drift ${error}`);cases++;}}
for(let y=140;y<440;y+=15)for(let x=150;x<470;x+=15){const a=point(x,y,t),b=point(x+15,y,t),c=point(x,y+15,t),area=(b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0]);minArea=Math.min(minArea,area);assert.ok(area>0,'folded face cell');cases++;}
}}
console.log(JSON.stringify({cases,minArea,maxEyeControlError:maxEyeError,productionChanged:false}));

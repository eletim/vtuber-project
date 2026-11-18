// Diagnostic only: registered skin material + isolated original feature contours.
// Never installed in the production renderer without visual acceptance.
export const boundary=[[195,280],[207,246],[239,222],[253,262],[286,274],[329,270],[331,204],[366,216],[411,246],[413,287],[402,330],[382,366],[350,395],[329,414],[295,404],[264,394],[235,379],[214,351],[202,321]];
const nose=[315,310];
const sideNose=[1005,691];
const target=boundary.map(([x,y])=>[x+(y>350?18:8),y]);
target[13]=[347,414];
// Measured underpaint/source registration is provisional. Bottom rim authored separately.
const src=boundary.map(([x,y])=>[(x-245)*1.85+790,(y-294)*1.85+660]);
src[10]=[1120,750];src[11]=[1075,815];src[12]=[991,910];src[13]=[955,935];src[14]=[848,932];src[15]=[744,894];src[16]=[663,840];src[17]=[624,794];src[18]=[598,738];
function canvas(w,h){const c=document.createElement('canvas');c.width=w;c.height=h;return c}
function path(ctx,pts){ctx.beginPath();pts.forEach(([x,y],i)=>i?ctx.lineTo(x,y):ctx.moveTo(x,y));ctx.closePath()}
function triangle(ctx,img,s,d){
 const [p,q,r]=s,[a,b,c]=d,den=(q[0]-p[0])*(r[1]-p[1])-(r[0]-p[0])*(q[1]-p[1]);
 if(Math.abs(den)<1e-5)return;
 const m00=((b[0]-a[0])*(r[1]-p[1])-(c[0]-a[0])*(q[1]-p[1]))/den;
 const m01=((c[0]-a[0])*(q[0]-p[0])-(b[0]-a[0])*(r[0]-p[0]))/den;
 const m10=((b[1]-a[1])*(r[1]-p[1])-(c[1]-a[1])*(q[1]-p[1]))/den;
 const m11=((c[1]-a[1])*(q[0]-p[0])-(b[1]-a[1])*(r[0]-p[0]))/den;
 ctx.save();path(ctx,d);ctx.clip();ctx.transform(m00,m10,m01,m11,a[0]-m00*p[0]-m01*p[1],a[1]-m10*p[0]-m11*p[1]);ctx.drawImage(img,0,0);ctx.restore();
}
const pixels=new WeakMap();
function read(im){if(!pixels.has(im)){const c=canvas(im.width,im.height),x=c.getContext('2d');x.drawImage(im,0,0);pixels.set(im,{w:im.width,h:im.height,data:x.getImageData(0,0,im.width,im.height).data})}return pixels.get(im)}
function sample(im,x,y){x=Math.max(0,Math.min(im.w-1,x));y=Math.max(0,Math.min(im.h-1,y));const ix=Math.floor(x),iy=Math.floor(y),fx=x-ix,fy=y-iy;let a=0,r=0,g=0,b=0;for(const [xx,yy,w] of [[ix,iy,(1-fx)*(1-fy)],[Math.min(ix+1,im.w-1),iy,fx*(1-fy)],[ix,Math.min(iy+1,im.h-1),(1-fx)*fy],[Math.min(ix+1,im.w-1),Math.min(iy+1,im.h-1),fx*fy]]){const i=(yy*im.w+xx)*4,wa=w*im.data[i+3]/255;a+=wa;r+=wa*im.data[i];g+=wa*im.data[i+1];b+=wa*im.data[i+2]}return a?[r/a,g/a,b/a,a*255]:[0,0,0,0]}
export function paintSkin(ctx,front,side,t){
 if(t<=0)return;
 const dst=boundary.map((p,i)=>[p[0]+(i>=11&&i<=13?(target[i][0]-p[0])*t:0),p[1]]),center=[315+25*t,310];
 const c=canvas(front.width,front.height),cx=c.getContext('2d'),result=cx.createImageData(c.width,c.height),f=read(front),b=read(side);
 const tris=[];for(let i=0;i<boundary.length;i++){const j=(i+1)%boundary.length;tris.push([[nose,boundary[i],boundary[j]],[sideNose,src[i],src[j]],[center,dst[i],dst[j]]])}
 const neckFront=[[235,379],[329,414],[382,366],[373,442],[280,442]],neckSide=[[663,840],[850,935],[850,850],[850,1040],[650,1040]],neckDest=[dst[16],dst[13],dst[11],[373,442],[280,442]];
 for(const ids of [[0,1,4],[1,3,4],[1,2,3]])tris.push([ids.map(i=>neckFront[i]),ids.map(i=>neckSide[i]),ids.map(i=>neckDest[i])]);
 for(const [aa,bb,dd] of tris){const [u,v,w]=dd,den=(v[1]-w[1])*(u[0]-w[0])+(w[0]-v[0])*(u[1]-w[1]);if(Math.abs(den)<1e-5)continue;
 for(let y=Math.max(0,Math.floor(Math.min(...dd.map(p=>p[1]))));y<=Math.min(c.height-1,Math.ceil(Math.max(...dd.map(p=>p[1]))));y++)for(let x=Math.max(0,Math.floor(Math.min(...dd.map(p=>p[0]))));x<=Math.min(c.width-1,Math.ceil(Math.max(...dd.map(p=>p[0]))));x++){const a=((v[1]-w[1])*(x+.5-w[0])+(w[0]-v[0])*(y+.5-w[1]))/den,beta=((w[1]-u[1])*(x+.5-w[0])+(u[0]-w[0])*(y+.5-w[1]))/den,g=1-a-beta;if(Math.min(a,beta,g)<-1e-7)continue;const map=ps=>[a*ps[0][0]+beta*ps[1][0]+g*ps[2][0],a*ps[0][1]+beta*ps[1][1]+g*ps[2][1]],sf=sample(f,...map(aa)),sb=sample(b,...map(bb)),idx=(y*c.width+x)*4;for(let k=0;k<4;k++)result.data[idx+k]=sf[k]*(1-t)+sb[k]*t;}
 }
 cx.putImageData(result,0,0);ctx.save();ctx.beginPath();ctx.rect(0,280,c.width,c.height-280);ctx.clip();ctx.save();ctx.globalCompositeOperation='destination-out';path(ctx,boundary);ctx.fill();path(ctx,neckFront);ctx.fill();ctx.restore();ctx.drawImage(c,0,0);ctx.restore();
}
export function paintFeature(ctx,part,t){
 if(t<=0){ctx.drawImage(part.image,...part.rect.slice(0,2));return}
 const mouth=part.name.startsWith('mouth'),left=part.name.startsWith('eye_screen_left');
 const polygons=mouth?[[68,43],[85,43],[101,40],[118,34],[122,36],[120,42],[106,49],[85,51],[69,49]]:left?[[44,47],[65,32],[108,30],[144,42],[168,62],[153,87],[118,104],[76,100],[51,81]]:[[19,47],[43,33],[86,31],[120,40],[143,60],[127,88],[91,105],[48,97],[24,78]];
 ctx.save();ctx.translate(part.rect[0]+(mouth?20:left?8:3)*t,part.rect[1]);path(ctx,polygons);ctx.clip();ctx.drawImage(part.image,0,0);ctx.restore();
}

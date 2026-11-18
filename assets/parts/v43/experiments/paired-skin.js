function path(ctx,pts){ctx.beginPath();pts.forEach(([x,y],i)=>i?ctx.lineTo(x,y):ctx.moveTo(x,y));ctx.closePath()}
// Isolated material correspondence experiment. No production import.
const cache=new WeakMap();
function can(w,h){const c=document.createElement('canvas');c.width=w;c.height=h;return c}
function pixels(im){if(!cache.has(im)){const c=can(im.width,im.height),x=c.getContext('2d');x.drawImage(im,0,0);cache.set(im,{w:im.width,h:im.height,d:x.getImageData(0,0,im.width,im.height).data})}return cache.get(im)}
function sample(im,x,y){if(x<0||y<0||x>=im.w-1||y>=im.h-1)return [0,0,0,0];const ix=Math.floor(x),iy=Math.floor(y),fx=x-ix,fy=y-iy,o=[0,0,0,0];for(const [dx,dy,w]of [[0,0,(1-fx)*(1-fy)],[1,0,fx*(1-fy)],[0,1,(1-fx)*fy],[1,1,fx*fy]]){const i=((iy+dy)*im.w+ix+dx)*4,aw=im.d[i+3]/255*w;for(let k=0;k<3;k++)o[k]+=im.d[i+k]*aw;o[3]+=aw}if(o[3]>1e-8){for(let k=0;k<3;k++)o[k]/=o[3]}o[3]*=255;return o}

const U=r=>r>1e-12?r*Math.log(r):0;
function fit(from,to){const n=from.length,N=n+3,a=Array.from({length:N},()=>Array(N+2).fill(0));for(let i=0;i<n;i++){for(let j=0;j<n;j++)a[i][j]=U(((from[i][0]-from[j][0])/400)**2+((from[i][1]-from[j][1])/400)**2);a[i][n]=1;a[i][n+1]=from[i][0]/400;a[i][n+2]=from[i][1]/400;a[n][i]=1;a[n+1][i]=from[i][0]/400;a[n+2][i]=from[i][1]/400;a[i][N]=to[i][0];a[i][N+1]=to[i][1]}
 for(let k=0;k<N;k++){let p=k;for(let i=k+1;i<N;i++)if(Math.abs(a[i][k])>Math.abs(a[p][k]))p=i;[a[k],a[p]]=[a[p],a[k]];const v=a[k][k];if(Math.abs(v)<1e-12)throw Error('singular landmarks');for(let j=k;j<N+2;j++)a[k][j]/=v;for(let i=0;i<N;i++)if(i!==k){const f=a[i][k];for(let j=k;j<N+2;j++)a[i][j]-=f*a[k][j]}}
 return (x,y)=>{let ox=a[n][N]+a[n+1][N]*x/400+a[n+2][N]*y/400,oy=a[n][N+1]+a[n+1][N+1]*x/400+a[n+2][N+1]*y/400;for(let i=0;i<n;i++){const w=U(((x-from[i][0])/400)**2+((y-from[i][1])/400)**2);ox+=a[i][N]*w;oy+=a[i][N+1]*w}return [ox,oy]};
}
// Nose, chin, cheek silhouette, temples, scalp, ears and neck. Manual registrations.
const front=[[315,310],[329,414],[235,379],[395,350],[190,260],[420,230],[315,80],[200,170],[420,160],[180,335],[460,290],[330,450],[280,442],[373,442],[234,289],[375,262],[318,356],[315,322]];
const turn=[[340,310],[347,414],[240,373],[405,340],[195,260],[425,230],[315,80],[200,170],[420,160],[185,332],[460,290],[330,450],[280,442],[373,442],[248,289],[379,269],[338,356],[349,323]];
const frontal=[[735,649],[780,909],[548,824],[975,762],[435,572],[1038,510],[735,95],[485,280],[1000,250],[467,705],[1070,605],[790,1030],[650,1020],[920,1020],[596,590],[909,525],[764,772],[728,677]];
const side=[[984,663],[955,935],[685,858],[1100,797],[580,585],[1120,530],[790,110],[540,300],[1080,280],[520,720],[1120,640],[750,1030],[640,1020],[855,1020],[790,660],[1047,621],[960,814],[1005,691]];
for(const [cx,cy,dx,dy,sx,sy] of [[234,289,14,0,40,22],[375,262,4,7,34,22],[318,356,20,0,25,8]])for(const [x,y] of [[-sx,-sy],[sx,-sy],[sx,sy],[-sx,sy]]){front.push([cx+x,cy+y]);turn.push([cx+x+dx,cy+y+dy]);frontal.push([735,649]);side.push([984+(cx+x-315)*2.4,663+(cy+y-310)*2.4]);}
let prepared;
const smooth=(a,b,x)=>{const t=Math.max(0,Math.min(1,(x-a)/(b-a)));return t*t*(3-2*t)};
export function paintPaired(ctx,original,frontImage,sideImage,t,sideContext,visible){
 if(!t)return;
 const sp=pixels(sideImage),src=pixels(original),profile=window.faceDirection||'right',toSide=profile==='right'?((x,y)=>[984+(x-315)*2.9,663+(y-310)*2.9]):profile==='left'?((x,y)=>[620+(x-315)*2.9,750+(y-310)*2.9]):profile==='up'?((x,y)=>[1078+(x-315)*1.6,393+(y-310)*1.6]):((x,y)=>[1780+(x-315)*1.6,500+(y-310)*1.6]),out=ctx.getImageData(0,0,src.w,src.h);
 for(let y=280;y<345;y++)for(let x=280;x<355;x++){const r=Math.hypot((x-315)/28,(y-313)/29),w=t*(1-smooth(.45,1,r));if(!w)continue;const b=sample(sp,...toSide(x,y)),i=(y*src.w+x)*4;for(let k=0;k<3;k++)out.data[i+k]=out.data[i+k]*(1-w)+b[k]*w;}
 ctx.putImageData(out,0,0);
}
export function paintPairedFeature(ctx,part,t){ctx.drawImage(part.image,...part.rect.slice(0,2));}

function featurePolygon(part){const mouth=part.name.startsWith('mouth'),left=part.name.startsWith('eye_screen_left');if(!mouth)return eyeContour(part);if(mouth&&part.state==='open'){const [x0,y0,x1,y1]=part.motion.bounds;return [[x0-2,y0-2],[x1+2,y0-2],[x1+2,y1+2],[x0-2,y1+2]].map(([x,y])=>[x-part.rect[0],y-part.rect[1]])}const poly=mouth?[[68,43],[85,43],[101,40],[118,34],[122,36],[120,42],[106,49],[85,51],[69,49]]:left?[[44,47],[65,32],[108,30],[144,42],[168,62],[153,87],[118,104],[76,100],[51,81]]:[[19,47],[43,33],[86,31],[120,40],[143,60],[127,88],[91,105],[48,97],[24,78]];const origin=mouth?[461,314]:left?[356,229]:[538,204];return poly.map(([x,y])=>[x+origin[0]-part.rect[0],y+origin[1]-part.rect[1]])}

const splitCache=new WeakMap();
function featureLayers(part){if(splitCache.has(part.image))return splitCache.get(part.image);const im=pixels(part.image),core=can(im.w,im.h),context=can(im.w,im.h),a=core.getContext('2d').createImageData(im.w,im.h),b=context.getContext('2d').createImageData(im.w,im.h),poly=featurePolygon(part);for(let y=0;y<im.h;y++)for(let x=0;x<im.w;x++){let inside=false;for(let i=0,j=poly.length-1;i<poly.length;j=i++){const [xi,yi]=poly[i],[xj,yj]=poly[j];if((yi>y+.5)!==(yj>y+.5)&&x+.5<(xj-xi)*(y+.5-yi)/(yj-yi)+xi)inside=!inside}if(part.name==='mouth.closed'){inside=false;for(let dy=-3;dy<=3&&!inside;dy++)for(let dx=-3;dx<=3;dx++){const xx=x+dx,yy=y+dy;if(xx<0||yy<0||xx>=im.w||yy>=im.h)continue;const gx=xx+part.rect[0],gy=yy+part.rect[1],[x0,y0,x1,y1]=part.motion.bounds;if(gx<x0||gx>x1||gy<y0||gy>y1)continue;const z=(yy*im.w+xx)*4;if(im.d[z+3]>128&&im.d[z+1]<220&&im.d[z]-im.d[z+1]>22){inside=true;break}}}const d=inside?a.data:b.data,idx=(y*im.w+x)*4;for(let k=0;k<4;k++)d[idx+k]=im.d[idx+k]}core.getContext('2d').putImageData(a,0,0);context.getContext('2d').putImageData(b,0,0);const out={core,context};splitCache.set(part.image,out);return out}

const contourCache=new WeakMap();
function previousEyeHull(part){if(contourCache.has(part.image))return contourCache.get(part.image);const im=pixels(part.image),[gx0,gy0,gx1,gy1]=part.motion.bounds,pts=[];for(let y=Math.max(0,gy0-part.rect[1]-6);y<Math.min(im.h,gy1-part.rect[1]+6);y++)for(let x=Math.max(0,gx0-part.rect[0]-6);x<Math.min(im.w,gx1-part.rect[0]+6);x++){const i=(y*im.w+x)*4;if(im.d[i+3]>128&&im.d[i]<235&&im.d[i+1]<180)pts.push([x,y])}pts.sort((a,b)=>a[0]-b[0]||a[1]-b[1]);const cross=(o,a,b)=>(a[0]-o[0])*(b[1]-o[1])-(a[1]-o[1])*(b[0]-o[0]);const lower=[],upper=[];for(const p of pts){while(lower.length>1&&cross(lower.at(-2),lower.at(-1),p)<=0)lower.pop();lower.push(p)}for(const p of [...pts].reverse()){while(upper.length>1&&cross(upper.at(-2),upper.at(-1),p)<=0)upper.pop();upper.push(p)}const hull=lower.slice(0,-1).concat(upper.slice(0,-1));if(hull.length<3)throw Error('Missing eye contour '+part.file);const center=hull.reduce((a,p)=>[a[0]+p[0]/hull.length,a[1]+p[1]/hull.length],[0,0]),poly=hull.map(p=>{const dx=p[0]-center[0],dy=p[1]-center[1],l=Math.hypot(dx,dy);return[p[0]+2*dx/l,p[1]+2*dy/l]});contourCache.set(part.image,poly);return poly}

export function featureDebug(parts){return parts.map(p=>({name:p.name,core:featureLayers(p).core.toDataURL(),context:featureLayers(p).context.toDataURL()}))}

function eyeContour(part){const left=part.name.startsWith('eye_screen_left'),origin=left?[356,229]:[538,204],poly=left?[[65,73],[72,60],[76,53],[78,43],[90,44],[100,38],[118,36],[133,39],[145,46],[151,53],[147,56],[147,74],[138,81],[122,86],[108,91],[95,88],[82,81],[74,77]]:[[35,65],[38,51],[50,42],[63,35],[79,30],[84,27],[89,32],[105,31],[104,37],[114,37],[112,41],[123,46],[129,49],[120,53],[113,60],[109,71],[101,79],[87,83],[67,83],[52,80],[42,73],[37,68]];return poly.map(([x,y])=>[x+origin[0]-part.rect[0],y+origin[1]-part.rect[1]])}

export function materialDebug(){return can(1,1).toDataURL()}

const mapCache=new Map();
function endpoint(profile){
 if(profile==='right')return turn;
 const out=front.map(p=>p.slice());
 const deltas=profile==='left'?[[-25,0],[-18,0],[-10,-7],[-5,-2],[-5,0],[-5,0],[0,0],[0,0],[0,0],[0,0],[-5,2],[0,0],[0,0],[0,0],[-4,-7],[-14,0],[-20,0],[-34,1]]:profile==='up'?[[0,-8],[0,-17],[0,-12],[0,-12],[0,-4],[0,-4],[0,0],[0,0],[0,0],[0,-5],[0,-5],[0,0],[0,0],[0,0],[0,-5],[0,-5],[0,-13],[0,-11]]:[[0,7],[0,-3],[0,0],[0,0],[0,5],[0,5],[0,0],[0,0],[0,0],[0,3],[0,3],[0,0],[0,0],[0,0],[0,8],[0,8],[0,2],[0,5]];
 for(let i=0;i<18;i++)out[i]=front[i].map((v,k)=>v+deltas[i][k]);
 for(let i=18;i<front.length;i++){const feature=14+Math.floor((i-18)/4);out[i]=front[i].map((v,k)=>v+deltas[feature][k]);}
 return out;
}
function maps(t){const profile=window.faceDirection||'right',key=profile+':'+t;if(!mapCache.has(key)){const end=endpoint(profile),dest=front.map((p,i)=>p.map((v,k)=>v+(end[i][k]-v)*t));const raw=fit(front,dest);const forward=(x,y)=>{let q=raw(x,y);for(const [index,sx,sy]of [[14,53,32],[15,51,32],[16,33,15]]){const c=front[index],r=Math.max(Math.abs(x-c[0])/sx,Math.abs(y-c[1])/sy),w=1-smooth(1,1.35,r);if(w){q=[q[0]*(1-w)+(x+dest[index][0]-c[0])*w,q[1]*(1-w)+(y+dest[index][1]-c[1])*w];}}return q};mapCache.set(key,{inverse:fit(dest,front),forward});}return mapCache.get(key)}

function followWeight(x,y){return smooth(120,200,y)*(1-smooth(425,470,y))*smooth(100,170,x)*(1-smooth(470,530,x))}
export function warpHeadImage(im,t){if(!t)return im;const src=pixels(im),c=can(src.w,src.h),cx=c.getContext('2d'),out=cx.createImageData(src.w,src.h),map=maps(t).inverse;out.data.set(src.d);for(let y=120;y<Math.min(470,src.h);y++)for(let x=100;x<Math.min(530,src.w);x++){const w=followWeight(x,y),q=map(x,y),v=sample(src,x+(q[0]-x)*w,y+(q[1]-y)*w),i=(y*src.w+x)*4;for(let k=0;k<4;k++)out.data[i+k]=v[k]}cx.putImageData(out,0,0);return c}
export function followHairGeometry(geometry,t){if(!t)return geometry;const out=geometry.slice(),map=maps(t).forward;for(let i=0;i<out.length;i+=2){const x=out[i]*1086-235,y=out[i+1]*1448-1,w=followWeight(x,y),q=map(x,y);out[i]+=(q[0]-x)*w/1086;out[i+1]+=(q[1]-y)*w/1448;}return out}

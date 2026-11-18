// Prototype eye compositor: gaze translates an unscaled iris, lids own closure.
export const clampEye=v=>Math.min(1,Math.max(0,v));
export function eyeCurve(points,x){let i=1;while(i<points.length-1&&points[i][0]<x)i++;const a=points[i-1],b=points[i],p=points[Math.max(0,i-2)],q=points[Math.min(points.length-1,i+1)],t=clampEye((x-a[0])/(b[0]-a[0])),span=b[0]-a[0],ma=(b[1]-p[1])/(b[0]-p[0]),mb=(q[1]-a[1])/(q[0]-a[0]);return (2*t**3-3*t*t+1)*a[1]+(t**3-2*t*t+t)*ma*span+(-2*t**3+3*t*t)*b[1]+(t**3-t*t)*mb*span;}
export function eyeAperture(meta,x,openness){const bottom=eyeCurve(meta.lower,x),top=eyeCurve(meta.upper,x);const o=clampEye(openness),closed=eyeCurve(meta.closed,x);return [closed+(top-closed)*o,closed+(bottom-closed)*o];}
export async function loadEyeComponents(base='/model/eyes_v46/',profile='left-neutral.json'){
 const meta=await(await fetch(base+profile)).json(),images={};
 for(const name of ['hair-foreground-mask','skin-calibrated','lower-lash','original','fixed-original','upper-lash','iris-visible','sclera-visible','iris-completed','sclera-registered','skin-registered']){const im=new Image();im.src=base+name+'.png';await im.decode();images[name]=im;}
 const pixels={};for(const [name,im] of Object.entries(images)){const c=document.createElement('canvas');c.width=meta.size[0];c.height=meta.size[1];const ctx=c.getContext('2d');ctx.drawImage(im,0,0);pixels[name]=ctx.getImageData(0,0,c.width,c.height).data;}
 const closed=new Image();closed.src='/model/'+(meta.closedFile||'eye_screen_left_closed.png');await closed.decode();const patch=document.createElement('canvas');patch.width=meta.size[0];patch.height=meta.size[1];const pc=patch.getContext('2d');pc.drawImage(closed,...(meta.closedOffset||[-12,-12]));pixels['closed-reference']=pc.getImageData(0,0,patch.width,patch.height).data;
 return expandEyeCanvas({meta,images,pixels},closed);
}
// Recover a valid premultiplied foreground without changing its composited
// native colour. A low guessed alpha cannot represent a dark rim pixel.
export function recoverIrisPixel(rgb,paper,alpha){
 for(let k=0;k<3;k++){
  alpha=Math.max(alpha,paper[k]>0?1-rgb[k]/paper[k]:0,paper[k]<255?(rgb[k]-paper[k])/(255-paper[k]):0);
 }
 alpha=clampEye(alpha);
 return [...rgb.map((v,k)=>Math.min(255*alpha,Math.max(0,v-paper[k]*(1-alpha)))),alpha];
}
export function fixedLowerLidPixel(rgb,dy,r){return dy>0&&r>.4&&rgb[0]>230&&rgb[2]>100&&rgb[1]-rgb[2]<35;}
function gazeLayer(eye){
 if(eye.gazeLayer)return eye.gazeLayer;
 const {meta,pixels}=eye,[w,h]=meta.size,a=new Float32Array(w*h*4),paper=[255,249,245],backdrop=new Float32Array(w*h*4);
 // The lower iris overlaps a painted skin/lid edge, not uniform white.
 // Estimate its fixed backing from bright native neighbours at the same height.
 // Keep the upper sclera/glint region on the original paper colour.
 for(let y=0;y<h;y++)for(let x=0;x<w;x++){
  const i=(y*w+x)*4,weight=clampEye((y-meta.irisCenter[1]-meta.irisRadius[1]*.2)/5);let local=paper;
  if(weight>0){const candidates=[-1,1].map(sign=>{const xx=Math.max(0,Math.min(w-1,Math.round(meta.irisCenter[0]+sign*(meta.irisRadius[0]+7))));return Array.from(pixels.original.slice((y*w+xx)*4,(y*w+xx)*4+3));}).filter(c=>c[0]>235&&c[1]>180&&c[2]>150);if(candidates.length)local=paper.map((_,k)=>candidates.reduce((v,c)=>v+c[k],0)/candidates.length);}
  for(let k=0;k<3;k++)backdrop[i+k]=paper[k]*(1-weight)+local[k]*weight;
 }
 for(let y=0;y<h;y++)for(let x=0;x<w;x++){
  const i=(y*w+x)*4,dx=x-meta.irisCenter[0],dy=y-meta.irisCenter[1],r=(dx/(meta.irisRadius[0]+5))**2+(dy/(meta.irisRadius[1]+6))**2;
  if(r>=1)continue;
  const visible=x>=meta.upper[0][0]&&x<=meta.upper.at(-1)[0]&&y>=eyeCurve(meta.upper,x)&&y<=eyeCurve(meta.lower,x)+6;
  let alpha=clampEye((1-r)*10),rgb;
  if(visible){rgb=Array.from(pixels.original.slice(i,i+3));
   // The approximate iris ellipse also crosses peach lower-lid skin. Skin is
   // fixed ownership, not opaque iris to erase and replace with white sclera.
   const lowerSkin=fixedLowerLidPixel(rgb,dy,r);
   if(lowerSkin)continue;
   // Separate pale sclera from the iris at its rim, keeping interior glints opaque.
   if(r>.52&&!(Math.abs(dx-2)<6&&Math.abs(dy+10)<6))alpha*=clampEye((paper[2]-rgb[2])/55);
   if(y>eyeCurve(meta.lower,x)&&!(rgb[0]-rgb[1]>12&&rgb[1]-rgb[2]>12))alpha=0;
   if(alpha<.015)continue;
   const recovered=recoverIrisPixel(rgb,Array.from(backdrop.slice(i,i+3)),alpha);alpha=recovered[3];for(let k=0;k<3;k++)a[i+k]=recovered[k];
  }else{alpha*=pixels['iris-completed'][i+3]/255;for(let k=0;k<3;k++)a[i+k]=pixels['iris-completed'][i+k]*alpha;}
  a[i+3]=alpha;
 }
 return eye.gazeLayer={pixels:a,paper,backdrop};
}
export function paintEyeComponents(ctx,eye,opening=1,gazeX=0,gazeY=0){
 const {meta,pixels}=eye,[w,h]=meta.size,o=clampEye(opening),gx=Math.max(-1,Math.min(1,gazeX))*meta.gazePixels[0],gy=Math.max(-1,Math.min(1,gazeY))*meta.gazePixels[1];
 if(o===1&&gx===0&&gy===0){ctx.putImageData(new ImageData(new Uint8ClampedArray(pixels.original),w,h),0,0);return;}
 if(o===0&&meta.authoredClosure){ctx.putImageData(new ImageData(new Uint8ClampedArray(pixels['closed-reference']),w,h),0,0);return;}
 if(meta.authoredClosure){paintRegisteredEye(ctx,eye,o,gx,gy);return;}
 const original=pixels.original,skin=pixels['skin-calibrated'],output=new Uint8ClampedArray(original);
 const hair=pixels['hair-foreground-mask'];
 const sample=(a,x,y)=>{x=Math.max(0,Math.min(w-1,x));y=Math.max(0,Math.min(h-1,y));const x0=Math.floor(x),y0=Math.floor(y),x1=Math.min(w-1,x0+1),y1=Math.min(h-1,y0+1),fx=x-x0,fy=y-y0;return [0,1,2,3].map(k=>a[(y0*w+x0)*4+k]*(1-fx)*(1-fy)+a[(y0*w+x1)*4+k]*fx*(1-fy)+a[(y1*w+x0)*4+k]*(1-fx)*fy+a[(y1*w+x1)*4+k]*fx*fy);};
 const lidSample=(x,y)=>{const index=(Math.round(Math.max(0,Math.min(h-1,y)))*w+x)*4;if(hair[index]>0){
  if(!meta.contourLidSampling){const a=sample(original,x-5,y),b=sample(original,x+5,y);return a.map((v,k)=>(v+b[k])*.5);}
  const offset=y-eyeCurve(meta.upper,x),neighbors=[];
  for(const direction of [-1,1])for(let distance=1;distance<=24;distance++){const xx=x+direction*distance;if(xx<meta.upper[0][0]||xx>meta.upper.at(-1)[0])break;const yy=eyeCurve(meta.upper,xx)+offset;if(sample(hair,xx,yy)[0]<8){neighbors.push({value:sample(original,xx,yy),weight:1/distance});break}}
  if(neighbors.length){const total=neighbors.reduce((s,n)=>s+n.weight,0);return [0,1,2,3].map(k=>neighbors.reduce((s,n)=>s+n.value[k]*n.weight,0)/total);}
 }return sample(original,x,y);};
 const moving=gazeLayer(eye);
 const cheekResidual=x=>{const values=[];for(let xx=Math.max(meta.upper[0][0],x-6);xx<=Math.min(meta.upper.at(-1)[0],x+6);xx++)for(let offset=-5;offset<=11;offset++){const yy=eyeCurve(meta.lower,xx)+offset,a=sample(offset<6?pixels['closed-reference']:original,xx,yy),b=sample(skin,xx,yy);if(a[0]>245&&a[1]>205&&a[2]>180&&sample(hair,xx,yy)[0]<8)values.push(a.slice(0,3).map((v,k)=>v-b[k]));}return [0,1,2].map(k=>values.length?values.reduce((s,v)=>s+v[k],0)/values.length:0);};
 for(let x=meta.upper[0][0];x<=meta.upper.at(-1)[0];x++){const top=eyeCurve(meta.upper,x),bottom=eyeCurve(meta.lower,x),[nt,nb]=eyeAperture(meta,x,o),thickness=.65+.35*o,band=meta.lidBand||16+8*clampEye((100-x)/10);
  const residual=cheekResidual(x);
  for(let y=Math.max(0,Math.ceil(top-band));y<Math.min(h,Math.max(bottom+5,nb+5));y++){const index=(y*w+x)*4;let c;
   const cover=(lo,hi)=>Math.max(0,Math.min(y+.5,hi)-Math.max(y-.5,lo));
   const wa=cover(nt,nb),wu=cover(nt-band*thickness,nt),wl=cover(nb,nb+5)*o,ws=Math.max(0,1-wa-wu-wl);
   let ball=Array.from(original.slice(index,index+4));
   if(gx!==0||gy!==0){const rest=sample(moving.pixels,x,y),shifted=sample(moving.pixels,x-gx,y-gy);ball=ball.map((z,k)=>k===3?z:z-rest[k]+shifted[k]+moving.backdrop[index+k]*(rest[3]-shifted[3]));}
   let upper=lidSample(x,top-(nt-y)/thickness);
   if(meta.authoredClosure){const target=sample(pixels['closed-reference'],x,eyeCurve(meta.closed,x)+(y-nt));upper=upper.map((v,k)=>v*o+target[k]*(1-o));}
   const lower=sample(original,x,bottom+(y-nb));
   let backing=Array.from(skin.slice(index,index+4));
   // Match the disoccluded skin to the original cheek at the lower boundary.
   // This is a colour residual, not a displacement of the eye or its texture.
   const cheekWeight=clampEye((y-(top-band))/(bottom+5-(top-band)));
   backing=backing.map((v,k)=>k===3?v:v+residual[k]*cheekWeight);
   const fixedEdge=clampEye(Math.min(y-(top-band),bottom+5-y));backing=backing.map((v,k)=>original[index+k]*(1-fixedEdge)+v*fixedEdge);
   c=backing.map((v,k)=>v*ws+upper[k]*wu+ball[k]*wa+lower[k]*wl);
   // Existing hair strand crossing the upper lid belongs to foreground hair.
   if(hair[index]>0){const alpha=hair[index]/255,oldUpper=cover(top-band,top),oldBall=cover(top,bottom),oldLower=cover(bottom,bottom+5),oldSkin=Math.max(0,1-oldUpper-oldBall-oldLower),lid=lidSample(x,y);const under=backing.map((v,k)=>v*oldSkin+lid[k]*oldUpper+original[index+k]*(oldBall+oldLower));c=c.map((v,k)=>original[index+k]+(v-under[k])*(1-alpha));}
   c[3]=original[index+3];for(let k=0;k<4;k++)output[index+k]=c[k];
  }
 }
 if(meta.authoredClosure){
  // Both upper-lid textures have already been registered to the same curve.
  // Restore the authored opaque endpoint, without fading displaced eye marks.
  const weight=clampEye(o/.2);const smooth=weight*weight*(3-2*weight);
  for(let i=0;i<output.length;i++)output[i]=pixels['closed-reference'][i]*(1-smooth)+output[i]*smooth;
 }
 ctx.putImageData(new ImageData(output,w,h),0,0);
}

// Openness describes a fraction of this expression's authored aperture.
// expressionParameters already applies its cap: undo that cap exactly once.
export function eyeOpening(value, authoredMaximum=1){return authoredMaximum>0?clampEye(value/authoredMaximum):0;}
export function alignEyeExpression(base,pixels,id,name){
 const meta={...base,upper:base.upper.map(p=>[...p]),lower:base.lower.map(p=>[...p]),closed:base.closed.map(p=>[...p]),irisCenter:[...base.irisCenter],authoredClosure:true};
 const left=name==='eye_screen_left',first=meta.upper[0][0],last=meta.upper.at(-1)[0];
 const lift=id==='surprised'?(left?-12:-15):id==='bashful'?12:id==='thinking'&&!left?-13:0;
 meta.upper=meta.upper.map(([x,y])=>[x,y+lift*Math.sin(Math.PI*(x-first)/(last-first))]);
 meta.irisCenter[1]+=4;
 if(id==='thinking')meta.irisCenter[0]-=left?13:12;
 const offsets={neutral:[0,0],soft_smile:[-15,-6],worried:[-7,0],surprised:[-17,-7],bashful:[-14,-6],displeased:[-7,4],thinking:[-4,0]};
 const offset=(offsets[id]||[0,0])[left?0:1];meta.closed=meta.closed.map(([x,y])=>[x,y+offset]);
 const [w,h]=meta.size,closed=pixels['closed-reference'];
 // Locate the lower edge of the actual painted closed lash at each interior
 // column. End corners remain independently authored (hair occludes them).
 meta.closed=meta.closed.map(([x,y],i)=>{
  if(i===0||i===meta.closed.length-1)return [x,y];
  const runs=[];let start=null;
  for(let yy=Math.max(0,Math.floor(y-18));yy<=Math.min(h-1,Math.ceil(y+18));yy++){
   const k=(yy*w+x)*4,dark=(closed[k]+closed[k+1]+closed[k+2])/3<155&&closed[k]<210;
   if(dark&&start===null)start=yy;
   if(!dark&&start!==null){runs.push([start,yy-1]);start=null;}
  }
  const candidates=runs.filter(r=>r[1]-r[0]>=2&&r[1]-r[0]<22).sort((a,b)=>Math.abs(a[1]-y)-Math.abs(b[1]-y));
  return [x,candidates.length?candidates[0][1]+1:y];
 });
 // Only clean skin below the closed lash supplies the newly exposed lid skin;
 // never reuse neutral blush underneath a different expression.
 const skin=new Uint8ClampedArray(pixels['skin-calibrated']);
 for(let x=first;x<=last;x++)for(let y=0;y<h;y++){
  const sourceY=Math.min(h-1,Math.max(y,Math.ceil(eyeCurve(meta.closed,x)+9))),i=(y*w+x)*4,j=(sourceY*w+x)*4;
  if(closed[j]>225&&closed[j+1]>160&&closed[j+2]>130)for(let c=0;c<3;c++)skin[i+c]=closed[j+c];
 }
 pixels['skin-calibrated']=skin;
 return meta;
}

// Match skin/lash landmarks before mixing their colour. Iris pixels are never
// part of this normal map: they are translated at native scale and clipped.
function paintRegisteredEye(ctx,eye,o,gx,gy){
 const {meta,pixels}=eye,[w,h]=meta.size,original=pixels.original,closed=pixels['closed-reference'],hair=pixels['hair-foreground-mask'],out=new Uint8ClampedArray(original),moving=gazeLayer(eye);
 const sample=(a,x,y,k)=>{x=Math.max(0,Math.min(w-1,x));y=Math.max(0,Math.min(h-1,y));const ix=Math.floor(x),iy=Math.floor(y),fx=x-ix,fy=y-iy;let value=0;for(let dy=0;dy<2;dy++)for(let dx=0;dx<2;dx++){const at=(Math.min(h-1,iy+dy)*w+Math.min(w-1,ix+dx))*4,weight=(dx?fx:1-fx)*(dy?fy:1-fy);value+=a[at+k]*weight*(k<3&&a!==moving.pixels?a[at+3]/255:1);}return value;};
 const native=(a,i,k)=>a[i+k]*(k<3?a[i+3]/255:1);

 const first=meta.upper[0][0],last=meta.upper.at(-1)[0];
 const inkStart=(data,x,edge)=>{let found=edge-6;for(let y=Math.max(0,Math.ceil(edge-18));y<edge;y++){const i=(y*w+x)*4;if(data[i+3]>200&&data[i]<185&&data[i+1]<135&&data[i+2]<125){found=y;break;}}return found;};
 for(let x=0;x<w;x++){
  const xx=Math.max(first,Math.min(last,x)),top=eyeCurve(meta.upper,xx),bottom=eyeCurve(meta.lower,xx),shut=eyeCurve(meta.closed,xx),[nt,nb]=eyeAperture(meta,xx,o),lo=Math.max(0,Math.min(top,shut)-32),hi=Math.min(h-1,Math.max(bottom,shut)+24);
  const side=clampEye(Math.min((x-first+10)/10,(last+10-x)/10));
  const ot=inkStart(original,x,top),ct=inkStart(closed,x,shut),it=ot*o+ct*(1-o);
  for(let y=0;y<h;y++){const i=(y*w+x)*4;
  let sy=y,cy=y;
  if(y>=lo&&y<it){sy=lo+(y-lo)*(ot-lo)/Math.max(.001,it-lo);cy=lo+(y-lo)*(ct-lo)/Math.max(.001,it-lo);}
  else if(y>=it&&y<nt){sy=ot+(y-it)*(top-ot)/Math.max(.001,nt-it);cy=ct+(y-it)*(shut-ct)/Math.max(.001,nt-it);}
  else if(y>=nb&&y<=hi){sy=bottom+(y-nb)*(hi-bottom)/Math.max(.001,hi-nb);cy=shut+(y-nb)*(hi-shut)/Math.max(.001,hi-nb);}
  else if(y>=nt&&y<nb){sy=y;cy=shut;}
  const aperture=side*Math.max(0,Math.min(y+.5,nb)-Math.max(y-.5,nt));
  for(let k=0;k<4;k++){
   const base=native(original,i,k)*o+native(closed,i,k)*(1-o);
   const aligned=sample(original,x,sy,k)*o+sample(closed,x,cy,k)*(1-o);
   let ball=native(original,i,k);if(k<3&&(gx||gy)){const ra=sample(moving.pixels,x,y,3),sa=sample(moving.pixels,x-gx,y-gy,3);ball=ball-sample(moving.pixels,x,y,k)+sample(moving.pixels,x-gx,y-gy,k)+moving.backdrop[i+k]*(ra-sa);}
   let value=base*(1-side)+aligned*side;value=value*(1-aperture)+ball*aperture;
   const fixed=hair[i]/255;out[i+k]=value*(1-fixed)+base*fixed;
  }
  if(out[i+3]>0)for(let k=0;k<3;k++)out[i+k]=out[i+k]*255/out[i+3];
 }}
 ctx.putImageData(new ImageData(out,w,h),0,0);
}

function expandEyeCanvas(eye,closedImage){
 const {meta,pixels}=eye,[w,h]=meta.size,[ox,oy]=meta.closedOffset||[-12,-12],px=-Math.min(0,ox),py=-Math.min(0,oy),nw=Math.max(w,ox+closedImage.width)+px,nh=Math.max(h,oy+closedImage.height)+py;
 const shifted={};for(const [name,data] of Object.entries(pixels)){const a=new Uint8ClampedArray(nw*nh*4);for(let y=0;y<h;y++)a.set(data.subarray(y*w*4,(y+1)*w*4),((y+py)*nw+px)*4);shifted[name]=a;}
 const c=document.createElement('canvas');c.width=nw;c.height=nh;const ctx=c.getContext('2d');ctx.drawImage(closedImage,ox+px,oy+py);shifted['closed-reference']=ctx.getImageData(0,0,nw,nh).data;
 const shift=points=>points.map(([x,y])=>[x+px,y+py]);return {...eye,pixels:shifted,meta:{...meta,size:[nw,nh],rect:[meta.rect[0]-px,meta.rect[1]-py,meta.rect[0]-px+nw,meta.rect[1]-py+nh],upper:shift(meta.upper),lower:shift(meta.lower),closed:shift(meta.closed),irisCenter:[meta.irisCenter[0]+px,meta.irisCenter[1]+py]}};
}

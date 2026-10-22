// Registered, contour-guided interpolation on one opaque hand surface.
// The silhouette moves between authored angles; two translucent hands are never
// overlaid. The proximal wrist retains its accepted paint and attachment.
const clamp=x=>Math.max(0,Math.min(1,x));
const smooth=x=>{x=clamp(x);return x*x*(3-2*x)};
const axis=[130/Math.hypot(130,118),-118/Math.hypot(130,118)],origin=[27,127];
const uv=(x,y)=>[(x-origin[0])*axis[0]+(y-origin[1])*axis[1],-(x-origin[0])*axis[1]+(y-origin[1])*axis[0]];
const xy=(u,v)=>[origin[0]+u*axis[0]-v*axis[1],origin[1]+u*axis[1]+v*axis[0]];
function sample(p,w,h,x,y){
 const ix=Math.floor(x),iy=Math.floor(y),fx=x-ix,fy=y-iy,result=[0,0,0,0];
 for(let j=0;j<2;j++)for(let i=0;i<2;i++){
  if(ix+i<0||iy+j<0||ix+i>=w||iy+j>=h)continue;
  const k=((iy+j)*w+ix+i)*4,f=(i?fx:1-fx)*(j?fy:1-fy),a=p[k+3]/255;
  for(let c=0;c<3;c++)result[c]+=p[k+c]*a*f;
  result[3]+=a*f;
 }
 return result;
}
export function handAngleMap(front,side,w,h){
 const spans=[front,side].map(p=>Array.from({length:261},(_,i)=>{
  const u=i-70;let lo=Infinity,hi=-Infinity;
  for(let v=-100;v<=100;v+=.5){const [x,y]=xy(u,v);if(sample(p,w,h,x,y)[3]>.3){lo=Math.min(lo,v);hi=Math.max(hi,v)}}
  return Number.isFinite(lo)?[lo-.6,hi+.6]:null;
 }));
 return {front,side,w,h,spans};
}
export function paintHandAngle(map,amount){
 const {front,side,w,h,spans}=map,t=clamp(amount);
 if(t===0)return new Uint8ClampedArray(front);
 const result=new Uint8ClampedArray(w*h*4);
 for(let y=0;y<h;y++)for(let x=0;x<w;x++){
  const k=(y*w+x)*4,[u,v]=uv(x,y),i=Math.floor(u)+70,frac=u-Math.floor(u);
  const at=s=>{const a=s[i],b=s[i+1];return a&&b?a.map((q,j)=>q+(b[j]-q)*frac):a};
  const a=at(spans[0]),b=at(spans[1]),blend=t*smooth(u/45);
  if(!a||!b||blend===0){result.set(front.subarray(k,k+4),k);continue}
  const lo=a[0]+(b[0]-a[0])*blend,hi=a[1]+(b[1]-a[1])*blend,f=(v-lo)/(hi-lo);
  if(f<0||f>1)continue;
  const va=a[0]+f*(a[1]-a[0]),vb=b[0]+f*(b[1]-b[0]);
  const A=sample(front,w,h,...xy(u,va)),B=sample(side,w,h,...xy(u,vb));
  const coverage=A[3]*(1-blend)+B[3]*blend;
  if(coverage<1e-5)continue;
  // Colour is interpolated on a registered surface, not as layer opacity.
  // Alpha is its coverage, preserving genuine finger gaps and antialiasing.
  for(let c=0;c<3;c++)result[k+c]=(A[c]*(1-blend)+B[c]*blend)/coverage;
  result[k+3]=255*coverage;
 }
 return result;
}

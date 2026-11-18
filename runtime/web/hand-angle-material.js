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
// Match internal creases and finger gaps before interpolating colour. Merely
// aligning the outside contour leaves two different sets of ink strokes.
function correspondence(front,side,w,h,u,a,b,previous){
 const n=65;
 const profile=(pixels,span)=>Array.from({length:n},(_,i)=>{
  const p=sample(pixels,w,h,...xy(u,span[0]+i/(n-1)*(span[1]-span[0]))),alpha=p[3];
  return {alpha,luma:alpha>.02?(p[0]*.2126+p[1]*.7152+p[2]*.0722)/(255*alpha):1};
 });
 const A=profile(front,a),B=profile(side,b);
 const ink=(p,i)=>{let peak=0;for(let j=Math.max(0,i-4);j<=Math.min(n-1,i+4);j++)peak=Math.max(peak,p[j].luma);return peak-p[i].luma};
 const cost=(i,j)=>6*Math.abs(A[i].alpha-B[j].alpha)+12*Math.abs(ink(A,i)-ink(B,j))+Math.abs(A[i].luma-B[j].luma)+.0015*Math.abs(i-j)+(previous?.[i]!==undefined ? .06*Math.abs(j-previous[i]*(n-1)):0);
 const dp=Array.from({length:n},()=>new Float64Array(n).fill(Infinity)),parent=Array.from({length:n},()=>new Int8Array(n));dp[0][0]=cost(0,0);
 for(let i=1;i<n;i++)for(let j=Math.max(1,i-18);j<Math.min(n,i+19);j++){
  for(const [di,dj,code] of [[1,1,1],[1,2,2],[2,1,3]])if(i>=di&&j>=dj){
   const candidate=dp[i-di][j-dj]+cost(i,j)+(code===1?0:.045);
   if(candidate<dp[i][j]){dp[i][j]=candidate;parent[i][j]=code}
  }
 }
 const path=[];let i=n-1,j=n-1;path.push([i,j]);
 while(i>0&&j>0){const code=parent[i][j];if(!code)break;i-=code===3?2:1;j-=code===2?2:1;path.push([i,j])}
 path.reverse();const map=new Float32Array(n);let k=0;
 for(let x=0;x<n;x++){while(k<path.length-2&&path[k+1][0]<x)k++;const [x0,y0]=path[k],[x1,y1]=path[Math.min(k+1,path.length-1)];map[x]=(x1===x0?y0:y0+(y1-y0)*(x-x0)/(x1-x0))/(n-1)}
 return map;
}
export function alignedCoordinates(map,f,blend){
 if(!map)return [f,f];let lo=0,hi=map.length-1;
 const target=i=>(1-blend)*i/(map.length-1)+blend*map[i];
 while(hi-lo>1){const mid=(lo+hi)>>1;if(target(mid)<f)lo=mid;else hi=mid}
 const t=clamp((f-target(lo))/(target(hi)-target(lo)));
 return [(lo+t)/(map.length-1),map[lo]+(map[hi]-map[lo])*t];
}
export function handAngleMap(front,side,w,h){
 const spans=[front,side].map(p=>Array.from({length:261},(_,i)=>{
  const u=i-70;let lo=Infinity,hi=-Infinity;
  for(let v=-100;v<=100;v+=.5){const [x,y]=xy(u,v);if(sample(p,w,h,x,y)[3]>.3){lo=Math.min(lo,v);hi=Math.max(hi,v)}}
  return Number.isFinite(lo)?[lo-.6,hi+.6]:null;
 }));
 const raw=[];for(let i=0;i<spans[0].length;i++){const a=spans[0][i],b=spans[1][i];raw.push(a&&b?correspondence(front,side,w,h,i-70,a,b,raw[i-1]):null)}
 // Average neighbouring longitudinal sections without changing endpoint order.
 const matches=raw.map((a,i)=>a?Float32Array.from(a,(v,k)=>{let sum=0,weight=0;for(let j=Math.max(0,i-6);j<=Math.min(raw.length-1,i+6);j++)if(raw[j]){const w=Math.exp(-((j-i)**2)/18);sum+=raw[j][k]*w;weight+=w}return sum/weight}):null);
 return {front,side,w,h,spans,matches};
}
export function paintHandAngle(map,amount){
 const {front,side,w,h,spans,matches}=map,t=clamp(amount);
 if(t===0)return new Uint8ClampedArray(front);
 const result=new Uint8ClampedArray(w*h*4);
 for(let y=0;y<h;y++)for(let x=0;x<w;x++){
  const k=(y*w+x)*4,[u,v]=uv(x,y),i=Math.floor(u)+70,frac=u-Math.floor(u);
  const at=s=>{const a=s[i],b=s[i+1];return a&&b?a.map((q,j)=>q+(b[j]-q)*frac):a};
  const a=at(spans[0]),b=at(spans[1]),blend=t*smooth(u/45);
  if(!a||!b||blend===0){result.set(front.subarray(k,k+4),k);continue}
  const lo=a[0]+(b[0]-a[0])*blend,hi=a[1]+(b[1]-a[1])*blend,f=(v-lo)/(hi-lo);
  if(f<0||f>1)continue;
  const c0=alignedCoordinates(matches?.[i],f,blend),c1=alignedCoordinates(matches?.[i+1],f,blend);
  const fa=c0[0]+(c1[0]-c0[0])*frac,fb=c0[1]+(c1[1]-c0[1])*frac;
  const va=a[0]+fa*(a[1]-a[0]),vb=b[0]+fb*(b[1]-b[0]);
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

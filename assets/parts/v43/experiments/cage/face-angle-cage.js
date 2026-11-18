// Small-angle portrait cage. Facial features are protected rigid islands;
// the surrounding skin interpolates sparse contour/occlusion landmarks.
// This is a bounded 2.5D approximation, not full side-view artwork.
const clamp=(v,a,b)=>Math.min(b,Math.max(a,v));
const smooth=(a,b,v)=>{const t=clamp((v-a)/(b-a),0,1);return t*t*(3-2*t)};
const anchors=[
 // x,y, yaw displacement, pitch displacement. Signed yaw points screen-right.
 [395,245,-4,0],[410,330,-3,-1],[470,390,3,-2],
 [565,418,7,-3],[645,365,5,-2],[695,270,-3,0],
 [480,294,5,-3],[620,262,5,-3],[550,320,12,-7],[570,363,8,-5],
 [540,140,0,2],[540,455,0,0],
];
const features=[{x:480,y:294,rx:58,ry:37,dx:5,dy:-3},
 {x:620,y:262,rx:53,ry:35,dx:5,dy:-3},
 {x:570,y:363,rx:48,ry:24,dx:8,dy:-5}];
export function faceAngleOffset(x,y,angleX,angleY){
 const yaw=clamp(angleX/15,-1,1),pitch=clamp(angleY/10,-1,1);
 let sx=0,sy=0,total=0;
 for(const [ax,ay,dx,dy] of anchors){const w=1/(100+(x-ax)**2+(y-ay)**2)**2;total+=w;sx+=w*dx*yaw;sy+=w*dy*pitch;}
 sx/=total;sy/=total;
 // Eye and mouth art move as units; unlike the rejected depth cap, the
 // displacement has no depth gradient through the pupils or mouth interior.
 for(const f of features){const radius=Math.hypot((x-f.x)/f.rx,(y-f.y)/f.ry),w=1-smooth(.85,1.5,radius);sx=sx*(1-w)+f.dx*yaw*w;sy=sy*(1-w)+f.dy*pitch*w;}
 const coverage=smooth(170,220,y)*(1-smooth(418,465,y))*(1-smooth(150,220,Math.abs(x-550)));
 return [sx*coverage,sy*coverage];
}

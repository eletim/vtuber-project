from pathlib import Path
from collections import deque
import json
import numpy as np
from PIL import Image,ImageFilter
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'assets/parts/v22/motion-review'
rows=[]
for index in range(21):
 im=Image.open(OUT/f'arm-isolated-{index:02}.png').convert('RGBA');im=im.resize((543,724),Image.Resampling.NEAREST)
 w,h=im.size;remaining=(np.array(im)[:,:,3]>=128).ravel().tolist();components=[]
 for start in range(w*h):
  if not remaining[start]:continue
  remaining[start]=False;queue=deque([start]);count=0
  while queue:
   p=queue.popleft();count+=1;py,px=divmod(p,w)
   for dy,dx in [(-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)]:
    ny,nx=py+dy,px+dx
    if 0<=ny<h and 0<=nx<w:
     q=ny*w+nx
     if remaining[q]:remaining[q]=False;queue.append(q)
  components.append(count)
 major=sorted((n for n in components if n>=100),reverse=True)
 rows.append({'amount':index/20,'major_components':len(major),'component_pixels_at_half_resolution':major})
report={'isolated_arm':rows,'all_poses_have_one_connected_major_arm':all(r['major_components']==1 for r in rows)}
reference=OUT/'hair-alpha-v19-reference.png'
if reference.exists():
 old=np.array(Image.open(reference).convert('RGBA'));interior=np.array(Image.fromarray(old[:,:,3]).filter(ImageFilter.MinFilter(7)))>=250
 oldwhite=(old[:,:,:3].min(axis=2)>235)&(old[:,:,3]>240)
 nearbywhite=np.array(Image.fromarray((oldwhite*255).astype('uint8')).filter(ImageFilter.MaxFilter(41)))>0
 samples=[]
 for time in range(5):
  frame=np.array(Image.open(OUT/f'hair-alpha-{time}.png').convert('RGBA'));gap=interior&(frame[:,:,3]<240);white=(frame[:,:,:3].min(axis=2)>235)&(frame[:,:,3]>240)
  samples.append({'time':time,'new_transparent_pixels_in_original_opaque_interior':int(gap.sum()),'white_pixels_farther_than_20px_from_original_white':int((white&~nearbywhite).sum())})
 report['hair_matte_comparison']={'original_white_pixels':int(oldwhite.sum()),'samples':samples,'note':'Original hair white matte and lower-leg cutouts have not been repaired. Motion changes silhouettes; this diagnostic flags interior changes for visual review, not automatic acceptance.'}
(OUT/'connection-and-matte-audit.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps(report))

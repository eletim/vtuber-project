from pathlib import Path
import json
import numpy as np
from PIL import Image,ImageDraw,ImageFilter
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'assets/parts/v23/review'
rows=[]
def holes(a):
 mask=Image.fromarray(((a[:,:,3]>=128)*255).astype('uint8')).copy()
 ImageDraw.floodfill(mask,(0,0),128)
 return np.array(mask)==0
for i in range(21):
 a=np.array(Image.open(OUT/f'head-v22-{i:02}.png').convert('RGBA'));b=np.array(Image.open(OUT/f'head-v23-{i:02}.png').convert('RGBA'))
 ha,hb=holes(a),holes(b);rows.append({'time':i/2,'v22_enclosed_transparent_pixels':int(ha.sum()),'v23_enclosed_transparent_pixels':int(hb.sum()),'new_enclosed_pixels':int((hb&~ha).sum()),'face_region_new_transparency':int(((a[150:450,420:700,3]>=250)&(b[150:450,420:700,3]<128)).sum())})
 if i in [4,8,12,16]:
  sheet=Image.new('RGB',(1260,750),'white')
  for col,arr in enumerate([a,b]):
   im=Image.fromarray(arr).crop((180,0,900,820)).resize((630,718))
   sheet.paste(im,(col*630,30),im);ImageDraw.Draw(sheet).text((col*630+10,10),f'v{22+col} / {i/2}s',fill='black')
  sheet.save(OUT/f'hair-pair-{i:02}.png')
(OUT/'alpha-audit.json').write_text(json.dumps({'frames':rows,'note':'Enclosed alpha holes are diagnostic only: shifted hair silhouettes can open/close pre-existing cutout gaps. Review paired frames and unchanged source texture hashes.'},indent=2)+'\n',encoding='utf-8')
print(json.dumps(rows))

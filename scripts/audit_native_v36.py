from pathlib import Path
from PIL import Image,ImageDraw
import numpy as np,json,hashlib
root=Path(__file__).resolve().parents[1];p=root/'assets/parts/v36/native-review'
report=[];previous=None;tiles=[];last_bbox=[260,650,420,850]
for f in sorted(p.glob('frame-*.png')):
 im=Image.open(f).convert('RGB');a=np.array(im);left=a[20:,:500];right=a[20:,500:];diff=np.max(np.abs(left.astype(int)-right.astype(int)),axis=2)>5
 ys,xs=np.where(diff)
 bbox=[int(xs.min()),int(ys.min()+20),int(xs.max()+1),int(ys.max()+21)] if len(xs) else None
 entry={'frame':int(f.stem.split('-')[1]),'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'difference_bbox':bbox,'mean_temporal_delta':float(np.abs(a[20:].astype(float)-previous).mean()) if previous is not None else 0};report.append(entry);previous=a[20:].astype(float)
 tile=Image.new('RGB',(220,240),'#397e91');d=ImageDraw.Draw(tile);d.text((4,3),f"{entry['frame']/30:.3f}s",fill='white')
 if bbox:last_bbox=bbox
 cx=max(610,min(890,(last_bbox[0]+last_bbox[2])/2+500));cy=max(130,min(810,(last_bbox[1]+last_bbox[3])/2))
 tile.paste(im.crop((int(cx)-110,int(cy)-110,int(cx)+110,int(cy)+110)),(0,20))
 tiles.append(tile)
for start in range(0,len(tiles),36):
 sheet=Image.new('RGB',(1320,1440),'#397e91')
 for i,tile in enumerate(tiles[start:start+36]):sheet.paste(tile,((i%6)*220,(i//6)*240))
 sheet.save(p/f'contact-{start//36+1}.jpg',quality=95)
(p/'native-temporal-audit.json').write_text(json.dumps({'count':len(report),'frames':report,'largest_changes':sorted(report,key=lambda x:x['mean_temporal_delta'],reverse=True)[:8]},indent=2),encoding='utf-8')
print(json.dumps({'count':len(report),'largest_changes':[(r['frame']/30,r['mean_temporal_delta']) for r in sorted(report,key=lambda x:x['mean_temporal_delta'],reverse=True)[:5]]}))

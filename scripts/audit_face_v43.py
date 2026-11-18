from pathlib import Path
import json,hashlib
import numpy as np
from PIL import Image,ImageDraw
root=Path('assets/parts/v43/runtime-face-final-review');frames=sorted((root/'frames').glob('frame-*.png'));assert len(frames)==480
rows=[];previous=None
for i,p in enumerate(frames):
 a=np.array(Image.open(p).convert('RGB'))[30:480,620:1240].astype(np.int16)
 row={'frame':i,'time':i/30,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
 if previous is not None:
  d=np.abs(a-previous);row.update(mean_rgb_change=float(d.mean()),changed_pixels_over_35=int((d.max(axis=2)>35).sum()))
 rows.append(row);previous=a
for direction,name in enumerate(['left','right','up','down']):
 sheet=Image.new('RGB',(1240,2500),'#397e91');draw=ImageDraw.Draw(sheet)
 for n in range(40):
  i=direction*120+n*3;x=n%4*310;y=n//4*250
  im=Image.open(frames[i]).crop((620,30,1240,480)).resize((310,225),Image.Resampling.LANCZOS)
  sheet.paste(im,(x,y+25));draw.text((x+5,y+5),f'{i/30:.2f}s / {i}',fill='white')
 sheet.save(root/f'dense-{name}.jpg',quality=93)
expressions=['neutral','soft_smile','big_smile','worried','surprised','bashful','displeased','thinking']
for side in [-15,15]:
 sheet=Image.new('RGB',(1240,1900),'#397e91');draw=ImageDraw.Draw(sheet)
 for i,e in enumerate(expressions):
  x=i%2*620;y=i//2*475;sheet.paste(Image.open(root/'stills'/f'{e}-mouth1-x{side}-y0.png'),(x,y+25));draw.text((x+5,y+5),e,fill='white')
 sheet.save(root/f'expressions-yaw-{side}.png')
report={'frames':len(rows),'all_frame_hashes':rows,'largest_changes':sorted(rows[1:],key=lambda r:r['mean_rgb_change'],reverse=True)[:12],'review_sheets':'Four directions, every third 30fps frame (0.1s); native endpoint/intermediate images retained separately.','source_module_sha256':hashlib.sha256(Path('runtime/web/face-angle-rig.js').read_bytes()).hexdigest()}
(root/'temporal-audit.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps({'frames':len(rows),'largest':report['largest_changes'][:3]}))

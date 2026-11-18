from pathlib import Path
from PIL import Image, ImageDraw
import numpy as np, json, hashlib
root=Path(__file__).resolve().parents[1]
p=root/'assets/parts/v37/native-review'
report=[];tiles=[];previous=None;previous_index=None
for f in sorted(p.glob('frame-*.png')):
 im=Image.open(f).convert('RGB');assert im.size==(2172,1472)
 a=np.array(im)[24:];index=int(f.stem.split('-')[1])
 entry={'frame':index,'time':index/30,'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'mean_version_delta':float(np.abs(a[:,:1086].astype(float)-a[:,1086:].astype(float)).mean()),'mean_temporal_delta':float(np.abs(a.astype(float)-previous).mean()) if previous_index is not None and index==previous_index+1 else None}
 report.append(entry);previous=a.astype(float);previous_index=index
 tile=Image.new('RGB',(324,240),'#397e91');ImageDraw.Draw(tile).text((4,3),f'{index/30:.3f}s v36 | v37',fill='white');tile.paste(im.crop((0,24,2172,1472)).resize((324,216)),(0,24));tiles.append(tile)
for start in range(0,len(tiles),24):
 sheet=Image.new('RGB',(1296,1440),'#397e91')
 for i,tile in enumerate(tiles[start:start+24]):sheet.paste(tile,((i%4)*324,(i//4)*240))
 sheet.save(p/f'contact-{start//24+1}.jpg',quality=95)
largest=sorted([r for r in report if r['mean_temporal_delta'] is not None],key=lambda r:r['mean_temporal_delta'],reverse=True)[:8]
(p/'native-temporal-audit.json').write_text(json.dumps({'count':len(report),'frames':report,'largest_changes':largest,'note':'Only adjacent frame deltas; gaps between selected windows excluded.'},indent=2),encoding='utf-8')
print(json.dumps({'count':len(report),'largest_changes':[(r['time'],r['mean_temporal_delta']) for r in largest]}))

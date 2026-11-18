"""Remove isolated cutout debris in the left loop, not the moving hair strands."""
from pathlib import Path
import json
import numpy as np
from PIL import Image
root=Path(__file__).resolve().parents[1];folder=root/'runtime/model';out=root/'assets/parts/v32'
m=json.loads((folder/'model.json').read_text(encoding='utf8'));layer=next(l for l in m['bodyLayers'] if l['id']=='hair_reveal_native')
old=np.array(Image.open(folder/'body_v28/hair_reveal_native.png').convert('RGBA'));a=old.copy()
y,x=np.indices(a.shape[:2]);x+=layer['rect'][0];y+=layer['rect'][1]
mask=(x<332)&(y>=211)&(y<292)&(a[:,:,3]>0)
a[mask]=0
assert np.array_equal(a[~mask],old[~mask])
Image.fromarray(a).save(folder/'body_v32/hair_reveal_native.png');layer['file']='body_v32/hair_reveal_native.png'
(folder/'model.json').write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
(out/'reveal-repair.json').write_text(json.dumps({'source':'body_v28/hair_reveal_native.png','target':layer['file'],'removed_debris_pixels':int(mask.sum()),'region':[281,211,332,292],'outside_region_changed':0,'moving_strands_changed':0,'reason':'isolated static cutout fragments visible inside the screen-left loop on all three composited backgrounds'},indent=2),encoding='utf8')
print(int(mask.sum()))

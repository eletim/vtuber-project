"""Local native texture mask: tuck the pointed inner flap into its rounded fold."""
from pathlib import Path
import json
import numpy as np
from PIL import Image
root=Path(__file__).resolve().parents[1];folder=root/'runtime/model';out=root/'assets/parts/v32'
m=json.loads((folder/'model.json').read_text(encoding='utf8'));l=next(l for l in m['bodyLayers'] if l['id']=='left_raised_drape')
old=np.array(Image.open(folder/'body_v22/left_raised_drape.png').convert('RGBA'));a=old.copy();y,x=np.indices(a.shape[:2]);x=x+l['rect'][0];y=y+l['rect'][1]
def smooth(lo,hi,q):
 t=np.clip((q-lo)/(hi-lo),0,1);return t*t*(3-2*t)
zone=smooth(466,476,x)*(1-smooth(500,510,x))
edge=672+.025*(x-490)**2
factor=1-zone*(1-smooth(edge,edge+2,y));a[:,:,3]=np.rint(a[:,:,3]*factor).astype('uint8');a[a[:,:,3]==0]=0
mask=np.any(a!=old,axis=2);assert not np.any(mask&(y>=706));assert not np.any(mask&(x<466));assert not np.any(mask&(x>510))
Image.fromarray(a).save(folder/'body_v32/left_raised_drape.png');l['file']='body_v32/left_raised_drape.png'
(folder/'model.json').write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
(out/'drape-tip-repair.json').write_text(json.dumps({'source':'body_v22/left_raised_drape.png','file':l['file'],'changed_pixels':int(mask.sum()),'bounds':[466,626,510,706],'method':'rounded native alpha mask with two-pixel antialias; no RGB repaint, no shoulder material touched'},indent=2),encoding='utf8')
print(int(mask.sum()))

"""Hair-only local edge chroma repair. Preserve alpha, highlights and ownership."""
from pathlib import Path
import json,subprocess
import numpy as np
from PIL import Image,ImageFilter
root=Path(__file__).resolve().parents[1]; model=root/'runtime/model'; out=root/'assets/parts/v32'; dest=model/'body_v32'
dest.mkdir(exist_ok=True);out.mkdir(exist_ok=True)
m=json.loads(subprocess.check_output(['git','show','23db0404b944b7e8fb4c98df466854d012319d95:runtime/model/model.json'],cwd=root));report=[]
offsets=sorted([(dy,dx) for dy in range(-12,13) for dx in range(-12,13)],key=lambda q:q[0]**2+q[1]**2)
for layer in m['bodyLayers']:
 if not layer.get('hairMotion'):continue
 old=np.array(Image.open(model/layer['file']).convert('RGBA'));a=old.copy();r,g,b=old[:,:,:3].astype(float).transpose(2,0,1)
 edge=np.array(Image.fromarray(old[:,:,3]).filter(ImageFilter.MinFilter(5)))<180
 # Preserve pale highlights. Only oversaturated brown-edge chroma is replaced.
 bad=edge&(old[:,:,3]>0)&((r-g>55)|(g-b>50))
 good=(old[:,:,3]>240)&(r-g>8)&(r-g<50)&(g-b>3)&(g-b<45)
 changed=0;missing=0
 for y,x in zip(*np.where(bad)):
  replacement=None
  for dy,dx in offsets:
   sy,sx=y+dy,x+dx
   if 0<=sy<a.shape[0] and 0<=sx<a.shape[1] and good[sy,sx]:replacement=old[sy,sx,:3].astype(float);break
  if replacement is None:missing+=1;continue
  # Keep the original luminance; this cannot substitute a dark outline.
  weights=np.array([.2126,.7152,.0722]);replacement+=np.dot(old[y,x,:3]-replacement,weights)
  a[y,x,:3]=np.clip(np.rint(replacement),0,255).astype('uint8');changed+=1
 assert np.array_equal(a[:,:,3],old[:,:,3]);assert np.array_equal(a[~bad],old[~bad])
 source=layer['file']
 if changed:
  target=dest/Path(source).name;Image.fromarray(a).save(target);layer['file']='body_v32/'+target.name
 report.append({'id':layer['id'],'source':source,'file':layer['file'],'changed_rgb_pixels':changed,'unresolved':missing,'alpha_changed':0})
(model/'model.json').write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
(out/'edge-audit.json').write_text(json.dumps({'method':'hair strands only; local native chroma, original luminance and alpha retained; no shoulder/face edits','layers':report},indent=2),encoding='utf8')
print(json.dumps(report))

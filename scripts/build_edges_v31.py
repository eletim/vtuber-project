"""Localized RGB decontamination in editable native parts; alpha/ownership stay exact."""
from pathlib import Path
import json,subprocess,hashlib
import numpy as np
from PIL import Image,ImageFilter
root=Path(__file__).resolve().parents[1]; model=root/'runtime/model';out=root/'assets/parts/v31';dest=model/'body_v31';dest.mkdir(exist_ok=True)
m=json.loads(subprocess.check_output(['git','show','e5aa8efc9d0a89a9fb19ed61724dc81b027a5119:runtime/model/model.json'],cwd=root))
paint=np.array(Image.open(out/'hair-edge-paint.png').convert('RGBA').resize(tuple(m['size']),Image.Resampling.LANCZOS));report=[]
def valid(a):
 r,g,b=[a[:,:,i].astype(int) for i in range(3)]
 return (a[:,:,3]>220)&(r-g>8)&(r-g<60)&(g-b>5)&(g-b<55)&(g>45)
good=valid(paint)
offsets=sorted([(dy,dx) for dy in range(-16,17) for dx in range(-16,17)],key=lambda q:q[0]**2+q[1]**2)
for layer in m['bodyLayers']:
 if not layer.get('hairMotion') and not layer.get('features'):continue
 def repair(file):
  old=np.array(Image.open(model/file).convert('RGBA'));a=old.copy();r,g,b=[old[:,:,i].astype(int) for i in range(3)];h,w=r.shape;yy,xx=np.indices((h,w));xx+=layer['rect'][0];yy+=layer['rect'][1]
  edge=np.array(Image.fromarray(old[:,:,3]).filter(ImageFilter.MinFilter(5)))<240
  bad=(((r-g>65)&(g-b<35))|((r-g<25)&(g-b>65)))&edge&(old[:,:,3]>0)
  # Never treat eye, skin, gold ornament, or mouth as hair contamination.
  bad&=~(((xx>=405)&(xx<=720)&(yy>=180)&(yy<=470))|((xx>=470)&(xx<=680)&(yy>=420)&(yy<=650))|((xx>=680)&(xx<=825)&(yy>=120)&(yy<=340)))
  changed=0;missing=0
  for y,x in zip(*np.where(bad)):
   gx,gy=int(xx[y,x]),int(yy[y,x]);replacement=None
   for dy,dx in offsets:
    sy,sx=gy+dy,gx+dx
    if 0<=sy<paint.shape[0] and 0<=sx<paint.shape[1] and good[sy,sx]:replacement=paint[sy,sx,:3];break
   if replacement is None:missing+=1;continue
   a[y,x,:3]=replacement;changed+=1
  assert np.array_equal(a[:,:,3],old[:,:,3]);assert np.array_equal(a[~bad],old[~bad])
  if changed:
   target=dest/Path(file).name;Image.fromarray(a).save(target);result='body_v31/'+target.name
  else:result=file
  report.append({'id':layer['id'],'source':file,'file':result,'changed_rgb_pixels':changed,'unresolved':missing,'alpha_changed':0,'outside_mask_changed':0})
  return result
 layer['file']=repair(layer['file'])
 if layer.get('expressionFiles'):layer['expressionFiles']={k:repair(v) for k,v in layer['expressionFiles'].items()}
(model/'model.json').write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(out/'edge-audit.json').write_text(json.dumps({'source_sha256':hashlib.sha256((out/'hair-edge-paint.png').read_bytes()).hexdigest(),'method':'RGB-only local decontamination using clean brown pixels from imagegen repair; unchanged native alpha/geometry','layers':report},indent=2)+'\n')
print(json.dumps(report))

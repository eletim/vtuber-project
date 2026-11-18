from pathlib import Path
import json, subprocess, hashlib
import numpy as np
from PIL import Image, ImageFilter
root=Path(__file__).resolve().parents[1]; model=root/'runtime/model'; out=root/'assets/parts/v30'
base=json.loads(subprocess.check_output(['git','show','2122ed7ad066fab1805b370f1fb22aa19739b0f8:runtime/model/model.json'],cwd=root))
layer=next(x for x in base['bodyLayers'] if x['id']=='left_shoulder_original_support')
old=np.array(Image.open(model/layer['file']).convert('RGBA')); h,w=old.shape[:2]
paint=np.array(Image.open(out/'shoulder-repair.png').convert('RGBA').resize((w,h),Image.Resampling.LANCZOS))
r,g,b=[old[:,:,i].astype(int) for i in range(3)]; dark=(r<200)&(r-g>18)&(old[:,:,3]>200)
seen=set(); repair=np.zeros((h,w),np.uint8); count=0
for y,x in zip(*np.where(dark)):
 if (y,x) in seen:continue
 todo=[(y,x)];seen.add((y,x));component=[]
 while todo:
  yy,xx=todo.pop();component.append((yy,xx))
  for dy in [-1,0,1]:
   for dx in [-1,0,1]:
    q=(yy+dy,xx+dx)
    if 0<=q[0]<h and 0<=q[1]<w and dark[q] and q not in seen:seen.add(q);todo.append(q)
 if len(component)<=7 and max(v[0] for v in component)<115:
  count+=1
  for q in component:repair[q]=255
mask=(np.array(Image.fromarray(repair).filter(ImageFilter.MaxFilter(3)))>0)&(old[:,:,3]>220)&(paint[:,:,3]>220)
result=old.copy();result[mask,:3]=paint[mask,:3]
assert np.array_equal(result[:,:,3],old[:,:,3])
target=model/'body_v30/left_shoulder_original_support.png';target.parent.mkdir(exist_ok=True);Image.fromarray(result).save(target)
m=json.loads((model/'model.json').read_text(encoding='utf-8'));next(x for x in m['bodyLayers'] if x['id']==layer['id'])['file']='body_v30/'+target.name
(model/'model.json').write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(out/'shoulder-repair-audit.json').write_text(json.dumps({'tool':'built-in image_gen.imagegen','isolated_components':count,'changed_pixels':int(np.any(result!=old,axis=2).sum()),'alpha_changed':0,'source_sha256':hashlib.sha256((out/'shoulder-repair.png').read_bytes()).hexdigest()},indent=2)+'\n')

"""Edit native hair-layer coverage; preserve protected face and warm highlights."""
from pathlib import Path
from collections import deque
import json,subprocess
import numpy as np
from PIL import Image,ImageFilter,ImageDraw
ROOT=Path(__file__).resolve().parents[1];MODEL=ROOT/'runtime/model';OUT=ROOT/'assets/parts/v28';DEST=MODEL/'body_v28'
OUT.mkdir(exist_ok=True);DEST.mkdir(exist_ok=True)
model=json.loads(subprocess.check_output(['git','show','58cfe626d254cc4262749c75d612bb33637fcca9:runtime/model/model.json'],cwd=ROOT))
report=[]
def clean(file,layer):
 a=np.array(Image.open(MODEL/file).convert('RGBA'));rgb=a[:,:,:3].astype(float);h,w=a.shape[:2];yy,xx=np.mgrid[:h,:w];xx+=layer['rect'][0];yy+=layer['rect'][1]
 domain=a[:,:,3]>0
 if layer.get('features') or layer['id']=='hair_reveal_native':
  # Face/neck and the full accessory are immutable, not color-classified.
  domain &= ~(((xx>=350)&(xx<=720)&(yy>=180)&(yy<=650))|((xx>=680)&(xx<=825)&(yy>=120)&(yy<=445)))
 if layer['id'].startswith('bang_'):return file
 lo=rgb.min(2);spread=rgb.max(2)-lo
 potential=domain&(lo>210)&(spread<25)
 boundary=np.array(Image.fromarray((a[:,:,3]>0).astype('uint8')*255).filter(ImageFilter.MinFilter(5)))==0
 core=potential&(lo>240)&(spread<12)
 seen=np.zeros((h,w),bool);selected=np.zeros((h,w),bool)
 for sy,sx in zip(*np.nonzero(potential)):
  if seen[sy,sx]:continue
  stack=[(sy,sx)];seen[sy,sx]=1;pixels=[];touch=False;cores=0
  while stack:
   y,x=stack.pop();pixels.append((y,x));touch|=bool(boundary[y,x]);cores+=int(core[y,x])
   for dy,dx in [(1,0),(-1,0),(0,1),(0,-1)]:
    ny,nx=y+dy,x+dx
    if 0<=ny<h and 0<=nx<w and potential[ny,nx] and not seen[ny,nx]:seen[ny,nx]=1;stack.append((ny,nx))
  if cores:
   py,px=zip(*pixels);selected[py,px]=1
 expanded=np.array(Image.fromarray(selected.astype('uint8')*255).filter(ImageFilter.MaxFilter(5)))>0
 selected |= expanded&domain&(lo>185)&(spread<45)
 # Nearest chromatic hair supplies foreground color for white-matte inversion.
 seeds=domain&(a[:,:,3]>160)&(spread>30)&(lo<215)
 if not selected.any() or not seeds.any():return file
 fy,fx=np.indices((h,w));known=seeds.copy();q=deque(zip(*np.nonzero(seeds)))
 while q:
  y,x=q.popleft()
  for dy,dx in [(1,0),(-1,0),(0,1),(0,-1)]:
   ny,nx=y+dy,x+dx
   if 0<=ny<h and 0<=nx<w and not known[ny,nx]:known[ny,nx]=1;fy[ny,nx]=fy[y,x];fx[ny,nx]=fx[y,x];q.append((ny,nx))
 foreground=rgb[fy,fx];coverage=np.median((255-rgb)/np.maximum(255-foreground,1),axis=2).clip(0,1)
 repaired=a.copy();repaired[selected,:3]=foreground[selected].round().astype('uint8');repaired[selected,3]=(a[selected,3]*coverage[selected]).round().astype('uint8');repaired[repaired[:,:,3]==0]=0
 assert np.array_equal(repaired[~domain],a[~domain])
 target='body_v28/'+Path(file).name;Image.fromarray(repaired).save(MODEL/target)
 opaque_before=int((core&(a[:,:,3]>240)).sum());opaque_after=int(((repaired[:,:,:3].min(2)>240)&((repaired[:,:,:3].max(2).astype(int)-repaired[:,:,:3].min(2))<12)&(repaired[:,:,3]>240)&domain).sum())
 report.append({'id':layer['id'],'source':file,'output':target,'modified_pixels':int(selected.sum()),'opaque_white_before':opaque_before,'opaque_white_after':opaque_after,'protected_changed_values':int(np.count_nonzero(a[~domain]!=repaired[~domain]))})
 # Native-layer comparison, no renderer, on black/white/chromatic backgrounds.
 if not layer.get('features'):
  canvas=Image.new('RGB',(w*2,h*3));draw=ImageDraw.Draw(canvas)
  for row,bg in enumerate(['black','white','#397e91']):
   for col,data in enumerate([a,repaired]):
    tile=Image.new('RGBA',(w,h),bg);tile.alpha_composite(Image.fromarray(data));canvas.paste(tile,(w*col,h*row))
  canvas.save(OUT/(layer['id']+'-matte-before-after.png'))
 return target
for layer in model['bodyLayers']:
 if layer.get('hairMotion') or layer.get('features') or layer['id']=='hair_reveal_native':
  layer['file']=clean(layer['file'],layer)
  if layer.get('expressionFiles'):
   layer['expressionFiles']={key:clean(file,layer) for key,file in layer['expressionFiles'].items()}
model['hairExport']['matteCorrection']='native-layer white-matte coverage inversion, protected face/accessory and warm highlights'
(MODEL/'model.json').write_text(json.dumps(model,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
(OUT/'matte-audit.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'layers':len(report),'white_before':sum(r['opaque_white_before'] for r in report),'white_after':sum(r['opaque_white_after'] for r in report),'protected_changed_values':sum(r['protected_changed_values'] for r in report)}))

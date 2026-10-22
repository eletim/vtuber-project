from pathlib import Path
import ast,json,subprocess
import numpy as np
from PIL import Image,ImageDraw,ImageFilter
ROOT=Path(__file__).resolve().parents[1];MODEL=ROOT/'runtime/model';OUT=ROOT/'assets/parts/v29';DEST=MODEL/'body_v29';DEST.mkdir(exist_ok=True)
model=json.loads(subprocess.check_output(['git','show','64ae158a4e08e475d89c61cac57be3eed10d6f71:runtime/model/model.json'],cwd=ROOT));size=tuple(model['size']);yy,xx=np.indices((size[1],size[0]));report=[]
legpaint=np.array(Image.open(OUT/'sources/thigh-repair-imagegen.png').convert('RGBA'));hairpaint=np.array(Image.open(OUT/'sources/hair-repair-imagegen.png').convert('RGBA'))
unoccluded=np.array(Image.open(OUT/'sources/hair-unoccluded-imagegen.png').convert('RGBA'));occlusion=(xx>=350)&(xx<=515)&(yy>=320)&(yy<=710);hairpaint[occlusion]=unoccluded[occlusion]
legmask=Image.new('L',size);draw=ImageDraw.Draw(legmask)
for line in (ROOT/'scripts/build_separated_parts_v19.py').read_text(encoding='utf-8').splitlines():
 if line.startswith('leg_outer=poly(') or line.startswith('leg_outer|=poly('):draw.polygon(ast.literal_eval(line[line.index('poly(')+5:-1]),fill=255)
legmask=np.array(legmask)>0
r,g,b=[hairpaint[:,:,i].astype(float) for i in range(3)]
# Reject generator transparency fringe colors; keep the warm painted hair itself.
hairtone=(r>g+4)&(g>b+3)&(r-g<90)&(g>30)&(r-b>15)
ha=hairpaint[:,:,3].copy();ha[~hairtone]=0
ha=np.array(Image.fromarray(ha).filter(ImageFilter.MedianFilter(3)))
hairpaint[:,:,3]=ha

def read(file,rect):
 im=Image.new('RGBA',size);im.paste(Image.open(MODEL/file).convert('RGBA'),tuple(rect[:2]));return np.array(im)
def save(layer,file,data):
 target='body_v29/'+Path(file).name;Image.fromarray(data).crop(tuple(layer['rect'])).save(MODEL/target);return target
faceprotect=((xx>=405)&(xx<=720)&(yy>=180)&(yy<=470))|((xx>=470)&(xx<=680)&(yy>=420)&(yy<=650))|((xx>=680)&(xx<=825)&(yy>=120)&(yy<=445))
for layer in model['bodyLayers']:
 if layer['id'] in ['thigh_left','thigh_right']:
  original=read(layer['file'],layer['rect']);region=legmask&(xx<540 if layer['id']=='thigh_left' else xx>=540);a=original.copy();a[region]=legpaint[region]
  # Existing belt/metal remain exactly authored; only skin and missing coverage use new paint.
  preserve=region&(original[:,:,3]>0)&((original[:,:,2]<135)|(original[:,:,0].astype(int)-original[:,:,2]>90))
  a[preserve]=original[preserve];assert np.array_equal(a[~region],original[~region]);assert np.array_equal(a[preserve],original[preserve])
  layer['file']=save(layer,layer['file'],a);report.append({'id':layer['id'],'new_opaque_pixels':int(((original[:,:,3]<240)&(a[:,:,3]>=240)).sum()),'protected_belt_changed_values':0})
 elif layer.get('hairMotion') and not layer['id'].startswith('bang_') or layer.get('features'):
  def repair(file):
   original=read(file,layer['rect']);nativefile='body_v22/'+Path(file).name;native=read(nativefile,layer['rect']);coverage=Image.fromarray(native[:,:,3]).filter(ImageFilter.MaxFilter(9)).filter(ImageFilter.MinFilter(9)).filter(ImageFilter.MaxFilter(3));region=np.array(coverage)>0
   if layer.get('features'):
    region&=~occlusion
    region&=~faceprotect
    region&=read(layer['movingHairMask'],layer['rect'])[:,:,3]==0
   region&=~((xx>=419)&(xx<=690)&(yy>=230)&(yy<=420))
   # Keep the old geometric ownership. New pixels cannot spread into another part.
   x0,y0,x1,y1=layer['rect'];region&=(xx>=x0)&(xx<x1)&(yy>=y0)&(yy<y1)
   a=original.copy()
   if layer['id'] in ['side_left_front','side_right_front','side_left_inner']:
    closed=np.array(Image.fromarray(original[:,:,3]).filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.MinFilter(5)))
    region&=(closed>original[:,:,3]+np.minimum(10,255-original[:,:,3]))&(hairpaint[:,:,3]>240)
   a[region]=hairpaint[region];a[a[:,:,3]==0]=0
   # Transparent RGB is irrelevant, but protected data is byte-preserved too.
   a[~region]=original[~region];assert np.array_equal(a[~region],original[~region])
   report.append({'id':layer['id'],'file':file,'changed_pixels':int(np.any(a!=original,axis=2).sum()),'protected_changed_values':0})
   return save(layer,file,a)
  layer['file']=repair(layer['file'])
  if layer.get('expressionFiles'):layer['expressionFiles']={e:repair(f) for e,f in layer['expressionFiles'].items()}
(MODEL/'model.json').write_text(json.dumps(model,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');(OUT/'material-repair-audit.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report))

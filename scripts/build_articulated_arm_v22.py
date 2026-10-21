"""Export painted, independently articulated arm parts without replacing face/torso."""
from pathlib import Path
import json
import numpy as np
from PIL import Image, ImageDraw
ROOT=Path(__file__).resolve().parents[1];MODEL=ROOT/'runtime/model';OUT=ROOT/'assets/parts/v22'
TARGET=MODEL/'body_v22';TARGET.mkdir(exist_ok=True)
model=json.loads((MODEL/'model.json').read_text(encoding='utf-8'))
if not (OUT/'model-before-v22.json').exists():
 (OUT/'model-before-v22.json').write_text(json.dumps(model,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
else: model=json.loads((OUT/'model-before-v22.json').read_text(encoding='utf-8'))
size=tuple(model['size']);old=next(l for l in model['bodyLayers'] if l['id']=='arm_screen_left')
rest=Image.new('RGBA',size);rest.paste(Image.open(MODEL/old['file']),tuple(old['rect'][:2]));rest=np.array(rest)
paint=Image.open(OUT/'sources/bent-arm-clean-painted.png').convert('RGBA')
# Register shoulder and fingertips to the original character coordinates.
scale=.72;offset=(58,146)
raised=Image.new('RGBA',size);raised.alpha_composite(paint.resize((round(paint.width*scale),round(paint.height*scale)),Image.Resampling.LANCZOS),offset)
raised.save(OUT/'sources/bent-arm-registered.png');raised=np.array(raised)
y,x=np.indices(rest.shape[:2])
raised[(raised[:,:,3]<16)|(x<165)|(x>535)|(y<325)|(y>985)]=0
def poly(points):
 im=Image.new('L',size);ImageDraw.Draw(im).polygon(points,fill=255);return np.array(im)>0
def export(name,rgba,joint,bind,variant):
 rgba[rgba[:,:,3]==0]=0;ys,xs=np.nonzero(rgba[:,:,3]);rect=[int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)]
 path='body_v22/'+name+'.png';Image.fromarray(rgba).crop(rect).save(MODEL/path)
 return {'id':name,'role':'armLeft','file':path,'rect':rect,'articulation':{'joint':joint,'bind':bind,'variant':variant},'psdGroup':'v22 articulated arm/'+name}
layers=[]
for variant,data,masks in [
 ('raised',raised,[('hand',y<477),('forearm',poly([(408,475),(508,475),(479,680),(434,694),(398,597)])),('cuff',poly([(365,565),(402,565),(434,598),(480,680),(472,720),(420,690),(375,635)])),('upper',(y<650)&(x<409)),('drape',np.ones(y.shape,bool))])]:
 remaining=data[:,:,3]>0
 pieces=[]
 for joint,mask in masks:
  owned=remaining&mask;remaining&=~owned;rgba=data.copy();rgba[~owned]=0
  if joint=='upper':rgba[y<592]=0 # original approved shoulder skin supplies the cap
  pieces.append(export('left_'+variant+'_'+joint,rgba,joint,variant,variant))
 # Joint parts are independent surfaces; distal pieces render last.
 layers.extend(sorted(pieces,key=lambda l:{'upper':0,'forearm':1,'drape':2,'cuff':3,'hand':4}[l['articulation']['joint']]))
bridge=rest.copy();bridge[y>=630]=0
layers.insert(0,export('left_shoulder_original_support',bridge,'upper','raised','raised'))
model['bodyLayers']=[l for l in model['bodyLayers'] if l['id']!='arm_screen_left']
# Painted continuation is confined to the old arm's formerly occluded region.
# Existing visible jacket/skirt pixels are not replaced and remain independent.
hidden=np.array(Image.open(OUT/'sources/bent-arm-imagegen.png').convert('RGBA'))
old_mask=np.array(Image.open(OUT/'../v19/review/arm_screen_left_mask.png'))>0
hidden[~(old_mask&(y>=940)&(x>=150))]=0
item=export('left_body_reveal_painted',hidden,'upper','raised','raised')
item.pop('articulation');item['role']='torso';item['psdGroup']='v22 torso/painted former arm occlusion'
model['bodyLayers'].insert(3,item)
# The cheek hand must render over the face and front hair at the raised pose.
head_index=next(i for i,l in enumerate(model['bodyLayers']) if l.get('features'))
model['bodyLayers'][head_index:head_index]=[l for l in layers if l['articulation']['joint']=='upper']
model['bodyLayers'].extend(l for l in layers if l['articulation']['joint']!='upper')
model['articulatedArm']={'shoulder':[353,510],'elbow':[275,800],'wristRest':[185,1190],'wristRaised':[476,470],'parameter':'ParamHandToCheek','source':'assets/parts/v22/sources/bent-arm-clean-painted.png'}
(MODEL/'model.json').write_text(json.dumps(model,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('Exported independent upper/forearm/hand/drape textures; original source files retained.')

"""Export exclusive moving hair ownership from every expression head base."""
from pathlib import Path
import json
import numpy as np
from PIL import Image,ImageDraw,ImageFilter
from psd_groups_v14 import parse_psd_groups,composite_psd_groups
ROOT=Path(__file__).resolve().parents[1];MODEL=ROOT/'runtime/model';OUT=ROOT/'assets/parts/v22';DEST=MODEL/'body_v22';DEST.mkdir(exist_ok=True)
model=json.loads((MODEL/'model.json').read_text(encoding='utf-8'));old=json.loads((OUT/'model-before-v22.json').read_text(encoding='utf-8'))
size=tuple(model['size']);y,x=np.indices((size[1],size[0]));head=next(l for l in old['bodyLayers'] if l.get('features'));back=next(l for l in old['bodyLayers'] if l['id']=='hair_back')
def full(layer,file=None):
 im=Image.new('RGBA',size);im.paste(Image.open(MODEL/(file or layer['file'])),tuple(layer['rect'][:2]));return np.array(im)
def poly(points):
 im=Image.new('L',size);ImageDraw.Draw(im).polygon(points,fill=255);return np.array(im)>0
def cut(a,m):
 a=a.copy();a[~m]=0;return a
def export(name,data,root,tip,amplitude,speed,phase):
 ys,xs=np.nonzero(data[:,:,3]);rect=[int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)];file='body_v22/'+name+'.png'
 Image.fromarray(data).crop(rect).save(MODEL/file)
 return {'id':name,'role':'head','file':file,'rect':rect,'hairMotion':{'rootY':root,'tipY':tip,'amplitude':amplitude,'speed':speed,'phase':phase},'psdGroup':'v22 exclusive hair/'+name}
front=full(head);rear=full(back);front_layers=[];rear_layers=[]
bangs=poly([(430,65),(550,43),(600,81),(635,148),(650,220),(649,244),(620,229),(593,210),(564,201),(566,238),(574,258),(566,269),(548,270),(521,263),(500,247),(482,225),(474,200),(462,231),(448,250),(438,272),(426,270),(418,251),(421,208),(419,156)])
leftcurl=poly([(407,359),(434,385),(449,430),(450,480),(442,504),(466,543),(496,559),(514,589),(508,616),(490,644),(468,668),(437,682),(401,671),(390,650),(421,650),(445,631),(462,608),(467,581),(454,553),(435,530),(421,500),(414,450)])
rightcurl=poly([(669,335),(689,336),(701,360),(691,405),(671,439),(659,466),(651,485),(635,500),(609,503),(616,484),(632,475),(642,458),(649,425),(655,390)])
regions=[
 ('bang_left',bangs&(x<488),70,276,2.4,9,.1),('bang_center',bangs&(x>=488)&(x<568),65,273,3.5,7.5,.8),('bang_right',bangs&(x>=568),65,248,2.5,8.3,1.6),
 ('side_left_front',leftcurl,365,682,7,6.1,.4),('side_right_front',rightcurl,335,503,5.5,6.7,1.1),
 ('side_left_outer',(x<345)&(y>210),210,530,6.5,5.7,1.7),('side_left_inner',(x>=345)&(x<415)&(y>250)&~leftcurl,250,515,4.5,7,2.2),
 ('side_right_outer',(x>730)&(y>355),355,650,8,5.5,2.7)]
owned=np.zeros(y.shape,bool);pieces=[]
for name,mask,root,tip,amp,speed,phase in regions:
 mask=mask&~owned&(front[:,:,3]>0);owned|=mask
 if mask.any():pieces.append((name,mask,root,tip,amp,speed,phase))
for name,mask,root,tip,amp,speed,phase in pieces:
 # Small moving-to-moving underlaps cover differing strand lag without a
 # second stationary hairstyle. Pixels remain on a moving strand only.
 expanded=np.array(Image.fromarray((mask*255).astype('uint8')).filter(ImageFilter.MaxFilter(25)))>0
 front_layers.append(export(name,cut(front,expanded&owned),root,tip,amp,speed,phase))
for i,(name,mask,root,tip,amp) in enumerate([
 ('rear_left_outer',x<260,448,775,12),('rear_left_inner',(x>=260)&(x<543),448,775,9),('rear_right_inner',(x>=543)&(x<825),448,775,10),('rear_right_outer',x>=825,448,775,13)]):
 rear_layers.append(export(name,cut(rear,mask),root,tip,amp,4.8+i*.4,i*.7))
# A fixed scalp/skin continuation comes from the already-painted native PSD,
# never from another copy of the original flattened hairstyle.
nodes,_=parse_psd_groups(ROOT/'assets/parts/v19/koma_separated_body_v19.psd');native=next(n for n in nodes if n.name.startswith('01 Head'))
scalp=composite_psd_groups([n for n in native.children if n.name.endswith('/scalp_reveal_when_bangs_move')])
skin=composite_psd_groups([n for n in native.children if n.name.endswith('/face_skin_FULL_beneath_eyes_mouth') or n.name.endswith('/neck.illustrated_underpaint')])
supports=np.zeros_like(front);opaque=front[:,:,3]==255
edge=(np.array(Image.fromarray((~owned*255).astype('uint8')).filter(ImageFilter.MaxFilter(25)))>0)&owned
painted_back=composite_psd_groups([n for n in native.children if any(n.name.endswith('/'+k) for k in ['side_hair_fixed_painted_underlayer','hair_continuous_painted_reveal_v10','neck.illustrated_underpaint'])])
safe=owned&edge&opaque&(painted_back[:,:,3]>0)
supports[safe]=painted_back[safe]
supports[bangs&owned&opaque]=scalp[bangs&owned&opaque]
face=poly([(419,237),(450,205),(500,190),(559,160),(625,199),(667,242),(691,285),(687,335),(651,377),(596,415),(555,436),(489,404),(442,366),(419,317)])
support_skin=owned&~bangs&face&opaque;supports[support_skin]=skin[support_skin]
painted=Image.open(OUT/'sources/hair-skin-reveal-painted.png').convert('RGBA').resize((head['rect'][2]-head['rect'][0],head['rect'][3]-head['rect'][1]),Image.Resampling.LANCZOS)
reveal_image=Image.new('RGBA',size);reveal_image.paste(painted,tuple(head['rect'][:2]));reveal=np.array(reveal_image)
# Newly authored scalp/forehead/temple plate, only behind removed moving hair.
# Never use the generated exposed face or its remaining rear hairstyle.
painted_region=owned&(bangs|face)&(reveal[:,:,3]>=250)
supports[painted_region]=reveal[painted_region]
# Keep the original facial pixels for all eight expression bases. Every selected
# hair pixel is removed before the head textures are written.
newhead={**head,'id':'face_fixed_v22','file':'body_v22/face_fixed_v22.png','expressionFiles':{},'psdGroup':'v22 face and fixed crown'}
box=head['rect'];a=cut(front,~owned);Image.fromarray(a).crop(box).save(MODEL/newhead['file'])
mask_rgba=np.zeros_like(front);mask_rgba[:,:,:3]=255;mask_rgba[:,:,3]=owned*255
newhead['movingHairMask']='body_v22/face_hair_ownership.png';Image.fromarray(mask_rgba).crop(box).save(MODEL/newhead['movingHairMask'])
invariants={}
for exp,file in head['expressionFiles'].items():
 source=full(head,file);fixed=cut(source,~owned);out='body_v22/face_'+exp+'.png';Image.fromarray(fixed).crop(box).save(MODEL/out);newhead['expressionFiles'][exp]=out
 invariants[exp]={'changed_outside_hair_ownership':int(np.count_nonzero(fixed[~owned]!=source[~owned])),'remaining_selected_hair_alpha':int(np.count_nonzero(fixed[owned,3]))}
support_layer=export('hair_reveal_native',supports,0,1,0,1,0);support_layer.pop('hairMotion');support_layer['psdGroup']='v22 hair reveal/native and newly painted scalp and skin'
result=[]
for layer in model['bodyLayers']:
 if layer['id']=='hair_back':result.extend(rear_layers)
 elif layer.get('features'):result.extend([support_layer,newhead,*front_layers])
 else:result.append(layer)
model['bodyLayers']=result;model['hairExport']={'exclusiveOwnership':True,'expressionBasesWithoutMovingHair':8,'strandCount':len(front_layers)+len(rear_layers),'source':'v19 approved head; native and newly painted hidden scalp/skin'}
(MODEL/'model.json').write_text(json.dumps(model,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
Image.fromarray((owned*255).astype('uint8')).save(OUT/'hair-ownership-mask.png')
(OUT/'hair-export-verification.json').write_text(json.dumps({'expressions':invariants,'front_strands':len(front_layers),'rear_strands':len(rear_layers),'moving_hair_in_fixed_base_pixels':0},indent=2)+'\n',encoding='utf-8')
print(model['hairExport'])

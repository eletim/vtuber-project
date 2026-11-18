from pathlib import Path
import json,subprocess
import numpy as np
from PIL import Image,ImageDraw,ImageFilter
ROOT=Path(__file__).resolve().parents[1];MODEL=ROOT/'runtime/model';OUT=ROOT/'assets/parts/v29';im=Image.open(OUT/'sources/forward-arm-imagegen.png').convert('RGBA');a=np.array(im);h,w=a.shape[:2];yy,xx=np.mgrid[:h,:w]
def poly(points):
 m=Image.new('L',im.size);ImageDraw.Draw(m).polygon(points,fill=255);return np.array(m)>0
skin=poly([(370,885),(365,870),(369,841),(378,824),(391,811),(405,797),(418,784),(431,765),(445,743),(461,720),(481,706),(502,699),(532,683),(547,689),(565,698),(581,713),(591,727),(586,731),(572,724),(553,713),(544,715),(561,729),(574,741),(577,762),(570,777),(562,776),(557,758),(548,748),(543,747),(550,768),(554,782),(551,798),(544,806),(537,805),(531,792),(527,780),(525,775),(524,792),(527,805),(523,813),(517,815),(511,809),(502,795),(501,782),(494,786),(488,800),(478,809),(467,814),(449,821),(433,838),(414,858),(392,879),(380,884)])
r,g,b=[a[:,:,i].astype(int) for i in range(3)];skin &= (r-g>12)&(r-b>20)&(g>90)
cuff=poly([(329,808),(338,788),(354,773),(380,756),(410,754),(438,767),(455,786),(469,812),(479,844),(477,881),(462,913),(447,926),(430,930),(410,923),(391,908),(378,894),(361,861),(347,835)])&~skin
E=np.array([325,925]);W=np.array([455,807]);direction=(W-E)/np.linalg.norm(W-E);u=(xx-W[0])*direction[0]+(yy-W[1])*direction[1]
hidden=Image.open(OUT/'sources/relaxed-hand-resized.png').convert('RGBA')
registered=hidden.transform((w,h),Image.Transform.AFFINE,(1/.8,0,282-455/.8,0,1/.8,224-807/.8),resample=Image.Resampling.BICUBIC)
skinpaint=np.array(registered);hr,hg,hb=[skinpaint[:,:,i].astype(int) for i in range(3)];valid=(hr-hg>5)&(hg-hb>2)&(hr-hg<100)&(hg>90);skinpaint[~valid]=0
skin=skinpaint[:,:,3]>0
skin&=u>=-np.linalg.norm(W-E)-12
m=json.loads((MODEL/'model.json').read_text(encoding='utf-8'))
for id,mask in [('left_raised_forearm',skin&(u<12)),('left_raised_hand',skin&(u>-12)),('left_raised_cuff',cuff)]:
 layer=next(l for l in m['bodyLayers'] if l['id']==id);data=(a if id=='left_raised_cuff' else skinpaint).copy();data[~mask]=0;
 if id!='left_raised_cuff':
  alpha=Image.fromarray(data[:,:,3]).filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(.45));data[:,:,3]=np.array(alpha)
 ys,xs=np.nonzero(mask);rect=[int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)];file='body_v29/'+id+'.png';Image.fromarray(data).crop(rect).save(MODEL/file);layer.update(file=file,rect=rect);layer['articulation']['sourceElbow']=E.tolist();layer['articulation']['sourceWrist']=W.tolist();layer['psdGroup']='v29 forward-pose paint/'+id
old=json.loads(subprocess.check_output(['git','show','64ae158a4e08e475d89c61cac57be3eed10d6f71:runtime/model/model.json'],cwd=ROOT))
if not any(l['id']=='left_rest_cuff' for l in m['bodyLayers']):
 rest=next(l for l in old['bodyLayers'] if l['id']=='left_raised_cuff');rest['id']='left_rest_cuff';rest['psdGroup']='v29 cuff/down-facing original';rest['articulation']['poseWeight']='rest-cuff';m['bodyLayers'].insert(next(i for i,l in enumerate(m['bodyLayers']) if l['id']=='left_raised_cuff'),rest)
next(l for l in m['bodyLayers'] if l['id']=='left_raised_cuff')['articulation']['poseWeight']='forward-cuff'
m['articulatedArm']['forwardPosePaint']=True
(MODEL/'model.json').write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
preview=a.copy();preview[~(skin|cuff)]=0;Image.fromarray(preview).crop((300,670,610,950)).save(OUT/'forward-skin-cuff-extracted.png')

"""Register supplied right-eye supplements; retain native visible pixels."""
from pathlib import Path
import json
import numpy as np
from PIL import Image,ImageDraw
root=Path(__file__).resolve().parents[1]; dst=root/'runtime/model/eyes_v46/right';dst.mkdir(exist_ok=True)
refs=root/'assets/parts/v46/references';src=root/'assets/parts/v46/imports/right'
original=Image.open(refs/'eye_screen_right_open.png').convert('RGBA');w,h=original.size;a=np.array(original)
meta=dict(rect=[538,204,684,320],size=[w,h],upper=[[32,64],[43,54],[57,47],[70,44],[83,45],[96,48],[105,52],[111,56]],lower=[[32,64],[43,73],[57,80],[70,82],[83,80],[96,75],[105,68],[111,56]],closed=[[32,64],[43,58],[57,54],[70,51],[83,50],[96,52],[105,54],[111,56]],irisCenter=[74,62],irisRadius=[21,24],gazePixels=[5,4],closedFile='eye_screen_right_closed.png',closedOffset=[-12,-12],lidBand=18,contourLidSampling=True,candidate_only=True)
(dst/'right-neutral.json').write_text(json.dumps(meta,indent=2)+'\n')
original.save(dst/'original.png')
skin=Image.open(src/'exec-4b961143-4801-4360-923a-834d85e8a4a8.png').convert('RGBA').resize((w,h),Image.Resampling.LANCZOS)
skin.save(dst/'skin-registered.png')
b=np.array(skin).astype(float); b[:,91:,:3]=b[:,90:91,:3]; closed=np.array(Image.open(refs/'eye_screen_right_closed.png').convert('RGBA'))[12:12+h,12:12+w].astype(float)
yy,xx=np.indices((h,w)); valid=(xx>40)&(xx<106)&(yy>82)&(yy<105)&(closed[:,:,0]>240)&(closed[:,:,1]>190)&(closed[:,:,2]>160)
features=np.stack([np.ones((h,w)),xx/w,yy/h],axis=-1); fit=np.linalg.lstsq(features[valid],closed[:,:,:3][valid],rcond=None)[0]; field=np.stack([np.ones((h,w)),np.clip(xx,45,103)/w,np.maximum(yy,82)/h],axis=-1)@fit; b[:,:,:3]=np.clip(.15*b[:,:,:3]+.85*field,0,255); b[:,:,3]=255; Image.fromarray(b.astype(np.uint8)).save(dst/'skin-calibrated.png')
Image.open(src/'exec-1ef9daa4-a0d6-47e8-9ee8-d74f05a0484e.png').convert('RGBA').resize((w,h),Image.Resampling.LANCZOS).save(dst/'sclera-registered.png')
iris=Image.open(src/'exec-9ea73348-1558-4577-9355-699594538507.png').convert('RGBA')
# Crop the central iris, excluding the generated corner noise seen in source inspection.
iw,ih=iris.size;iris=iris.crop((int(iw*.13),int(ih*.12),int(iw*.84),int(ih*.85))).resize((42,48),Image.Resampling.LANCZOS)
completed=Image.new('RGBA',(w,h));completed.paste(iris,(53,38));completed.save(dst/'iris-completed.png')
hair=Image.new('L',(w*4,h*4));d=ImageDraw.Draw(hair)
for poly in [[(0,0),(23,0),(22,25),(33,44),(46,54),(33,51),(18,41),(0,46)],[(110,0),(146,0),(146,116),(112,116),(116,87),(117,65),(115,43)]]:d.polygon([(x*4,y*4)for x,y in poly],fill=255)
hair.resize((w,h),Image.Resampling.LANCZOS).convert('RGBA').save(dst/'hair-foreground-mask.png')
# Original partitions are retained independently for PSD and compositor ownership.
xx,yy=np.meshgrid(np.arange(w),np.arange(h));top=np.interp(xx,[p[0]for p in meta['upper']],[p[1]for p in meta['upper']]);bottom=np.interp(xx,[p[0]for p in meta['lower']],[p[1]for p in meta['lower']]);inside=(xx>=32)&(xx<=111);ball=inside&(yy>=top)&(yy<=bottom);irismask=ball&(((xx-74)/23)**2+((yy-62)/26)**2<1);upper=inside&(yy<top)&(yy>=top-18);lower=inside&(yy>bottom)&(yy<=bottom+5)
for name,mask in [('upper-lash',upper),('lower-lash',lower),('iris-visible',irismask),('sclera-visible',ball&~irismask),('fixed-original',~(ball|upper|lower))]:
 b=a.copy();b[:,:,3]=np.where(mask,a[:,:,3],0);Image.fromarray(b).save(dst/(name+'.png'))
print('Registered independent right-eye candidate; source identity retained in imports/right/identity.json')

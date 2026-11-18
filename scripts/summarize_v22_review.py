"""Make review contact sheets and compare the saved PSD bind image with WebGL."""
from pathlib import Path
import json,hashlib
import numpy as np
from PIL import Image,ImageDraw,ImageFilter
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'assets/parts/v22';REVIEW=OUT/'motion-review'
def contact(files,name,width=326,cols=5):
    items=[]
    for label,file in files:
        im=Image.open(REVIEW/file).convert('RGBA');im.thumbnail((width,440))
        tile=Image.new('RGB',(width,470),'#888888');tile.paste(im,((width-im.width)//2,26),im);ImageDraw.Draw(tile).text((8,8),label,fill='white');items.append(tile)
    sheet=Image.new('RGB',(cols*width,470*((len(items)+cols-1)//cols)),'#888888')
    for i,item in enumerate(items):sheet.paste(item,((i%cols)*width,(i//cols)*470))
    sheet.save(REVIEW/name)
contact([(f'Arm {v}',f'arm-white-{v}.png') for v in [0,.25,.5,.75,1]],'arm-five-poses.png')
expressions=['neutral','soft_smile','big_smile','worried','surprised','bashful','displeased','thinking']
contact([(e,f'expression-{e}-1-white.png') for e in expressions],'all-eight-raised.png',326,4)
contact([(f'Arm {i/20}',f'arm-isolated-{i:02}.png') for i in [0,5,10,15,20]],'isolated-arms-contact.png')
contact([(f'Video {t}s',f'video-decoded-{t}.png') for t in [1.2,1.4,1.6,5.2,5.4,5.6]],'video-transition-contact.png',480,3)
def on_bg(a,value):return a[:,:,:3].astype(float)*(a[:,:,3:]/255)+value*(1-a[:,:,3:]/255)
a=np.array(Image.open(OUT/'psd-bind-pose.png').convert('RGBA'));b=np.array(Image.open(REVIEW/'browser-bind-pose.png').convert('RGBA'))
metrics={}
for bg in [0,255]:
    d=np.abs(on_bg(a,bg)-on_bg(b,bg));metrics[str(bg)]={'mean_absolute_rgb_difference_0_to_255':float(d.mean()),'pixels_any_channel_difference_over_16':int((d.max(axis=2)>16).sum()),'total_pixels':int(d.shape[0]*d.shape[1])}
report={'psd_sha256':hashlib.sha256((OUT/'koma_articulated_v22.psd').read_bytes()).hexdigest(),'model_sha256':hashlib.sha256((ROOT/'runtime/model/model.json').read_bytes()).hexdigest(),'psd_webgl_bind_pose':metrics,'note':'PSD integer-alpha compositing and WebGL bilinear sampling differ at edges. This compares the same neutral, raised bind pose with motion disabled.'}
old=np.array(Image.open(REVIEW/'hair-alpha-v19-reference.png'));interior=np.array(Image.fromarray(old[:,:,3]).filter(ImageFilter.MinFilter(41)))>=250
rows=[]
for t in range(5):
    current=np.array(Image.open(REVIEW/f'hair-alpha-{t}.png'));gap=interior&(current[:,:,3]<240);rows.append({'time':t,'transparent_pixels_inside_20px_eroded_original':int(gap.sum())})
    if t==4:
        marked=Image.fromarray(current);overlay=np.zeros_like(current);overlay[gap]=[255,0,0,255];marked=Image.alpha_composite(marked,Image.fromarray(overlay));marked.save(REVIEW/'hair-deep-gap-diagnostic.png')
report['deep_hair_gap_diagnostic']=rows
(REVIEW/'final-asset-verification.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps(report))

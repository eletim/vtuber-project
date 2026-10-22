from pathlib import Path
import json,subprocess
from PIL import Image,ImageDraw
import numpy as np
root=Path(__file__).resolve().parents[1];out=root/'assets/parts/v32';folder=root/'runtime/model'
m=json.loads((folder/'model.json').read_text(encoding='utf8'));old=json.loads(subprocess.check_output(['git','show','23db0404b944b7e8fb4c98df466854d012319d95:runtime/model/model.json'],cwd=root));checks=[]
for l in m['bodyLayers']:
 b=next(x for x in old['bodyLayers'] if x['id']==l['id']);a=np.array(Image.open(folder/l['file']).convert('RGBA'));before=np.array(Image.open(folder/b['file']).convert('RGBA'))
 item={'id':l['id'],'alpha_changed':int(np.sum(a[:,:,3]!=before[:,:,3])),'rgb_changed':int(np.sum(np.any(a[:,:,:3]!=before[:,:,:3],axis=2))),'metadata_changed':l!=b};checks.append(item)
 if not l.get('hairMotion') and l['id'] not in ['hair_reveal_native','left_raised_drape']:assert not item['alpha_changed'] and not item['rgb_changed'] and not item['metadata_changed']
 if l.get('hairMotion'):assert not item['alpha_changed']
(out/'preservation-audit.json').write_text(json.dumps(checks,indent=2),encoding='utf8')
canvas=Image.new('RGB',(1100,1410),'#ddd');d=ImageDraw.Draw(canvas)
for row,bg in enumerate(['white','black','#397e91']):
 for col,v in enumerate([31,32]):
  im=Image.open(root/f'assets/parts/v{v}/review/arm-0.5.png').convert('RGBA');comp=Image.new('RGBA',im.size,bg);comp.alpha_composite(im)
  crop=comp.crop((240,230,460,410)).resize((550,450));canvas.paste(crop,(col*550,row*470+20));d.text((col*550+8,row*470+4),f'v{v} / actual composite {bg}',fill='black')
canvas.save(out/'hair-composite-comparison.png')
# Contact sheets use actual opaque backgrounds, rather than a viewer's rendering
# of unassociated 1/255-alpha RGB values in transparent PNGs.
files=sorted((out/'review').glob('extreme-*.png'));c=Image.new('RGB',(1440,1080),'#397e91');d=ImageDraw.Draw(c)
for i,p in enumerate(files):
 im=Image.open(p).convert('RGBA');bg=Image.new('RGBA',im.size,['white','black','#397e91'][i%3]);bg.alpha_composite(im);bg.thumbnail((360,250));x=i%4*360;y=i//4*270;c.paste(bg,(x+(360-bg.width)//2,y+20));d.text((x+5,y+3),p.stem,fill='white')
c.save(out/'review/expression-extremes-contact.jpg')
print(json.dumps({'layers':len(checks),'hair_rgb_pixels':sum(x['rgb_changed'] for x in checks if x['id'] not in ['hair_reveal_native','left_raised_drape']),'reveal':next(x for x in checks if x['id']=='hair_reveal_native'),'unrelated_materials_unchanged':True}))

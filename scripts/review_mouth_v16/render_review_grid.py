from pathlib import Path
import json,math
from PIL import Image,ImageDraw,ImageFont
import numpy as np
D=Path(__file__).resolve().parent
code=(D/'render_v15.py').read_text().split("fontfile=")[0].replace("D/'frames.json'","D/'grid.json'").replace("D/'mesh.bin'","D/'grid-mesh.bin'")
exec(compile(code,str(D/'render_v15.py'),'exec'))
O=D.parent/'generated';O.mkdir(exist_ok=True)
fnt=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',15)
sheets={};stats=[]
for i,s in enumerate(poses):
 composite(s);Clear(0x4000);v=mesh[i];VertexPointer(2,0x1406,0,v.ctypes.data);DrawElements(0x0004,len(indices),0x1403,indices.ctypes.data);Finish();ReadPixels(0,0,AW,AH,0x1908,0x1401,pixels.ctypes.data);assert GetError()==0
 rgba=pixels[::-1].copy();alpha=rgba[:,:,3:4].astype(np.float32);rgba[:,:,:3]=np.clip(np.rint(rgba[:,:,:3].astype(np.float32)*255/np.maximum(alpha,1)),0,255).astype(np.uint8)
 avatar=Image.fromarray(rgba,'RGBA');bg=Image.new('RGBA',avatar.size,(247,242,236,255));bg.alpha_composite(avatar);rgb=bg.convert('RGB')
 # Keep the whole face visible at every test tilt, not only the mouth crop.
 face=rgb.crop((220,80,540,370));mouth=rgb.crop((330,215,440,290)).resize((440,300),Image.Resampling.NEAREST)
 stem=f'{s["requested"]}_tilt{s["tilt"]:+d}_open{s["amount"]:.3f}'
 face.save(O/(stem+'_face.png'));mouth.save(O/(stem+'_mouth.png'))
 base_amounts=[0,.15,.20,.25,.35,.65,1];extra_amounts=[.141,.16,.214]
 values=base_amounts if s['amount'] in base_amounts else extra_amounts
 key=s['requested']+('_matrix' if values==base_amounts else '_threshold')
 if key not in sheets:sheets[key]=Image.new('RGB',(len(values)*320,3*318),'white')
 sheet=sheets[key];xx=values.index(s['amount'])*320;yy=[-8,0,8].index(s['tilt'])*318;sheet.paste(face,(xx,yy+28));d=ImageDraw.Draw(sheet);d.text((xx+7,yy+5),f'{s["requested"]} Z={s["tilt"]:+d} M={s["amount"]:.3f}',fill='black',font=fnt)
 # Face/head mouth region is opaque before and after deformation.
 theta=math.radians(s['tilt']);cx=(540+math.cos(theta)*13-math.sin(theta)*(-69))*AW/MW;cy=(425+math.sin(theta)*13+math.cos(theta)*(-69))*AH/MH
 roi=rgba[round(cy)-24:round(cy)+24,round(cx)-40:round(cx)+40];stats.append({'case':stem,'alpha_min_mouth_region':int(roi[:,:,3].min()),'dark_pixels_rgb_lt80':int((roi[:,:,:3].max(axis=2)<80).sum())})
for key,im in sheets.items():im.save(O/(key+'.png'))
(O/'stats.json').write_text(json.dumps(stats,indent=2));print('Rendered',len(stats),'cases in',O)

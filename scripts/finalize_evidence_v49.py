from pathlib import Path
from PIL import Image, ImageDraw
import shutil,json,hashlib
p=Path('assets/parts/v49')
(p/'review/keyframes').mkdir(exist_ok=True)
for n in [12,22,147,237,247,282,*range(310,331)]:shutil.copyfile(p/f'review/frames/frame-{n:03}.png',p/f'review/keyframes/frame-{n:03}.png')
for side in ['left','right']:
 s=Image.new('RGB',(1015,1190),'#36505a');d=ImageDraw.Draw(s)
 for i,expr in enumerate(['neutral','soft_smile','worried','surprised','bashful','displeased','thinking']):
  for j,n in enumerate([0,15,30,45,60]):
   im=Image.open(p/f'audit/dense/{expr}-{side}-{n:02}.png');s.paste(im,(j*203,i*170+20),im);d.text((j*203,i*170),f'{expr} {n}/60',fill='white')
 s.save(p/f'dense-contact-{side}.png')
s=Image.new('RGB',(1440,1680),'#36505a');d=ImageDraw.Draw(s)
for i,n in enumerate(range(310,331)):
 im=Image.open(p/f'review/frames/frame-{n:03}.png');x=i%3*480;y=i//3*240;d.text((x,y),f'{n} ({n/30:.3f}s) v48 above / v49 below',fill='white');s.paste(im.crop((0,175,480,285)),(x,y+20));s.paste(im.crop((480,175,960,285)),(x,y+130))
s.save(p/'transition-310-330.png')
rows=[]
for n in [12,22,147,237,247,282,310,315,327]:
 im=Image.open(p/f'review/frames/frame-{n:03}.png');im.thumbnail((720,315));rows.append(im)
s=Image.new('RGB',(1440,1575),'#36505a');d=ImageDraw.Draw(s)
for i,im in enumerate(rows):s.paste(im,((i%2)*720,(i//2)*315));d.text(((i%2)*720,(i//2)*315),str([12,22,147,237,247,282,310,315,327][i]),fill='red')
s.save(p/'regression-contact.png')
files=[Path('runtime/web/eye-components.js'),Path('runtime/model/model.json'),*sorted((p/'review/keyframes').glob('*.png'))]
(p/'evidence-hashes.json').write_text(json.dumps({str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in files},indent=2)+'\n')

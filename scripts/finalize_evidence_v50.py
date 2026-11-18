from pathlib import Path
from PIL import Image,ImageDraw
import json,hashlib,shutil
p=Path('assets/parts/v50/review');k=p/'keyframes';k.mkdir(exist_ok=True)
indices=sorted(set([0,30,60,90,120,180,240,300,330,360,390,420,435,450,480,510,540,570,600,630,660,689]+list(range(178,206))+list(range(433,461))+list(range(598,626))))
for i in indices:shutil.copyfile(p/f'frames/face-{i:03}.png',k/f'face-{i:03}.png')
for label,ids in [('actions',[60,90,240,330,360,420,450,480,540,600,630,660]),('switch',[432,435,438,441,444,447,450,453,456,459,462,465])]:
 if label=='actions':
  s=Image.new('RGB',(1088,6*724),'#263c48')
  for j,i in enumerate(ids):s.paste(Image.open(p/f'full-{i:03}.png'),((j%2)*544,(j//2)*724))
 else:
  s=Image.new('RGB',(1440,4*440),'#263c48');d=ImageDraw.Draw(s)
  for j,i in enumerate(ids):x=j%3*480;y=j//3*440;s.paste(Image.open(p/f'frames/face-{i:03}.png'),(x,y+20));d.text((x,y),str(i/30),fill='white')
 s.save(p/f'{label}-contact.png')
r=json.loads((p/'report.json').read_text());rows=r['frames'];maxsteps={key:max(abs(a['pose'][key]-b['pose'][key]) for a,b in zip(rows,rows[1:])) for key in rows[0]['pose']};assert all(x['pose']['ParamAngleX']==x['pose']['ParamAngleY']==0 for x in rows)
f=Path('runtime/web/eye-components.js');baseline=hashlib.sha256(f.read_bytes()).hexdigest()
(p/'motion-audit.json').write_text(json.dumps({'max_per_30fps_step':maxsteps,'no_yaw_pitch_commands':True,'eye_renderer_sha256':baseline,'note':'Step measurements supplement visual inspection; not a naturalness score.'},indent=2)+'\n')
print(maxsteps)

from pathlib import Path
from PIL import Image,ImageDraw
import numpy as np,json
p=Path('assets/parts/v41/acting-native');frames=[];tiles=[];last=None;prev=None
for f in sorted(p.glob('frame-*.png')):
 im=Image.open(f).convert('RGB');idx=int(f.stem.split('-')[1]);a=np.asarray(im)[24:];delta=float(np.abs(a.astype(float)-prev).mean()) if last is not None and idx==last+1 else None;frames.append({'frame':idx,'time':idx/30,'meanDelta':delta});last=idx;prev=a.astype(float)
 tile=im.resize((300,244));ImageDraw.Draw(tile).rectangle((0,0,300,14),fill='#397e91');ImageDraw.Draw(tile).text((4,1),f'{idx/30:.3f}s v40 | v41',fill='white');tiles.append(tile)
for start in range(0,len(tiles),24):
 out=Image.new('RGB',(1200,1464),'#397e91')
 for i,im in enumerate(tiles[start:start+24]):out.paste(im,((i%4)*300,(i//4)*244))
 out.save(p/f'contact-{start//24+1:02}.jpg',quality=95)
largest=sorted([x for x in frames if x['meanDelta'] is not None],key=lambda x:x['meanDelta'],reverse=True)[:10]
(p/'temporal-audit.json').write_text(json.dumps({'count':len(frames),'frames':frames,'largest':largest},indent=2));print(largest[:3])
p=Path('assets/parts/v41/review');files=sorted(p.glob('extreme-*.png'));out=Image.new('RGB',(1600,1440),'#397e91')
for i,f in enumerate(files):
 im=Image.open(f).convert('RGBA');bg=Image.new('RGBA',im.size,'white' if i%2 else 'black');bg.alpha_composite(im);bg=bg.convert('RGB').resize((400,533));x=(i%4)*400;y=(i//4)*360;out.paste(bg.crop((0,0,400,330)),(x,y+25));ImageDraw.Draw(out).text((x+5,y+5),f.stem,fill='white')
out.save(p/'face-expression-contact.jpg',quality=95)

from pathlib import Path
import json
from collections import deque
import numpy as np
from PIL import Image,ImageDraw
OUT=Path(__file__).resolve().parents[1]/'assets/parts/v24/review'
def holes(image):
 a=np.array(image.convert('RGBA'));mask=Image.fromarray(((a[:,:,3]>=128)*255).astype('uint8')).copy();ImageDraw.floodfill(mask,(0,0),128);return np.array(mask)==0
rows=[]
for file in sorted(OUT.glob('pose-v24-*.png')):
 im=Image.open(file).convert('RGBA');a=np.array(im);small=im.resize((543,724),Image.Resampling.NEAREST);gap=holes(small);pending=set(zip(*np.nonzero(gap)));components=[]
 while pending:
  p=pending.pop();stack=[p];pixels=[p]
  while stack:
   y,x=stack.pop()
   for dy,dx in [(0,1),(0,-1),(1,0),(-1,0)]:
    q=(y+dy,x+dx)
    if q in pending:pending.remove(q);stack.append(q);pixels.append(q)
  if len(pixels)>=4:
   ys,xs=zip(*pixels);components.append({'pixels_half_resolution':len(pixels),'box_source':[int(min(xs)*2),int(min(ys)*2),int(max(xs)*2),int(max(ys)*2)]})
 rows.append({'file':file.name,'alpha_pixels_on_canvas_border':int((a[0,:,3]>0).sum()+(a[-1,:,3]>0).sum()+(a[:,0,3]>0).sum()+(a[:,-1,3]>0).sum()),'enclosed_transparent_pixels_half_resolution':int(gap.sum()),'largest_components':sorted(components,key=lambda c:c['pixels_half_resolution'],reverse=True)[:5]})
extremes=[]
for file in sorted(OUT.glob('extreme-*.png')):
 a=np.array(Image.open(file));extremes.append({'file':file.name,'border_alpha_pixels':int((a[0,:,3]>0).sum()+(a[-1,:,3]>0).sum()+(a[:,0,3]>0).sum()+(a[:,-1,3]>0).sum())})
def sheet(files,name,cols,width=280,height=410):
 out=Image.new('RGB',(cols*width,((len(files)+cols-1)//cols)*height),'#777777');draw=ImageDraw.Draw(out)
 for i,file in enumerate(files):
  im=Image.open(file).convert('RGBA');im.thumbnail((width,height-24));x=(i%cols)*width;y=(i//cols)*height;out.paste(im,(x,y+24),im);draw.text((x+5,y+5),file.stem,fill='white')
 out.save(OUT/name)
sheet([OUT/f'pose-v24-{t}.png' for t in [1.8,2.8,4,5.8,6.15,6.7,7.9,10]],'motion-contact.png',4)
sheet(sorted(OUT.glob('extreme-*.png')),'expression-extremes.png',4)
report={'motion_frames':rows,'extremes':extremes,'note':'Enclosed alpha gaps include inherited hair/leg matte holes and armpit negative space surrounded by the hanging sleeve. These topology counts are not defect counts. Border coverage checks catch crown clipping.'}
(OUT/'image-audit.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps({'frames':len(rows),'border_clipped_frames':[r['file'] for r in rows if r['alpha_pixels_on_canvas_border']],'maximum_enclosed_half_resolution':max(r['enclosed_transparent_pixels_half_resolution'] for r in rows),'extremes':len(extremes),'extreme_clipping':[r for r in extremes if r['border_alpha_pixels']]}))

from pathlib import Path
from PIL import Image,ImageDraw
import json
p=Path(__file__).resolve().parents[1]/'assets/parts/v32/review/all-frames-material-final'
r=json.loads((p/'temporal-report.json').read_text());frames=[f for f in r['frames'] if 10<=f['time']<=16]
for start in range(0,len(frames),30):
 c=Image.new('RGB',(1200,1450),'#ddd');d=ImageDraw.Draw(c)
 for j,item in enumerate(frames[start:start+30]):
  x=j%6*200;y=j//6*290;c.paste(Image.open(p/item['file']).resize((200,272)),(x,y+18));d.text((x+4,y+3),f"{item['time']:.3f}s / {item['index']}",fill='black')
 c.save(p/f'contact-{start//30}.jpg')
items=r['highestArmChanges'][:6];c=Image.new('RGB',(1500,360),'#ddd');d=ImageDraw.Draw(c)
for j,item in enumerate(items):c.paste(Image.open(p/item['file']),(j*250,20));d.text((j*250+4,4),f"{item['time']:.3f}s",fill='black')
c.save(p/'largest-changes.jpg')
print(json.dumps({'arm_frames':len(frames),'sheets':(len(frames)+29)//30,'range':[10,16],'encoded_frames':r['encodedSamples'],'playback':r['playback']['quality']}))

from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
from layered_egl import LayeredRenderer
D=Path(__file__).resolve().parent;out=D/'arm-extremes';r=LayeredRenderer(out);font=ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',18);sheet=Image.new('RGB',(2*650,420*len(r.plan['frames'])),'#eeeeee');draw=ImageDraw.Draw(sheet)
for i,s in enumerate(r.plan['frames']):
 avatar=r.render(i);avatar.save(out/f'{i:02d}-{s["label"]}.png')
 for col,color in enumerate(['black','white']):
  bg=Image.new('RGBA',avatar.size,color);bg.alpha_composite(avatar);im=bg.crop((255,390,680,655)).convert('RGB').resize((637,398),Image.Resampling.NEAREST);x=col*650;y=i*420;sheet.paste(im,(x,y+22));draw.text((x+8,y+2),s['label']+' / '+color,font=font,fill='black')
sheet.save(D/'koma-v19-full-range-shoulders.png');print(D/'koma-v19-full-range-shoulders.png')

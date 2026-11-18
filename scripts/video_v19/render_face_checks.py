from pathlib import Path
import json,hashlib
from PIL import Image,ImageDraw,ImageFont
from layered_egl import LayeredRenderer
D=Path(__file__).resolve().parent;r=LayeredRenderer(D);picks=r.plan['faceReviewFrames'];sheet=Image.new('RGB',(1140,350*8),'#f7f0e6');draw=ImageDraw.Draw(sheet);font=ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',18);out=D/'face-preflight';out.mkdir(exist_ok=True)
for k,f in enumerate(picks):
 avatar=r.render(f['frame']);bg=Image.new('RGBA',avatar.size,'#f7f0e6');bg.alpha_composite(avatar);im=bg.crop((260,133,640,453)).convert('RGB');im.save(out/f'{f["expression"]}-{f["target_opening"]}.png');x=k%3*380;y=k//3*350;sheet.paste(im,(x,y+30));draw.text((x+6,y+3),f'{f["expression"]} f{f["frame"]} mouth{f["actual_opening"]:.2f}',font=font,fill='#604a38')
sheet.save(D/'koma-v19-face-preflight.png');print(D/'koma-v19-face-preflight.png')

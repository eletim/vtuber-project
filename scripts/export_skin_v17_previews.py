#!/usr/bin/env python3
"""Export current v17 endpoint comparisons and unchanged Photoshop controls."""
from pathlib import Path
import json
import shutil
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from build_expressions_v15 import alpha_over,CROP

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'assets/parts/v17'
MODEL=ROOT/'runtime/model'

def build():
    model=json.loads((MODEL/'model.json').read_text())
    variants=[('Eyes open / mouth closed',(1,1,0)),('Eyes open / mouth open',(1,1,1)),
              ('Eyes closed / mouth closed',(0,0,0)),('Eyes closed / mouth open',(0,0,1))]
    sheet=Image.new('RGB',(1600,8*338+60),'#f5eee7')
    draw=ImageDraw.Draw(sheet);font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',18)
    draw.text((15,15),'HAZUKI KOMA / v17: corrected surprised closed-mouth skin; original lip art retained',font=font,fill='#49372d')
    (OUT/'previews').mkdir(parents=True,exist_ok=True)
    for row,e in enumerate(model['expressions']):
        base=np.asarray(Image.open(MODEL/e['base']).convert('RGBA'))
        parts=[]
        for p in e['parts']:
            full=np.zeros_like(base);x,y,r,b=p['rect']
            full[y:b,x:r]=np.asarray(Image.open(MODEL/p['file']).convert('RGBA'));parts.append((p,full))
        for col,(label,bits) in enumerate(variants):
            states=dict(zip(['eye_screen_left','eye_screen_right','mouth'],['open' if bit else 'closed' for bit in bits]))
            frame=base.copy()
            for p,full in parts:
                name,state=p['name'].rsplit('.',1)
                if states[name]==state:frame=alpha_over(frame,full)
            crop=Image.fromarray(frame).crop(CROP)
            x=col*400;y=60+row*338
            draw.text((x+8,y+6),e['id']+' / '+label,font=font,fill='#49372d')
            sheet.paste(crop,(x,y+38))
            if e['id']=='surprised':crop.save(OUT/'previews'/f'surprised_L{bits[0]}_R{bits[1]}_M{bits[2]}_face.png')
    sheet.save(OUT/'expression_motion_contact_sheet.png')
    shutil.copy2(ROOT/'assets/parts/v15/Switch_Koma_Expression.jsx',OUT/'Switch_Koma_Expression.jsx')
    text=(ROOT/'assets/parts/v15/使い方.txt').read_text()
    text=text.replace('koma_expression_motion_v15.psd','koma_expression_skin_v17.psd')
    text='v17: 「驚き」の閉じ口の周囲の肌を補正。口の線、アルファ、他の114レイヤーは保持。\n旧v15 PSDは保存したまま、新しいv17 PSDを使用してください。\n\n'+text
    (OUT/'使い方.txt').write_text(text)
    print(OUT/'expression_motion_contact_sheet.png')

if __name__=='__main__':build()

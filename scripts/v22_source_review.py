from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
from psd_groups_v14 import parse_psd_groups, LayerGroup
root=Path(__file__).resolve().parents[1]
nodes,size=parse_psd_groups(root/'assets/parts/v19/koma_separated_body_v19.psd')
out=root/'assets/parts/v22';out.mkdir(exist_ok=True)
head=next(n for n in nodes if n.name.startswith('01 Head'))
names=['face_expression_painted_skin_v9','front_bangs','hair_side_left','hair_side_right','hair_crown','hair_back_left','hair_back_right','face_skin_FULL_beneath_eyes_mouth','side_hair_fixed_painted_underlayer','hair_base_FULL_beneath_hair_parts']
panel=Image.new('RGB',(5*272,2*390),'#888888');d=ImageDraw.Draw(panel)
for i,name in enumerate(names):
 n=next(n for n in head.children if n.name.split('/')[-1]==name)
 im=Image.fromarray(n.rgba);im.thumbnail((272,362));x=i%5*272;y=i//5*390;panel.paste(im,(x,y+28),im);d.text((x+2,y+2),name[:34],fill='white')
panel.save(out/'source-layer-review.png')

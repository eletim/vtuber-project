"""Matched-time shoulder skin/vest boundaries on black and white, without retouching."""
from pathlib import Path
import argparse,json
from PIL import Image,ImageDraw,ImageFont
D=Path(__file__).resolve().parent;p=argparse.ArgumentParser();p.add_argument('--baseline',type=Path);args=p.parse_args();plan=json.loads((D/'frames.json').read_text());w,h=json.loads((D/'source/runtime/model/model.json').read_text())['size'];font=ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',20);sheet=Image.new('RGB',(4*360,2*420),'#eeeeee');draw=ImageDraw.Draw(sheet)
for row,(i,roi,name) in enumerate([(plan['diagnosticPeakFrameIndices'][0],[275,455,445,790],'Left shoulder'),(plan['diagnosticPeakFrameIndices'][1],[685,475,855,810],'Right shoulder')]):
 rect=tuple(round((v/s+.08)/1.16*a) for v,s,a in zip(roi,[w,h,w,h],[900,1200,900,1200]))
 panels=[(D,0,'black','Rest'),(args.baseline or D,i,'black','Before' if args.baseline else 'Peak black'),(D,i,'black','After black' if args.baseline else 'Peak black'),(D,i,'white','After white' if args.baseline else 'Peak white')]
 for col,(directory,frame,color,label) in enumerate(panels):
  im=Image.open(directory/f'verified-frames/{frame:04d}-avatar.png').convert('RGBA');bg=Image.new('RGBA',im.size,color);bg.alpha_composite(im);crop=bg.crop(rect).convert('RGB');crop.thumbnail((350,360));scale=min(350/crop.width,360/crop.height);crop=crop.resize((round(crop.width*scale),round(crop.height*scale)),Image.Resampling.NEAREST);x=col*360;y=row*420;sheet.paste(crop,(x+5,y+50));draw.text((x+6,y+5),f'{name}: {label}',font=font,fill='black');draw.text((x+6,y+27),f'Frame {frame} / {frame/30:.2f}s',font=font,fill='black')
sheet.save(D/'koma-v19-shoulder-attachment.png');print(D/'koma-v19-shoulder-attachment.png')

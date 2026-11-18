"""Exact-frame, unchanged-color skin comparisons across all expressions."""
from pathlib import Path
import json, subprocess, argparse, shutil
from PIL import Image, ImageDraw, ImageFont
D=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('--before',type=Path,default=Path('/workspace/shared/vtuber-v16-preview/koma-v16-mouth-motion.mp4'));p.add_argument('--old-pipeline',type=Path,default=Path('/workspace/shared/vtuber-v16-preview'));a=p.parse_args()
plan=json.loads((a.old_pipeline/'frames.json').read_text());out=D/'encoded-skin-audit';out.mkdir(exist_ok=True)
font=ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',20,index=0);smallfont=ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',13,index=0)
region=(1240,555,1470,735);cellw,cellh=300,274;rows=[]
for row,eid in enumerate(plan['ids']):
 candidates=[f for f in plan['frames'] if f['expressionFrame']['id']==eid and f['expressionFrame']['phase']=='idle' and not f['blink'] and (eid=='big_smile' or f['facePose']['ParamEyeLOpen']>.5)]
 for col,target in enumerate([0,.25,.65]):
  f=min(candidates,key=lambda f:abs(f['facePose']['ParamMouthOpenY']-target))
  rows.append({'row':row,'column':col,'expression':eid,'frame':f['i'],'time':f['i']/30,'requested_opening':target,'actual_opening':f['facePose']['ParamMouthOpenY']})
indices=sorted({r['frame'] for r in rows});cache={}
for version,video in [('v16',a.before),('v17',D/'koma-v17-mouth-motion.mp4')]:
 sub=out/version;sub.mkdir(exist_ok=True);selector='select='+'+'.join(f'eq(n\\,{n})' for n in indices)
 subprocess.run(['ffmpeg','-v','error','-y','-i',str(video),'-vf',selector,'-fps_mode','vfr',str(sub/'frame-%04d.png')],check=True)
 files=sorted(sub.glob('frame-*.png'));assert len(files)==len(indices)
 cache[version]=dict(zip(indices,files))
sheet=Image.new('RGB',(cellw*6,cellh*8),'#f7f0e6');draw=ImageDraw.Draw(sheet)
for r in rows:
 for version in ['v16','v17']:
  dest=out/f'{r["expression"]}-{r["column"]}-{version}.png';shutil.copyfile(cache[version][r['frame']],dest)
  crop=Image.open(dest).convert('RGB').crop(region).resize((300,235),Image.Resampling.LANCZOS)
  x=(r['column']*2+(version=='v17'))*cellw;y=r['row']*cellh
  sheet.paste(crop,(x,y+39));draw.text((x+6,y+2),f'{r["expression"]} {version}',font=font,fill='#604a38');draw.text((x+6,y+23),f'{r["time"]:.3f}s / mouth {r["actual_opening"]:.3f}',font=smallfont,fill='#604a38')
for row,eid in enumerate(plan['ids']):sheet.crop((0,row*cellh,6*cellw,(row+1)*cellh)).save(out/f'{eid}-skin-before-after.png')
sheet.save(D/'koma-v17-all8-skin-before-after.png')
(out/'selection.json').write_text(json.dumps({'crop':region,'unchanged_colors':True,'selection_basis':'v16 stable non-blink frames; exact decoded frame indices and crop coordinates in v17','frames':rows},indent=2))
print('Prepared 24 exact old/new encoded skin comparisons across all eight expressions.')

from pathlib import Path
import argparse,json,subprocess
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from layered_egl import LayeredRenderer,AW,AH
D=Path(__file__).resolve().parent;parser=argparse.ArgumentParser();parser.add_argument('--frames-only',action='store_true');args=parser.parse_args();renderer=LayeredRenderer(D);plan=renderer.plan;poses=plan['frames'];W,H=1080,1440;stage=(90,92)
def font(size,bold=False):return ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSansCJK-'+('Bold' if bold else 'Regular')+'.ttc',size,index=0)
f18=font(18);f20=font(20);f24=font(24);b24=font(24,True);b40=font(40,True)
y,x=np.mgrid[0:H,0:W];rad=np.clip(np.sqrt(((x-540)/1000)**2+((y-540)/1300)**2),0,1);colors=np.stack([252-14*rad,247-20*rad,237-27*rad],axis=2).astype(np.uint8);background=Image.fromarray(colors).convert('RGBA');b=ImageDraw.Draw(background)
b.text((38,15),'羽月こま',font=b40,fill='#45372e');b.text((300,30),'腕・胴体・スカートを独立化 / v19',font=f24,fill='#786553');b.line((38,78,1042,78),fill='#ded1be',width=2)
b.text((40,1310),'VOICEVOX:雨晴はう / 保存済み音声を再使用（新規台詞なし）',font=f20,fill='#71563c')
b.text((40,1342),'現行コードの独立メッシュで再描画。操作画面の録画ではありません。',font=f18,fill='#846b54')
b.text((40,1372),'従来の太もも・髪の境界は残ります。Cubism形式ではありません。',font=f18,fill='#9b653e')
cmd=['ffmpeg','-v','warning','-y','-f','rawvideo','-pixel_format','rgb24','-video_size',f'{W}x{H}','-framerate',str(plan['fps']),'-i','pipe:0','-i',str(D/'timeline-audio.wav'),'-map','0:v:0','-map','1:a:0','-c:v','libx264','-threads','2','-preset','fast','-crf','18','-pix_fmt','yuv420p','-c:a','aac','-b:a','128k','-t',str(plan['duration']),'-movflags','+faststart',str(D/'koma-v19-separated-body-motion.mp4')]
proc=None if args.frames_only else subprocess.Popen(cmd,stdin=subprocess.PIPE);out=D/'verified-frames';out.mkdir(exist_ok=True);lossless=D/'isolation-lossless';lossless.mkdir(exist_ok=True);picks=plan['reviewFrameIndices'];baselines={};diffs={};frame_bounds={};size=renderer.model['size']
protected={'central_blouse_corset':[465,570,680,940],'left_vest':[390,790,435,965],'right_vest':[710,790,745,950]}
def projected(rect):
 x0,y0,x1,y1=rect;return tuple(int(round((v/s+.08)/1.16*a)) for v,s,a in zip([x0,y0,x1,y1],[size[0],size[1],size[0],size[1]],[AW,AH,AW,AH]))
mask=np.zeros((AH,AW),bool)
for r in protected.values():
 x0,y0,x1,y1=projected(r);mask[y0:y1,x0:x1]=True
reference=np.array(renderer.render(0));torso_reference=np.array(renderer.render(0,only_roles=['torso']));Image.fromarray(torso_reference).save(lossless/'torso-0000.png');foreground_reference=np.array(renderer.render(0,only_roles=['armLeft','armRight','head']));Image.fromarray(foreground_reference).save(lossless/'foreground-0000.png');dynamic_diffs={}
# Pixel invariance applies to both raw RGBA and composited pixels on the video background.
for i,s in enumerate(poses):
 if args.frames_only and i not in picks:continue
 avatar=renderer.render(i);a=np.array(avatar);frame_bounds[str(i)]=avatar.getchannel('A').getbbox();bounds=frame_bounds[str(i)];assert bounds and bounds[0]>1 and bounds[1]>1 and bounds[2]<AW-1 and bounds[3]<AH-1,'Avatar clipped at frame '+str(i)
 if i<540:
  d=np.abs(a[mask].astype(int)-reference[mask].astype(int));diffs[str(i)]={'changed_pixels':int(np.any(d!=0,axis=1).sum()),'max_channel_delta':int(d.max())}
  if i in picks or diffs[str(i)]['changed_pixels']:
   foreground=renderer.render(i,only_roles=['armLeft','armRight','head']);fg=np.array(foreground);visible=mask&(torso_reference[:,:,3]==255)&(foreground_reference[:,:,3]==0)&(fg[:,:,3]==0);assert visible.sum()>500
   vd=np.abs(a[visible].astype(int)-reference[visible].astype(int));dynamic_diffs[str(i)]={'visible_pixels':int(visible.sum()),'changed_pixels':int(np.any(vd!=0,axis=1).sum()),'max_channel_delta':int(vd.max())}
   if i in picks:foreground.save(lossless/f'foreground-{i:04d}.png');Image.fromarray((visible*255).astype(np.uint8)).save(lossless/f'visible-mask-{i:04d}.png')
  else:
   dynamic_diffs[str(i)]={'visible_pixels':None,'changed_pixels':0,'max_channel_delta':0,'proof':'Entire protected ROI is identical; therefore every unoccluded subset is identical. Foreground masks are additionally rendered and saved at selected review frames.'}
 if i in picks:
  avatar.save(out/f'{i:04d}-avatar.png')
  if i<540:
   torso=renderer.render(i,only_roles=['torso']);torso.save(lossless/f'torso-{i:04d}.png');assert np.array_equal(np.array(torso),torso_reference),'Torso-only composite moved'
   avatar.save(lossless/f'full-{i:04d}.png')
  if 300<=i<480:renderer.render(i,only_roles=['skirt']).save(lossless/f'skirt-{i:04d}.png')
 frame=background.copy();frame.alpha_composite(avatar,stage);draw=ImageDraw.Draw(frame);draw.text((835,30),f'{s["t"]:05.2f}秒',font=f20,fill='#97846f');draw.text((40,103),'スカートのみ / ウエスト固定・小さな揺れ' if s['section']=='skirt' else s['label'],font=b24,fill='#704c2d');draw.text((40,140),'安全範囲：最大±3px（元画像）' if s['section']=='skirt' else ('発話中' if s['voice'] else ('部位の分離確認' if i<540 else '待機')),font=f18,fill='#97846f');draw.rounded_rectangle((40,1416,1040,1422),radius=3,fill='#e0d2be')
 if i:draw.rounded_rectangle((40,1416,40+1000*i/(len(poses)-1),1422),radius=3,fill='#aa7a42')
 if i in picks:frame.convert('RGB').save(out/f'{i:04d}-{s["requested"]}.png')
 if proc:proc.stdin.write(frame.convert('RGB').tobytes())
 if i%150==0:print(f'Rendered {i}/{len(poses)} independent-layer frames',flush=True)
if proc:proc.stdin.close();assert proc.wait()==0
(D/('stage-bounds-preflight.json' if args.frames_only else 'stage-bounds-all.json')).write_text(json.dumps(frame_bounds,indent=2))
report={'mode':'preflight' if args.frames_only else 'all-diagnostic-frames','torso_only_lossless_samples':'all identical to frame 0','protected_source_rectangles':protected,'protected_avatar_rectangles':{k:projected(v) for k,v in protected.items()},'protected_pixel_count':int(mask.sum()),'unoccluded_frames':dynamic_diffs,'unoccluded_max_changed_pixels':max(d['changed_pixels'] for d in dynamic_diffs.values()),'unoccluded_max_channel_delta':max(d['max_channel_delta'] for d in dynamic_diffs.values()),'frames':diffs,'max_changed_pixels':max(d['changed_pixels'] for d in diffs.values()),'max_channel_delta':max(d['max_channel_delta'] for d in diffs.values()),'method':'Raw lossless independent-layer RGBA renders; torso-only samples exact. Protected torso source ROI projected to fixed diagnostic rest framing, further restricted to torso alpha255 and foreground(arms/head) alpha0 at both reference and current. Foreground RGBA and visible masks are saved for independent recomputation. Raw RGBA equality implies identical source-over on fixed video background.'}
(D/('isolation-pixel-preflight.json' if args.frames_only else 'isolation-pixels.json')).write_text(json.dumps(report,indent=2))
selected=[0]+plan['diagnosticPeakFrameIndices']+[990];sheet=Image.new('RGB',(360*3,510*2),'#f7f0e6');draw=ImageDraw.Draw(sheet)
for k,i in enumerate(selected[:6]):
 im=Image.open(out/f'{i:04d}-{poses[i]["requested"]}.png').resize((360,480),Image.Resampling.LANCZOS);x=k%3*360;y=k//3*510;sheet.paste(im,(x,y+30));draw.text((x+8,y+3),f'{i/30:.2f}s / {poses[i]["section"]}',font=f18,fill='#604a38')
sheet.save(D/'koma-v19-diagnostic-sheet.png')
# Actual cutout/occlusion review on high-contrast grounds, not merely synthetic alpha.
join_picks=[0]+plan['diagnosticPeakFrameIndices'];joins=Image.new('RGB',(1080,520*len(join_picks)),'#eeeeee');jd=ImageDraw.Draw(joins);crop=projected([170,450,970,1130])
for row,i in enumerate(join_picks):
 avatar=Image.open(out/f'{i:04d}-avatar.png').convert('RGBA')
 for col,color in enumerate(['white','black']):
  bg=Image.new('RGBA',avatar.size,color);bg.alpha_composite(avatar);bg.convert('RGB').save(lossless/f'full-{i:04d}-{color}.png');tile=bg.crop(crop).convert('RGB');tile.thumbnail((530,480),Image.Resampling.LANCZOS);joins.paste(tile,(col*540,row*520+35));jd.text((col*540+8,row*520+5),f'{i/30:.2f}s / {color}',font=f18,fill='#604a38')
joins.save(D/'koma-v19-joins-black-white.png')
print('KEYFRAMES COMPLETE' if args.frames_only else 'VIDEO COMPLETE',flush=True);print(json.dumps({'max_protected_changed_pixels':report['max_changed_pixels'],'max_protected_channel_delta':report['max_channel_delta']}))

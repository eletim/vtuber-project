from pathlib import Path
import argparse,json,subprocess
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from layered_egl import LayeredRenderer,AW,AH
D=Path(__file__).resolve().parent;parser=argparse.ArgumentParser();parser.add_argument('--frames-only',action='store_true');args=parser.parse_args();renderer=LayeredRenderer(D);plan=renderer.plan;poses=plan['frames'];W,H=1080,1440;stage=(90,92)
def font(size,bold=False):return ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSansCJK-'+('Bold' if bold else 'Regular')+'.ttc',size,index=0)
f18=font(18);f20=font(20);f24=font(24);b24=font(24,True);b40=font(40,True)
y,x=np.mgrid[0:H,0:W];rad=np.clip(np.sqrt(((x-540)/1000)**2+((y-540)/1300)**2),0,1);colors=np.stack([252-14*rad,247-20*rad,237-27*rad],axis=2).astype(np.uint8);background=Image.fromarray(colors).convert('RGBA');b=ImageDraw.Draw(background)
b.text((38,15),'羽月こま',font=b40,fill='#45372e');b.text((300,30),'今回の文章から新規音声合成 / v20',font=f24,fill='#786553');b.line((38,78,1042,78),fill='#ded1be',width=2)
b.text((40,1250),'「こんにちは、羽月こまです。今入力してもらった文章から、',font=f20,fill='#71563c')
b.text((40,1280),'新しく声を作っています。声に合わせて、表情や腕も動かしますね。」',font=f20,fill='#71563c')
b.text((40,1320),'VOICEVOX:雨晴はう / 新規合成した音声を一度再生',font=f20,fill='#71563c')
b.text((40,1352),'現行コードによるオフライン再描画。操作画面の録画ではありません。',font=f18,fill='#846b54')
b.text((40,1380),'腕・胴体・スカートは独立。従来の髪・太ももの境界は残ります。',font=f18,fill='#9b653e')
cmd=['ffmpeg','-v','warning','-y','-f','rawvideo','-pixel_format','rgb24','-video_size',f'{W}x{H}','-framerate',str(plan['fps']),'-i','pipe:0','-i',str(D/'timeline-audio.wav'),'-map','0:v:0','-map','1:a:0','-c:v','libx264','-threads','2','-preset','fast','-crf','18','-pix_fmt','yuv420p','-c:a','aac','-b:a','128k','-t',str(plan['duration']),'-movflags','+faststart',str(D/'koma-v20-fresh-speech.mp4')]
proc=None if args.frames_only else subprocess.Popen(cmd,stdin=subprocess.PIPE);out=D/'verified-frames';out.mkdir(exist_ok=True);picks=plan['reviewFrameIndices'];bounds={}
for i,s in enumerate(poses):
 if args.frames_only and i not in picks:continue
 avatar=renderer.render(i);bb=avatar.getchannel('A').getbbox();bounds[str(i)]=bb;assert bb and bb[0]>1 and bb[1]>1 and bb[2]<AW-1 and bb[3]<AH-1,'Avatar clipping '+str(i)
 frame=background.copy();frame.alpha_composite(avatar,stage);draw=ImageDraw.Draw(frame);draw.text((930,35),f'{s["t"]:05.2f}秒',font=f18,fill='#97846f');draw.text((40,103),s['label'],font=b24,fill='#704c2d');draw.text((40,140),'発話中：新規音声の音量で口・腕を動かす' if s['voice'] else '待機 / 音声の再利用ではありません',font=f18,fill='#97846f');draw.rounded_rectangle((40,1416,1040,1422),radius=3,fill='#e0d2be')
 if i:draw.rounded_rectangle((40,1416,40+1000*i/(len(poses)-1),1422),radius=3,fill='#aa7a42')
 if i in picks:avatar.save(out/f'{i:04d}-avatar.png');frame.convert('RGB').save(out/f'{i:04d}.png')
 if proc:proc.stdin.write(frame.convert('RGB').tobytes())
 if i%90==0:print(f'Rendered {i}/{len(poses)} fresh-speech frames',flush=True)
if proc:proc.stdin.close();assert proc.wait()==0
(D/('stage-bounds-preflight.json' if args.frames_only else 'stage-bounds-all.json')).write_text(json.dumps(bounds,indent=2))
sheet=Image.new('RGB',(360*3,510*4),'#f7f0e6');draw=ImageDraw.Draw(sheet)
for k,i in enumerate(picks):
 im=Image.open(out/f'{i:04d}.png').resize((360,480),Image.Resampling.LANCZOS);x=k%3*360;y=k//3*510;sheet.paste(im,(x,y+30));draw.text((x+8,y+3),f'{i/30:.2f}s / {poses[i]["section"]}',font=f18,fill='#604a38')
sheet.save(D/'koma-v20-lossless-contact.png');print('KEYFRAMES COMPLETE' if args.frames_only else 'VIDEO COMPLETE',flush=True)

from pathlib import Path
import json,hashlib,subprocess,wave,shutil
import numpy as np
from PIL import Image,ImageDraw,ImageFont
D=Path(__file__).resolve().parent;video=D/'koma-v18-arm-body-motion.mp4';plan=json.loads((D/'frames.json').read_text());frames=plan['frames'];assert video.stat().st_size<20_000_000,'MP4 must be below20MB'
probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_format','-show_streams','-of','json',str(video)]));subprocess.run(['ffmpeg','-v','error','-i',str(video),'-f','null','-'],check=True)
vs=next(s for s in probe['streams'] if s['codec_type']=='video');assert (vs['width'],vs['height'],vs['nb_frames'])==(1080,1440,'1260')
subprocess.run(['ffmpeg','-v','error','-y','-i',str(video),'-vn','-ac','1','-ar','24000','-f','f32le',str(D/'decoded-audio.f32')],check=True)
a=np.fromfile(D/'decoded-audio.f32',dtype=np.float32)
with wave.open(str(D/'timeline-audio.wav'),'rb') as w:b=np.frombuffer(w.readframes(w.getnframes()),dtype='<i2').astype(float)/32768
correlation=float(np.corrcoef(a[:len(b)],b)[0,1]);assert correlation>.99
picks=plan['reviewFrameIndices'];peaks=plan.get('gestureWindowFrameIndices',plan['gesturePeakFrameIndices'][:2]);windows={str(peak):[max(0,min(1259,peak+d)) for d in [-15,-10,-5,0,5,10,15]] for peak in peaks};indices=sorted(set(picks+[i for window in windows.values() for i in window]));encoded=D/'encoded-frames';encoded.mkdir(exist_ok=True)
selector='select='+'+'.join(f'eq(n\\,{i})' for i in indices)
subprocess.run(['ffmpeg','-v','error','-y','-i',str(video),'-vf',selector,'-fps_mode','vfr',str(encoded/'selected-%04d.png')],check=True)
files=sorted(encoded.glob('selected-*.png'));assert len(files)==len(indices);by_index=dict(zip(indices,files))
for i,p in by_index.items():shutil.copyfile(p,encoded/f'frame-{i:04d}.png')
font=ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',20,index=0)
cols=4;rows=(len(picks)+cols-1)//cols;sheet=Image.new('RGB',(360*cols,510*rows),'#f7f0e6');draw=ImageDraw.Draw(sheet)
for k,i in enumerate(picks):
 im=Image.open(by_index[i]).convert('RGB').resize((360,480),Image.Resampling.LANCZOS);x=k%cols*360;y=k//cols*510;sheet.paste(im,(x,y+30));draw.text((x+8,y+3),f'Frame {i} / {i/30:.2f}s',font=font,fill='#604a38')
sheet.save(D/'koma-v18-body-contact-sheet.png')
for peak,window in windows.items():
 sheet=Image.new('RGB',(360*7,510),'#f7f0e6');draw=ImageDraw.Draw(sheet)
 for k,i in enumerate(window):
  im=Image.open(by_index[i]).convert('RGB').resize((360,480),Image.Resampling.LANCZOS);sheet.paste(im,(k*360,30));draw.text((k*360+8,3),f'{i/30:.3f}s',font=font,fill='#604a38')
 sheet.save(D/f'gesture-window-{peak}.png')
# No color adjustment: approved mouth-skin check from the actual encoded portrait.
Image.open(by_index[653]).crop((300,190,800,620)).save(D/'koma-v18-frame653-face.png')
bounds={p.name:Image.open(p).getchannel('A').getbbox() for p in (D/'verified-frames').glob('*avatar.png')}
assert bounds and all(b[0]>1 and b[1]>1 and b[2]<899 and b[3]<1199 for b in bounds.values())
(D/'stage-bounds.json').write_text(json.dumps(bounds,indent=2))
result={'video':video.name,'sha256':hashlib.sha256(video.read_bytes()).hexdigest(),'size_bytes':video.stat().st_size,'metadata':probe,'full_decode':'PASS','audio_correlation':correlation,'audio_peak':float(abs(a).max()),'motion':json.loads((D/'motion-verification.json').read_text()),'source':json.loads((D/'source-provenance.json').read_text()),'decoded_review_frames':indices,'gesture_windows':windows,'notes':['Offline OpenGL re-render using exact runtime stateful motion driver and BodyRig; not GUI recording or browser E2E.','Original VOICEVOX:雨晴はう sample reused; no new dialogue.','Eyes use authored open/closed sprites, not continuous eyelid morphing.','Approved v17 face/model assets unchanged. Body mesh and arm/torso trajectories intentionally change.','Existing thigh cutout gaps and hair matte are unchanged; character artwork ends at thighs. No Cubism claim.']}
(D/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps({'duration':probe['format']['duration'],'bytes':video.stat().st_size,'sha256':result['sha256'],'audio_correlation':correlation,'review_frames':indices},indent=2))

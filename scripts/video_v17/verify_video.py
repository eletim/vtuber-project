from pathlib import Path
import json,hashlib,subprocess,wave
import numpy as np
from PIL import Image,ImageDraw,ImageFont
D=Path(__file__).resolve().parent;video=D/'koma-v17-mouth-motion.mp4';plan=json.loads((D/'frames.json').read_text());frames=plan['frames']
assert video.stat().st_size < 20_000_000, 'Video must remain below 20 MB for delivery'
probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_format','-show_streams','-of','json',str(video)]))
subprocess.run(['ffmpeg','-v','error','-i',str(video),'-f','null','-'],check=True)
subprocess.run(['ffmpeg','-v','error','-y','-i',str(video),'-vn','-ac','1','-ar','24000','-f','f32le',str(D/'decoded-audio.f32')],check=True)
a=np.fromfile(D/'decoded-audio.f32',dtype=np.float32)
with wave.open(str(D/'timeline-audio.wav'),'rb') as w:b=np.frombuffer(w.readframes(w.getnframes()),dtype='<i2').astype(float)/32768
voice_correlation=float(np.corrcoef(a[:len(b)],b)[0,1]);assert voice_correlation>.99
summary={};selection=[]
for eid in plan['ids']:
 stable=[f for f in frames if f['expressionFrame']['id']==eid and f['expressionFrame']['phase']=='idle']
 voiced=[f for f in stable if f['voice']]
 assert len(stable)>=100 and len(voiced)>30,(eid,len(stable),len(voiced))
 vals=[f['facePose']['ParamMouthOpenY'] for f in voiced]
 assert max(vals)-min(vals)>.25,(eid,min(vals),max(vals))
 eyes=[f['facePose']['ParamEyeLOpen'] for f in stable]
 if eid!='big_smile':assert max(eyes)>.5 and min(eyes)<.12,(eid,min(eyes),max(eyes))
 summary[eid]={'stable_frames':len(stable),'voiced_frames':len(voiced),'mouth_range':[min(vals),max(vals)],'eye_range':[min(eyes),max(eyes)],'opening_scales':len(set(round(part['opening']['scale'],4) for f in voiced for part in f['draw'] if part['name'].startswith('mouth')))}
 selection.append(max((f for f in voiced if not f['blink'] and (eid=='big_smile' or f['facePose']['ParamEyeLOpen']>.5)),key=lambda f:f['facePose']['ParamMouthOpenY']))
thumbs=[];encoded=D/'encoded-frames';encoded.mkdir(exist_ok=True)
for f in selection:
 target=encoded/(f['requested']+'.png')
 subprocess.run(['ffmpeg','-v','error','-y','-ss',str(f['t']),'-i',str(video),'-frames:v','1',str(target)],check=True)
 thumbs.append(Image.open(target).convert('RGB').resize((800,540),Image.Resampling.LANCZOS))
sheet=Image.new('RGB',(1600,2160),'#f2e9da')
for i,im in enumerate(thumbs):sheet.paste(im,(i%2*800,i//2*540))
sheet.save(D/'koma-v17-expression-contact-sheet.png')
# Keep the expressive face-inset grid small enough for direct visual QA.
faced=Image.new('RGB',(1536,802),'#f7f0e6');draw=ImageDraw.Draw(faced);font=ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',22,index=0)
for i,f in enumerate(selection):
 im=Image.open(encoded/(f['requested']+'.png')).crop((1138,430,1522,786));x=i%4*384;y=i//4*401
 faced.paste(im,(x,y+39));draw.text((x+10,y+3),f'{i+1}. {f["label"]}',font=font,fill='#654832')
faced.save(D/'koma-v17-expression-face-sheet.png')
result={'video':video.name,'sha256':hashlib.sha256(video.read_bytes()).hexdigest(),'size_bytes':video.stat().st_size,'metadata':probe,'full_decode':'PASS','audio_correlation':voice_correlation,'audio_peak':float(abs(a).max()),'expressions':summary,'source':json.loads((D/'source-provenance.json').read_text()),'notes':['Offline OpenGL re-rendering, not GUI capture or browser E2E.','Original VOICEVOX:雨晴はう recording repeated four times; no new dialogue synthesized.','Exact runtime blink-masked expression transition and tangent/normal mouth RGBA deformation used. Eyes retain opaque authored open/closed endpoints, not continuous eyelid morphing.','Thigh cutout gaps and hair matte remain visible.']}
(D/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
print(json.dumps({'duration':probe['format']['duration'],'bytes':video.stat().st_size,'audio_correlation':voice_correlation,'expressions':summary},ensure_ascii=False,indent=2))

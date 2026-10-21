from pathlib import Path
import hashlib,json,subprocess,wave
import numpy as np
from PIL import Image,ImageDraw,ImageFont
D=Path(__file__).resolve().parent;video=D/'koma-v20-fresh-speech.mp4';plan=json.loads((D/'frames.json').read_text());frames=plan['frames'];voice=json.loads((D/'fresh-voice-verification.json').read_text());assert video.stat().st_size<20_000_000
probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_format','-show_streams','-of','json',str(video)]));subprocess.run(['ffmpeg','-v','error','-i',str(video),'-f','null','-'],check=True)
vs=next(s for s in probe['streams'] if s['codec_type']=='video');assert (vs['width'],vs['height'],vs['nb_frames'])==(1080,1440,'450');assert float(probe['format']['duration'])==15
subprocess.run(['ffmpeg','-v','error','-y','-i',str(video),'-vn','-ac','1','-ar','24000','-f','f32le',str(D/'decoded-audio.f32')],check=True);a=np.fromfile(D/'decoded-audio.f32',dtype=np.float32)
with wave.open(str(D/'timeline-audio.wav'),'rb') as w:b=np.frombuffer(w.readframes(w.getnframes()),dtype='<i2').astype(float)/32768
with wave.open(str(D/'fresh-voice.wav'),'rb') as w:fresh=np.frombuffer(w.readframes(w.getnframes()),dtype='<i2')
start=36000;assert np.array_equal((b[start:start+len(fresh)]*32768).astype('<i2'),fresh);correlation=float(np.corrcoef(a[:len(b)],b)[0,1]);assert correlation>.99
critical={n:max(range(len(frames)),key=lambda i:frames[i]['p'][n]) for n in ['ParamMouthOpenY','ParamArmLOpen','ParamArmROpen']};selected=sorted(set(plan['reviewFrameIndices']+list(critical.values())));out=D/'encoded-frames';out.mkdir(exist_ok=True);selector='select='+'+'.join(f'eq(n\\,{i})' for i in selected);subprocess.run(['ffmpeg','-v','error','-y','-i',str(video),'-vf',selector,'-fps_mode','vfr',str(out/'selected-%04d.png')],check=True);files=sorted(out.glob('selected-*.png'));assert len(files)==len(selected)
font=ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',20);sheet=Image.new('RGB',(1080,510*((len(selected)+2)//3)),'#f7f0e6');draw=ImageDraw.Draw(sheet);face=Image.new('RGB',(1140,700),'#f7f0e6');fd=ImageDraw.Draw(face);face_indices=[60,critical['ParamMouthOpenY'],150,210,270,330]
for k,(i,p) in enumerate(zip(selected,files)):
 im=Image.open(p);im.save(out/f'frame-{i:04d}.png');x=k%3*360;y=k//3*510;sheet.paste(im.resize((360,480),Image.Resampling.LANCZOS),(x,y+30));draw.text((x+8,y+3),f'{i/30:.2f}s / {frames[i]["section"]}',font=font,fill='#604a38')
 if i in face_indices:
  n=face_indices.index(i);x=n%3*380;y=n//3*350;face.paste(im.crop((350,225,730,545)),(x,y+30));fd.text((x+5,y+3),f'{i/30:.2f}s mouth {frames[i]["p"]["ParamMouthOpenY"]:.2f}',font=font,fill='#604a38')
sheet.save(D/'koma-v20-contact-sheet.png');face.save(D/'koma-v20-face-checks.png')
params=['ParamMouthOpenY','ParamArmLOpen','ParamArmROpen','ParamBodyAngleX'];motion={k:{'min':min(f['p'][k] for f in frames),'max':max(f['p'][k] for f in frames)} for k in params};assert motion['ParamMouthOpenY']['max']>.1 and max(motion['ParamArmLOpen']['max'],motion['ParamArmROpen']['max'])>.1
assert all(not f['voice'] and f['p']['ParamMouthOpenY']==0 for f in frames[:45]);assert frames[-1]['p']['ParamMouthOpenY']<.001
model=json.loads((D/'source/runtime/model/model.json').read_text());nx,ny=model['mesh'];rest_area=1/(nx*ny);geometry={}
for role in plan['roles']:
 mesh=np.memmap(D/f'mesh-{role}.bin',dtype=np.float32,mode='r',shape=(450,ny+1,nx+1,2));a0=mesh[:,:-1,:-1];a1=mesh[:,:-1,1:];a2=mesh[:,1:,:-1];a3=mesh[:,1:,1:];cross=lambda u,v:u[...,0]*v[...,1]-u[...,1]*v[...,0];ratios=np.minimum(cross(a1-a0,a2-a0),cross(a3-a1,a2-a1))/rest_area;minimum=float(ratios.min());assert minimum>0,'Folded '+role;geometry[role]={'minimum_signed_area_ratio':minimum,'folded_triangles':0}
result={'passed':True,'video':video.name,'sha256':hashlib.sha256(video.read_bytes()).hexdigest(),'bytes':video.stat().st_size,'full_decode':'PASS','metadata':probe,'fresh_voice_provenance':voice,'single_complete_utterance_unmodified':True,'voice_starts_seconds':[1.5],'decoded_audio_correlation':correlation,'motion':motion,'all_frame_mesh_geometry':geometry,'critical_frame_indices':critical,'idle_before_speech':True,'final_mouth_closed':True,'source':json.loads((D/'source-provenance.json').read_text()),'scope':'Offline code-generated preview using the actual accepted separate-layer meshes, PerformanceMotion and RMS mouth. Not a browser or UI end-to-end test.'};(D/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps({k:result[k] for k in ['passed','sha256','bytes','decoded_audio_correlation','motion']},indent=2))

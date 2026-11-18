from pathlib import Path
import hashlib,json,subprocess,wave,argparse
from PIL import Image,ImageDraw,ImageFont
D=Path(__file__).resolve().parent
parser=argparse.ArgumentParser();parser.add_argument('--before',type=Path,default=Path('/workspace/scratch/f1d5e45451e6/recovered_v15/koma-v15-expression-motion.mp4'));parser.add_argument('--old-pipeline',type=Path,default=Path('/workspace/shared/vtuber-v16-review/v15_pipeline'));args=parser.parse_args()
old=args.old_pipeline;new=D;before=args.before;after=D/'koma-v16-mouth-motion.mp4'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
oldframes=json.loads((old/'frames.json').read_text())['frames'];newframes=json.loads((new/'frames.json').read_text())['frames']
assert len(oldframes)==len(newframes)==1260
oldposes=[f['p'] for f in oldframes];newposes=[f['p'] for f in newframes];assert oldposes==newposes,'Head/body/voice parameter timeline changed'
assert sha(old/'mesh.bin')==sha(new/'mesh.bin'),'Final mesh trajectory changed'
def wavhash(p):
 with wave.open(str(p),'rb') as w:return w.getparams()[:4],hashlib.sha256(w.readframes(w.getnframes())).hexdigest()
assert wavhash(old/'timeline-audio.wav')==wavhash(new/'timeline-audio.wav'),'Audio timeline changed'
out=D/'comparison-frames';out.mkdir(exist_ok=True);font=ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',24,index=0)
times=[6,6.5,7,12,12.5,13];sheet=Image.new('RGB',(6*384,2*402+64),'#f5ecdf');draw=ImageDraw.Draw(sheet)
draw.text((15,12),'同じ時刻・同じ姿勢・同じ音声で比較  /  上：v15 修正前  /  下：v16 修正後',font=font,fill='#664a35')
for row,(tag,video) in enumerate([('v15',before),('v16',after)]):
 for i,t in enumerate(times):
  target=out/f'{tag}-{t:04.1f}s.png';subprocess.run(['ffmpeg','-v','error','-y','-ss',str(t),'-i',str(video),'-frames:v','1',str(target)],check=True)
  im=Image.open(target).convert('RGB');crop=im.crop((1138,430,1522,786));x=i*384;y=64+row*402
  sheet.paste(crop,(x,y+40));draw.text((x+12,y+5),f'{tag}  {t:.1f}s',font=font,fill='#664a35')
sheet.save(D/'koma-v16-sameframe-before-after.png')
# Mouth-only crop is selected identically in both versions, not retargeted to hide defects.
mouth=Image.new('RGB',(6*384,2*202+64),'#f5ecdf');draw=ImageDraw.Draw(mouth);draw.text((15,12),'口元拡大・同一領域  /  上：修正前  /  下：修正後',font=font,fill='#664a35')
for row,tag in enumerate(['v15','v16']):
 for i,t in enumerate(times):
  im=Image.open(out/f'{tag}-{t:04.1f}s.png').convert('RGB');crop=im.crop((1273,600,1453,676)).resize((384,162),Image.Resampling.LANCZOS);x=i*384;y=64+row*202
  mouth.paste(crop,(x,y+40));draw.text((x+12,y+4),f'{tag}  {t:.1f}s',font=font,fill='#664a35')
mouth.save(D/'koma-v16-mouth-before-after.png')
result={'frame_count':1260,'all_pose_arrays_exactly_identical':True,'mesh_sha256_identical':sha(new/'mesh.bin'),'audio_pcm_sha256_identical':wavhash(new/'timeline-audio.wav')[1],'before_video_sha256':sha(before),'after_video_sha256':sha(after),'sameframe_times_seconds':times,'fixed_face_crop':[1138,430,1522,786],'fixed_mouth_crop':[1273,600,1453,676],'note':'No reduction or removal of head/body motion; same42sec audio and poses. Only mouth rendering changed, plus title labels.'}
(D/'before-after-verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps(result,indent=2))

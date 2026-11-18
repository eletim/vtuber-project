from pathlib import Path
import hashlib,json,shutil,wave,array,subprocess,argparse
parser=argparse.ArgumentParser();parser.add_argument('--source',type=Path,required=True,help='Finalized VTuber repository root');args=parser.parse_args()
D=Path(__file__).resolve().parent;repo=args.source.resolve()
manifest=json.loads((repo/'runtime/model/model.json').read_text())
ids=['neutral','soft_smile','big_smile','worried','surprised','bashful','displeased','thinking']
assert {e['id'] for e in manifest.get('expressions',[])}==set(ids),'Final eight-expression manifest not ready'
files=[p for p in (repo/'runtime/web').rglob('*') if p.is_file()]+[p for p in (repo/'runtime/model').rglob('*') if p.is_file()]+[repo/'runtime/package.json',repo/'runtime/server.py']
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
hashes={str(p.relative_to(repo)):sha(p) for p in files}
for p in files:
 target=D/'source'/p.relative_to(repo);target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target)
assert hashes=={str(p.relative_to(repo)):sha(p) for p in files},'Runtime changed during snapshot; source must be refreshed when stable'
original=repo/'assets/parts/v13/koma-free-voice.wav';target=D/'source/assets/parts/v13/koma-free-voice.wav';target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(original,target)
assert sha(target)=='dd10f1395abb9dce388339e8cf4701911b637429e2174a77737ebd8058e7db7b','Saved voice differs from original approved sample'
with wave.open(str(target),'rb') as w:
 assert w.getframerate()==24000 and w.getnchannels()==1 and w.getsampwidth()==2
 raw=w.readframes(w.getnframes());samples=array.array('h',raw)
(D/'audio_samples.json').write_text(json.dumps([v/32768 for v in samples]))
timeline=array.array('h',[0])*(42*24000)
for start in [.5,10.5,20.5,30.5]:
 offset=round(start*24000);timeline[offset:offset+len(samples)]=samples
with wave.open(str(D/'timeline-audio.wav'),'wb') as w:w.setnchannels(1);w.setsampwidth(2);w.setframerate(24000);w.writeframes(timeline.tobytes())
provenance={'source_repo':str(repo),'source_head':subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip(),'worktree_status':subprocess.check_output(['git','-C',str(repo),'status','--short'],text=True),'file_sha256':hashes,'voice_sha256':sha(target),'method':'Unmodified runtime JS math; exact exported feature-strip geometry composited in premultiplied OpenGL framebuffer; not browser UI/E2E recording.'}
(D/'source-provenance.json').write_text(json.dumps(provenance,ensure_ascii=False,indent=2))
print('Snapshot ready,',len(files),'source files; eight expressions; original voice verified')

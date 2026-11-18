from pathlib import Path
import zipfile,hashlib,shutil,json
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT.parent/'delivery-v43';OUT.mkdir(exist_ok=True)
def info(p):return {'path':str(p.resolve()),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
files=[ROOT/'assets/parts/v43/runtime-face-final-review/koma-v43-face-directions-cfr.mp4',ROOT/'assets/parts/v43/performance-review/koma-v43-performance-sample.mp4',ROOT/'assets/parts/v43/performance-review/koma-v42-v43-performance-comparison.mp4',ROOT/'assets/parts/v43/sync-review/koma-v43-two-context-sync.mp4']
for p in files:shutil.copyfile(p,OUT/p.name)
changed=['runtime/web/renderer.js','runtime/web/face-angle-rig.js','runtime/web/acting-controller.js','runtime/model/model.json','docs/v43-face-directions.md']+[str(p.relative_to(ROOT)).replace('\\','/') for p in (ROOT/'runtime/model/face_angles_v43').glob('*.png')]
base=ROOT.parent/'delivery-v42/koma-v42-runtime.zip';target=OUT/'koma-v43-runtime.zip'
with zipfile.ZipFile(base) as src,zipfile.ZipFile(target,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as dst:
 for name in src.namelist():
  if name not in changed:dst.writestr(name,src.read(name))
 for name in changed:dst.write(ROOT/name,name)
with zipfile.ZipFile(target) as z:assert z.testzip() is None
# Preserve the complete archive and provide chunks below 20 MB for later transport.
parts=[]
with target.open('rb') as f:
 i=0
 while data:=f.read(18_000_000):
  i+=1;p=OUT/(target.name+f'.part{i:02d}');p.write_bytes(data);parts.append(info(p))
h=hashlib.sha256()
for part in parts:h.update(Path(part['path']).read_bytes())
assert h.hexdigest()==info(target)['sha256']
report={'videos':[info(OUT/p.name) for p in files],'runtime':info(target),'runtime_parts':parts,'psd':info(ROOT/'assets/parts/v43/koma_face_directions_v43.psd')}
(OUT/'package-artifacts.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps(report,ensure_ascii=False))

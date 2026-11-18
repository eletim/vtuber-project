"""Reuse reviewed motion only after proving all numerical inputs/helpers unchanged.
Useful for ownership-only artwork corrections; never bypasses new-art visual QA.
"""
from pathlib import Path
import argparse,json,hashlib,os,shutil,subprocess
D=Path(__file__).resolve().parent;p=argparse.ArgumentParser();p.add_argument('--from-directory',type=Path,required=True);a=p.parse_args();old=a.from_directory.resolve();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
helpers=['body-rig.js','performance.js','controls.js','expressions.js','render-plan.js'];checks={}
for f in helpers:
 one=old/'source/runtime/web'/f;two=D/'source/runtime/web'/f;assert sha(one)==sha(two),f;checks[f]=sha(two)
models=[json.loads((d/'source/runtime/model/model.json').read_text()) for d in [old,D]]
for k in ['size','mesh','skinning','bodyRig','bodySampling','expressions']:assert models[0][k]==models[1][k],k
assert sha(old/'source/runtime/model'/models[0]['skinning'])==sha(D/'source/runtime/model'/models[1]['skinning'])
face_files={p['file'] for e in models[1]['expressions'] for p in e['parts']}
for f in face_files:assert sha(old/'source/runtime/model'/f)==sha(D/'source/runtime/model'/f),f
assert sha(old/'timeline-audio.wav')==sha(D/'timeline-audio.wav')
for f in list(old.glob('mesh-*.bin'))+[old/'mouth-frames.rgba']:
 target=D/f.name
 if target.exists():assert sha(target)==sha(f),f.name
 else:os.link(f,target)
for f in ['frames.json','mesh-manifest.json','isolation-verification.json']:shutil.copy2(old/f,D/f)
# Re-export new crop/occlusion metadata through the actual frozen runtime helper.
js='''import fs from 'node:fs';import {pathToFileURL} from 'node:url';const d=process.argv[1],{bodyLayers,bodyTextureFile,bodyTextureRect,bodySamplingPlan}=await import(pathToFileURL(d+'/source/runtime/web/render-plan.js'));const m=JSON.parse(fs.readFileSync(d+'/source/runtime/model/model.json')),p=JSON.parse(fs.readFileSync(d+'/frames.json'));p.layers=bodyLayers(m).map(l=>({...l,textureRect:bodyTextureRect(l,m)}));p.sampling=bodySamplingPlan(m,900,1200);for(const f of p.frames){const e=m.expressions.find(e=>e.id===f.expressionFrame.id);f.layerFiles=p.layers.map(l=>bodyTextureFile(l,e,m));}fs.writeFileSync(d+'/frames.json',JSON.stringify(p));'''
subprocess.run(['node','--input-type=module','-e',js,str(D)],check=True)
from PIL import Image
plan=json.loads((D/'frames.json').read_text())
for layer in plan['layers']:
 for file in set([layer['file']]+list(layer.get('expressionFiles',{}).values())):assert Image.open(D/'source/runtime/model'/file).size==(layer['rect'][2]-layer['rect'][0],layer['rect'][3]-layer['rect'][1]),file
report=json.loads((D/'isolation-verification.json').read_text());report['layers']=plan['layers'];(D/'isolation-verification.json').write_text(json.dumps(report,indent=2))
(D/'motion-reuse.json').write_text(json.dumps({'passed':True,'from_directory':str(old),'helper_sha256':checks,'unchanged_model_fields':['size','mesh','skinning','bodyRig','bodySampling','expressions'],'unchanged_face_parts':len(face_files),'audio_identical':True,'layer_metadata':'Re-exported all current ordered bodyLayers, texture crops/files and sampling via the actual runtime render-plan helper; PNG crop dimensions validated.','method':'Reused exact chronological pose/mesh/mouth streams only after all imported numerical helpers, model input records, skinning values, face sprites and audio matched. New independently separated artwork is rendered and reviewed afresh.'},indent=2));print('Motion reuse invariants PASS')

#!/usr/bin/env python3
"""Build a self-contained-source runtime ZIP from pre-exported v15 artwork."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import zipfile
ROOT=Path(__file__).resolve().parents[1]

def build(destination, *, version='v15', guide='docs/expression-motion-v15.md', artwork_folder='assets/parts/v15'):
    destination=Path(destination);destination.mkdir(parents=True,exist_ok=True)
    stage=destination/f'koma-{version}-runtime'
    if stage.exists():
        raise RuntimeError(f'Refusing to overwrite existing bundle staging directory: {stage}')
    (stage/'runtime/vendor').mkdir(parents=True)
    (stage/'runtime/vendor/.keep').write_text('Pinned tracking dependencies are downloaded by scripts/run_runtime.py.\n')
    for name in ['web','model']:
        shutil.copytree(ROOT/'runtime'/name,stage/'runtime'/name)
    for name in ['server.py','voice.py','ai_client.py','vendor-manifest.json']:
        shutil.copy2(ROOT/'runtime'/name,stage/'runtime'/name)
    (stage/'scripts').mkdir()
    shutil.copy2(ROOT/'scripts/run_runtime.py',stage/'scripts/run_runtime.py')
    (stage/'samples').mkdir()
    shutil.copy2(ROOT/'assets/parts/v13/koma-free-voice.wav',stage/'samples/koma-free-voice.wav')
    (stage/'artwork_controls').mkdir()
    for name in ['Switch_Koma_Expression.jsx','使い方.txt','expression_motion_contact_sheet.png']:
        shutil.copy2(ROOT/artwork_folder/name,stage/'artwork_controls'/name)
    (stage/'requirements-runtime.txt').write_text('aiohttp>=3.10\n')
    shutil.copy2(ROOT/guide,stage/'README_日本語.md')
    model=json.loads((stage/'runtime/model/model.json').read_text())
    assert len(model.get('expressions',[]))==8,'Expected all eight expressions'
    references={model['base'],model['skinning']}
    for entry in [model]+model['expressions']:
        references.add(entry['base'])
        references.update(p['file'] for p in entry['parts'])
    for layer in model.get('bodyLayers',[]):
        references.add(layer['file'])
        references.update(layer.get('expressionFiles',{}).values())
    for name in references:
        p=(stage/'runtime/model'/name).resolve()
        assert p.is_relative_to((stage/'runtime/model').resolve())
        assert p.is_file(),f'Missing model file: {name}'
    records=[]
    for p in sorted(stage.rglob('*')):
        if p.is_file():records.append({'file':str(p.relative_to(stage)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size})
    (stage/'bundle_manifest.json').write_text(json.dumps({'version':version,'format':model['format'],'expressions':list(e['id'] for e in model['expressions']),'files':records},ensure_ascii=False,indent=2)+'\n')
    target=destination/f'koma-{version}-runtime.zip'
    with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for p in sorted(stage.rglob('*')):
            if p.is_file():z.write(p,p.relative_to(destination))
    with zipfile.ZipFile(target) as z:assert z.testzip() is None
    print(json.dumps({'zip':str(target),'bytes':target.stat().st_size,'files':len(records),'references_checked':len(references)},ensure_ascii=False))
    return target

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('destination',type=Path);args=p.parse_args();build(args.destination)

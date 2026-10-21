#!/usr/bin/env python3
"""Build a v20 runtime and two lossless delivery ZIPs; never include engine binaries."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import zipfile
from package_runtime_v15 import build
from split_runtime_bundle_v19 import split
ROOT=Path(__file__).resolve().parents[1]

def package(destination, evidence, version="v20", guide="docs/text-speech-v20.md"):
    destination=Path(destination);evidence=Path(evidence)
    archive=build(destination,version=version,guide=guide,artwork_folder='assets/parts/v19')
    stage=destination/f'koma-{version}-runtime'
    for old in (stage/'samples').iterdir():old.unlink()
    shutil.copy2(evidence/'koma-v20-runtime-fresh-voice.wav',stage/'samples/koma-v20-fresh-voice.wav')
    shutil.copy2(evidence/'runtime-fresh-speech-verification.json',stage/'samples/runtime-fresh-speech-verification.json')
    shutil.copy2(ROOT/'scripts/setup_voicevox.py',stage/'scripts/setup_voicevox.py')
    if version == 'v21':
        shutil.copy2(ROOT/'scripts/setup_local_model.py',stage/'scripts/setup_local_model.py')
    (stage/'requirements-voicevox-setup.txt').write_text('py7zr>=0.22\n')
    records=[]
    for p in sorted(stage.rglob('*')):
        if p.is_file() and p.name!='bundle_manifest.json':
            records.append({'file':str(p.relative_to(stage)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size})
    manifest=json.loads((stage/'bundle_manifest.json').read_text());manifest['files']=records
    (stage/'bundle_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as out:
        for p in sorted(stage.rglob('*')):
            if p.is_file():out.write(p,p.relative_to(destination))
    report=split(archive,version=version)
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('destination',type=Path);p.add_argument('--evidence',type=Path,required=True)
    args=p.parse_args();package(args.destination,args.evidence)

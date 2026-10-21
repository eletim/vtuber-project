#!/usr/bin/env python3
"""Require v18 to preserve every accepted artwork/model and facial renderer byte."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]
BASE='e70184fb6c5bc6fe33e1d0da0cd47f0fc2970415'
PATHS=['assets','runtime/model','runtime/web/expressions.js','runtime/web/renderer.js']

def verify():
    rows=subprocess.check_output(['git','-C',str(ROOT),'ls-tree','-r','-z',BASE,*PATHS]).split(b'\0')
    files=[]
    for row in rows:
        if not row:continue
        metadata,name=row.split(b'\t',1)
        _,kind,expected=metadata.split()
        if kind!=b'blob':continue
        path=name.decode(); data=(ROOT/path).read_bytes()
        actual=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
        assert actual==expected.decode(),f'Changed approved artwork/face implementation: {path}'
        files.append({'file':path,'git_blob':actual})
    return {'status':'PASS','baseline_commit':BASE,'preserved_file_count':len(files),
            'all_previous_artwork_and_psds_unchanged':True,'full_model_and_skinning_unchanged':True,
            'v17_mouth_skin_correction_unchanged':True,'expression_helper_and_renderer_unchanged':True,
            'new_psd_required':False,'files':files}

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path)
    args=parser.parse_args();result=verify()
    if args.output:args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='files'},indent=2))

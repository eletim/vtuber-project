#!/usr/bin/env python3
"""Verify every original painted asset and runtime function survives the v17 fix."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]
BASE='78ede7b68d5729915f8916582973fb385bbfec05'

def git(*args):
    return subprocess.check_output(['git','-C',str(ROOT),*args])

def verify():
    preserved=[]
    for row in git('ls-tree','-r','-z',BASE,'assets','runtime/model','runtime/web').split(b'\0'):
        if not row:continue
        metadata,name=row.split(b'\t',1);_,kind,expected=metadata.split()
        if kind!=b'blob':continue
        path=name.decode()
        if path=='runtime/model/model.json':continue
        actual=git('hash-object',str(ROOT/path)).strip()
        assert actual==expected,f'Changed original asset/function: {path}'
        preserved.append({'file':path,'git_blob':actual.decode()})
    before=json.loads(git('show',BASE+':runtime/model/model.json'))
    after=json.loads((ROOT/'runtime/model/model.json').read_text())
    expected=json.loads(json.dumps(before))
    expected['expression_source_psd']='assets/parts/v17/koma_expression_skin_v17.psd'
    expression=next(e for e in expected['expressions'] if e['id']=='surprised')
    part=next(p for p in expression['parts'] if p['parameter']=='ParamMouthOpenY' and p['state']=='closed')
    part['file']='expressions/surprised/mouth_closed_skin_v17.png'
    assert after==expected,'Manifest changed beyond the two intended file references'
    return {'status':'PASS','baseline_commit':BASE,'preserved_file_count':len(preserved),
            'all_original_artwork_files_unchanged':True,'all_runtime_functions_unchanged':True,
            'neutral_original_pixels_unchanged':True,'model_manifest_only_two_file_references_changed':True,
            'new_sprite_sha256':hashlib.sha256((ROOT/'runtime/model'/part['file']).read_bytes()).hexdigest(),
            'files':preserved}

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path);args=parser.parse_args()
    result=verify()
    if args.output:args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='files'},ensure_ascii=False,indent=2))

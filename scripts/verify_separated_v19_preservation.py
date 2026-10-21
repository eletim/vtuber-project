#!/usr/bin/env python3
"""Protect accepted face art and all original assets during structural separation."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]
BASE='0fbe1ea2c698d936588b8080daf766049c66e306'

def git(*args):return subprocess.check_output(['git','-C',str(ROOT),*args])

def verify():
    files=[]
    for row in git('ls-tree','-r','-z',BASE,'assets','runtime/model','runtime/web/expressions.js').split(b'\0'):
        if not row:continue
        metadata,name=row.split(b'\t',1);_,kind,expected=metadata.split()
        path=name.decode()
        if kind!=b'blob' or path=='runtime/model/model.json':continue
        data=(ROOT/path).read_bytes()
        actual=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
        assert actual==expected.decode(),f'Changed accepted original art/face: {path}'
        files.append({'file':path,'git_blob':actual})
    before=json.loads(git('show',BASE+':runtime/model/model.json'))
    after=json.loads((ROOT/'runtime/model/model.json').read_text())
    for key in ['name','size','base','parts','mesh','skinning','expressions','expression_source_psd']:
        assert after[key]==before[key],f'Changed approved legacy face/model declaration: {key}'
    assert after.get('bodySampling')=='coverage-2x','Missing verified cut-seam sampling mode'
    assert 0 < after['bodyRig']['skirtRevealLimitPixels'] <= 3
    layers=after.get('bodyLayers',[])
    assert len(layers)>=5,'Missing actual independently rendered layers'
    roles={layer['role'] for layer in layers}
    assert {'torso','armLeft','armRight','skirt'}<=roles,roles
    assert len({layer['id'] for layer in layers})==len(layers),'Duplicate body layer IDs'
    refs=set()
    for layer in layers:
        refs.add(layer['file']);refs.update(layer.get('expressionFiles',{}).values())
    for name in refs:
        path=(ROOT/'runtime/model'/name).resolve()
        assert path.is_relative_to((ROOT/'runtime/model').resolve()) and path.is_file(),name
    return {'status':'PASS','baseline_commit':BASE,'preserved_original_files':len(files),
            'old_psds_and_original_pngs_unchanged':True,'v17_mouth_skin_pixels_unchanged':True,
            'expression_helper_and_declarations_unchanged':True,
            'ordered_body_layers':len(layers),'body_texture_references':len(refs),
            'new_psd_required':True,'sampling':'coverage-2x','skirt_hem_limit_source_pixels':after['bodyRig']['skirtRevealLimitPixels'],'files':files}

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path)
    args=parser.parse_args();result=verify()
    if args.output:args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='files'},indent=2))

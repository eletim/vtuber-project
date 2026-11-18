#!/usr/bin/env python3
"""Opt-in official llama.cpp CPU + Qwen3 model installer (about 1.85 GB).

Local project files only: no account, API key, service, sudo or system settings.
Run only when installing this free local engine/model is wanted and authorized.
"""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import tarfile
from urllib.request import urlretrieve
ROOT=Path(__file__).resolve().parents[1]
BUILD='b11669'
MODEL_REVISION='90862c4b9d2787eaed51d12237eafdfe7c5f6077'
SOURCES={
 'engine':{'url':f'https://github.com/ggml-org/llama.cpp/releases/download/{BUILD}/llama-{BUILD}-bin-ubuntu-x64.tar.gz',
           'sha256':'cf07c1c112d709bd67e522017471de57ed0ec8bea031d732c5422351c07f65ac',
           'bytes':17851611,'filename':f'llama-{BUILD}-bin-ubuntu-x64.tar.gz'},
 'model':{'url':f'https://huggingface.co/Qwen/Qwen3-1.7B-GGUF/resolve/{MODEL_REVISION}/Qwen3-1.7B-Q8_0.gguf',
          'sha256':'061b54daade076b5d3362dac252678d17da8c68f07560be70818cace6590cb1a',
          'bytes':1834426016,'filename':'Qwen3-1.7B-Q8_0.gguf'}}

def sha256(path):
    digest=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):digest.update(chunk)
    return digest.hexdigest()

def fetch(source,target):
    if target.is_file() and target.stat().st_size==source['bytes'] and sha256(target)==source['sha256']:
        print('Verified existing',target.name,flush=True);return
    temporary=target.with_suffix(target.suffix+'.download')
    last=[-1]
    def progress(block,size,total):
        amount=block*size//(64*1024*1024)
        if amount!=last[0]:
            last[0]=amount;print(target.name, min(block*size,total), '/', total, 'bytes',flush=True)
    urlretrieve(source['url'],temporary,progress)
    if temporary.stat().st_size!=source['bytes'] or sha256(temporary)!=source['sha256']:
        temporary.unlink(missing_ok=True)
        raise RuntimeError('Official download size/SHA256 mismatch: '+target.name)
    temporary.replace(target)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--show-plan',action='store_true',help='Print pinned sources only; no downloads or writes')
    args=parser.parse_args()
    if args.show_plan:
        print(json.dumps(SOURCES,indent=2));return
    if platform.system()!='Linux' or platform.machine() not in ('x86_64','AMD64'):
        raise SystemExit('This installer is Linux x64 only. Use an existing local llama.cpp server on other platforms.')
    target=ROOT/'runtime/vendor/llamacpp';target.mkdir(parents=True,exist_ok=True)
    for source in SOURCES.values():fetch(source,target/source['filename'])
    archive=target/SOURCES['engine']['filename']
    # Python data filter rejects absolute/escaping links and special files.
    with tarfile.open(archive,'r:gz') as package:
        package.extractall(target,filter='data')
    binary=target/f'llama-{BUILD}/llama-server'
    if not binary.is_file():raise RuntimeError('Unexpected official archive layout; do not guess or execute another file')
    binary.chmod(binary.stat().st_mode|0o100)
    (target/'install-provenance.json').write_text(json.dumps({'build':BUILD,'model_revision':MODEL_REVISION,'sources':SOURCES,'account_or_key_created':False},indent=2)+'\n')
    print('Installed local files; no engine started. Binary:',binary)
    print('Model:',target/SOURCES['model']['filename'])

if __name__=='__main__':main()

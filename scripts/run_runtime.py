#!/usr/bin/env python3
"""Fetch pinned face-tracking dependencies once, then run Koma locally."""
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from urllib.request import urlretrieve
ROOT=Path(__file__).resolve().parents[1]


def prepare():
    for item in json.loads((ROOT/'runtime/vendor-manifest.json').read_text()):
        path=ROOT/'runtime/vendor'/item['path']
        if path.exists() and hashlib.sha256(path.read_bytes()).hexdigest()==item['sha256']:
            continue
        path.parent.mkdir(parents=True,exist_ok=True)
        temporary=path.with_suffix(path.suffix+'.download')
        print('Downloading',item['path'],flush=True)
        urlretrieve(item['url'],temporary)
        if hashlib.sha256(temporary.read_bytes()).hexdigest()!=item['sha256']:
            temporary.unlink()
            raise RuntimeError('Dependency checksum mismatch: '+item['path'])
        temporary.replace(path)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port',type=int,default=8766)
    parser.add_argument('--prepare-only',action='store_true')
    args=parser.parse_args()
    prepare()
    if not args.prepare_only:
        raise SystemExit(subprocess.call([sys.executable,str(ROOT/'runtime/server.py'),'--port',str(args.port)]))

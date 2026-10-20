#!/usr/bin/env python3
"""Fetch pinned face-tracking dependencies once, then run Koma locally."""
import argparse
import hashlib
import json
import subprocess
import sys
import time
from urllib.request import urlopen
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
    parser.add_argument('--voicevox',action='store_true',help='Start the Linux engine installed by setup_voicevox.py')
    parser.add_argument('--voicevox-engine',type=Path,help='Start an existing VOICEVOX engine executable')
    args=parser.parse_args()
    prepare()
    if not args.prepare_only:
        engine=None
        try:
            executable=args.voicevox_engine or (ROOT/'runtime/vendor/voicevox/linux-cpu-x64/run' if args.voicevox else None)
            if executable:
                engine=subprocess.Popen([str(executable.resolve()),'--host','127.0.0.1','--port','50021','--cpu_num_threads','2'])
                for _ in range(300):
                    if engine.poll() is not None:
                        raise RuntimeError('VOICEVOX failed to start')
                    try:
                        with urlopen('http://127.0.0.1:50021/version',timeout=1):break
                    except OSError:time.sleep(.2)
                else:raise RuntimeError('VOICEVOX startup timeout')
            raise SystemExit(subprocess.call([sys.executable,str(ROOT/'runtime/server.py'),'--port',str(args.port)]))
        finally:
            if engine:
                engine.terminate()
                try:engine.wait(timeout=5)
                except subprocess.TimeoutExpired:engine.kill()

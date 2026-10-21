#!/usr/bin/env python3
"""Fetch pinned face-tracking dependencies once, then run Koma locally."""
import argparse
import hashlib
import json
import os
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


def local_model_environment(prefix):
    # No inherited API keys, remote tools/MCP, model flags or proxy settings.
    env={key:os.environ[key] for key in ('PATH','LANG','LC_ALL','TMPDIR') if key in os.environ}
    home=Path(prefix)/'local-home';home.mkdir(exist_ok=True)
    env['HOME']=str(home)
    return env


def wait_ready(process, url, label):
    for _ in range(450):
        if process.poll() is not None:
            raise RuntimeError(label+' failed to start; see its log above')
        try:
            with urlopen(url,timeout=1):return
        except OSError:time.sleep(.2)
    raise RuntimeError(label+' startup timeout')


def stop_owned(process):
    if process is None or process.poll() is not None:return
    process.terminate()
    try:process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill();process.wait()


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port',type=int,default=8766)
    parser.add_argument('--prepare-only',action='store_true')
    parser.add_argument('--text-only',action='store_true',help='Skip camera dependency downloads; text speech and avatar rendering still work')
    parser.add_argument('--voicevox',action='store_true',help='Start the Linux engine installed by setup_voicevox.py')
    parser.add_argument('--voicevox-engine',type=Path,help='Start an existing VOICEVOX engine executable')
    parser.add_argument('--local-model',action='store_true',help='Start the optional official local model installed by setup_local_model.py (no downloads)')
    args=parser.parse_args()
    if not args.text_only:
        prepare()
    if not args.prepare_only:
        engine=None;model_engine=None;server=None
        try:
            runtime_env=os.environ.copy()
            executable=args.voicevox_engine or (ROOT/'runtime/vendor/voicevox/linux-cpu-x64/run' if args.voicevox else None)
            if executable:
                env = os.environ.copy()
                for name, folder in (('XDG_DATA_HOME','user-data'),('XDG_CONFIG_HOME','user-config'),('XDG_CACHE_HOME','user-cache')):
                    env[name] = str(ROOT/'runtime/vendor/voicevox'/folder)
                engine=subprocess.Popen([str(executable.resolve()),'--host','127.0.0.1','--port','50021','--cpu_num_threads','2'],env=env)
                wait_ready(engine,'http://127.0.0.1:50021/version','VOICEVOX')
            if args.local_model:
                prefix=ROOT/'runtime/vendor/llamacpp'
                binary=prefix/'llama-b11669/llama-server'
                model=prefix/'Qwen3-1.7B-Q8_0.gguf'
                if not binary.is_file() or not model.is_file():
                    raise RuntimeError('Optional local model is not installed. See docs/local-conversation-v21.md; nothing was downloaded automatically.')
                model_env=local_model_environment(prefix)
                model_engine=subprocess.Popen([str(binary),'-m',str(model),'--offline','--host','127.0.0.1','--port','8081',
                    '--alias','koma-qwen3-1.7b','--device','none','--gpu-layers','0','--ctx-size','4096',
                    '--threads','4','--threads-batch','4','--parallel','1','--no-webui','--no-agent',
                    '--cors-origins','localhost','--reasoning','off','--chat-template-kwargs','{"enable_thinking":false}'],env=model_env)
                wait_ready(model_engine,'http://127.0.0.1:8081/health','llama.cpp')
                runtime_env.update(KOMA_LLM_PROVIDER='llamacpp',KOMA_LLM_URL='http://127.0.0.1:8081',KOMA_LLM_MODEL='koma-qwen3-1.7b')
            server=subprocess.Popen([sys.executable,str(ROOT/'runtime/server.py'),'--port',str(args.port)],env=runtime_env)
            raise SystemExit(server.wait())
        except KeyboardInterrupt:
            print('Stopping local runtime and only the engines started by this command.')
        finally:
            stop_owned(server);stop_owned(model_engine);stop_owned(engine)

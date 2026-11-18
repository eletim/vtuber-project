#!/usr/bin/env python3
"""Run real engine and runtime in one session; verify fresh speech through HTTP/WS.
No browser, microphone, stored WAV fallback, or third-party API is used.
"""
import argparse
import asyncio
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from datetime import datetime, timezone
import aiohttp
from aiohttp import web
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'runtime'))
from server import create_app
from voice import Voicevox, validate_wav
TEXT='こんにちは、羽月こまです。今入力してもらった文章から、新しく声を作っています。声に合わせて、表情や腕も動かしますね。'

async def verify(out):
    provider=Voicevox()
    for _ in range(120):
        health=await provider.status()
        if health['available']: break
        await asyncio.sleep(.5)
    else: raise RuntimeError(health['message'])
    runner=web.AppRunner(create_app(provider));await runner.setup()
    site=web.TCPSite(runner,'127.0.0.1',0);await site.start()
    url='http://127.0.0.1:'+str(site._server.sockets[0].getsockname()[1])
    started=time.monotonic()
    try:
        async with aiohttp.ClientSession() as s:
            async def post(path,data):
                async with s.post(url+path,json=data) as r:
                    payload=await r.text()
                    assert r.status==200,(r.status,payload)
                    return json.loads(payload)
            async with s.ws_connect(url+'/ws?role=controller') as ws, s.ws_connect(url+'/ws?role=overlay') as overlay:
                await ws.receive_json();await overlay.receive_json()
                await post('/api/mode',{'mode':'ai'})
                for peer in (ws,overlay):
                    assert (await peer.receive_json())['reason']=='mode_change'
                    await peer.receive_json()
                event=await post('/api/speech',{'text':TEXT,'request_id':'v20-fresh-verification','emotion':'happy'})
                states=[]
                for peer,playing in ((ws,True),(overlay,False)):
                    cancelled=await peer.receive_json();assert cancelled['reason']=='superseded'
                    pending=await peer.receive_json();assert pending['speech']['phase']=='synthesizing'
                    ready=await peer.receive_json();assert ready['type']=='speech' and ready['play'] is playing
                    assert ready['request_id']==event['request_id'] and ready['text']==TEXT
                    states.append({'role':'controller' if playing else 'overlay','play':ready['play']})
                async with s.get(url+event['url']) as r:
                    assert r.status==200;wav=await r.read()
                duration=validate_wav(wav)
                (out/'koma-v20-runtime-fresh-voice.wav').write_bytes(wav)
                (out/'fresh-voice-text.txt').write_text(TEXT+'\n',encoding='utf-8')
                base={'clip_id':event['clip_id'],'position':0,'sequence':0,'state':'playing'}
                playing=await post('/api/playback',base)
                assert playing['emotion']=='happy'
                async with s.get(url+'/api/state') as r: state=await r.json()
                assert state['expression']['id']=='soft_smile' and state['expression']['owner']=='speech'
                paused=await post('/api/playback',{**base,'state':'paused','position':1,'sequence':1})
                assert paused['emotion']=='neutral'
                await post('/api/playback',{**base,'position':1,'sequence':2})
                await post('/api/speech/cancel',{'request_id':event['request_id']})
                async with s.post(url+'/api/playback',json={**base,'sequence':3}) as r: assert r.status==409
                async with s.get(url+'/api/state') as r: final=await r.json()
                assert final['mode']=='ai' and final['speech']['phase']=='idle'
                assert final['expression']['id']=='neutral' and final['parameters']['ParamMouthOpenY']==0
                report={'verified_at_utc':datetime.now(timezone.utc).isoformat(),'freshly_synthesized':True,
                        'input_text':TEXT,'provider':health,'duration_seconds':duration,'wav_bytes':len(wav),
                        'wav_sha256':hashlib.sha256(wav).hexdigest(),'elapsed_seconds':time.monotonic()-started,
                        'controller_and_overlay':states,'play_pause_resume_stop':'pass','stale_playback_after_stop':409,
                        'expression_during_playback':'soft_smile','final_mode':'ai','final_speech':'idle',
                        'scope':'Actual local VOICEVOX -> runtime HTTP/WS -> downloaded PCM. Playback status is exercised by HTTP. Browser audio output and GUI E2E are not claimed.'}
                (out/'runtime-fresh-speech-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
                print(json.dumps(report,ensure_ascii=False,indent=2))
    finally: await runner.cleanup()

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--engine',type=Path,default=ROOT/'runtime/vendor/voicevox/linux-cpu-x64/run')
    args=p.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    env=os.environ.copy()
    for key,folder in [('XDG_DATA_HOME','user-data'),('XDG_CONFIG_HOME','user-config'),('XDG_CACHE_HOME','user-cache')]:
        env[key] = str(ROOT/'runtime/vendor/voicevox'/folder)
    with (args.output/'runtime-voicevox-engine.log').open('w') as log:
        engine=subprocess.Popen([str(args.engine.resolve()),'--host','127.0.0.1','--port','50021','--cpu_num_threads','4','--output_log_utf8'],env=env,stdout=log,stderr=subprocess.STDOUT)
        try: asyncio.run(verify(args.output))
        finally:
            engine.terminate()
            try:engine.wait(timeout=5)
            except subprocess.TimeoutExpired:engine.kill();engine.wait()

if __name__=='__main__':main()

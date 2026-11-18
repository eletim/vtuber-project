#!/usr/bin/env python3
"""Verify v20 ZIP bytes, model preservation, fresh sample and packaged API."""
import argparse
import asyncio
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import zipfile
from aiohttp.test_utils import TestClient, TestServer

async def verify(bundle):
    with tempfile.TemporaryDirectory(prefix='koma-v20-verify-') as temporary:
        root=Path(temporary)
        with zipfile.ZipFile(bundle) as archive:
            assert archive.testzip() is None
            assert all(not n.startswith('/') and '..' not in Path(n).parts for n in archive.namelist())
            archive.extractall(root)
        stage=next(root.iterdir());manifest=json.loads((stage/'bundle_manifest.json').read_text())
        for row in manifest['files']:
            data=(stage/row['file']).read_bytes()
            assert hashlib.sha256(data).hexdigest()==row['sha256'],row['file']
        sys.path.insert(0,str(stage/'runtime'))
        spec=importlib.util.spec_from_file_location('bundle_v20_server',stage/'runtime/server.py')
        server=importlib.util.module_from_spec(spec);spec.loader.exec_module(server)
        from voice import validate_wav
        wav=(stage/'samples/koma-v20-fresh-voice.wav').read_bytes()
        proof=json.loads((stage/'samples/runtime-fresh-speech-verification.json').read_text())
        assert hashlib.sha256(wav).hexdigest()==proof['wav_sha256']
        assert proof['freshly_synthesized'] is True
        duration=validate_wav(wav)
        class Voice:
            credit='VOICEVOX:雨晴はう'
            async def status(self):return {'available':True,'provider':'VOICEVOX','version':'fixture'}
            async def synthesize(self,text):return wav
        async with TestClient(TestServer(server.create_app(Voice()))) as client:
            page=await client.get('/');assert page.status==200
            assert '音声停止' in await page.text()
            for path in ['/web/app.js','/web/renderer.js','/model/model.json']:
                assert (await client.get(path)).status==200
            assert (await (await client.get('/api/voice')).json())['available']
            await client.post('/api/mode',json={'mode':'ai'})
            r=await client.post('/api/speech',json={'text':'検証用','request_id':'bundle-check'});assert r.status==200
            event=await r.json();assert event['duration']==duration
            assert (await client.get(event['url'])).status==200
            assert (await client.post('/api/speech/cancel',json={'request_id':'bundle-check'})).status==200
            assert (await client.post('/api/playback',json={'clip_id':event['clip_id'],'state':'playing','position':0,'sequence':0})).status==409
        model=json.loads((stage/'runtime/model/model.json').read_text())
        assert model['bodySampling']=='coverage-2x'
        assert {'torso','armLeft','armRight','skirt','head'}<={layer['role'] for layer in model['bodyLayers']}
        assert len(model['expressions'])==8
        assert (stage/'scripts/setup_voicevox.py').is_file()
        return {'status':'PASS','files_hash_verified':len(manifest['files']),
                'sample_duration_seconds':duration,'sample_sha256':hashlib.sha256(wav).hexdigest(),
                'packaged_static_assets_and_health_speech_stop_api':'PASS (fixture provider)',
                'actual_engine_evidence':'samples/runtime-fresh-speech-verification.json',
                'separated_v19_model_roles':sorted({layer['role'] for layer in model['bodyLayers']}),
                'browser_e2e':'NOT RUN; no permitted browser path'}
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('bundle',type=Path);p.add_argument('--output',type=Path)
    args=p.parse_args();report=asyncio.run(verify(args.bundle));text=json.dumps(report,ensure_ascii=False,indent=2)+'\n'
    if args.output:args.output.write_text(text)
    print(text,end='')

#!/usr/bin/env python3
"""Validate the delivered ZIP and its HTTP/API routes, without a browser."""
import argparse
import asyncio
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import wave
import zipfile

from aiohttp.test_utils import TestClient, TestServer


async def verify(bundle):
    with tempfile.TemporaryDirectory(prefix='koma-v15-bundle-') as temporary:
        with zipfile.ZipFile(bundle) as archive:
            assert archive.testzip() is None
            for name in archive.namelist():
                assert not Path(name).is_absolute() and '..' not in Path(name).parts
            archive.extractall(temporary)
        stage=Path(temporary)/'koma-v15-runtime'
        manifest=json.loads((stage/'bundle_manifest.json').read_text())
        for record in manifest['files']:
            file=stage/record['file']
            assert file.stat().st_size==record['bytes']
            assert hashlib.sha256(file.read_bytes()).hexdigest()==record['sha256']
        sys.path.insert(0,str(stage/'runtime'))
        spec=importlib.util.spec_from_file_location('koma_bundle_server',stage/'runtime/server.py')
        server=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(server)
        async with TestClient(TestServer(server.create_app())) as client:
            response=await client.get('/')
            assert response.status==200 and 'id="expression"' in await response.text()
            response=await client.get('/model/model.json')
            assert response.status==200
            model=await response.json()
            assert len(model['expressions'])==8
            files={model['base'],model['skinning']}
            for expression in model['expressions']:
                files.add(expression['base'])
                files.update(part['file'] for part in expression['parts'])
                response=await client.post('/api/expression',json={
                    'source':'human','expression':expression['id'],'duration':30})
                assert response.status==200
                assert (await response.json())['id']==expression['id']
            for file in sorted(files):
                response=await client.get('/model/'+file)
                assert response.status==200, file
                assert await response.read()==(stage/'runtime/model'/file).read_bytes()
            response=await client.post('/api/mode',json={'mode':'ai'})
            assert response.status==200
            assert (await response.json())['expression']['id']=='neutral'
        with wave.open(str(stage/'samples/koma-free-voice.wav')) as audio:
            assert audio.getnchannels()==1 and audio.getframerate()==24000
            duration=audio.getnframes()/audio.getframerate()
        return {'status':'PASS','bundle':Path(bundle).name,
                'sha256':hashlib.sha256(Path(bundle).read_bytes()).hexdigest(),
                'file_hashes_verified':len(manifest['files']),
                'model_http_assets_verified':len(files),'expression_api_states_verified':8,
                'reset_to_neutral':True,'voice_duration_seconds':duration,
                'limitations':'HTTP/API and archive verification only; no browser/WebGL/camera/microphone/Photoshop E2E.'}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('bundle',type=Path)
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    report=asyncio.run(verify(args.bundle))
    text=json.dumps(report,ensure_ascii=False,indent=2)+'\n'
    if args.output:
        args.output.write_text(text)
    print(text,end='')

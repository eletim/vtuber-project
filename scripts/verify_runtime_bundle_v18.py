#!/usr/bin/env python3
"""Verify a v18 ZIP, all model routes, and four new body-control API channels."""
import argparse
import asyncio
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import zipfile

from aiohttp.test_utils import TestClient, TestServer
from verify_runtime_bundle_v15 import verify as verify_art_bundle

PARAMETERS=('ParamArmLOpen','ParamArmROpen','ParamShoulderY','ParamBodyShiftX')

async def verify(bundle):
    report=await verify_art_bundle(bundle)
    with tempfile.TemporaryDirectory(prefix='koma-v18-controls-') as temporary:
        with zipfile.ZipFile(bundle) as archive:archive.extractall(temporary)
        stage=next(Path(temporary).iterdir())
        sys.path.insert(0,str(stage/'runtime'))
        spec=importlib.util.spec_from_file_location('koma_v18_bundle_server',stage/'runtime/server.py')
        server=importlib.util.module_from_spec(spec);spec.loader.exec_module(server)
        async with TestClient(TestServer(server.create_app())) as client:
            for source in ['human','ai']:
                response=await client.post('/api/mode',json={'mode':source})
                assert response.status==200
                state=await response.json()
                assert all(state['parameters'][name]==0 for name in PARAMETERS)
                for value,expected in [(.65,.65),(-4,-1),(4,1)]:
                    response=await client.post('/api/control',json={
                        'source':source,'parameters':{name:value for name in PARAMETERS}})
                    assert response.status==200
                    state=await response.json()
                    assert all(state['parameters'][name]==expected for name in PARAMETERS)
                response=await client.post('/api/control',json={
                    'source':source,'parameters':{PARAMETERS[0]:True}})
                assert response.status==400
            response=await client.post('/api/performance',json={'enabled':False})
            assert response.status==200
            response=await client.post('/api/mode',json={'mode':'human'})
            assert response.status==200
            state=await response.json()
            assert all(state['parameters'][name]==0 for name in PARAMETERS)
    report.update({'body_parameter_ids':PARAMETERS,'both_control_modes_verified':True,
                   'body_parameter_clamps_and_validation_verified':True,
                   'body_parameters_reset_on_mode_change':True})
    return report

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('bundle',type=Path);parser.add_argument('--output',type=Path)
    args=parser.parse_args();report=asyncio.run(verify(args.bundle))
    text=json.dumps(report,ensure_ascii=False,indent=2)+'\n'
    if args.output:args.output.write_text(text)
    print(text,end='')

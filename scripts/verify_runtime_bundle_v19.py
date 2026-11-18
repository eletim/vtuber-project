#!/usr/bin/env python3
"""Verify a structural v19 ZIP, its layered assets, and isolated skirt control API."""
import argparse
import asyncio
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import zipfile

from aiohttp.test_utils import TestClient, TestServer
from verify_runtime_bundle_v18 import verify as verify_body_bundle

async def verify(bundle):
    report=await verify_body_bundle(bundle)
    with tempfile.TemporaryDirectory(prefix='koma-v19-controls-') as temporary:
        with zipfile.ZipFile(bundle) as archive:archive.extractall(temporary)
        stage=next(Path(temporary).iterdir())
        model=json.loads((stage/'runtime/model/model.json').read_text())
        assert model.get('bodySampling')=='coverage-2x'
        assert 0 < model['bodyRig']['skirtRevealLimitPixels'] <= 3
        layers=model['bodyLayers']
        assert len(layers)>=5
        assert {'torso','armLeft','armRight','skirt','head'}<={layer['role'] for layer in layers}
        assert sum(bool(layer.get('features')) for layer in layers)==1
        sys.path.insert(0,str(stage/'runtime'))
        spec=importlib.util.spec_from_file_location('koma_v19_bundle_server',stage/'runtime/server.py')
        server=importlib.util.module_from_spec(spec);spec.loader.exec_module(server)
        async with TestClient(TestServer(server.create_app())) as client:
            for source in ['human','ai']:
                response=await client.post('/api/mode',json={'mode':source})
                assert response.status==200
                state=await response.json();assert state['parameters']['ParamSkirtSway']==0
                for value,expected in [(.65,.65),(-4,-1),(4,1)]:
                    response=await client.post('/api/control',json={
                        'source':source,'parameters':{'ParamSkirtSway':value}})
                    assert response.status==200
                    state=await response.json();assert state['parameters']['ParamSkirtSway']==expected
                    assert state['parameters']['ParamArmLOpen']==0
                    assert state['parameters']['ParamArmROpen']==0
                response=await client.post('/api/control',json={
                    'source':source,'parameters':{'ParamSkirtSway':True}})
                assert response.status==400
            response=await client.post('/api/mode',json={'mode':'human'})
            state=await response.json();assert state['parameters']['ParamSkirtSway']==0
    report.update({'body_sampling':'coverage-2x','skirt_limit_source_pixels':model['bodyRig']['skirtRevealLimitPixels'],'body_layers':len(layers),'roles':sorted({layer['role'] for layer in layers}),
                   'skirt_control_modes_clamps_validation_and_reset_verified':True,
                   'skirt_control_does_not_set_arm_inputs':True})
    return report

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('bundle',type=Path);parser.add_argument('--output',type=Path)
    args=parser.parse_args();report=asyncio.run(verify(args.bundle))
    text=json.dumps(report,ensure_ascii=False,indent=2)+'\n'
    if args.output:args.output.write_text(text)
    print(text,end='')

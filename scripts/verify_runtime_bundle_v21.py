#!/usr/bin/env python3
"""Verify a v21 package is safely unconfigured, not a claim of actual AI inference."""
import argparse
import asyncio
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch
import zipfile
from aiohttp.test_utils import TestClient,TestServer
from verify_runtime_bundle_v20 import verify as verify_base

async def verify(bundle):
    report=await verify_base(bundle)
    with tempfile.TemporaryDirectory(prefix='koma-v21-package-') as temporary:
        with zipfile.ZipFile(bundle) as archive:archive.extractall(temporary)
        stage=next(Path(temporary).iterdir());sys.path.insert(0,str(stage/'runtime'))
        spec=importlib.util.spec_from_file_location('bundle_v21_server',stage/'runtime/server.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        with patch.dict('os.environ',{},clear=True):app=module.create_app()
        async with TestClient(TestServer(app)) as client:
            response=await client.get('/api/conversation');assert response.status==200
            status=await response.json();assert status['configured'] is False and status['available'] is False
            assert status['status']=='unconfigured'
            await client.post('/api/mode',json={'mode':'ai'})
            response=await client.post('/api/conversation',json={'text':'検証用','request_id':'unconfigured-check'})
            assert response.status==503 and '未設定' in await response.text()
            response=await client.post('/api/conversation/clear',json={});assert response.status==200
            assert (await response.json())['cleared'] is True
        assert (stage/'scripts/setup_local_model.py').is_file()
    report.update({'conversation_state':'UNCONFIGURED','unconfigured_status_no_generation_and_clear_api':'PASS',
                   'actual_model_inference':'NOT RUN; installation permission pending','runtime_installation':'Opt-in only; no bundled model or automatic download'})
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('bundle',type=Path);p.add_argument('--output',type=Path)
    args=p.parse_args();report=asyncio.run(verify(args.bundle));text=json.dumps(report,ensure_ascii=False,indent=2)+'\n'
    if args.output:args.output.write_text(text)
    print(text,end='')

#!/usr/bin/env python3
"""Install the pinned official Linux x64 CPU engine (1.8 GB download).
Requires: python -m pip install py7zr
Windows/macOS: install and start the official VOICEVOX desktop app instead.
"""
import hashlib
import os
from pathlib import Path
import platform
from urllib.request import urlretrieve
ROOT=Path(__file__).resolve().parents[1]
VERSION='0.25.2'
SHA256='bab016a966131b89bad398e7b898f8c742617dc80a7da49bf494cd07133dbc7a'
URL=f'https://github.com/VOICEVOX/voicevox_engine/releases/download/{VERSION}/voicevox_engine-linux-cpu-x64-{VERSION}.7z.001'

def main():
    if platform.system()!='Linux' or platform.machine() not in ('x86_64','AMD64'):
        raise SystemExit('Install the official VOICEVOX desktop app: https://voicevox.hiroshiba.jp/')
    import py7zr
    target=ROOT/'runtime/vendor/voicevox'
    target.mkdir(parents=True,exist_ok=True)
    archive=target/'engine.7z.001'
    if not archive.exists():
        print('Downloading official VOICEVOX CPU engine (1.8 GB)…',flush=True)
        urlretrieve(URL,archive)
    digest=hashlib.file_digest(archive.open('rb'),'sha256').hexdigest()
    if digest!=SHA256:
        archive.unlink()
        raise SystemExit('Checksum mismatch; archive deleted. Run again.')
    with py7zr.SevenZipFile(archive) as package:
        package.extractall(target)
    run=target/'linux-cpu-x64/run';os.chmod(run,0o755)
    print('Installed:',run)
    print('Start: python scripts/run_runtime.py --voicevox')

if __name__=='__main__':main()

#!/usr/bin/env python3
"""Verify v16 retains all delivered paint, PSDs, model assets and motion inputs."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BASE = 'd80adf55d7a35edec81b370431d44c6aa7f30677'


def git(*arguments):
    return subprocess.check_output(['git', '-C', str(ROOT), *arguments])


def verify(base=BASE):
    records = []
    rows = git('ls-tree', '-r', '-z', base, 'assets', 'runtime/model',
               'runtime/web/body-rig.js', 'runtime/web/performance.js',
               'runtime/web/controls.js').split(b'\0')
    for row in rows:
        if not row:
            continue
        metadata, encoded_path = row.split(b'\t', 1)
        _, kind, expected = metadata.split()
        if kind != b'blob':
            continue
        relative = encoded_path.decode()
        path = ROOT / relative
        assert path.is_file(), f'Missing preserved file: {relative}'
        actual = git('hash-object', str(path)).strip()
        assert actual == expected, f'Changed preserved file: {relative}'
        records.append({'file': relative, 'git_blob': actual.decode()})
    assert records, 'No preservation candidates found'
    return {
        'status': 'PASS', 'baseline_commit': base,
        'preserved_files': len(records),
        'scope': 'Every pre-existing assets/ and runtime/model/ file, plus body rig, performance and controls source.',
        'artwork_and_psd_unchanged': True,
        'neutral_authored_pixels_unchanged': True,
        'body_and_head_motion_source_unchanged': True,
        'psd_sha256': hashlib.sha256((ROOT / 'assets/parts/v15/koma_expression_motion_v15.psd').read_bytes()).hexdigest(),
        'files': records,
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', default=BASE)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    report = verify(args.base)
    text = json.dumps(report, ensure_ascii=False, indent=2) + '\n'
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text)
    print(json.dumps({key: value for key, value in report.items() if key != 'files'}, ensure_ascii=False, indent=2))

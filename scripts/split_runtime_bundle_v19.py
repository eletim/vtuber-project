#!/usr/bin/env python3
"""Split a verified v19 runtime ZIP without changing or omitting any payload."""
import argparse
import hashlib
import json
from pathlib import Path
import tempfile
import zipfile

LIMIT = 19_500_000

def split(bundle):
    bundle = Path(bundle)
    paths = {kind: bundle.with_name(f'koma-v19-runtime-{kind}.zip')
             for kind in ('core', 'model')}
    for path in paths.values():
        if path.exists():
            raise RuntimeError(f'Refusing to overwrite {path}')
    expected = {}
    with zipfile.ZipFile(bundle) as original:
        assert original.testzip() is None
        members = original.infolist()
        assert all(not p.filename.startswith('/') and '..' not in Path(p.filename).parts
                   for p in members)
        for kind, path in paths.items():
            with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as out:
                for info in members:
                    is_model = info.filename.startswith('koma-v19-runtime/runtime/model/')
                    if is_model != (kind == 'model'):
                        continue
                    data = original.read(info.filename)
                    expected[info.filename] = hashlib.sha256(data).hexdigest()
                    out.writestr(info, data, compress_type=zipfile.ZIP_DEFLATED,
                                 compresslevel=9)
            assert path.stat().st_size < LIMIT, (path, path.stat().st_size, LIMIT)
    with tempfile.TemporaryDirectory(prefix='koma-v19-two-zip-') as temporary:
        root = Path(temporary)
        seen = set()
        for path in paths.values():
            with zipfile.ZipFile(path) as archive:
                assert archive.testzip() is None
                assert not seen.intersection(archive.namelist()), 'Duplicate split member'
                seen.update(archive.namelist())
                archive.extractall(root)
        assert seen == set(expected)
        for name, sha in expected.items():
            assert hashlib.sha256((root / name).read_bytes()).hexdigest() == sha, name
        manifest = json.loads((root / 'koma-v19-runtime/bundle_manifest.json').read_text())
        for row in manifest['files']:
            data = (root / 'koma-v19-runtime' / row['file']).read_bytes()
            assert hashlib.sha256(data).hexdigest() == row['sha256'], row['file']
    report = {'status': 'PASS', 'source_zip_sha256': hashlib.sha256(bundle.read_bytes()).hexdigest(),
              'files_reconstructed_byte_identically': len(expected),
              'image_quality_and_source_files_unchanged': True,
              'maximum_attachment_bytes': LIMIT,
              'archives': [{'file': path.name, 'bytes': path.stat().st_size,
                            'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
                           for path in paths.values()]}
    bundle.with_name('split-bundle-verification.json').write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    bundle.with_name('実行ZIPの展開手順.txt').write_text(
        '羽月こま v19 実行版: 2つのZIPを組み合わせます\n\n'
        '1. koma-v19-runtime-core.zip と koma-v19-runtime-model.zip を両方保存します。\n'
        '2. 2つを同じ場所へ展開し、中の koma-v19-runtime フォルダーを統合してください。\n'
        '   フォルダー全体を置き換えず、中のファイルを追加します。\n'
        '3. runtime/model/model.json と scripts/run_runtime.py の両方があることを確認します。\n'
        '4. README_日本語.md に沿って起動します。\n\n'
        '画質の変更や素材の削除はありません。2つの展開後の全ファイルを完全版ZIPと照合済みです。\n'
        'PSDは別の編集用ファイルで、実行時には不要です。\n', encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return report

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('bundle', type=Path)
    split(parser.parse_args().bundle)

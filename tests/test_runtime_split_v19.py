"""Delivery splitting preserves every original byte without reducing artwork."""
import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('split_v19', ROOT / 'scripts/split_runtime_bundle_v19.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class RuntimeSplitV19Tests(unittest.TestCase):
    def test_two_archives_reconstruct_bytes_and_do_not_overwrite(self):
        payload = {'runtime/model/model.json': b'{"bodyLayers":[]}',
                   'runtime/model/body_v19/pixels.png': bytes(range(256)),
                   'scripts/run_runtime.py': b'print("ready")\n'}
        manifest = {'files': [{'file': name, 'sha256': hashlib.sha256(data).hexdigest()}
                              for name, data in payload.items()]}
        payload['bundle_manifest.json'] = json.dumps(manifest).encode()
        with tempfile.TemporaryDirectory() as temporary:
            bundle = Path(temporary) / 'koma-v19-runtime.zip'
            with zipfile.ZipFile(bundle, 'w') as archive:
                for name, data in payload.items():
                    archive.writestr('koma-v19-runtime/' + name, data)
            with contextlib.redirect_stdout(io.StringIO()):
                report = module.split(bundle)
            self.assertEqual(report['files_reconstructed_byte_identically'], len(payload))
            self.assertTrue(report['image_quality_and_source_files_unchanged'])
            with zipfile.ZipFile(bundle.with_name('koma-v19-runtime-model.zip')) as archive:
                self.assertTrue(all('/runtime/model/' in name for name in archive.namelist()))
            with self.assertRaises(RuntimeError):
                module.split(bundle)

    def test_unsafe_archive_path_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            bundle = Path(temporary) / 'unsafe.zip'
            with zipfile.ZipFile(bundle, 'w') as archive:
                archive.writestr('../escape.txt', b'no')
            with self.assertRaises(AssertionError):
                module.split(bundle)

if __name__ == '__main__':
    unittest.main()

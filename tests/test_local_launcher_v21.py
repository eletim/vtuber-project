"""No-download tests for the opt-in local model installation/launcher helpers."""
import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock,patch
ROOT=Path(__file__).resolve().parents[1]
def module(name,file):
    spec=importlib.util.spec_from_file_location(name,ROOT/'scripts'/file)
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result
setup=module('setup_local_test','setup_local_model.py')
run=module('run_local_test','run_runtime.py')

class LocalSetup(unittest.TestCase):
    def test_verified_existing_file_never_downloads(self):
        data=b'fixture'
        source={'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'url':'https://example.invalid/model'}
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'model.gguf';path.write_bytes(data)
            with patch.object(setup,'urlretrieve') as get:setup.fetch(source,path)
            get.assert_not_called()
    def test_checksum_failure_never_installs(self):
        source={'bytes':3,'sha256':'0'*64,'url':'https://example.invalid/model'}
        def fake(url,target,callback):Path(target).write_bytes(b'bad')
        with tempfile.TemporaryDirectory() as d:
            target=Path(d)/'model.gguf'
            with patch.object(setup,'urlretrieve',side_effect=fake):
                with self.assertRaises(RuntimeError):setup.fetch(source,target)
            self.assertFalse(target.exists());self.assertFalse(target.with_suffix('.gguf.download').exists())
    def test_official_pinned_sources(self):
        self.assertTrue(setup.SOURCES['engine']['url'].startswith('https://github.com/ggml-org/llama.cpp/releases/download/'))
        self.assertTrue(setup.SOURCES['model']['url'].startswith('https://huggingface.co/Qwen/Qwen3-1.7B-GGUF/resolve/'))
        self.assertEqual(len(setup.SOURCES['model']['sha256']),64)
    def test_model_process_does_not_inherit_credentials_or_remote_flags(self):
        with tempfile.TemporaryDirectory() as d:
            with patch.dict(run.os.environ, {'LLAMA_API_KEY':'fixture-not-a-key','HF_TOKEN':'fixture','MCP_CONFIG':'fixture','HTTP_PROXY':'fixture'}, clear=False):
                env=run.local_model_environment(Path(d))
            self.assertFalse(set(env)&{'LLAMA_API_KEY','HF_TOKEN','MCP_CONFIG','HTTP_PROXY'})
            self.assertEqual(env['HOME'],str(Path(d)/'local-home'))
    def test_failed_owned_process_is_detected(self):
        process=Mock();process.poll.return_value=1
        with self.assertRaisesRegex(RuntimeError,'failed to start'):run.wait_ready(process,'http://127.0.0.1:8081/health','fixture')
    def test_stop_only_owned_live_process(self):
        run.stop_owned(None)
        stopped=Mock();stopped.poll.return_value=0;run.stop_owned(stopped);stopped.terminate.assert_not_called()
        live=Mock();live.poll.return_value=None;run.stop_owned(live);live.terminate.assert_called_once();live.wait.assert_called_once_with(timeout=5)

if __name__=='__main__':unittest.main()

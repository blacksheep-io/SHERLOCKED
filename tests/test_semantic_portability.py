import json
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
from sherlocked.semantic import SemanticEncoder,SemanticUnavailable,REQUIRED_ASSETS,get_shared_encoder
from sherlocked.engine import Engine


class ModelFixture:
    def __init__(self,fail=False):
        self.calls=[]
        self.fail=fail
    def eval(self):
        return self
    def encode(self,texts,**kwargs):
        self.calls.append(texts)
        if self.fail:
            raise RuntimeError('simulated CUDA allocation failure')
        return np.tile(np.eye(384,dtype=np.float32)[0],(len(texts),1))


class SemanticPortabilityTests(unittest.TestCase):
    def test_model_assets_complete_and_missing_mode_never_downloads(self):
        with tempfile.TemporaryDirectory() as directory:
            encoder=SemanticEncoder()
            encoder.directory=Path(directory)
            (encoder.directory/'sherlocked_model.json').write_text(json.dumps(encoder.config))
            (encoder.directory/'model.safetensors').touch()
            self.assertFalse(encoder.status()['available'])
            self.assertIn('tokenizer.json',encoder.status()['missing_assets'])
            with patch.object(encoder,'download',side_effect=AssertionError('offline network attempt')):
                with self.assertRaises(SemanticUnavailable):
                    encoder.load()
            for asset in REQUIRED_ASSETS:
                path=encoder.directory/asset
                path.parent.mkdir(parents=True,exist_ok=True)
                path.touch()
            self.assertTrue(encoder.status()['available'])
            self.assertIs(encoder.download(),encoder)

    def test_singleton_across_engine_weight_changes_and_configurable_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            def resource(name):
                return Path(directory)/name
            with patch('sherlocked.semantic.resource_path',side_effect=resource):
                first=get_shared_encoder('cpu')
                self.assertIs(first,get_shared_encoder('cpu'))
                self.assertEqual(first.directory,Path(directory)/'models'/'multilingual-e5-small')
                self.assertEqual(first.cache_directory,Path(directory)/'cache'/'embeddings')
                rows=[{'report_id':'A','text':'a bicycle missing'}]
                a=Engine(rows,config={'device':'cpu','weights':{'tfidf':1}})
                b=Engine(rows,config={'device':'cpu','weights':{'bm25':1}})
                self.assertIs(a.semantic,b.semantic)
                self.assertIsNot(first,get_shared_encoder('cuda'))
                self.assertFalse(first.allow_download)
                self.assertTrue(get_shared_encoder('cpu',allow_download=True).allow_download)
                self.assertFalse(first.allow_download)

    def test_batched_duplicates_memory_and_disk_cache(self):
        with tempfile.TemporaryDirectory() as directory:
            encoder=SemanticEncoder('cpu')
            encoder.cache_directory=Path(directory)
            encoder.model=ModelFixture()
            with patch.object(encoder,'load',return_value=encoder):
                vectors=encoder.encode(['same','same','different'])
                self.assertEqual(vectors.shape,(3,384))
                self.assertEqual(len(encoder.model.calls[0]),2)
                encoder.encode(['same'])
                self.assertEqual(len(encoder.model.calls),1)
                self.assertEqual(encoder.cache_stats['memory_hits'],1)
                encoder.clear_memory_cache()
                encoder.encode(['same'])
                self.assertEqual(encoder.cache_stats['disk_hits'],1)
                encoder.clear_memory_cache()
                for path in Path(directory).glob('*.npy'):
                    path.write_bytes(b'corrupt cache fixture')
                encoder.encode(['same'])
                self.assertEqual(len(encoder.model.calls),2)
                self.assertEqual(encoder.cache_stats['invalid_disk_entries'],1)
                before=encoder._identity('same','query')
                encoder.config['max_length']=256
                self.assertNotEqual(before,encoder._identity('same','query'))

    def test_auto_fallback_same_model_and_explicit_cuda_failure(self):
        torch=types.SimpleNamespace(cuda=types.SimpleNamespace(is_available=lambda:True),set_num_threads=lambda n:None)
        attempts=[]
        def factory(path,device,**kwargs):
            attempts.append(device)
            if device=='cuda':
                raise RuntimeError('simulated GPU initialize failure')
            return ModelFixture()
        modules={'torch':torch,'sentence_transformers':types.SimpleNamespace(SentenceTransformer=factory)}
        with tempfile.TemporaryDirectory() as directory, patch.dict('sys.modules',modules):
            auto=SemanticEncoder('auto')
            auto.directory=Path(directory)
            with patch.object(auto,'status',return_value={'available':True}):
                auto.load()
            self.assertEqual(attempts,['cuda','cpu'])
            self.assertEqual(auto.device,'cpu')
            self.assertIn('CUDA initialization failed',auto.fallback_reason)
            self.assertEqual(auto.metadata['active_device'],'cpu')
            explicit=SemanticEncoder('cuda')
            explicit.directory=Path(directory)
            with patch.object(explicit,'status',return_value={'available':True}):
                with self.assertRaises(SemanticUnavailable):
                    explicit.load()
            self.assertIsNone(explicit.model)

    def test_cpu_auto_when_pytorch_cuda_unavailable(self):
        torch=types.SimpleNamespace(cuda=types.SimpleNamespace(is_available=lambda:False),set_num_threads=lambda n:None)
        calls=[]
        def factory(path,device,**kwargs):
            calls.append(device)
            return ModelFixture()
        with tempfile.TemporaryDirectory() as directory, patch.dict('sys.modules',{'torch':torch,'sentence_transformers':types.SimpleNamespace(SentenceTransformer=factory)}):
            encoder=SemanticEncoder('auto')
            encoder.directory=Path(directory)
            with patch.object(encoder,'status',return_value={'available':True}):
                encoder.load()
            self.assertEqual(calls,['cpu'])
            self.assertEqual(encoder.device,'cpu')


if __name__=='__main__':
    unittest.main()

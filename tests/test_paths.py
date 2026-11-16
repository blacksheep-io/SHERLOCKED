import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from sherlocked.paths import ROOT,resource_path,ensure_directories,portable_path
from sherlocked.runtime import save_export

class PathTests(unittest.TestCase):
    def test_paths_independent_of_working_directory(self):
        previous=Path.cwd()
        with tempfile.TemporaryDirectory() as directory:
            try:
                os.chdir(directory)
                self.assertEqual(resource_path('dataset'),ROOT/'data')
                self.assertEqual(portable_path(ROOT/'data/reports.jsonl'),'data/reports.jsonl')
            finally:
                os.chdir(previous)

    def test_external_directory_overrides_and_exports(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            with patch.dict(os.environ,{'SHERLOCKED_EXPORT_DIR':str(root/'exports'),'SHERLOCKED_DATABASE_PATH':str(root/'db'/'test.sqlite3')}):
                self.assertEqual(resource_path('database'),root/'db/test.sqlite3')
                first=save_export({'text':'বাংলা'},'evidence.json',{'device':'cpu'})
                second=save_export({'text':'বাংলা'},'evidence.json')
                self.assertNotEqual(first,second)
                self.assertEqual(json.loads(first.read_text(encoding='utf-8'))['text'],'বাংলা')
                self.assertTrue(first.with_name(first.name+'.metadata.json').exists())
                with self.assertRaises(ValueError): save_export({},'../escape.json')
                with self.assertRaises(ValueError): resource_path('unknown')

if __name__=='__main__': unittest.main()

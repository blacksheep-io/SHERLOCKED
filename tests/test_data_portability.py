"""Temporary-resource tests; canonical source data is never mutated."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from sherlocked.dataset import generate, load, write_dataset
from sherlocked.research_data import write_challenge
from sherlocked.storage import Store
from sherlocked.ingestion import validate_records
from sherlocked.evaluate import run
from sherlocked.experiments import run_experiment


class DataPortabilityTests(unittest.TestCase):
    def test_safe_generation_preserves_user_edits_and_identical_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            write_dataset(root)
            before={p.name:(p.read_bytes(),p.stat().st_mtime_ns) for p in root.iterdir()}
            write_dataset(root)
            self.assertEqual(before,{p.name:(p.read_bytes(),p.stat().st_mtime_ns) for p in root.iterdir()})
            (root/'reports.jsonl').write_text('Intentional user edit',encoding='utf-8')
            manifest=(root/'manifest.json').read_bytes()
            with self.assertRaises(FileExistsError): write_dataset(root)
            self.assertEqual((root/'reports.jsonl').read_text(),'Intentional user edit')
            self.assertEqual(manifest,(root/'manifest.json').read_bytes())
            write_dataset(root,overwrite=True)
            self.assertEqual(len(load(root/'reports.jsonl')),90)

    def test_challenge_conflict_is_checked_before_any_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            (root/'challenge_qrels.jsonl').write_bytes(b'Existing researcher labels')
            with self.assertRaises(FileExistsError): write_challenge(root)
            self.assertEqual([p.name for p in root.iterdir()],['challenge_qrels.jsonl'])

    def test_configured_data_and_database_ignore_current_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            data=root/'configured dataset'
            elsewhere=root/'unrelated working folder'
            elsewhere.mkdir()
            env={'SHERLOCKED_DATASET_DIR':str(data),'SHERLOCKED_DATABASE_PATH':str(root/'db path'/'local.sqlite3')}
            previous=Path.cwd()
            try:
                os.chdir(elsewhere)
                with patch.dict(os.environ,env):
                    write_dataset()
                    self.assertEqual(len(load()),90)
                    store=Store()
                    store.initialize(load())
                    self.assertEqual(store.path,root/'db path'/'local.sqlite3')
                    self.assertEqual(store.health()['reports'],90)
                self.assertFalse((elsewhere/'data').exists())
            finally: os.chdir(previous)

    def test_legacy_baseline_saves_unique_results_without_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            write_dataset(root/'data')
            results=root/'results'
            results.mkdir()
            legacy=results/'tfidf_dev.json'
            legacy.write_bytes(b'Historical result must remain')
            with patch.dict(os.environ,{'SHERLOCKED_DATASET_DIR':str(root/'data'),'SHERLOCKED_RESULTS_DIR':str(results)}):
                first=run('dev'); second=run('dev')
            self.assertNotEqual(first['output_path'],second['output_path'])
            self.assertTrue(Path(first['output_path']).exists())
            self.assertEqual(legacy.read_bytes(),b'Historical result must remain')

    def test_null_entities_are_missing_not_a_parser_failure(self):
        row=generate()[0]
        row['entities']=None
        self.assertTrue(validate_records([row])[0]['entities'])

    def test_default_experiment_paths_use_configured_resources(self):
        class FixtureEngine:
            model_metadata={}
            def search(self,query,candidates,**kwargs):
                return [dict(report=row,score=1.) for row in candidates if row['report_id']!=query['report_id']][:kwargs['k']]
        rows=[dict(report_id='T',text='train',split='train',family_id='train',fictional=True),
              dict(report_id='A',text='first',split='dev',family_id='pair',fictional=True),
              dict(report_id='B',text='second',split='dev',family_id='pair',fictional=True)]
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            data=root/'dataset'; data.mkdir()
            (data/'reports.jsonl').write_text('\n'.join(json.dumps(row) for row in rows),encoding='utf-8')
            with patch.dict(os.environ,{'SHERLOCKED_DATASET_DIR':str(data),'SHERLOCKED_RESULTS_DIR':str(root/'saved results')}):
                result=run_experiment(['tfidf'],engine=FixtureEngine())
            self.assertEqual(Path(result['json_path']).parent,root/'saved results'/'experiments')
            self.assertEqual(result['portable_provenance']['dataset_filename'],'reports.jsonl')
            self.assertEqual(result['methods']['tfidf']['status'],'completed')


if __name__=='__main__': unittest.main()

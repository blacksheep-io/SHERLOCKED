import json
import math
import tempfile
import unittest
from pathlib import Path
from sherlocked.experiments import (retrieval_metrics, family_bootstrap, run_experiment,
                                    summary_csv, validate_partitions)


class FixtureEngine:
    model_metadata = {'model_id': 'unit-test-fixture-only'}

    def search(self, query, candidates, **kwargs):
        return [dict(report=r, score=1 if r['family_id'] == query['family_id'] else 0)
                for r in sorted(candidates, key=lambda r: (r['family_id'] != query['family_id'], r['report_id']))
                if r['report_id'] != query['report_id']][:kwargs['k']]


class ExperimentTests(unittest.TestCase):
    def test_metrics_dynamic_cutoff_and_no_positive(self):
        metrics = retrieval_metrics(['x', 'a'], {'a'}, k=2)
        self.assertEqual(metrics['precision'], .5)
        self.assertEqual(metrics['recall'], 1)
        self.assertEqual(metrics['mrr'], .5)
        self.assertAlmostEqual(metrics['ndcg'], 1/math.log2(3))
        self.assertIsNone(retrieval_metrics(['x'], set())['recall'])
        with self.assertRaises(ValueError):
            retrieval_metrics(['x', 'x'], {'x'})

    def test_family_leakage(self):
        with self.assertRaisesRegex(ValueError, 'leakage'):
            validate_partitions([dict(report_id='a',family_id='same',split='train',fictional=True),
                                 dict(report_id='b',family_id='same',split='dev',fictional=True)])

    def test_export_and_reproducible_ranking(self):
        rows = [dict(report_id='T',family_id='train',split='train',fictional=True,text='fixture')]
        rows += [dict(report_id=f'D{i}',family_id='related' if i < 2 else None,split='dev',fictional=True,
                      language='en',variant='fixture',text='fictional fixture') for i in range(3)]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            dataset = root / 'fixture.jsonl'
            dataset.write_text('\n'.join(json.dumps(r) for r in rows), encoding='utf-8')
            first = run_experiment(['tfidf'], dataset_path=dataset, output_dir=root/'results', engine=FixtureEngine())
            second = run_experiment(['tfidf'], dataset_path=dataset, output_dir=root/'results', engine=FixtureEngine())
            self.assertEqual(first['ranking_fingerprint'], second['ranking_fingerprint'])
            self.assertNotEqual(first['experiment_id'], second['experiment_id'])
            self.assertTrue(Path(first['json_path']).exists())
            self.assertIn('tfidf,completed', summary_csv(first))
            self.assertNotIn(b'\r\r\n', Path(first['csv_path']).read_bytes())
            stats = first['methods']['tfidf']['aggregate']
            self.assertEqual(stats['no_match_query_count'], 1)
            self.assertEqual(stats['no_match_false_positive_query_rate'], 0)
            self.assertEqual(first['methods']['tfidf']['family_bootstrap']['family_count'], 2)

    def test_source_only_drops_annotations_not_labels(self):
        class SourceEngine(FixtureEngine):
            def search(self, query, candidates, **kwargs):
                for row in [query, *candidates]:
                    self.assert_source(row)
                return super().search(query, candidates, **kwargs)
            @staticmethod
            def assert_source(row):
                if any(key in row for key in ['location', 'occurred_at', 'entities', 'incident_type']):
                    raise AssertionError('Provided metadata leaked into source-only run')
                if 'family_id' not in row:
                    raise AssertionError('Labels required by evaluation were removed')
        rows = [dict(report_id=str(i),family_id='family' if i else 'train',split='train' if i==0 else 'dev',
                     fictional=True,text='fixture',location='annotated',occurred_at='2025-01-01',entities=[])
                for i in range(3)]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'fixture.jsonl'
            path.write_text('\n'.join(json.dumps(row) for row in rows), encoding='utf-8')
            artifact = run_experiment(['tfidf'], config={'source_only': True}, dataset_path=path,
                                      output_dir=Path(directory)/'out', engine=SourceEngine())
            self.assertEqual(artifact['methods']['tfidf']['status'], 'completed')

    def test_failure_is_explicit(self):
        class BrokenEngine(FixtureEngine):
            def search(self, *args, **kwargs):
                raise RuntimeError('model unavailable')
        rows = [dict(report_id=str(i),family_id=str(i),split='train' if i==0 else 'dev',
                     fictional=True,text='fixture') for i in range(3)]
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'fixture.jsonl'
            path.write_text('\n'.join(json.dumps(r) for r in rows), encoding='utf-8')
            result=run_experiment(['semantic'], dataset_path=path, output_dir=Path(directory)/'out', engine=BrokenEngine())
            self.assertEqual(result['methods']['semantic']['status'], 'failed')
            self.assertIn('model unavailable',result['methods']['semantic']['error'])


if __name__ == '__main__':
    unittest.main()

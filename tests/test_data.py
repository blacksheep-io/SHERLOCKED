import json
from pathlib import Path
import tempfile
import unittest
from sherlocked.dataset import generate
from sherlocked.ingestion import parse_jsonl,export_jsonl,validate_records,decode_text
from sherlocked.signals import analyze_report,enrich_report,compare_entities,compare_structured,identify_language
from sherlocked.storage import Store
from sherlocked.research_data import generate_challenge,qrels,write_challenge


class SignalTests(unittest.TestCase):
    def test_script_identification(self):
        self.assertEqual(identify_language('নীল সাইকেল হারিয়ে গেছে'), 'bn')
        self.assertEqual(identify_language('A bicycle is missing'), 'en')
        self.assertEqual(identify_language('নীল bicycle missing'), 'mixed')
        self.assertEqual(identify_language('123 !'), 'unknown')

    def test_original_and_offsets(self):
        text = 'Person: Arif Noor; Organization: Lotus Club. পদ্ম চত্বরের সাইকেল হারিয়ে যায়। Date 2025-01-02.'
        report = analyze_report(text)
        self.assertEqual(report['text'],text)
        self.assertEqual(report['occurred_at'],'2025-01-02')
        for entity in report['entities']:
            self.assertEqual(text[entity['start']:entity['end']],entity['surface'])
        self.assertIn('person',{e['type'] for e in report['entities']})
        self.assertIn('organization',{e['type'] for e in report['entities']})
        self.assertEqual(report['location'],'lotus')

    def test_provided_annotation_not_source_claim(self):
        fixture = generate()[1]
        result = enrich_report(fixture)
        self.assertEqual(result['text'],fixture['text'])
        self.assertEqual(result['occurred_at'],fixture['occurred_at'])
        self.assertEqual(result['metadata_provenance']['occurred_at']['method'],'provided_annotation')
        self.assertNotIn('start',result['metadata_provenance']['occurred_at'])

    def test_entity_match_statuses(self):
        en,bn = analyze_report('bicycle at Lotus'),analyze_report('পদ্ম চত্বরে সাইকেল')
        match = compare_entities(en,bn)
        self.assertEqual(match['score'],1)
        self.assertTrue(all(row['status']=='normalized' for row in match['matches']))
        self.assertEqual(compare_entities(en,en)['matches'][0]['status'],'exact')
        approximate = compare_entities(analyze_report('Person: Samira Rahman.'),analyze_report('Person: Samira Rahmen.'))
        self.assertEqual(approximate['matches'][0]['status'],'approximate')
        self.assertIsNone(compare_entities(analyze_report('Nothing recorded.'),en)['score'])

    def test_missing_structured_not_mismatch(self):
        missing = compare_structured(analyze_report('Nothing recorded.'),analyze_report('No details available.'))
        self.assertIsNone(missing['score'])
        self.assertEqual(len(missing['missing']),3)
        a = analyze_report('Location: Lotus. Missing parcel. 2025-01-01')
        b = analyze_report('Location: River. Missing parcel. 2025-01-09')
        result = compare_structured(a,b)
        self.assertAlmostEqual(result['score'],1/3)
        self.assertEqual({r['field'] for r in result['contradictions']},{'location','occurred_at'})

    def test_empty_report_rejected(self):
        with self.assertRaises(ValueError):
            analyze_report('   ')


class StoreTests(unittest.TestCase):
    def test_challenge_generation_and_qrels(self):
        rows=generate_challenge()
        self.assertEqual(rows,generate_challenge())
        self.assertEqual(len(rows),39)
        validated=validate_records(rows)
        self.assertEqual(len(validated),39)
        labels=qrels(rows)
        self.assertTrue(any(row['grade']==1 for row in labels))
        self.assertTrue(all(row['grade']==0 for row in labels if row['query_id'].startswith('XN')))
        self.assertEqual(len({r['family_id'] for r in rows}),15)
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            write_challenge(root)
            self.assertEqual(len(parse_jsonl((root/'challenge_reports.jsonl').read_bytes())),39)
            self.assertTrue((root/'qrels.jsonl').exists())

    def test_initialize_idempotent_and_preserve_original(self):
        with tempfile.TemporaryDirectory() as path:
            store = Store(Path(path)/'data.sqlite3')
            rows = generate()
            store.initialize(rows);store.initialize(rows)
            self.assertEqual(len(store.list_reports()),90)
            self.assertEqual(store.health()['status'],'ok')
            self.assertEqual(store.list_reports()[0]['text'],rows[0]['text'])
            self.assertTrue(store.list_reports()[0]['entities'])

    def test_atomic_import_and_duplicates(self):
        with tempfile.TemporaryDirectory() as path:
            store = Store(Path(path)/'data.sqlite3')
            first = analyze_report('A new fictional fire report.','USER-1')
            store.add_report(first)
            with self.assertRaises(ValueError):
                store.import_reports([analyze_report('A different report.','USER-2'),first])
            self.assertEqual(len(store.list_reports()),1)
            duplicate = analyze_report(first['text'],'USER-3')
            with self.assertRaises(ValueError):
                store.add_report(duplicate)
            self.assertEqual(len(store.list_reports()),1)
            self.assertEqual(len(parse_jsonl(store.export_jsonl())),1)

    def test_cross_split_and_invalid_spans(self):
        rows = generate()[:2]
        rows[1]['split']='test'
        with self.assertRaises(ValueError):
            validate_records(rows)
        record = analyze_report('Known source text.','A')
        record['entities']=[dict(type='person',surface='Fake',start=0,end=4)]
        with self.assertRaises(ValueError):
            validate_records([record])
        with self.assertRaises(ValueError):
            decode_text(b'\xff\xff')
        with self.assertRaises(ValueError):
            parse_jsonl('not json')


if __name__=='__main__':
    unittest.main()

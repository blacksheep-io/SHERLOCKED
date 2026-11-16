import math
import unittest
import tempfile
import hashlib
from pathlib import Path
from sherlocked.dataset import generate, write_dataset
from sherlocked.retrieval import KeywordIndex, tokenize
from sherlocked.evaluate import metrics


class BaselineTests(unittest.TestCase):
    def test_written_bytes_and_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = write_dataset(root)
            first = (root/'reports.jsonl').read_bytes()
            self.assertNotIn(b'\r\n', first)
            self.assertEqual(hashlib.sha256(first).hexdigest(), manifest['sha256'])
            write_dataset(root)
            self.assertEqual(first, (root/'reports.jsonl').read_bytes())

    def test_dataset_contract(self):
        rows = generate()
        self.assertEqual(rows, generate())
        self.assertEqual(len(rows), 90)
        self.assertEqual(len({r['report_id'] for r in rows}), 90)
        families = {}
        for r in rows:
            families.setdefault(r['family_id'], set()).add(r['split'])
            self.assertTrue(r['fictional'])
            self.assertTrue(r['text'])
        self.assertTrue(all(len(v)==1 for v in families.values()))
        self.assertEqual({r['language'] for r in rows}, {'en','bn','mixed'})

    def test_bangla_marks(self):
        self.assertEqual(tokenize('সাক্ষী সাইকেল।'), ['সাক্ষী','সাইকেল'])

    def test_known_ranking_and_explanation(self):
        rows = [dict(report_id='A', text='blue bicycle'), dict(report_id='B',text='blue bicycle'),
                dict(report_id='C',text='orange boat')]
        index = KeywordIndex(rows)
        result = index.search('blue bicycle', rows, exclude_id='A')
        self.assertEqual([r['report']['report_id'] for r in result], ['B'])
        self.assertAlmostEqual(result[0]['score'], 1)
        self.assertAlmostEqual(sum(s['contribution'] for s in result[0]['signals']), 1)
        for s in result[0]['signals']:
            for a,b in s['candidate_spans']:
                self.assertEqual(rows[1]['text'][a:b], s['term'])

    def test_empty_oov_ties(self):
        rows = [dict(report_id='B',text='boat'),dict(report_id='A',text='boat')]
        index = KeywordIndex(rows)
        self.assertEqual(index.search('', rows), [])
        self.assertEqual(index.search('unseen', rows), [])
        self.assertEqual([r['report']['report_id'] for r in index.search('boat',rows)], ['A','B'])
        self.assertEqual(index.search('boat',[]), [])

    def test_metrics_hand_computed(self):
        m = metrics(['x','a','b','z','w'], {'a','b'})
        self.assertAlmostEqual(m['precision_at_5'], .4)
        self.assertEqual(m['recall_at_5'], 1)
        self.assertEqual(m['mrr_at_5'], .5)
        self.assertAlmostEqual(m['ndcg_at_5'], (1/math.log2(3)+.5)/(1+1/math.log2(3)))

    def test_fit_isolation(self):
        rows = generate()
        train = [r for r in rows if r['split']=='train']
        index = KeywordIndex(train)
        before = dict(index.vectorizer.vocabulary_)
        index.search('unseenheldouttoken', [dict(report_id='X',text='unseenheldouttoken')])
        self.assertEqual(before, index.vectorizer.vocabulary_)
        self.assertNotIn('unseenheldouttoken', before)


if __name__ == '__main__':
    unittest.main()

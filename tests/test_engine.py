import math
import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch
import numpy as np
from sherlocked.engine import BM25Index, Engine
from sherlocked.semantic import SemanticEncoder, SemanticUnavailable


def report(identifier,text,**metadata):
    return dict(report_id=identifier,text=text,fictional=True,source_id=f'test:{identifier}',**metadata)


class FakeEncoder:
    """Deterministic numerical fixture, never used by the app or reported model runs."""
    metadata={'model_id':'test-only'}
    def scores(self,query,texts):
        return np.array([.8 if 'bicycle' in text else .1 for text in texts])
    def passage_evidence(self,query,text):
        return dict(query_text=query,candidate_text=text,cosine=.8)


class EngineTests(unittest.TestCase):
    def setUp(self):
        self.rows=[report('A','blue bicycle missing'),report('B','blue bicycle missing'),report('C','orange boat found')]

    def test_bm25_formula_and_evidence(self):
        index=BM25Index(self.rows)
        terms=index.explain('blue bicycle',self.rows[0]['text'])
        expected=2*math.log(1+(3-2+.5)/(2+.5))
        self.assertAlmostEqual(sum(t['contribution'] for t in terms),expected)
        self.assertGreater(index.scores('bicycle',self.rows)[0],index.scores('bicycle',self.rows)[2])
        for signal in terms:
            for a,b in signal['candidate_spans']:
                self.assertEqual(self.rows[0]['text'][a:b],signal['term'])
        with self.assertRaises(ValueError):
            BM25Index(self.rows,b=2)

    def test_independent_lexical_methods_no_model(self):
        engine=Engine(self.rows)
        with patch.object(engine.semantic,'load',side_effect=AssertionError('must not load')):
            for method in ('tfidf','bm25','entity','structured'):
                rows=engine.search(self.rows[0],self.rows,method=method,exclude_id='A',include_zero=True)
                self.assertEqual(len(rows),2)
                self.assertNotIn('A',[r['report']['report_id'] for r in rows])

    def test_fusion_and_rrf(self):
        engine=Engine(self.rows,semantic=FakeEncoder())
        for method in ('semantic','hybrid','rrf','hybrid_rerank'):
            rows=engine.search(self.rows[0],self.rows,method=method,exclude_id='A')
            self.assertEqual(rows[0]['report']['report_id'],'B')
            self.assertEqual(rows[0]['status'],'potential relationship')
            if method in ('hybrid','rrf'):
                self.assertAlmostEqual(sum(rows[0]['explanation']['contributions'].values()),rows[0]['score'])
        with self.assertRaises(ValueError):
            engine.search(self.rows[0],self.rows,weights={'semantic':-1})
        self.assertEqual(engine.search(report('Q',''),self.rows),[])

    def test_semantic_failure_never_lexical_fallback(self):
        encoder=SemanticEncoder()
        with patch.object(encoder,'status',return_value={'available':False}):
            engine=Engine(self.rows,semantic=encoder)
            with self.assertRaises(SemanticUnavailable):
                engine.search(self.rows[0],self.rows,method='semantic')
            with self.assertRaises(SemanticUnavailable):
                engine.search(self.rows[0],self.rows,method='hybrid')
            self.assertTrue(engine.search(self.rows[0],self.rows,method='bm25'))

    def test_empty_invalid_and_duplicate_candidates(self):
        engine=Engine(iter(self.rows))
        for method in ['tfidf','bm25','semantic','entity','structured','hybrid','rrf']:
            self.assertEqual(engine.search({'text':'  ','location':'Lotus'},self.rows,method=method),[])
        with self.assertRaises(ValueError):
            engine.search({'text':None},self.rows)
        with self.assertRaises(ValueError):
            engine.search(self.rows[0],[self.rows[1],self.rows[1]])
        with self.assertRaises(ValueError):
            Engine([report('P','...')])
        for k in [0,1.5,True]:
            with self.assertRaises(ValueError):
                engine.search(self.rows[0],self.rows,k=k)
        # Duplicate narratives remain separate source records; no deduplication or identity merge.
        results=engine.search(self.rows[0],self.rows,method='tfidf',include_zero=True)
        self.assertEqual([r['report']['report_id'] for r in results[:2]],['A','B'])

    def test_unknown_metadata_and_rrf_constant(self):
        empty=[report('A','unclassified wording'),report('B','other wording')]
        engine=Engine(empty,config={'rrf_k':0,'weights':{'tfidf':1}})
        row=engine.search(empty[0],empty,method='rrf',exclude_id='A')[0]
        self.assertAlmostEqual(row['score'],1)
        self.assertIsNone(row['components']['structured'])
        self.assertIsNone(row['components']['entity'])
        row=engine.search(empty[0],empty,method='hybrid',exclude_id='A')[0]
        self.assertEqual(set(row['explanation']['contributions']),{'tfidf'})
        for invalid in [-1,float('nan'),float('inf')]:
            with self.assertRaises(ValueError):
                Engine(empty,config={'rrf_k':invalid})


class SemanticCacheTests(unittest.TestCase):
    def test_cache_roles_revision_and_corruption(self):
        encoder=SemanticEncoder()
        class FakeModel:
            def __init__(self):
                self.calls=[]
            def encode(self,texts,**kwargs):
                self.calls.append(texts)
                return np.tile(np.eye(384,dtype=np.float32)[0],(len(texts),1))
        encoder.model=FakeModel()
        with tempfile.TemporaryDirectory() as directory, patch.object(encoder,'load',return_value=encoder):
            encoder.cache_directory=Path(directory)
            self.assertEqual(encoder.encode([]).shape,(0,384))
            encoder.encode(['same narrative'],'query')
            encoder.encode(['same narrative'],'query')
            self.assertEqual(len(encoder.model.calls),1)
            encoder.encode(['same narrative'],'passage')
            self.assertEqual(len(encoder.model.calls),2)
            self.assertTrue(encoder.model.calls[0][0].startswith('query: '))
            self.assertTrue(encoder.model.calls[1][0].startswith('passage: '))
            encoder.config['revision']='f'*40
            encoder.encode(['same narrative'],'query')
            self.assertEqual(len(encoder.model.calls),3)
            for path in Path(directory).glob('*.npy'):
                np.save(path,np.zeros(384,dtype=np.float32),allow_pickle=False)
            encoder.clear_memory_cache()
            encoder.encode(['same narrative'],'query')
            self.assertEqual(len(encoder.model.calls),4)
        with self.assertRaises(ValueError):
            SemanticEncoder(revision='main')
        with self.assertRaises(ValueError):
            SemanticEncoder(model_id='unreviewed/model')


if __name__=='__main__':
    unittest.main()

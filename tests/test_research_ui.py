"""Research display contracts: missing/failed results never become invented metrics."""
import unittest
import hashlib
import tempfile
from copy import deepcopy
from pathlib import Path,PureWindowsPath
from sherlocked.ui_research import _metric_frame,_metric_matrix,_completed,_number,_resolve_dataset_source


class ResearchPresentationTests(unittest.TestCase):
    def test_failed_method_does_not_enter_measured_matrix(self):
        run={'methods':{
            'tfidf':{'status':'completed','aggregate':{'precision':.2,'recall':.5,'mrr':.25,'ndcg':.3}},
            'semantic':{'status':'failed','error':'model unavailable','aggregate':{}}
        }}
        matrix=_metric_matrix(run)
        self.assertEqual(list(matrix.index),['TF-IDF'])
        self.assertAlmostEqual(matrix.loc['TF-IDF','ndcg'],.3)
        self.assertEqual(set(_completed(run)),{'tfidf'})
        self.assertEqual(len(_metric_frame(run)),2)

    def test_undefined_recall_stays_missing(self):
        run={'methods':{'semantic':{'status':'completed','aggregate':{'precision':0.,'recall':None,'mrr':0.,'ndcg':None}}}}
        matrix=_metric_matrix(run)
        self.assertTrue(matrix['recall'].isna().all())
        self.assertTrue(matrix['ndcg'].isna().all())
        self.assertEqual(_number(None),'—')
        self.assertEqual(_number(0.),'0.000')

    def test_empty_history_has_no_measured_matrix(self):
        self.assertTrue(_metric_matrix({'methods':{}}).empty)

    def test_metric_presentation_does_not_mutate_the_saved_record(self):
        from copy import deepcopy
        run={'experiment_id':'immutable-fixture','k':5,'methods':{
            'hybrid':{'status':'completed','aggregate':{'precision':.4,'recall':.5,'mrr':.6,'ndcg':.7},
                      'queries':[{'query_id':'Q1','ranked_scores':[.123456789],'missed_relevant_ids':['R2']}]},
            'semantic':{'status':'failed','error':'offline model missing'}
        }}
        before=deepcopy(run)
        _metric_frame(run)
        _metric_matrix(run)
        _completed(run)
        self.assertEqual(run,before)



class DatasetSourceResolutionTests(unittest.TestCase):
    def test_matching_relocated_windows_source_uses_configured_directory(self):
        payload=b'{"report_id":"Q1","text":"fictional source"}\n'
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); data=root/'configured dataset'; data.mkdir()
            candidate=data/'reports.jsonl'; candidate.write_bytes(payload)
            historical=str(PureWindowsPath(str(root))/'missing old PC'/'reports.jsonl')
            artifact={'dataset_path':historical,'dataset_sha256':hashlib.sha256(payload).hexdigest(),
                      'configuration':{'source_only':True}}
            before=deepcopy(artifact)
            self.assertEqual(_resolve_dataset_source(artifact,root,data),candidate.resolve())
            self.assertEqual(artifact,before)

    def test_wrong_hash_refuses_both_recorded_and_relocated_sources(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); data=root/'configured'; data.mkdir()
            original=root/'old/reports.jsonl'; original.parent.mkdir()
            original.write_bytes(b'changed historical content')
            (data/'reports.jsonl').write_bytes(b'changed copied content')
            artifact={'dataset_path':str(original),'dataset_sha256':hashlib.sha256(b'expected original bytes').hexdigest()}
            before=deepcopy(artifact)
            self.assertIsNone(_resolve_dataset_source(artifact,root,data))
            self.assertEqual(artifact,before)

    def test_relative_original_path_wins_and_artifact_remains_unchanged(self):
        payload=b'original fictional corpus'
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); original=root/'data/reports.jsonl'; original.parent.mkdir()
            original.write_bytes(payload)
            copied=root/'configured/reports.jsonl'; copied.parent.mkdir(); copied.write_bytes(payload)
            artifact={'dataset_path':'data/reports.jsonl','dataset_sha256':hashlib.sha256(payload).hexdigest()}
            before=deepcopy(artifact)
            self.assertEqual(_resolve_dataset_source(artifact,root,copied.parent),original.resolve())
            self.assertEqual(artifact,before)
            self.assertEqual(artifact['dataset_path'],'data/reports.jsonl')

    def test_legacy_record_without_hash_never_guesses_a_moved_source(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); data=root/'configured'; data.mkdir()
            (data/'reports.jsonl').write_bytes(b'existing copy without recorded checksum')
            original=root/'old/reports.jsonl'
            artifact={'dataset_path':str(original)}
            before=deepcopy(artifact)
            self.assertIsNone(_resolve_dataset_source(artifact,root,data))
            original.parent.mkdir(); original.write_bytes(b'legacy recorded source')
            self.assertEqual(_resolve_dataset_source(artifact,root,data),original.resolve())
            self.assertEqual(artifact,before)

if __name__=='__main__': unittest.main()


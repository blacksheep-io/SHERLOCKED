import unittest
from streamlit.testing.v1 import AppTest
from sherlocked.ui_ashford import load_fixture,timeline
from sherlocked.engine import Engine
from sherlocked.signals import enrich_report


class AshfordTests(unittest.TestCase):
    def test_fixture_separate_and_source_dated(self):
        fixture=load_fixture();rows=fixture['reports']
        self.assertEqual(len(rows),6)
        self.assertFalse(fixture['research_ground_truth'])
        self.assertEqual({r['language'] for r in rows},{'en','bn','mixed'})
        for row in rows:
            self.assertNotIn('family_id',row);self.assertNotIn('split',row)
            self.assertIn(row['occurred_at'],row['text'])
            self.assertTrue(row['fictional'])
        self.assertEqual(len(timeline(rows).data[0].x),6)

    def test_actual_demo_retrieval_and_controls(self):
        rows=[enrich_report(r) for r in load_fixture()['reports']]
        hits=Engine(rows).search(rows[0],rows,method='bm25',k=4,exclude_id=rows[0]['report_id'])
        self.assertTrue(hits)
        self.assertTrue(all(hit['report']['report_id']!='AM-001' for hit in hits))
        app=AppTest.from_string('from sherlocked.ui_ashford import render\nfrom sherlocked.settings import read_settings\nrender(read_settings())',default_timeout=60).run()
        self.assertFalse(app.exception,str(app.exception))
        self.assertTrue(any('SEPARATE DEMO CORPUS' in mark.value for mark in app.markdown))
        next(button for button in app.button if button.label=='Analyze archive links').click().run()
        self.assertFalse(app.exception,str(app.exception))
        self.assertTrue(app.session_state['ashford_analysis']['results'])
        self.assertTrue(any(select.label=='Inspect Ashford link' for select in app.selectbox))


if __name__=='__main__':unittest.main()

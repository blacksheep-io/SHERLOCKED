import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch
from streamlit.testing.v1 import AppTest

class AppTests(unittest.TestCase):
    def setUp(self):
        self.access_directory=tempfile.TemporaryDirectory()
        self.access_patch=patch('sherlocked.auth.access_database_path',return_value=Path(self.access_directory.name)/'access.sqlite3')
        self.access_patch.start()
    def tearDown(self):
        self.access_patch.stop();self.access_directory.cleanup()
    def test_seven_screens_and_real_queries(self):
        app=AppTest.from_file('app.py',default_timeout=60).run()
        self.assertFalse(app.exception)
        next(b for b in app.button if b.label=='Investigator access').click().run()
        next(t for t in app.text_input if t.label=='Username').set_value('demo')
        next(t for t in app.text_input if t.label=='Password').set_value('sherlocked-demo')
        next(b for b in app.button if b.label=='Unlock the workspace').click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state['access_user'],'demo')
        sections=['Report Explorer','AI Analysis Workspace','Relationship Explorer','Research Evaluation Lab','System Settings','Ashford Manor','Intelligence Dashboard']
        for section in sections:
            next(button for button in app.sidebar.button if button.label==section).click().run()
            self.assertFalse(app.exception,str(app.exception))
            if section=='Report Explorer':
                next(w for w in app.selectbox if w.label=='Inspect report').set_value('R03-2').run()
                next(b for b in app.button if b.label=='Use in analysis').click().run()
            if section=='AI Analysis Workspace':
                self.assertEqual(next(w for w in app.selectbox if w.label=='Start from dataset report').value,'R03-2')
                next(b for b in app.button if b.label=='Discover related reports').click().run()
                self.assertFalse(app.exception)
                self.assertTrue(app.session_state['analysis_result']['results'])
                for text in ['সাক্ষী পদ্ম চত্বরে সাইকেল দেখেন।','A bicycle is missing near Lotus square.','পদ্ম square bicycle missing.']:
                    next(t for t in app.text_area if t.label=='Original report').set_value(text)
                    next(s for s in app.selectbox if s.label=='Retrieval method').set_value('BM25')
                    next(b for b in app.button if b.label=='Discover related reports').click().run()
                    self.assertFalse(app.exception)
                    self.assertTrue(app.session_state['analysis_result']['results'])
            if section=='Relationship Explorer':
                next(b for b in app.button if b.label=='Build relationship graph').click().run()
                self.assertFalse(app.exception)
                self.assertTrue(app.session_state['graph_result']['results'])

if __name__=='__main__': unittest.main()

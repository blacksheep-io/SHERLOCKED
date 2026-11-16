"""Branded entry, authenticated route protection and theme continuity."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from streamlit.testing.v1 import AppTest


def button(app,label):
    return next(item for item in app.button if item.label==label)


def submit_login(app,username='demo',password='sherlocked-demo'):
    next(w for w in app.text_input if w.label=='Username').set_value(username)
    next(w for w in app.text_input if w.label=='Password').set_value(password)
    button(app,'Unlock the workspace').click().run()


class EntryTests(unittest.TestCase):
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory()
        self.access_path=Path(self.directory.name)/'access.sqlite3'
        self.access_patch=patch('sherlocked.auth.access_database_path',return_value=self.access_path)
        self.access_patch.start()
    def tearDown(self):
        self.access_patch.stop();self.directory.cleanup()

    def test_landing_login_theme_workspace_logout_and_route_gate(self):
        app=AppTest.from_file('app.py',default_timeout=60).run()
        self.assertFalse(app.exception)
        self.assertNotIn('access_user',app.session_state)
        self.assertFalse(self.access_path.exists(),'Landing should not initialize local credentials')
        button(app,'Dark mode').click().run()
        self.assertEqual(app.session_state['visual_theme'],'dark')
        button(app,'Investigator access').click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state['visual_theme'],'dark')
        submit_login(app,password='incorrect-password')
        self.assertFalse(app.exception)
        self.assertNotIn('access_user',app.session_state)
        self.assertTrue(any('Sign-in unsuccessful' in item.value for item in app.error))
        submit_login(app)
        self.assertFalse(app.exception,str(app.exception))
        self.assertEqual(app.session_state['access_user'],'demo')
        self.assertEqual(app.session_state['visual_theme'],'dark')
        self.assertTrue(any(b.label=='Intelligence Dashboard' for b in app.sidebar.button))
        # Navigation after successful form submission catches stale login-widget IDs.
        button(app,'Report Explorer').click().run()
        self.assertFalse(app.exception)
        button(app,'Light mode').click().run()
        self.assertEqual(app.session_state['visual_theme'],'light')
        button(app,'Sign out').click().run()
        self.assertFalse(app.exception)
        self.assertNotIn('access_user',app.session_state)
        self.assertEqual(app.session_state['entry_view'],'landing')
        self.assertEqual(app.session_state['visual_theme'],'light')
        self.assertFalse(any(b.label=='Report Explorer' for b in app.sidebar.button))
        app.session_state['entry_view']='workspace'
        app.run()
        self.assertFalse(app.exception)
        self.assertNotIn('access_user',app.session_state)
        self.assertTrue(any(b.label=='Investigator access' for b in app.button))

    def test_landing_has_no_report_controls_or_retrieval(self):
        with patch('sherlocked.ui.get_engine') as engine:
            app=AppTest.from_file('app.py',default_timeout=60).run()
            self.assertFalse(app.exception)
            engine.assert_not_called()
        self.assertEqual(len(app.selectbox),0)
        self.assertEqual(len(app.text_area),0)
        self.assertFalse(self.access_path.exists())
        labels=[b.label for b in app.button]
        self.assertIn('Enter the research lab',labels)
        self.assertIn('Investigator access',labels)
        self.assertNotIn('Examine in the lab',labels)
        markup=' '.join(item.value for item in app.markdown)
        self.assertNotIn('sk-preview-result',markup)
        self.assertNotIn('WORKING PREVIEW',markup)
        button(app,'Enter the research lab').click().run()
        self.assertFalse(app.exception)
        self.assertTrue(any(w.label=='Username' for w in app.text_input))

    def test_theme_changes_chart_surfaces_without_changing_scores_or_source(self):
        source='Original <source> পদ্ম & সাইকেল।'
        script='''
import copy
import streamlit as st
from sherlocked.design import apply_theme,theme_control,current_theme,signal_chart,source_quote,chart_theme
import plotly.graph_objects as go
apply_theme();theme_control()
source=SOURCE_LITERAL
hit={'components':{'tfidf':.4,'bm25':17.2,'semantic':None,'entity':0.},'normalized_components':{'tfidf':.4,'bm25':.8,'semantic':None,'entity':0.},'report':{'text':source}}
before=copy.deepcopy(hit);figure=signal_chart(hit)
pie=chart_theme(go.Figure(go.Pie(labels=['English','Bangla'],values=[2,1])))
heatmap=chart_theme(go.Figure(go.Heatmap(z=[[.2,.5]],colorscale=[[0,'#FBF8F0'],[1,'#ECE6D6']],texttemplate='%{z}',textfont={'color':'#121211'})))
source_quote(source,'source:fixture')
st.json({'theme':current_theme(),'raw':list(figure.data[0].customdata),'display':list(figure.data[0].x),'source':hit['report']['text'],'unchanged':hit==before,'surface':figure.layout.paper_bgcolor,'chart_text':figure.layout.font.color,'pie_values':list(pie.data[0].values),'heatmap_values':[list(row) for row in heatmap.data[0].z],'heatmap_text':heatmap.data[0].textfont.color,'heatmap_colorscale':list(heatmap.data[0].colorscale)})
'''.replace('SOURCE_LITERAL',ascii(source))
        app=AppTest.from_string(script,default_timeout=30).run()
        self.assertFalse(app.exception)
        def snapshot():
            value=app.json[0].value
            return json.loads(value) if isinstance(value,str) else value
        light=snapshot()
        button(app,'Dark mode').click().run()
        self.assertFalse(app.exception)
        dark=snapshot()
        self.assertNotEqual(light['surface'],dark['surface'])
        self.assertEqual([light['theme'],dark['theme']],['light','dark'])
        self.assertEqual(light['chart_text'],'#121211')
        self.assertEqual(dark['chart_text'],'#ECE6D6')
        self.assertEqual(light['heatmap_colorscale'],dark['heatmap_colorscale'])
        for result in [light,dark]:
            self.assertEqual(result['raw'],[.4,17.2,0.])
            self.assertEqual(result['display'],[.4,.8,0.])
            self.assertEqual(result['source'],source)
            self.assertTrue(result['unchanged'])
            self.assertEqual(result['pie_values'],[2,1])
            self.assertEqual(result['heatmap_values'],[[.2,.5]])
            self.assertEqual(result['heatmap_text'],'#121211')
        self.assertTrue(any('&lt;source&gt;' in m.value for m in app.markdown))


if __name__=='__main__': unittest.main()

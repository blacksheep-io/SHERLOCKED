import unittest
from streamlit.testing.v1 import AppTest
from sherlocked.dataset import generate
from sherlocked.ui_data import _language_donut,_family_grid,_inventory_health,_date_label,_recent_relationship_bundle
from sherlocked.design import chart_theme,PALETTE

EXPLORER='''
import streamlit as st
from sherlocked.dataset import generate
from sherlocked.signals import enrich_report
from sherlocked.ui_data import explorer
class MemoryStore:
    def add_report(self,report):
        st.session_state.saved_reports=st.session_state.get('saved_reports',[])+[report]
rows=[enrich_report(row) for row in generate()]+st.session_state.get('saved_reports',[])
explorer(rows,MemoryStore())
'''


class DataViewTests(unittest.TestCase):
    def test_charts_encode_actual_dataset_and_shared_surfaces(self):
        rows=generate();donut=_language_donut(rows)
        self.assertEqual(sum(donut.data[0].values),90)
        self.assertEqual(dict(zip(donut.data[0].labels,donut.data[0].values)),{'Bangla':18,'English':36,'Mixed / transliterated':36})
        grid,height=_family_grid(rows)
        self.assertEqual(height,3)
        self.assertEqual(sum(len(row) for row in grid.data[0].z),18)
        self.assertEqual(chart_theme(grid).layout.paper_bgcolor,PALETTE['panel'])
        self.assertTrue(all(ok for name,ok in _inventory_health(rows)))
        self.assertEqual(_date_label(None),'Time unknown')

    def test_recent_relationships_follow_actual_completion_not_graph_priority(self):
        analysis={'query':{'report_id':'A'},'method':'bm25','results':[{'report':{'report_id':'B'},'score':.5}]}
        graph={'query':{'report_id':'G'},'method':'tfidf','results':[{'report':{'report_id':'H'},'score':.4}]}
        activity=[{'id':'2026-11-13T09:02:00+00:00','query_id':'A','method':'bm25','count':1,'top_report':'B'},
                  {'id':'2026-11-13T09:01:00+00:00','query_id':'G','method':'tfidf','count':1,'top_report':'H'}]
        self.assertIs(_recent_relationship_bundle(analysis,graph,activity)['bundle'],analysis)
        graph['completed_at']='2026-11-13T09:03:00+00:00'
        self.assertIs(_recent_relationship_bundle(analysis,graph,activity)['bundle'],graph)
        empty={'query':{'report_id':'E'},'method':'bm25','results':[],'completed_at':'2026-11-13T09:04:00+00:00'}
        self.assertIs(_recent_relationship_bundle(empty,graph,activity)['bundle'],empty)
        self.assertIsNone(_recent_relationship_bundle(analysis,None,[])['recorded_at'])

    def test_explorer_filter_source_selection_and_empty_state(self):
        app=AppTest.from_string(EXPLORER,default_timeout=30).run()
        self.assertFalse(app.exception)
        app.selectbox(key='report_inspect').set_value('R03-2').run()
        app.button(key='use_explorer_report').click().run()
        self.assertEqual(app.session_state['selected_query']['report_id'],'R03-2')
        app.text_input(key='report_filter').set_value('no report can match this phrase').run()
        self.assertFalse(app.exception)
        self.assertFalse(any(item.key=='report_inspect' for item in app.selectbox))
        app.text_input(key='report_filter').set_value('').run()
        app.selectbox(key='report_language').set_value('bn').run()
        self.assertEqual(len(app.selectbox(key='report_inspect').options),18)

    def test_submission_confirmation_and_original_source_preserved(self):
        app=AppTest.from_string(EXPLORER,default_timeout=30).run()
        original='ব্যক্তি: নীলা সেন; Fictional camera report near Lotus.'
        app.text_area(key='new_report_text').set_value(original)
        next(b for b in app.button if b.label=='Save fictional report').click().run()
        self.assertTrue(app.error)
        app.checkbox(key='new_report_confirm').check().run()
        next(b for b in app.button if b.label=='Save fictional report').click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state['saved_reports'][0]['text'],original)
        self.assertEqual(app.session_state['saved_reports'][0]['split'],'unassigned')


if __name__=='__main__':unittest.main()

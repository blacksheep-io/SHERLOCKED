import unittest
from sherlocked.signals import analyze_report,compare_entities
from sherlocked.visualization import relationship_graph,relationship_data,relationship_selection


class GraphPresentationTests(unittest.TestCase):
    def setUp(self):
        self.query=analyze_report('Person: Arif Noor; bicycle at Lotus.','Q')
        self.related=analyze_report('Person: Arif Noor; a bicycle was missing at Lotus.','C')
        self.hit=dict(report=self.related,score=.7,method='tfidf',explanation={'entities':compare_entities(self.query,self.related)})

    def test_legacy_graph_and_suggested_styles(self):
        hits=[dict(report=analyze_report('bicycle '+str(i),f'C{i}'),score=.2,method='tfidf') for i in range(3)]
        figure=relationship_graph(self.query,hits)
        self.assertEqual(len(figure.data),4)
        self.assertEqual(list(figure.data[-1].customdata),['Q','C0','C1','C2'])
        self.assertEqual(figure.layout.paper_bgcolor,'#121211')
        self.assertTrue(all(trace.line.dash=='dash' for trace in figure.data[:-1]))
        self.assertEqual(figure.layout.dragmode,'pan')

    def test_mentions_remain_source_specific(self):
        data=relationship_data(self.query,[self.hit],include_entities=True)
        persons=[n for n in data['nodes'].values() if n.get('entity_type')=='person']
        self.assertEqual(len(persons),2)
        self.assertNotEqual(persons[0]['id'],persons[1]['id'])
        self.assertEqual(data['human_verified_count'],0)
        source_edges=[e for e in data['edges'] if e['type']=='source_mention']
        self.assertTrue(source_edges)
        for edge in source_edges:
            e=edge['evidence']; report=data['reports'][e['report_id']]
            self.assertEqual(report['text'][e['start']:e['end']],e['text'])
        self.assertTrue(any(e['type']=='suggested_entity' for e in data['edges']))
        self.assertTrue(all(e['source'] in data['nodes'] and e['target'] in data['nodes'] for e in data['edges']))

    def test_documented_link_requires_human_record_and_source(self):
        record=dict(source_report_id='Q',target_report_id='C',status='human_verified',relation_type='Reviewer-recorded association',
                    human_confirmation={'reviewer':'Fictional reviewer','confirmed_at':'2026-11-05T10:00:00+06:00'},
                    evidence={'report_id':'Q','source_id':self.query['source_id'],'start':0,'end':6,'text':self.query['text'][:6]})
        args=dict(include_entities=True,documented_links=[record])
        self.assertEqual(relationship_data(self.query,[self.hit],**args)['human_verified_count'],1)
        record['evidence']['text']='invented evidence'
        self.assertEqual(relationship_data(self.query,[self.hit],**args)['human_verified_count'],0)
        record['evidence']['text']=self.query['text'][:6]; record['human_confirmation']={}
        self.assertEqual(relationship_data(self.query,[self.hit],**args)['human_verified_count'],0)

    def test_filters_and_plotly_selection_ids(self):
        data=relationship_data(self.query,[self.hit],include_entities=True,entity_types=['person'])
        self.assertTrue(all(n['type']=='report' or n['entity_type']=='person' for n in data['nodes'].values()))
        figure=relationship_graph(self.query,[self.hit],include_entities=True,entity_types=['person'])
        valid=set(data['nodes'])|{e['id'] for e in data['edges']}
        for trace in figure.data: self.assertTrue(set(trace.customdata)<=valid)
        empty=relationship_data(self.query,[self.hit],include_entities=True,filter_text='no-such-report-phrase')
        self.assertEqual(set(empty['reports']),{'Q'})
        self.assertFalse(relationship_data(self.query,[self.hit],include_entities=True,layers=[])['edges'])

    def test_graph_escapes_source_text(self):
        record=analyze_report('Person: <script>alert(1)</script>; bicycle.','<img src=x>')
        serialized=relationship_graph(record,[],include_entities=True).to_json()
        self.assertNotIn('<script>',serialized)
        self.assertNotIn('<img src=x>',serialized)
        self.assertIn('&lt;',serialized)


    def test_relationship_screen_real_search_and_inspection(self):
        from streamlit.testing.v1 import AppTest
        script="""
from sherlocked.ui_relationships import render
from sherlocked.dataset import generate
from sherlocked.engine import Engine
from sherlocked.settings import read_settings
rows=generate()
def run(query,records,method,k,config,exclude):
    return Engine(records).search(query,records,method=method,k=k,exclude_id=exclude)
render(rows,read_settings(),run)
"""
        app=AppTest.from_string(script,default_timeout=45).run()
        self.assertFalse(app.exception)
        next(b for b in app.button if b.label=='Build relationship graph').click().run()
        self.assertFalse(app.exception)
        graph=app.session_state['graph_result']
        self.assertTrue(graph['results'])
        data=relationship_data(graph['query'],graph['results'],include_entities=True)
        choice=next(key for key,node in data['nodes'].items() if node.get('entity_type')=='location')
        next(w for w in app.selectbox if w.label=='Inspect node or connection').set_value(choice).run()
        self.assertFalse(app.exception)
        next(w for w in app.text_input if w.label=='Find within graph').set_value('no-such-report-phrase').run()
        self.assertFalse(app.exception)


    def test_noir_nodes_and_differences_require_actual_evidence(self):
        plain=relationship_data(self.query,[self.hit],include_entities=True)
        self.assertFalse(any(e['type']=='contradiction' for e in plain['edges']))
        self.hit['explanation']['structured']={'contradictions':[{'field':'location','query':'Lotus','candidate':'River','note':'Recorded values differ'}]}
        data=relationship_data(self.query,[self.hit],include_entities=True)
        differences=[e for e in data['edges'] if e['type']=='contradiction']
        self.assertEqual(len(differences),1)
        self.assertEqual(differences[0]['evidence'][0]['field'],'location')
        fig=relationship_graph(self.query,[self.hit],include_entities=True)
        self.assertEqual(fig.data[-1].marker.color[0],'#ECE6D6')
        report_index=list(fig.data[-1].customdata).index('report:C')
        self.assertEqual(fig.data[-1].marker.color[report_index],'#1D1D19')
        self.assertEqual(fig.data[-1].marker.line.color[report_index],'#E07A70')
        # Recorded differences use readable rose on the intentional ink graph.
        self.assertEqual(next(t for t in fig.data if t.name=='contradiction').line.color,'#E07A70')



    def test_coincident_edge_endpoint_selects_report_and_midpoint_selects_link(self):
        data=relationship_data(self.query,[self.hit],include_entities=True)
        figure=relationship_graph(self.query,[self.hit],include_entities=True)
        for edge,trace in zip(data['edges'],figure.data[:-1]):
            self.assertEqual(trace.customdata[0],edge['source'])
            self.assertEqual(trace.customdata[1],edge['id'])
            self.assertEqual(trace.customdata[2],edge['target'])
        literal=next(edge for edge in data['edges'] if edge['type']=='source_mention' and edge['source']=='report:C')
        endpoint_event=[{'customdata':literal['source'],'point_index':0},{'customdata':'report:C','point_index':1}]
        self.assertEqual(relationship_selection(endpoint_event,data),'report:C')
        # Plotly may return a coincident node after a link point. Nodes take precedence.
        mixed_event=[{'customdata':literal['id'],'point_index':1},{'customdata':'report:C'}]
        self.assertEqual(relationship_selection(mixed_event,data),'report:C')
        self.assertEqual(relationship_selection([{'customdata':literal['id']}],data),literal['id'])
        self.assertEqual(relationship_selection([{'customdata':'C'}],data),'report:C')
        self.assertIsNone(relationship_selection([{'customdata':'stale-graph-id'},{}],data))



class NoirAnalysisPresentationTests(unittest.TestCase):
    def test_analysis_preserves_multilingual_queries_actual_scores_and_review_state(self):
        from streamlit.testing.v1 import AppTest
        script="""
from sherlocked.ui_analysis import render
from sherlocked.dataset import generate
from sherlocked.settings import read_settings
render(generate(),read_settings())
"""
        app=AppTest.from_string(script,default_timeout=45).run()
        self.assertFalse(app.exception)
        queries=['A bicycle is missing near Lotus square.','সাক্ষী পদ্ম চত্বরে সাইকেল দেখেন।','পদ্ম square bicycle missing.']
        for text in queries:
            next(w for w in app.text_area if w.label=='Original report').set_value(text)
            next(w for w in app.selectbox if w.label=='Retrieval method').set_value('BM25')
            next(b for b in app.button if b.label=='Discover related reports').click().run()
            self.assertFalse(app.exception,str(app.exception))
            bundle=app.session_state['analysis_result']
            self.assertEqual(bundle['query']['text'],text)
            self.assertTrue(bundle['results'])
            self.assertTrue(bundle.get('completed_at_utc'))
            markup=' '.join(str(w.value) for w in app.markdown)
            self.assertIn(f"{bundle['results'][0]['score']:.4f}",markup)
            self.assertIn('HUMAN REVIEW / UNREVIEWED',markup)
            self.assertFalse(any('approve' in b.label.casefold() for b in app.button))


if __name__=='__main__': unittest.main()

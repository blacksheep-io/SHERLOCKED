"""Relationship intelligence canvas and source evidence inspector."""
from datetime import datetime,timezone
import streamlit as st
from .signals import enrich_report
from .visualization import relationship_graph,relationship_data,relationship_selection


def render(records,settings,search_fn=None):
    from .ui import search,heading,source,explain,download,METHODS
    from .design import panel_header,source_document,status_badge
    from .evidence_ui import review_gate
    search_fn=search_fn or search
    heading('The Relationship Board','A source-backed board of report suggestions, literal mentions, and recorded differences. Select a connection to open its evidence.')
    if not records: st.info('No fictional reports are available. Add a dataset in Report Explorer.'); return
    by_id={r['report_id']:r for r in records}
    controls=st.columns([2.1,1.7,1.1,1.4],vertical_alignment='bottom')
    selected=controls[0].selectbox('Central report',list(by_id))
    method=controls[1].selectbox('Graph retrieval method',list(METHODS))
    count=controls[2].slider('Neighbors',1,10,5)
    build=controls[3].button('Build relationship graph',type='primary',width='stretch')
    if build:
        hits=search_fn(by_id[selected],records,METHODS[method],count,settings,selected)
        if hits is not None:
            st.session_state.graph_result={'query':by_id[selected],'results':hits,'configuration':dict(settings),'method':METHODS[method],'completed_at_utc':datetime.now(timezone.utc).isoformat()}
            st.session_state.pop('relationship_last_selection',None)
            st.rerun()
    graph=st.session_state.get('graph_result') or {'query':by_id[selected],'results':[],'configuration':dict(settings),'method':None}
    filters=st.columns([2.4,1.5,2.6])
    needle=filters[0].text_input('Find within graph',placeholder='Report ID, phrase, source mention…')
    entities=filters[1].toggle('Show source mentions',value=True)
    layer_labels={'Report suggestions':'suggested_report','Source mentions':'source_mention','Mention comparisons':'suggested_entity','Human-documented links':'documented','Recorded differences':'contradiction'}
    types=sorted({m['type'] for r in [graph['query'],*[h['report'] for h in graph['results']]] for m in enrich_report(r).get('entities',[])})
    with filters[2].expander('Connection and mention filters'):
        layers=st.multiselect('Connection layers',list(layer_labels),default=list(layer_labels))
        entity_types=st.multiselect('Mention types',types,default=types) if entities and types else None
    args=dict(include_entities=entities,entity_types=entity_types,filter_text=needle,documented_links=graph.get('documented_links',[]),layers=[layer_labels[l] for l in layers],max_mentions=5)
    data=relationship_data(graph['query'],graph['results'],**args)
    report_edges=sum(e['type']=='suggested_report' for e in data['edges']); mention_edges=sum(e['type']=='source_mention' for e in data['edges'])
    st.markdown(status_badge(f"{len(data['reports'])} REPORTS")+' '+status_badge(f'{report_edges} SUGGESTED LINKS','info')+' '+status_badge(f'{mention_edges} SOURCE MENTIONS')+' '+status_badge('HUMAN REVIEW / UNREVIEWED','warning'),unsafe_allow_html=True)
    canvas,inspector=st.columns([7,3],gap='medium')
    with canvas:
        panel_header('The evidence board','Ivory: source report · rose outline: candidate file · brass: source-specific mention')
        figure=relationship_graph(graph['query'],graph['results'],**args,selected_id=st.session_state.get('relationship_inspect_choice'),height=655)
        event=st.plotly_chart(figure,on_select='rerun',selection_mode='points',width='stretch',key='relationship_canvas',config={'scrollZoom':True,'displaylogo':False,'modeBarButtonsToRemove':['lasso2d','select2d']})
        st.caption('Dashed rose / AI suggestion · solid grey / literal mention · dotted brass / mention comparison · oxblood / recorded difference')
        st.caption('Drag to pan · scroll or toolbar to zoom · select a node or edge midpoint to inspect. No identity is automatically merged.')
        if not graph['results']: st.info('The canvas shows actual source mentions only. Build the graph to compute report suggestions.')
        elif not report_edges and 'Report suggestions' in layers: st.info('No positive report suggestions match the current search and filters.')
    with inspector:
        panel_header('Connection dossier','Original sources and actual computational signals')
        review_gate()
        edges={e['id']:e for e in data['edges']}; choices=list(data['nodes'])+list(edges)
        points=event.get('selection',{}).get('points',[]) if event else []; signature=repr(points)
        if points and signature!=st.session_state.get('relationship_last_selection'):
            clicked=relationship_selection(points,data)
            if clicked in choices: st.session_state.relationship_inspect_choice=clicked
            st.session_state.relationship_last_selection=signature
        if st.session_state.get('relationship_inspect_choice') not in choices: st.session_state.relationship_inspect_choice=data['query_id']
        def label(key):
            node=data['nodes'].get(key)
            if node: return ('REPORT · ' if node['type']=='report' else node['entity_type'].upper()+' · ')+node['label']+((' · '+node['report_id']) if node['type']=='mention' else '')
            edge=edges[key]; return 'LINK · '+edge['label']+' · '+data['nodes'][edge['target']]['label']
        target=st.selectbox('Inspect node or connection',choices,format_func=label,key='relationship_inspect_choice')
        if target in data['nodes']:
            node=data['nodes'][target]
            if node['type']=='report':
                source_document(node['report'],compact=True); hit=data['hits'].get(node['report_id'])
                if hit:
                    st.caption(f"{hit.get('method','retrieval')} · score {hit['score']:.4f} · potential relationship")
                    with st.expander('Ranking signals and source evidence'): explain(hit,graph['query'])
            else:
                mention=node['mention']; record=data['reports'][node['report_id']]
                st.markdown(status_badge(node['entity_type'].upper(),'info'),unsafe_allow_html=True); st.text(mention['surface'])
                st.caption('Literal source span; entity identity remains unverified.'); st.code(f"{record.get('source_id','')} [{mention['start']}:{mention['end']}]")
                st.text(record['text'][max(0,mention['start']-65):min(len(record['text']),mention['end']+65)])
                with st.expander('Original source report'): source(record)
        else:
            edge=edges[target]; st.markdown(status_badge(edge['label'],'info'),unsafe_allow_html=True); st.caption(edge['status'])
            if edge.get('score') is not None: st.metric('Ranking signal',f"{edge['score']:.4f}"); st.caption('Not a calibrated probability.')
            if edge['type']=='suggested_report':
                with st.expander('Source-grounded matching evidence',expanded=True): explain(edge['hit'],graph['query'])
            else:
                st.json(edge['evidence'])
                if edge.get('human_confirmation'): st.json(edge['human_confirmation'])
        if data['human_verified_count']==0: st.caption('No verified investigative link is stored in this workspace. The review gate is read-only; literal mentions do not confirm a relationship.')
        if data['omitted_mentions']: st.caption(f"{data['omitted_mentions']} additional mentions are outside this five-mentions-per-report view; all remain in original sources.")
    download('Export graph evidence',{'query':graph['query'],'results':graph['results'],'nodes':data['nodes'],'edges':data['edges'],'configuration':graph.get('configuration'),'limitations':data['limitation']},'relationship_evidence.json')

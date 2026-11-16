"""Separate authored presentation study. No database or benchmark mutation."""
import html
import json
from datetime import datetime
import plotly.graph_objects as go
import streamlit as st
from .paths import ROOT
from .signals import enrich_report

FIXTURE=ROOT/'assets/illustrative/ashford_manor.json'


@st.cache_data(show_spinner=False)
def _read_fixture(payload):
    fixture=json.loads(payload)
    if fixture.get('research_ground_truth') is not False:
        raise ValueError('Ashford presentation fixture must not carry benchmark claims')
    rows=fixture['reports']
    if not rows or len({r['report_id'] for r in rows})!=len(rows):raise ValueError('Illustrative source IDs must be unique')
    for row in rows:
        if row.get('fictional') is not True or any(key in row for key in ['family_id','split']):raise ValueError('Illustrative sources must be fictional and separate from benchmark partitions')
        datetime.fromisoformat(row['occurred_at'])
        if row['occurred_at'] not in row['text']:raise ValueError('Illustrative timeline time must be stated in its source narrative')
    return fixture


def load_fixture():
    return _read_fixture(FIXTURE.read_text(encoding='utf-8-sig'))


def timeline(reports):
    reports=sorted(reports,key=lambda r:r['occurred_at'])
    colors={'en':'#121211','bn':'#9B1C1C','mixed':'#B08D57'}
    fig=go.Figure(go.Scatter(x=[r['occurred_at'] for r in reports],y=[0]*len(reports),mode='markers+text',
        marker={'size':12,'color':[colors.get(r['language'],'#4A463E') for r in reports],'line':{'color':'#FBF8F0','width':3}},
        text=[r['report_id'] for r in reports],textposition=['top center' if i%2 else 'bottom center' for i in range(len(reports))],
        textfont={'family':'Consolas,monospace','size':12,'color':'#121211'},customdata=[[r['source_id'],r['title'],r['occurred_at']] for r in reports],
        hovertemplate='%{customdata[1]}<br>%{customdata[2]}<br>%{customdata[0]}<extra></extra>'))
    fig.update_layout(showlegend=False,margin={'l':30,'r':30,'t':35,'b':35},xaxis={'type':'date','tickformat':'%H:%M','title':'Authored observation times / UTC+06:00'},yaxis={'visible':False,'range':[-1,1]})
    return fig


def render(settings):
    from .ui import heading,METHODS,search,explain,download
    from .design import panel_header,section_label,status_badge,source_document,chart_theme,empty_state
    from .visualization import relationship_graph
    fixture=load_fixture();records=[enrich_report(row) for row in fixture['reports']];by_id={row['report_id']:row for row in records}
    heading('Ashford Manor','Separate demo corpus. Six fictional sources for presentation, never part of the research benchmark or local report database.')
    st.markdown('<div class="am-hero"><small>SEPARATE DEMO CORPUS / AUTHORED 05 NOV 2026</small><div class="am-title">The missing archive folio.</div><p>Six accounts describe a blue-ribbon cover, an interrupted passage light and an incomplete inventory. Read each original source before interpreting a possible connection.</p><div class="am-provenance">FICTIONAL AND UNREVIEWED / NO BENCHMARK LABELS / NO VERIFIED PERSON IDENTITIES</div></div>',unsafe_allow_html=True)
    overview,brief=st.columns([1.65,1],gap='medium')
    with overview:
        with st.container(border=True):
            st.image((ROOT/'assets/illustrative/ashford_manor_plan.svg').read_text(encoding='utf-8'),width='stretch')
            st.caption('Original fictional architectural illustration. No measured scene geometry, reconstruction or movement paths are asserted.')
    with brief:
        with st.container(border=True):
            panel_header('Demo source register','Six authored records / English, Bangla and mixed language')
            st.markdown(status_badge('SEPARATE DEMO CORPUS','warning')+' '+status_badge('NOT EVALUATION DATA','neutral'),unsafe_allow_html=True)
            st.write('**Question:** Which reports share inspectable signals with the missing-folio note?')
            st.write('**Unknown:** Whether the observed cover or folder belongs to the missing folio.')
            st.caption(fixture['provenance'])
    with st.container(border=True):
        panel_header('Recorded observation times','Each point references a timestamp explicitly stated in its authored source')
        st.plotly_chart(chart_theme(timeline(records),height=180),width='stretch',key='ashford_timeline',config={'displaylogo':False})
        st.caption(fixture['timeline_note'])
    source,analysis=st.columns([1.1,1],gap='medium')
    with source:
        with st.container(border=True):
            panel_header('Original account','Read the source before interpreting a matching signal')
            selected=st.selectbox('Ashford source report',list(by_id),format_func=lambda rid:rid+' / '+by_id[rid].get('title',''),key='ashford_source')
            source_document(by_id[selected])
            st.caption('Entity extraction remains heuristic; literal mention overlap does not resolve negation or identity.')
    with analysis:
        with st.container(border=True):
            panel_header('Compare the demo sources','Actual retrieval over this separate six-source corpus')
            with st.form('ashford_discovery'):
                method_name=st.selectbox('Archive retrieval method',list(METHODS),key='ashford_method')
                k=st.slider('Archive result limit',1,5,4,key='ashford_k')
                run=st.form_submit_button('Analyze archive links',type='primary',icon=':material/biotech:')
            st.caption('The lexical index fits this six-document demonstration corpus. These rankings are not a research evaluation or known relationship labels.')
            if run:
                hits=search(by_id[selected],records,METHODS[method_name],k,settings,selected)
                if hits is not None:
                    st.session_state.ashford_analysis={'query':by_id[selected],'results':hits,'method':METHODS[method_name],'configuration':dict(settings),'fixture_provenance':fixture['provenance']}
                    st.rerun()
    bundle=st.session_state.get('ashford_analysis')
    if not bundle:
        empty_state('No archive links computed','Choose a source and run comparison. The graph will display actual retrieval outputs only.');return
    section_label(f"LAST COMPUTED / {bundle['query']['report_id']} / {bundle['method'].upper()} / {len(bundle['results'])} SUGGESTIONS")
    if selected!=bundle['query']['report_id']:st.info('The selected source changed. Run comparison again to replace the last computed analysis shown below.')
    graph,evidence=st.columns([1.25,1],gap='medium')
    with graph:
        with st.container(border=True):
            panel_header('Unverified source relationships','Computed suggestions only / no confirmed investigative links')
            st.plotly_chart(relationship_graph(bundle['query'],bundle['results'],include_entities=True,height=460),width='stretch',key='ashford_graph',config={'displaylogo':False})
    with evidence:
        with st.container(border=True):
            panel_header('Source-linked evidence','Inspect an individual suggested connection')
            options=[hit['report']['report_id'] for hit in bundle['results']]
            if options:
                target=st.selectbox('Inspect Ashford link',options,key='ashford_target')
                explain(next(hit for hit in bundle['results'] if hit['report']['report_id']==target),bundle['query'])
            else:empty_state('No positive signals','Choose another source or explicitly select another retrieval method.')
    download('Export Ashford comparison',bundle,'ashford_illustrative_comparison.json')

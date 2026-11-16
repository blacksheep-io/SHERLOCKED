"""Dark document intelligence views from actual local sources and results."""
import hashlib
import html
import json
import math
from collections import Counter,defaultdict
from datetime import datetime
import plotly.graph_objects as go
import streamlit as st
from .ingestion import decode_text,export_jsonl
from .signals import analyze_report
from .semantic import get_shared_encoder
from .paths import resource_path

COLORS={'en':'#9B1C1C','bn':'#B08D57','mixed':'#4A463E','unknown':'#E07A70'}
LANGUAGES={'en':'English','bn':'Bangla','mixed':'Mixed / transliterated','unknown':'Unknown'}


def _date_label(value):
    if not value:return 'Time unknown'
    try:
        date=datetime.fromisoformat(value.replace('Z','+00:00'))
        return date.strftime('%d %b %Y')+(' / '+date.strftime('%H:%M') if 'T' in value else '')
    except (ValueError,AttributeError):return str(value)


def _language_donut(records):
    counts=Counter(r.get('language','unknown') for r in records);names=sorted(counts)
    fig=go.Figure(go.Pie(labels=[LANGUAGES.get(n,n) for n in names],values=[counts[n] for n in names],hole=.76,sort=False,textinfo='none',
        marker={'colors':[COLORS.get(n,'#4A463E') for n in names],'line':{'color':'#FBF8F0','width':3}},hovertemplate='%{label}<br>%{value} sources / %{percent}<extra></extra>'))
    fig.update_layout(showlegend=False,margin=dict(l=5,r=5,t=5,b=5),annotations=[dict(text=f'<b>{len(records)}</b>',x=.5,y=.55,showarrow=False,font={'size':25,'color':'#121211'}),dict(text='SOURCES',x=.5,y=.38,showarrow=False,font={'size':12,'color':'#4A463E'})])
    return fig


def _family_grid(records):
    groups=defaultdict(list)
    for record in records:groups[record.get('family_id') or 'Unassigned'].append(record)
    families=sorted(groups);cols=min(6,max(1,len(families)));rows=max(1,math.ceil(len(families)/cols))
    z=[[None]*cols for _ in range(rows)];text=[['']*cols for _ in range(rows)];hover=[['']*cols for _ in range(rows)]
    for i,family in enumerate(families):
        r,c=divmod(i,cols);items=groups[family];splits=sorted({item.get('split','unassigned') for item in items})
        z[r][c]={'train':0,'dev':1,'test':2,'unassigned':3}.get(splits[0],3) if len(splits)==1 else 3
        partition=splits[0].upper() if len(splits)==1 else 'MIXED'
        text[r][c]=f'{html.escape(str(family))}<br><b>{len(items)}</b> / {partition}'
        coverage=', '.join(f'{lang}: {count}' for lang,count in sorted(Counter(item.get('language','unknown') for item in items).items()))
        hover[r][c]=f'{family}<br>{len(items)} fictional reports<br>Partition: {", ".join(splits)}<br>{coverage}'
    scale=[[0,'#E8E1D1'],[.166,'#E8E1D1'],[.167,'#E8D4B5'],[.499,'#E8D4B5'],[.5,'#DDDAD4'],[.833,'#DDDAD4'],[.834,'#F3E6D7'],[1,'#F3E6D7']]
    fig=go.Figure(go.Heatmap(z=z,zmin=0,zmax=3,text=text,texttemplate='%{text}',textfont={'size':12,'color':'#121211'},customdata=hover,hovertemplate='%{customdata}<extra></extra>',colorscale=scale,showscale=False,xgap=5,ygap=5))
    fig.update_layout(margin=dict(l=0,r=0,t=0,b=0),xaxis={'visible':False},yaxis={'visible':False,'autorange':'reversed'})
    return fig,rows


def _inventory_health(records):
    ids=[r.get('report_id') for r in records];families=defaultdict(set)
    for row in records:
        if row.get('family_id'):families[row['family_id']].add(row.get('split'))
    checks=[('Unique source IDs',len(ids)==len(set(ids))),('Fictional records',all(r.get('fictional') is True for r in records)),('Source references',all(bool(r.get('source_id')) for r in records)),('Family isolation',all(len(s)==1 for s in families.values()))]
    try:
        folder=resource_path('dataset');manifest=json.loads((folder/'manifest.json').read_text(encoding='utf-8-sig'))
        checks.append(('Canonical checksum',hashlib.sha256((folder/'reports.jsonl').read_bytes()).hexdigest()==manifest.get('sha256')))
    except (OSError,ValueError):checks.append(('Canonical checksum',False))
    return checks


@st.cache_data(ttl=30,show_spinner=False)
def _hardware_status():
    try:
        import torch
        available=torch.cuda.is_available()
        return dict(cuda=available,gpu=torch.cuda.get_device_name(0) if available else None,torch=torch.__version__,error=None)
    except Exception as error:return dict(cuda=False,gpu=None,torch=None,error=str(error))



def dashboard(records,settings):
    from .ui import heading,paths
    from .design import panel_header,status_badge,chart_theme
    heading('Intelligence Dashboard','The local research register. Original sources, measured experiments and unverified report relationships.')
    recent=paths();families={r['family_id'] for r in records if r.get('family_id')};languages=Counter(r.get('language','unknown') for r in records)
    st.markdown(f'<div class="noir-cover"><div><div class="noir-cover-kicker">Source collection / fictional research</div><div class="noir-cover-title">An archive of<br>possible connections.</div><p>Read the sources. Compare the signals. Keep a suggested relationship separate from a confirmed finding.</p></div><div class="noir-register"><div><span>Registered reports</span><b>{len(records):03d}</b></div><div><span>Scenario families</span><b>{len(families):02d}</b></div><div><span>Language views</span><b>{len(languages):02d}</b></div><div><span>Saved measured runs</span><b>{len(recent):02d}</b></div></div></div>',unsafe_allow_html=True)
    collection,desk=st.columns([1.6,1],gap='large')
    with collection:
        with st.container(border=True):
            panel_header('Collection composition','Language coverage / authored source labels')
            ring,coverage=st.columns([.85,1.15],vertical_alignment='center')
            with ring:st.plotly_chart(chart_theme(_language_donut(records),height=185),width='stretch',key='language_coverage',config={'displayModeBar':False})
            with coverage:
                for name,count in sorted(languages.items()):
                    st.markdown(f'<div class="ds-row"><span>{html.escape(LANGUAGES.get(name,name))}</span><strong>{count:02d} / {count/max(1,len(records))*100:.0f}%</strong></div>',unsafe_allow_html=True)
                st.caption('Language labels are authored. Script detection does not reliably identify Latin-only transliteration.')
            panel_header('Scenario register','Actual family counts / partition boundaries')
            fig,rows=_family_grid(records)
            st.plotly_chart(chart_theme(fig,height=max(185,rows*64)),width='stretch',key='family_coverage',config={'displayModeBar':False})
            st.markdown('<div class="ds-legend"><span><i style="background:#E8E1D1"></i>TRAIN</span><span><i style="background:#E8D4B5"></i>DEVELOPMENT</span><span><i style="background:#DDDAD4"></i>TEST</span><span><i style="background:#F3E6D7"></i>UNASSIGNED</span></div>',unsafe_allow_html=True)
            st.markdown('<div class="ds-tags">'+''.join(status_badge(label,'success' if ok else 'error') for label,ok in _inventory_health(records))+'</div>',unsafe_allow_html=True)
            st.caption('Checks describe dataset integrity. They do not verify any investigative relationship.')
    with desk:
        _station(settings)
        _activity()
    _experiment_ledger(recent)
    st.caption('Controlled synthetic data only. Small-sample results do not establish real-world investigative accuracy.')



def _station(settings):
    from .design import panel_header,status_badge
    with st.container(border=True):
        panel_header('Inference ledger','Model assets / hardware capability / actual active device')
        status=get_shared_encoder(device=settings.get('device','auto'),allow_download=settings.get('model_mode','offline')=='online').status();hardware=_hardware_status()
        st.markdown(status_badge('MODEL ASSETS READY' if status['available'] else 'MODEL SETUP REQUIRED','success' if status['available'] else 'warning')+' '+status_badge('CUDA AVAILABLE' if hardware['cuda'] else 'CPU CAPABILITY','info' if hardware['cuda'] else 'neutral'),unsafe_allow_html=True)
        for label,value in [('Encoder',status.get('model_id','Unknown')),('Dimensions',status.get('dimensions','Unknown')),('Requested device',settings.get('device','auto')),('Active inference',status.get('active_device') or 'Not loaded'),('Hardware',hardware.get('gpu') or 'CPU'),('PyTorch',hardware.get('torch') or 'Unavailable')]:
            st.markdown(f'<div class="ds-row"><span>{html.escape(label)}</span><strong>{html.escape(str(value))}</strong></div>',unsafe_allow_html=True)
        if status.get('fallback_reason'):st.warning(status['fallback_reason'])
        if hardware.get('error'):st.warning('Hardware inspection failed: '+hardware['error'])
        st.caption('CUDA capability is distinct from active inference. Model failure never substitutes a retrieval method.')


def _activity():
    from .design import panel_header,empty_state
    with st.container(border=True):
        panel_header('Session notes','Completed searches / newest first')
        activity=st.session_state.get('analysis_activity',[]);bundle=st.session_state.get('analysis_result')
        if activity:
            for event in activity[:4]:
                st.markdown(f'<div class="ds-link"><div><b>{html.escape(str(event.get("query_id","query")))}</b><small>{html.escape(str(event.get("method","retrieval")))} / {html.escape(str(event.get("time","")))}</small></div><span>{html.escape(str(event.get("count",0)))} LINKS</span></div>',unsafe_allow_html=True)
        elif bundle:
            st.markdown(f'<div class="ds-link"><div><b>{html.escape(bundle["query"]["report_id"])}</b><small>{html.escape(bundle.get("method","retrieval"))} / time not recorded</small></div><span>{len(bundle["results"])} LINKS</span></div>',unsafe_allow_html=True)
        else:empty_state('The session register is empty','Run report discovery to record an actual search. Session notes are not a persisted audit trail.')
    with st.container(border=True):
        panel_header('Suggested connections','Latest available completed result / unverified')
        selected=_recent_relationship_bundle(st.session_state.get('analysis_result'),st.session_state.get('graph_result'),activity)
        bundle=selected['bundle'] if selected else None
        if bundle and bundle.get('results'):
            st.caption(selected['origin']+' / '+(selected['recorded_at'] or 'Undated session result'))
            for hit in bundle['results'][:4]:
                st.markdown(f'<div class="ds-link"><div><b>{html.escape(bundle["query"]["report_id"])} → {html.escape(hit["report"]["report_id"])}</b><small>{html.escape(hit.get("method",bundle.get("method","retrieval")))} / human review required</small></div><span>{hit["score"]:.4f}</span></div>',unsafe_allow_html=True)
            st.caption('Ranking signals are not probabilities. Source evidence is available in Relationship Explorer.')
        elif bundle:empty_state('The latest run returned no positive links','Earlier suggestions are not substituted for the newest empty result.')
        else:empty_state('No connections have been computed','Build a graph or run an analysis. This panel does not invent relationships.')



def explorer(records,store):
    from .ui import heading
    from .design import panel_header,section_label,status_badge,source_document,empty_state
    heading('Report Explorer','A source-first document workspace. Original narratives remain immutable and extracted views retain provenance.')
    if st.session_state.pop('report_saved',False):st.success('Fictional report saved locally. It remains outside the canonical research benchmark.')
    browse,submit=st.tabs(['Browse reports','Submit fictional report'])
    with browse:
        index,document=st.columns([.92,1.55],gap='medium')
        with index:
            with st.container(border=True):
                panel_header('Source register','Search the collection / open an original source')
                query=st.text_input('Search ID, narrative or metadata',placeholder='ID / location / source text',key='report_filter',icon=':material/search:')
                one,two=st.columns(2)
                language=one.selectbox('Language',['All']+sorted({r.get('language','unknown') for r in records}),key='report_language')
                incident=two.selectbox('Incident type',['All']+sorted({r['incident_type'] for r in records if r.get('incident_type')}),key='report_incident')
                filtered=[]
                for record in records:
                    haystack=' '.join(str(record.get(field) or '') for field in ['report_id','text','location','incident_type','source_id']).casefold()
                    if (not query or query.casefold() in haystack) and (language=='All' or record.get('language')==language) and (incident=='All' or record.get('incident_type')==incident):filtered.append(record)
                section_label(f'{len(filtered):03d} MATCHING / {len(records):03d} TOTAL')
                if filtered:
                    st.dataframe([{'ID':r['report_id'],'Lang':r.get('language','unknown').upper(),'Document preview':r['text'][:90]} for r in filtered],hide_index=True,width='stretch',height=300)
                    selected=st.selectbox('Inspect report',[r['report_id'] for r in filtered],key='report_inspect')
                    report=next(r for r in filtered if r['report_id']==selected)
                    st.download_button('Export filtered reports as JSONL',export_jsonl(filtered),'sherlocked-filtered-reports.jsonl','application/x-ndjson',key='export_filtered',icon=':material/download:')
                else:report=None;empty_state('No matching sources','Change the search text or clear the language and incident filters.')
        with document:
            if report is None:
                with st.container(border=True):empty_state('Source inspection','Select a matching report from the document index.')
            else:
                with st.container(border=True):
                    panel_header('Original source',report['report_id']+' / immutable narrative')
                    st.markdown('<div class="ds-tags">'+status_badge(report.get('language','unknown').upper(),'info')+status_badge((report.get('incident_type') or 'TYPE UNKNOWN').replace('_',' '),'neutral')+status_badge(_date_label(report.get('occurred_at')),'neutral')+status_badge('FICTIONAL','warning')+'</div>',unsafe_allow_html=True)
                    source_document(report)
                    if st.button('Use in analysis',key='use_explorer_report',type='primary',icon=':material/biotech:'):
                        st.session_state.selected_query=report;st.success('Report selected. Open AI Analysis Workspace to inspect related-report suggestions.')
                _document_intelligence(report)
    with submit:
        _submission(store)


def _document_intelligence(report):
    from .design import panel_header,empty_state
    with st.container(border=True):
        panel_header('Source annotations','Literal mentions and recorded fields / identity unverified')
        mentions,fields,trace=st.tabs(['Entity mentions','Recorded fields','Source trace'])
        provenance=report.get('metadata_provenance',{})
        with mentions:
            entities=report.get('entities') or []
            if entities:
                st.dataframe([{'Type':e.get('type'),'Original mention':e.get('surface',e.get('value','')),'Span':f"{e.get('start','?')}:{e.get('end','?')}",'Method':e.get('method','provided annotation')} for e in entities],hide_index=True,width='stretch')
                st.caption('Half-open Unicode offsets reference the original narrative. Similar names never establish shared identity.')
            else:empty_state('No explicit entities extracted','Unknown information is not a negative match. Inspect the source before interpreting a missing mention.')
        with fields:
            rows=[]
            for field in ['incident_type','location','occurred_at']:
                origin=provenance.get(field,{})
                rows.append({'Field':field,'Value':report.get(field) or 'Unknown','Provenance':origin.get('method','Unknown') if isinstance(origin,dict) else str(origin)})
            st.dataframe(rows,hide_index=True,width='stretch');st.caption('Fixture annotations may not appear in the narrative. They remain distinct from extraction.')
        with trace:
            st.text(report.get('source_id','Source reference unavailable'))
            st.caption(f"Partition: {report.get('split','unassigned')} / Variant: {report.get('variant','unknown')} / Generator: {report.get('generator_version','unknown')}")
            with st.expander('Full extracted views and provenance'):st.json({'entities':report.get('entities',[]),'metadata_provenance':provenance,'language_detection':report.get('language_detection',{})})


def _submission(store):
    from .design import panel_header
    with st.container(border=True):
        panel_header("File a fictional source","Local collection only / excluded from the canonical benchmark")
        st.caption('Saved reports are local, unassigned to a scenario family, and do not enter the fixed research benchmark. Entity labels such as Person:, Organization:, Location: and Identifier: can make explicit mentions inspectable.')
        with st.form('submit_fictional_report',clear_on_submit=False):
            text=st.text_area('Original fictional narrative',height=180,max_chars=100000,key='new_report_text',placeholder='Write an English, Bangla or mixed-language fictional report…')
            upload=st.file_uploader('Or use a UTF-8 .txt source (uploaded text takes precedence)',type=['txt'],key='new_report_upload')
            one,two=st.columns(2)
            incident=one.selectbox('Optional confirmed incident type',['Extract automatically','missing_property','theft','fire','damage','lost_property'],key='new_report_incident')
            location=two.text_input('Optional confirmed location',key='new_report_location')
            occurred=st.text_input('Optional confirmed date / time (ISO 8601)',placeholder='2025-03-01 or 2025-03-01T18:00:00+06:00',key='new_report_date')
            confirmed=st.checkbox('I confirm that this report is fictional.',key='new_report_confirm')
            save=st.form_submit_button('Save fictional report',type='primary')
        if save:
            try:
                if not confirmed:
                    raise ValueError('Confirm that the report is fictional before saving.')
                original=decode_text(upload.getvalue()) if upload else text
                metadata={}
                if incident!='Extract automatically':metadata['incident_type']=incident
                if location.strip():metadata['location']=location.strip()
                if occurred.strip():
                    datetime.fromisoformat(occurred.strip().replace('Z','+00:00'))
                    metadata['occurred_at']=occurred.strip()
                report=analyze_report(original,metadata=metadata)
                store.add_report(report)
                st.session_state.selected_query=report
                st.session_state.report_saved=True
                st.rerun()
            except (ValueError,TypeError) as error:
                st.error(str(error))


def _experiment_ledger(recent):
    from .ui import download
    from .design import panel_header,section_label,empty_state
    with st.container(border=True):
        panel_header('Research ledger','Latest saved measurements / historical artifacts remain unchanged')
        if not recent:
            empty_state('No measured experiment yet','Run an evaluation in Research Evaluation Lab. No illustrative performance numbers are substituted.');return
        try:
            result=json.loads(recent[0].read_text(encoding='utf-8'))
            section_label(f"{result.get('split','unknown').upper()} / K={result.get('k','?')} / {result.get('experiment_id',recent[0].stem)}")
            rows=[]
            for method,entry in result.get('methods',{}).items():
                values=entry.get('aggregate',{});rows.append({'Method':method,'State':entry.get('status'),'P@K':values.get('precision'),'R@K':values.get('recall'),'MRR':values.get('mrr'),'nDCG@K':values.get('ndcg')})
            st.dataframe(rows,hide_index=True,width='stretch',column_config={name:st.column_config.NumberColumn(format='%.3f') for name in ['P@K','R@K','MRR','nDCG@K']})
            st.caption(f"Source-only metadata: {result.get('configuration',{}).get('source_only',False)} / {result.get('protocol','Protocol stored in artifact')}")
            download('Export latest experiment',result,'sherlocked-latest-experiment.json')
            with st.expander('Recent experiment history'):
                history=[]
                for path in recent[:10]:
                    try:
                        item=json.loads(path.read_text(encoding='utf-8'));history.append({'Experiment':item.get('experiment_id',path.stem),'Split':item.get('split'),'K':item.get('k'),'Created UTC':item.get('created_at_utc')})
                    except (OSError,ValueError):continue
                st.dataframe(history,hide_index=True,width='stretch')
        except (OSError,ValueError) as error:st.warning(f'Experiment artifact could not be read: {error}')



def _recent_relationship_bundle(analysis=None,graph=None,activity=()):
    """Select real completion time, then matching newest-first search events.

    Older sessions without timestamps are explicitly labelled undated; no clock
    value is invented simply because the dashboard was opened.
    """
    def stamp(value):
        try:
            date=datetime.fromisoformat(str(value).replace('Z','+00:00'))
            return date.timestamp() if date.tzinfo is not None else None
        except (ValueError,TypeError):return None
    choices=[]
    for origin,bundle in [('Analysis',analysis),('Graph',graph)]:
        if not bundle:continue
        recorded=bundle.get('completed_at') or bundle.get('finished_at') or bundle.get('created_at')
        timestamp=stamp(recorded);event_index=None
        method=bundle.get('method') or next((hit.get('method') for hit in bundle.get('results',[]) if hit.get('method')),None)
        top=bundle.get('results',[{}])[0].get('report',{}).get('report_id') if bundle.get('results') else None
        for index,event in enumerate(activity):
            if (event.get('query_id')==bundle.get('query',{}).get('report_id') and event.get('method')==method
                    and event.get('count')==len(bundle.get('results',[])) and event.get('top_report')==top):
                event_index=index
                if timestamp is None:
                    recorded=event.get('id');timestamp=stamp(recorded)
                break
        rank=(timestamp is not None,timestamp if timestamp is not None else -event_index if event_index is not None else float('-inf'),origin=='Analysis')
        choices.append((rank,{'bundle':bundle,'origin':origin,'recorded_at':recorded if timestamp is not None else None}))
    return max(choices,key=lambda pair:pair[0])[1] if choices else None


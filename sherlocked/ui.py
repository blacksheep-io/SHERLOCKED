"""SHERLOCKED application shell and presentation-service adapters."""
import json
import logging
from datetime import datetime,timezone
from html import escape
import pandas as pd
import streamlit as st
from .dataset import load
from .engine import Engine
from .signals import enrich_report
from .storage import Store
from .semantic import get_shared_encoder
from .settings import read_settings
from .paths import resource_path,ROOT
from .runtime import configure_logging,save_export
from .design import apply_theme,section_label,status_badge,source_document,dataset_health,chart_theme,logo_uri,page_title,theme_control

SECTIONS=['Intelligence Dashboard','Report Explorer','AI Analysis Workspace','Relationship Explorer','Research Evaluation Lab','System Settings','Ashford Manor']
METHODS={'TF-IDF':'tfidf','BM25':'bm25','Multilingual semantic':'semantic','Entity similarity':'entity','Structured similarity':'structured','Hybrid weighted':'hybrid','Hybrid rank fusion':'rrf','Hybrid evidence reranking':'hybrid_rerank'}
ICONS=['dashboard','folder_open','travel_explore','hub','science','settings','account_balance']

@st.cache_resource
def get_store(database_path=None,dataset_path=None):
    store=Store(database_path or resource_path('database'))
    store.initialize(load(dataset_path or resource_path('dataset')/'reports.jsonl'))
    return store

@st.cache_resource(show_spinner=False,max_entries=3)
def get_engine(rows,config):
    return Engine(json.loads(rows),config=json.loads(config))

@st.cache_data(show_spinner=False,max_entries=3)
def workspace_records(database_path,signature):
    return [enrich_report(r) for r in Store(database_path).list_reports()]

def heading(title,description):
    active=st.session_state.get('active_section',SECTIONS[0])
    number=SECTIONS.index(active)+1 if active in SECTIONS else 1
    section_label(f'SHERLOCKED / MODULE {number:02d} / LOCAL RESEARCH')
    page_title(title,description)

def source(report):
    source_document(report)

def download(label,value,name):
    st.download_button(label,json.dumps(value,ensure_ascii=False,indent=2,default=str),name,'application/json',on_click=save_export,args=(value,name))

def search(query,rows,method,k,config,exclude=None):
    try:
        config={**config,'bm25_k1':config['k1'],'bm25_b':config['b'],'allow_download':config.get('model_mode','offline')=='online'}
        with st.spinner('Computing similarities and source evidence…'):
            engine=get_engine(json.dumps(rows,ensure_ascii=False,sort_keys=True),json.dumps(config,sort_keys=True))
            results=engine.search(query,rows,method=method,k=k,exclude_id=exclude)
            st.session_state.inference_status=engine.semantic.status()
            event={'id':datetime.now(timezone.utc).isoformat(),'time':datetime.now(timezone.utc).strftime('%H:%M:%S UTC'),
                   'method':method,'query_id':query.get('report_id','session'),'count':len(results),
                   'top_report':results[0]['report']['report_id'] if results else None,'top_score':results[0]['score'] if results else None}
            st.session_state.analysis_activity=([event]+st.session_state.get('analysis_activity',[]))[:12]
            return results
    except Exception as error:
        logging.exception('Search failed')
        st.error(f'{method} failed: {error}')
        st.info('Prepare the model in System Settings or explicitly choose TF-IDF / BM25. No method was substituted.')
        return None

def explain(hit,query):
    from .evidence_ui import render
    render(hit,query)

def paths():
    return sorted((resource_path('results')/'experiments').glob('*.json'),key=lambda p:p.stat().st_mtime,reverse=True)

def experiment_table(result):
    rows=[]
    for method,value in result.get('methods',{}).items():
        aggregate=value.get('aggregate',{})
        rows.append({'Method':method,'State':value.get('status'),'P@'+str(result.get('k',5)):aggregate.get('precision'),
                     'R@'+str(result.get('k',5)):aggregate.get('recall'),'MRR':aggregate.get('mrr'),'nDCG@'+str(result.get('k',5)):aggregate.get('ndcg')})
    st.dataframe(pd.DataFrame(rows),hide_index=True,width='stretch',column_config={key:st.column_config.NumberColumn(format='%.3f') for key in rows[0] if key not in ('Method','State')} if rows else None)

def navigate(section):
    st.session_state.active_section=section

def shell(records,settings):
    from .ui_entry import sign_out
    section=st.session_state.get('active_section',SECTIONS[0])
    if section not in SECTIONS: section=SECTIONS[0]
    status=get_shared_encoder(device=settings['device'],allow_download=settings.get('model_mode','offline')=='online').status()
    health=dataset_health()
    model_label='MODEL '+('LOADED' if status.get('loaded') else 'CACHED' if status['available'] else 'MISSING')
    device_label='INFERENCE '+str(status.get('active_device') or 'not loaded').upper()
    with st.sidebar:
        st.markdown('<div class="sk-brand"><img src="'+logo_uri()+'" alt="Original detective emblem: deerstalker, profile and curved pipe"><div><div class="sk-brand-name">SHERLOCKED</div><div class="sk-brand-sub">CASE FILE NOIR</div></div></div><div class="sk-workspace"><small>ACTIVE WORKSPACE</small><strong>LOCAL INVESTIGATIVE RESEARCH</strong>'+status_badge('FICTIONAL SOURCES','warning')+'</div>',unsafe_allow_html=True)
        for group,indices in [('THE INVESTIGATION',[0,1,2,3]),('THE RESEARCH',[4]),('THE ARCHIVE',[6]),('THE SYSTEM',[5])]:
            st.markdown('<div class="sk-nav-group">'+group+'</div>',unsafe_allow_html=True)
            for i in indices:
                st.button(SECTIONS[i],key='nav_'+str(i),icon=':material/'+ICONS[i]+':',type='primary' if section==SECTIONS[i] else 'secondary',width='stretch',on_click=navigate,args=(SECTIONS[i],))
        st.divider()
        st.caption('SIGNED IN / '+st.session_state.get('access_user','local').upper())
        st.button('Sign out',icon=':material/logout:',on_click=sign_out,width='stretch')
        st.markdown(status_badge(model_label,'ai')+' '+status_badge('CORPUS CHECK OK' if health['valid'] else 'CHECK CORPUS','success' if health['valid'] else 'error'),unsafe_allow_html=True)
        st.caption(device_label+' / requested '+settings['device'])
        st.caption(f"{len(records)} source reports / E5-small 384-D")
        if status.get('fallback_reason'): st.warning(status['fallback_reason'])
        st.markdown('<div class="sk-footnote">Every computed link remains a lead.<br>Human review is required.</div>',unsafe_allow_html=True)
    left,middle,right=st.columns([4,1.7,1.4],vertical_alignment='center')
    with left:
        workspace='ASHFORD / SEPARATE DEMO CORPUS' if section=='Ashford Manor' else 'LOCAL LAB / FICTIONAL REPORTS'
        st.markdown('<div class="sk-topline"><strong>'+workspace+'</strong><span class="divider">/</span><span>'+escape(section.upper())+'</span>'+status_badge(model_label,'ai')+status_badge(device_label)+status_badge('CORPUS CHECK OK' if health['valid'] else 'CORPUS CHECK FAILED','success' if health['valid'] else 'error')+'</div>',unsafe_allow_html=True)
    with middle:
        with st.popover('Quick jump',icon=':material/search:',width='stretch'):
            target=st.selectbox('Module',SECTIONS,key='quick_module')
            st.button('Open module',on_click=navigate,args=(target,),width='stretch')
    with right:theme_control()
    return section

def main():
    st.set_page_config(page_title='SHERLOCKED | Case File Noir',page_icon=ROOT/'assets/branding/favicon.svg',layout='wide')
    apply_theme()
    from .ui_entry import gateway
    try:
        if not gateway():return
    except (OSError,ValueError) as error:
        st.error(f'Entry resources could not be opened: {error}');return
    try:
        configure_logging();database=resource_path('database');dataset=resource_path('dataset')/'reports.jsonl'
        store=get_store(str(database),str(dataset))
        signature=tuple((p.stat().st_mtime_ns,p.stat().st_size) if p.exists() else (0,0) for p in [database,database.with_name(database.name+'-wal')])
        records=workspace_records(str(database),signature);settings=read_settings()
    except Exception as error:
        st.error(f'Local resources could not be opened: {error}');st.info('Run SETUP_SHERLOCKED.bat or check configs/paths.json.');st.stop()
    section=shell(records,settings)
    from .ui_data import dashboard,explorer
    from .ui_research import research,system
    if section==SECTIONS[0]: dashboard(records,settings)
    elif section==SECTIONS[1]: explorer(records,store)
    elif section==SECTIONS[2]:
        from .ui_analysis import render
        render(records,settings)
    elif section==SECTIONS[3]:
        from .ui_relationships import render
        render(records,settings)
    elif section==SECTIONS[4]: research(settings)
    elif section==SECTIONS[5]: system(settings,store,records)
    else:
        from .ui_ashford import render
        render(settings)
    st.markdown('<footer class="sk-module-footer">SHERLOCKED / CASE FILE NOIR / LOCAL RESEARCH / SOURCE-TRACEABLE LEADS / HUMAN OVERSIGHT</footer>',unsafe_allow_html=True)


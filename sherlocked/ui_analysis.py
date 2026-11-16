"""CASE FILE NOIR source-to-candidate workspace; existing retrieval is unchanged."""
import csv,io
from datetime import datetime,timezone
from html import escape
import streamlit as st
from .design import panel_header,metric_strip,status_badge,empty_state,source_document
from .runtime import save_export


def candidate_card(hit,rank):
    from .design import ranked_candidate
    ranked_candidate(hit,rank)

def render(records,settings):
    from .ui import heading,search,explain,download,METHODS
    from .signals import analyze_report
    from .semantic import get_shared_encoder
    heading('AI Analysis Workspace','A source document, a ranked set of candidate files, and an inspectable record of why they connect.')
    if not records: empty_state('No source documents available','Import a fictional report dataset in Report Explorer.');return
    by_id={r['report_id']:r for r in records};ids=list(by_id)
    desired=st.session_state.get('selected_query',ids[0]);desired=desired.get('report_id',ids[0]) if isinstance(desired,dict) else desired
    if desired in ids and desired!=st.session_state.get('_applied_query'):
        st.session_state.analysis_source_id=desired;st.session_state._applied_query=desired
    left,right=st.columns([1,1.75],gap='large')
    with left:
        panel_header('The source document','01 / SELECT & PREPARE')
        selected=st.selectbox('Start from dataset report',ids,key='analysis_source_id')
        with st.expander('Source preview or upload',expanded=False):
            source_document(by_id[selected],compact=True)
            upload=st.file_uploader('Or load a UTF-8 fictional report',type=['txt'])
        text=by_id[selected]['text']
        if upload:
            try:
                if upload.size>100000: raise ValueError('Use a UTF-8 report smaller than 100 KB')
                text=upload.getvalue().decode('utf-8')
            except (UnicodeDecodeError,ValueError) as error: st.error(str(error));st.stop()
        with st.form('analysis'):
            query_text=st.text_area('Original report',text,height=160,max_chars=10000)
            panel_header('Retrieval instructions','02 / COMPUTE')
            method_column,count_column=st.columns([2,1])
            method_name=method_column.selectbox('Retrieval method',list(METHODS))
            k=count_column.slider('Top K',1,15,5)
            run=st.form_submit_button('Discover related reports',type='primary',width='stretch')
            with st.expander('Optional manually confirmed metadata'):
                location=st.text_input('Confirmed location');incident=st.text_input('Confirmed incident type')
                st.caption('Leave blank to retain source annotation/extraction. Person: and Identifier: labels make explicit mentions inspectable.')
        status=get_shared_encoder(device=settings['device'],allow_download=settings.get('model_mode','offline')=='online').status()
        st.markdown(status_badge('MODEL ASSETS READY' if status['available'] else 'MODEL SETUP REQUIRED','neutral' if status['available'] else 'warning')+' '+status_badge('DEVICE / '+str(status.get('active_device') or 'not loaded')),unsafe_allow_html=True)
        st.caption('Original text and source offsets are preserved. No result establishes shared identity.')
        if run:
            try:
                same=query_text==by_id[selected]['text'];query=dict(by_id[selected]) if same else analyze_report(query_text)
                query['metadata_provenance']=dict(query.get('metadata_provenance',{}))
                if location: query['location']=location;query['metadata_provenance']['location']='manually confirmed'
                if incident: query['incident_type']=incident;query['metadata_provenance']['incident_type']='manually confirmed'
                hits=search(query,records,METHODS[method_name],k,settings,selected if same else None)
                if hits is not None:
                    st.session_state.analysis_result={'query':query,'results':hits,'method':METHODS[method_name],'configuration':dict(settings),
                        'model':get_shared_encoder(device=settings['device'],allow_download=settings.get('model_mode','offline')=='online').metadata,
                        'completed_at_utc':datetime.now(timezone.utc).isoformat()}
                    st.rerun()
            except ValueError as error: st.error(str(error))
    with right:
        panel_header('The candidate files','03 / RANKED FINDINGS')
        bundle=st.session_state.get('analysis_result')
        if not bundle:
            empty_state('Awaiting an analysis run','Choose a source and retrieval method. Actual candidate files and their evidence will appear here.');return
        hits=bundle['results']
        st.caption('Completed run / '+bundle['method']+' / '+str(bundle['query'].get('report_id','session'))+' / '+str(bundle.get('completed_at_utc','time not recorded')))
        if not hits: empty_state('No positive matching signals','Try another method or add explicitly known details. No method is substituted automatically.');return
        metric_strip([{'label':'Candidate files','value':f'{len(hits):02d}','detail':'potential report relationships'},
                      {'label':'Leading signal','value':f"{hits[0]['score']:.3f}",'detail':bundle['method']+' / not probability'},
                      {'label':'Review gate','value':'UNREVIEWED','detail':'read-only advisory result'}])
        with st.container(height=210,border=False):
            for rank,hit in enumerate(hits,1): candidate_card(hit,rank)
        selected_candidate=st.selectbox('Inspect candidate',[h['report']['report_id'] for h in hits])
        hit=next(h for h in hits if h['report']['report_id']==selected_candidate)
        panel_header('The evidence dossier',selected_candidate+' / '+hit.get('method',bundle['method']))
        explain(hit,bundle['query'])
        inference=st.session_state.get('inference_status',{})
        st.caption('Active inference device: '+str(inference.get('active_device') or 'not loaded / lexical retrieval'))
        if inference.get('fallback_reason'): st.warning(inference['fallback_reason'])
        first,second=st.columns(2)
        with first: download('Export full evidence JSON',bundle,'search_evidence.json')
        output=io.StringIO();writer=csv.writer(output);writer.writerow(['rank','report_id','method','score','status'])
        for i,h in enumerate(hits,1): writer.writerow([i,h['report']['report_id'],bundle['method'],h['score'],h['status']])
        with second: st.download_button('Export rankings CSV',output.getvalue(),'rankings.csv','text/csv',on_click=save_export,args=(output.getvalue(),'rankings.csv',{'configuration':bundle.get('configuration'),'model':bundle.get('model')}))

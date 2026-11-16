"""Scientific experiment workstation and local system diagnostics.

Presentation only: runners, retrieval methods, data and stored artifacts are unchanged.
"""
import html
import hashlib
import json
import subprocess
import sys
from pathlib import Path,PureWindowsPath

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from .experiments import METHODS, list_experiments, run_experiment, summary_csv
from .ingestion import parse_jsonl
from .semantic import get_shared_encoder
from .settings import ROOT, save_settings
from .paths import resource_path, path_report
from .runtime import save_export

# CASE FILE NOIR: warm paper, readable ink, restrained evidentiary accents.
from .design import TOKENS
COLORS = dict(bg=TOKENS['paper'],panel=TOKENS['paper-card'],border=TOKENS['line'],text=TOKENS['ink'],
              muted=TOKENS['muted'],oxblood=TOKENS['oxblood'],rose=TOKENS['rose'],brass=TOKENS['brass'],
              success=TOKENS['ink'],error=TOKENS['oxblood'])
METRICS = ['precision','recall','mrr','ndcg']
LABELS = {'tfidf':'TF-IDF','bm25':'BM25','semantic':'Multilingual E5','entity':'Entity signals',
          'structured':'Structured signals','hybrid':'Weighted hybrid','rrf':'Rank fusion',
          'hybrid_rerank':'Hybrid + contradiction review','hybrid_without_entity':'Without entities',
          'hybrid_without_structured':'Without structured','hybrid_without_semantic':'Without semantic',
          'lexical_semantic':'Lexical + semantic'}
LANGUAGES = {'en':'English','bn':'Bangla','mixed':'Mixed','unknown':'Unknown'}


def _number(value, digits=3):
    return f'{value:.{digits}f}' if value is not None else '—'


def _completed(result):
    return {name:entry for name,entry in result.get('methods',{}).items()
            if entry.get('status')=='completed'}


def _metric_frame(result):
    rows=[]
    for name,entry in result.get('methods',{}).items():
        stats=entry.get('aggregate',{})
        rows.append(dict(method=name,label=LABELS.get(name,name),status=entry.get('status','unknown'),
                         **{key:stats.get(key) for key in METRICS+['query_count','latency_ms','latency_p95_ms']}))
    return pd.DataFrame(rows)


def _metric_matrix(result):
    """Only measured completed methods; absent metrics stay missing, never zero."""
    frame=_metric_frame(result)
    if frame.empty: return frame
    return frame[frame['status']=='completed'].set_index('label')[METRICS]


def _comparison_charts(result):
    from .design import chart_theme,panel_header
    matrix=_metric_matrix(result)
    if matrix.empty:
        st.info('This run has no completed method. Inspect the recorded failure details.')
        return
    cutoff=result['k']
    left,right=st.columns([1.25,1],gap='large')
    with left:
        panel_header('Comparison plate',f'Measured retrieval quality at K={cutoff} · shaded cells retain the exact recorded scores')
        labels=[f'P@{cutoff}',f'R@{cutoff}',f'MRR@{cutoff}',f'nDCG@{cutoff}']
        text=[[_number(value) if pd.notna(value) else '—' for value in row] for row in matrix.values]
        figure=go.Figure(go.Heatmap(z=matrix.values,x=labels,y=matrix.index.tolist(),text=text,
            texttemplate='%{text}',textfont=dict(size=12,color=COLORS['text']),zmin=0,zmax=1,
            colorscale=[[0,COLORS['panel']],[.55,'#E8D9C1'],[1,'#EDB6AE']],showscale=False,
            hovertemplate='%{y}<br>%{x}: %{z:.4f}<extra></extra>',xgap=5,ygap=5))
        figure.update_yaxes(autorange='reversed',tickfont=dict(size=11))
        figure.update_xaxes(side='top',showgrid=False)
        st.plotly_chart(chart_theme(figure,height=max(285,34*len(matrix)+105)),width='stretch',key='method_fingerprint')
    with right:
        panel_header('Confidence notes','nDCG with recorded 95% family-bootstrap intervals')
        figure=go.Figure()
        for name,entry in _completed(result).items():
            score=entry['aggregate'].get('ndcg')
            if score is None: continue
            interval=entry.get('family_bootstrap',{}).get('intervals_95',{}).get('ndcg')
            error=dict(type='data',symmetric=False,array=[max(0,interval[1]-score)],
                       arrayminus=[max(0,score-interval[0])],color=COLORS['muted'],thickness=1.3,width=4) if interval else None
            figure.add_trace(go.Scatter(x=[score],y=[LABELS.get(name,name)],mode='markers',showlegend=False,
                marker=dict(size=9,color=COLORS['oxblood'] if 'hybrid' in name or name=='rrf' else COLORS['brass'],
                            symbol='diamond' if 'hybrid' in name or name=='rrf' else 'circle'),
                error_x=error,hovertemplate='%{y}<br>nDCG: %{x:.4f}<extra></extra>'))
        figure.update_xaxes(range=[-.02,1.03],title='nDCG · binary relevance')
        figure.update_yaxes(autorange='reversed',showgrid=False)
        st.plotly_chart(chart_theme(figure,height=max(285,34*len(matrix)+105)),width='stretch',key='ranking_intervals')
        st.caption('Small family counts make intervals unstable. These are synthetic measurements, not operational accuracy.')


def _ablation_panel(result):
    from .design import chart_theme,panel_header,empty_state
    completed=_completed(result)
    baseline=completed.get('hybrid')
    names=[name for name in completed if name.startswith('hybrid_without_') or name=='lexical_semantic']
    if not baseline or not names:
        empty_state('No ablation study in this run','Enable the component ablations in experiment setup. No ablation values are inferred from other runs.')
        return
    base=baseline['aggregate'].get('ndcg')
    if base is None: return
    rows=[dict(component=LABELS.get(name,name),ndcg=completed[name]['aggregate'].get('ndcg'),
               recall=completed[name]['aggregate'].get('recall'),
               delta=completed[name]['aggregate']['ndcg']-base) for name in names
          if completed[name]['aggregate'].get('ndcg') is not None]
    panel_header('Component examination',f'Change in nDCG@{result["k"]} against the same run’s weighted hybrid ({base:.3f})')
    frame=pd.DataFrame(rows)
    figure=go.Figure(go.Bar(x=frame['delta'],y=frame['component'],orientation='h',
        marker_color=[COLORS['oxblood'] if value>=0 else COLORS['brass'] for value in frame['delta']],
        text=[f'{value:+.3f}' for value in frame['delta']],textposition='outside',
        hovertemplate='%{y}<br>Δ nDCG: %{x:+.4f}<extra></extra>'))
    figure.add_vline(x=0,line_color=COLORS['muted'],line_width=1)
    figure.update_xaxes(title='Δ nDCG · positive means removal improved this run',zeroline=False)
    figure.update_yaxes(autorange='reversed',showgrid=False)
    st.plotly_chart(chart_theme(figure,height=max(270,len(rows)*48+90)),width='stretch',key='ablation_delta')
    st.dataframe(frame.rename(columns={'component':'Ablation','ndcg':f'nDCG@{result["k"]}','recall':f'Recall@{result["k"]}','delta':'Δ nDCG'}),
                 hide_index=True,width='stretch')
    st.caption('A negative or positive result is retained. Component utility is dataset-dependent; default weights are not claimed to be optimized.')


def _resolve_dataset_source(artifact,project_root,dataset_directory):
    """Resolve source bytes without rewriting the historical experiment artifact.

    Recorded paths retain priority. A relocated basename is accepted only inside
    the configured dataset directory and only with the recorded SHA-256.
    """
    recorded=artifact.get('dataset_path')
    if not isinstance(recorded,(str,Path)) or not str(recorded):
        return None
    expected=artifact.get('dataset_sha256')
    if expected in (None,''):
        expected=None
    elif not isinstance(expected,str) or len(expected)!=64 or any(c not in '0123456789abcdefABCDEF' for c in expected):
        return None
    else:
        expected=expected.lower()

    def matches(candidate):
        try:
            if not candidate.is_file():
                return False
            if expected is None:
                return True
            digest=hashlib.sha256()
            with candidate.open('rb') as source:
                for block in iter(lambda:source.read(1024*1024),b''):
                    digest.update(block)
            return digest.hexdigest()==expected
        except (OSError,ValueError):
            return False

    try:
        original=Path(recorded)
        if not original.is_absolute():
            original=Path(project_root)/original
        original=original.resolve()
        if matches(original):
            return original
        if expected is None:
            return None
        # PureWindowsPath also handles archived Windows paths on another OS.
        name=PureWindowsPath(str(recorded)).name
        if not name or name in ('.','..') or any(c in name for c in ('\\','/',':','\0')):
            return None
        directory=Path(dataset_directory)
        if not directory.is_absolute():
            directory=Path(project_root)/directory
        directory=directory.resolve()
        relocated=(directory/name).resolve()
        if not relocated.is_relative_to(directory):
            return None
        return relocated if matches(relocated) else None
    except (OSError,ValueError,TypeError):
        return None


def _error_panel(result,entry):
    from .design import panel_header,metric_strip,source_document
    rows=entry.get('queries',[])
    if not rows:
        st.info('No per-query ranking records are available.')
        return
    stats=entry['aggregate']
    metric_strip([
        dict(label='Queries',value=str(len(rows)),detail='Recorded, including difficult queries'),
        dict(label='Unrelated / query',value=_number(stats.get('mean_unrelated_results_at_k'),2),detail=f'Within top {result["k"]}',tone='warning'),
        dict(label='No-match queries',value=str(stats.get('no_match_query_count',0)),detail='Reported separately from recall'),
        dict(label='No-match false positives',value=_number(stats.get('no_match_false_positive_query_rate'),2),
             detail='Positive-score suggestions · threshold 0',tone='warning')])
    table=[]
    for row in rows:
        table.append({'Query':row['query_id'],'Language':LANGUAGES.get(row.get('language'),row.get('language')),
                      'Variant':row.get('variant'),'Relevant':row.get('relevant_count'),
                      'Unrelated returned':len(row.get('false_positive_ids',[])),
                      'Missed related':len(row.get('missed_relevant_ids',[])),
                      f'R@{result["k"]}':row.get('recall'),f'nDCG@{result["k"]}':row.get('ndcg')})
    panel_header('Error ledger','Inspect actual false suggestions and missed synthetic siblings')
    st.dataframe(pd.DataFrame(table).sort_values('Unrelated returned',ascending=False),
                 hide_index=True,width='stretch')
    query_id=st.selectbox('Inspect query ranking',[row['query_id'] for row in rows],key='error_query')
    query=next(row for row in rows if row['query_id']==query_id)
    ranking=[{'Rank':i+1,'Report':report_id,'Score':query.get('ranked_scores',[None]*len(query['ranked_ids']))[i],
              'Synthetic relevance':'unrelated' if report_id in query.get('false_positive_ids',[]) else 'related',
              'Language':query.get('candidate_languages',['unknown']*len(query['ranked_ids']))[i]}
             for i,report_id in enumerate(query.get('ranked_ids',[]))]
    a,b=st.columns([1.2,1],gap='large')
    with a:
        st.dataframe(ranking,hide_index=True,width='stretch')
    with b:
        st.caption('MISSED RELATED REPORTS')
        st.write(', '.join(query.get('missed_relevant_ids',[])) or 'None recorded in this ranking.')
        st.caption('INTERPRETATION')
        st.write('Relevance comes from synthetic family labels. Similarity and shared mentions do not confirm an investigative relationship.')
    path=_resolve_dataset_source(result,ROOT,resource_path('dataset'))
    if path is not None:
        try:
            from .dataset import load
            reports={row['report_id']:row for row in load(path)}
            inspect_ids=[rid for rid in [query_id,*query.get('ranked_ids',[])] if rid in reports]
            if inspect_ids:
                with st.expander('Read original query / candidate source'):
                    selected=st.selectbox('Source report',inspect_ids,key='error_source')
                    source_document(reports[selected])
        except (OSError,ValueError,KeyError):
            st.caption('Original source files could not be read; exact ranked identifiers remain preserved.')
    else:
        st.caption('Original sources are unavailable or could not be matched to the recorded dataset hash; exact ranked identifiers remain preserved.')
    with st.expander('Raw per-query computation record'):
        st.json(query)


def _language_panel(result,entry):
    from .design import chart_theme,panel_header
    left,right=st.columns([1,1.1],gap='large')
    with left:
        panel_header('Query language slices','Measured macro metrics; missing values are undefined')
        frame=pd.DataFrame.from_dict(entry.get('by_language',{}),orient='index')
        if not frame.empty:
            frame.index=[LANGUAGES.get(value,value) for value in frame.index]
            st.dataframe(frame[[key for key in METRICS+['query_count'] if key in frame]],width='stretch')
        panel_header('Missing information / variant','Controlled generator variants, not inferred error labels')
        variants=pd.DataFrame.from_dict(entry.get('by_variant',{}),orient='index')
        st.dataframe(variants[[key for key in ['recall','ndcg','query_count'] if key in variants]],width='stretch')
    with right:
        panel_header('Cross-language retrieval','Recall conditioned on positive query → candidate language pairs')
        pairs=entry.get('recall_by_language_pair',{})
        parsed=[(key.split('→'),value) for key,value in pairs.items() if '→' in key]
        sources=sorted({pair[0][0] for pair in parsed}); targets=sorted({pair[0][1] for pair in parsed})
        if sources and targets:
            matrix=[[pairs.get(source+'→'+target) for target in targets] for source in sources]
            figure=go.Figure(go.Heatmap(z=matrix,x=[LANGUAGES.get(v,v) for v in targets],
                y=[LANGUAGES.get(v,v) for v in sources],zmin=0,zmax=1,
                text=[[_number(v) for v in row] for row in matrix],texttemplate='%{text}',textfont=dict(color=COLORS['text']),
                colorscale=[[0,COLORS['panel']],[1,'#EDB6AE']],showscale=False,xgap=5,ygap=5,
                hovertemplate='Query %{y} → candidate %{x}<br>Recall: %{z:.4f}<extra></extra>'))
            figure.update_xaxes(title='Candidate language',side='bottom',showgrid=False)
            figure.update_yaxes(title='Query language',autorange='reversed',showgrid=False)
            st.plotly_chart(chart_theme(figure,height=340),width='stretch',key='language_pairs')
        else:
            st.info('This artifact has no recorded language-pair measurements.')
        st.caption('Empty cells indicate no relevant pairs; they are not zero recall.')


def _history_panel(saved):
    from .design import panel_header
    panel_header('Archive register','Saved runs retain dataset hash, cutoff, split, configuration and exact rankings')
    register=[{'Run':item['experiment_id'],'Created UTC':item.get('created_at_utc'),
               'Partition':item.get('split'),'K':item.get('k'),
               'Dataset':Path(item.get('dataset_path','')).name,
               'Source only':item.get('configuration',{}).get('source_only',False),
               'Completed':sum(entry.get('status')=='completed' for entry in item.get('methods',{}).values())}
              for item in saved]
    st.dataframe(register,hide_index=True,width='stretch')
    ids=[item['experiment_id'] for item in saved]
    chosen=st.multiselect('Runs to compare',ids,default=ids[:2],key='history_comparison')
    selected=[item for item in saved if item['experiment_id'] in chosen]
    if not selected: return
    configs=[]; methods=[]
    for artifact in selected:
        config=artifact.get('configuration',{})
        model=artifact.get('model') or {}
        configs.append({'Run':artifact['experiment_id'],'Partition':artifact.get('split'),'K':artifact.get('k'),
                        'Source only':config.get('source_only',False),'Device':model.get('device',config.get('device','auto')),
                        'BM25 k1':config.get('bm25_k1',config.get('k1',1.5)),
                        'BM25 b':config.get('bm25_b',config.get('b',.75)),'RRF constant':config.get('rrf_k',60),
                        'Model revision':str(model.get('revision','unrecorded'))[:12],
                        'Dataset hash':str(artifact.get('dataset_sha256','unrecorded'))[:12],
                        'Weights':json.dumps(config.get('weights',{}),sort_keys=True)})
        for method,entry in _completed(artifact).items():
            methods.append({'Run':artifact['experiment_id'],'Method':LABELS.get(method,method),
                            **{key:entry['aggregate'].get(key) for key in METRICS}})
    panel_header('Configuration comparison','Compare compatible protocols before interpreting performance differences')
    st.dataframe(configs,hide_index=True,width='stretch')
    protocols={(item.get('dataset_sha256'),item.get('split'),item.get('k'),
                item.get('configuration',{}).get('source_only',False)) for item in selected}
    if len(protocols)>1:
        st.warning('Selected runs use different datasets, partitions, cutoffs or annotation policies. Their scores are not directly interchangeable.')
    st.dataframe(methods,hide_index=True,width='stretch')


def _execution_controls(settings,expanded=False):
    from .design import panel_header
    with st.expander('Open a new evaluation record',expanded=expanded,icon=':material/science:'):
        panel_header('Evaluation instructions','Train-fitted indexes · scenario-family isolation · all measurements remain reproducible')
        first,second=st.columns(2,gap='large')
        with first:
            dataset_name=st.selectbox('Evaluation dataset',['Original 90-report fixture','Challenge scenarios and no-match queries'])
            methods=st.multiselect('Retrieval methods',METHODS,default=['tfidf','bm25','semantic','hybrid','rrf'])
            source_only=st.checkbox('Extract from narrative only (exclude supplied annotation shortcuts)',value=True)
        with second:
            split=st.selectbox('Partition',['dev','test'])
            k=st.slider('Metric cutoff K',1,10,5)
            ablations=st.checkbox('Include four hybrid component ablations')
        frozen=st.checkbox('I have frozen the model and configuration; this test run will not tune them') if split=='test' else True
        st.caption('Development is for model selection. Test is for frozen evaluation. Family labels are never ranking features. Sentence-pair explanation inference is excluded from experiment timings.')
        if st.button('Run evaluation',type='primary',disabled=not methods or not frozen,icon=':material/play_arrow:'):
            dataset_path=resource_path('dataset')/('reports.jsonl' if dataset_name.startswith('Original') else 'challenge_reports.jsonl')
            config=dict(settings,source_only=source_only,explain_passages=False,
                        bm25_k1=settings['k1'],bm25_b=settings['b'],allow_download=settings.get('model_mode','offline')=='online')
            try:
                with st.spinner('Computing rankings, metrics and family uncertainty…'):
                    artifact=run_experiment(methods,split,k,config,dataset_path,ablations=ablations)
                st.session_state['selected_experiment']=artifact['experiment_id']
                failed=[name for name,entry in artifact['methods'].items() if entry['status']!='completed']
                if failed: st.warning('Saved with explicit method failures: '+', '.join(failed))
                else: st.success('Measured experiment saved with configuration and source hashes.')
            except Exception as exc:
                st.error(f'Experiment could not run: {exc}')


def research(settings):
    from .ui import heading,download
    from .design import section_label,panel_header,status_badge,metric_strip,empty_state
    heading('Research Evaluation Lab','The study register: measured comparisons, component examinations and a traceable error ledger.')
    saved=list_experiments()
    _execution_controls(settings,expanded=not saved)
    saved=list_experiments()
    if not saved:
        empty_state('The study register is empty','Open an evaluation record above. Comparison sheets appear only after an actual experiment completes.')
        return
    ids=[item['experiment_id'] for item in saved]
    preferred=st.session_state.get('selected_experiment')
    with st.container(border=True,key='research_record_sheet'):
        section_label('LABORATORY REGISTER / SAVED RESEARCH')
        experiment_column,method_column=st.columns([1.7,1])
        selected=experiment_column.selectbox('Inspect a saved experiment',ids,index=ids.index(preferred) if preferred in ids else 0)
        result=next(item for item in saved if item['experiment_id']==selected)
        complete=_completed(result)
        failure_count=len(result.get('methods',{}))-len(complete)
        names=list(result.get('methods',{}))
        if not names:
            empty_state('No method records','This saved artifact contains no method output.')
            return
        selected_method=method_column.selectbox('Inspect method and errors',names,format_func=lambda value:LABELS.get(value,value))
        entry=result['methods'][selected_method]
        stats=entry.get('aggregate',{})
        badges=(status_badge('MEASURED' if complete else 'FAILED RECORD','success' if complete else 'error')+' '+
                status_badge(str(result['split']).upper(),'neutral')+' '+
                status_badge(f'{len(complete)} completed','neutral')+
                (' '+status_badge(f'{failure_count} failed','error') if failure_count else ''))
        st.markdown(badges,unsafe_allow_html=True)
        panel_header('Comparative retrieval study',Path(result['dataset_path']).name)
        st.caption(f'Recorded UTC: {result["created_at_utc"]} · cutoff K={result["k"]} · narrative-only={result["configuration"].get("source_only",False)}')
        metric_strip([dict(label=f'{label}@{result["k"]}',value=_number(stats.get(key)),
                           detail=LABELS.get(selected_method,selected_method),tone='ai' if key=='ndcg' else 'neutral')
                      for key,label in [('precision','Precision'),('recall','Recall'),('mrr','MRR'),('ndcg','nDCG')]])
        st.caption('Reading note: these are observed retrieval measures, not calibrated probabilities. Undefined no-positive recall/nDCG remain a dash.')
    tabs=st.tabs(['Comparison sheets','Component notes','Error ledger','Language evidence','Archive index'])
    with tabs[0]:
        section_label('EXHIBIT A / MEASURED COMPARISONS')
        with st.container(key='research_comparison_charts'):
            _comparison_charts(result)
        with st.expander('Exact metric table and measured latency'):
            st.dataframe(_metric_frame(result).drop(columns=['label']),hide_index=True,width='stretch')
            st.caption('Latency retains cache and initial-load effects. No concurrent load-test result is implied.')
    with tabs[1]:
        section_label('EXHIBIT B / COMPONENT EXAMINATION')
        _ablation_panel(result)
    with tabs[2]:
        section_label('EXHIBIT C / RETRIEVAL ERRORS')
        if entry.get('status')=='completed':
            _error_panel(result,entry)
        else:
            st.error(entry.get('error','This method did not complete. No result was substituted.'))
            st.info('Prepare the pinned model in System Settings or explicitly select a lexical method.')
    with tabs[3]:
        section_label('EXHIBIT D / LANGUAGE EVIDENCE')
        if entry.get('status')=='completed': _language_panel(result,entry)
        else: empty_state('No language measurements','The selected method failed; inspect its recorded error.')
    with tabs[4]: _history_panel(saved)
    with st.expander('Export this measured record'):
        left,right=st.columns(2)
        with left: download('Export experiment JSON',result,f'{selected}.json')
        with right:
            st.download_button('Export summary CSV',summary_csv(result),f'{selected}.csv','text/csv',
                on_click=save_export,args=(summary_csv(result),f'{selected}.csv',{'configuration':result.get('configuration'),'model':result.get('model')}),
                icon=':material/download:')
    with st.expander('Provenance / exact configuration'):
        st.json({key:value for key,value in result.items() if key!='methods'})


def system(settings,store,records):
    from .ui import heading,download
    from .design import section_label,panel_header,status_badge,metric_strip
    heading('System Settings','The instrument register: model readiness, execution policy and the local research archive.')
    encoder=get_shared_encoder(device=settings['device'],allow_download=settings.get('model_mode','offline')=='online')
    model_status=encoder.status()
    database=store.health()
    active=model_status.get('active_device')
    metric_strip([
        dict(label='Model assets',value='READY' if model_status.get('available') else 'MISSING',
             detail=model_status.get('model_id','Pinned multilingual encoder'),tone='success' if model_status.get('available') else 'warning'),
        dict(label='Inference device',value=str(active).upper() if active else 'NOT LOADED',
             detail='Requested: '+settings['device'],tone='ai'),
        dict(label='Local database',value=str(database.get('status','unknown')).upper(),
             detail=f'{database.get("reports",len(records))} fictional reports',tone='success' if database.get('status')=='ok' else 'error'),
        dict(label='Model mode',value=settings.get('model_mode','offline').upper(),
             detail='Local assets only' if settings.get('model_mode','offline')=='offline' else 'Approved downloads allowed',tone='info')])
    if model_status.get('fallback_reason'): st.warning(model_status['fallback_reason'])
    tabs=st.tabs(['Execution policy','Model register','Data cabinet','Diagnostic notes'])
    with tabs[0]:
        section_label('INSTRUMENT REGISTER / RETRIEVAL')
        with st.form('retrieval_settings'):
            panel_header('Execution policy','The next search or experiment records these settings; existing results remain unchanged.')
            a,b,c=st.columns(3)
            device=a.selectbox('Inference device',['auto','cpu','cuda'],index=['auto','cpu','cuda'].index(settings['device']))
            model_mode=b.selectbox('Model availability mode',['offline','online'],index=['offline','online'].index(settings.get('model_mode','offline')))
            rrf_k=c.number_input('RRF rank constant',min_value=1,max_value=500,value=int(settings.get('rrf_k',60)))
            a,b=st.columns(2)
            k1=a.slider('BM25 k1',.1,3.0,float(settings['k1']),.1)
            norm_b=b.slider('BM25 length normalization b',0.0,1.0,float(settings['b']),.05)
            panel_header('Combination ledger','Nonnegative contributions; observed signals are renormalized. These are not probabilities.')
            columns=st.columns(5)
            weights={name:columns[i].number_input(f'{name} weight',min_value=0.0,max_value=10.0,value=float(value),step=.05)
                     for i,(name,value) in enumerate(settings['weights'].items())}
            st.caption('Approved model: intfloat/multilingual-e5-small. Online mode may download this pinned model; offline never requests it from the network.')
            if st.form_submit_button('Save retrieval settings',type='primary',icon=':material/save:'):
                try:
                    save_settings(dict(settings,device=device,k1=k1,b=norm_b,rrf_k=int(rrf_k),weights=weights,model_mode=model_mode))
                    st.success('Configuration saved. It applies to the next search or experiment.')
                except Exception as exc: st.error(str(exc))
    with tabs[1]:
        section_label('MODEL REGISTER / LOCAL ASSETS')
        st.markdown(status_badge('LOADED' if model_status.get('loaded') else 'NOT LOADED',
                                'success' if model_status.get('loaded') else 'neutral')+' '+
                    status_badge('ASSETS READY' if model_status.get('available') else 'ASSETS MISSING',
                                 'success' if model_status.get('available') else 'warning'),unsafe_allow_html=True)
        st.dataframe([
            {'Property':'Encoder','Value':model_status.get('model_id','intfloat/multilingual-e5-small')},
            {'Property':'Pinned revision','Value':model_status.get('revision','unavailable')},
            {'Property':'Dimensions','Value':str(model_status.get('dimensions','unavailable'))},
            {'Property':'Active device','Value':str(active or 'Not loaded; no inference claimed')},
            {'Property':'License','Value':'MIT'},
            {'Property':'Local directory','Value':str(model_status.get('local_model','unavailable'))}],
            hide_index=True,width='stretch')
        cache=model_status.get('cache_stats',{})
        metric_strip([dict(label='Memory cache hits',value=str(cache.get('memory_hits',0)),detail='This shared encoder process'),
                      dict(label='Disk cache hits',value=str(cache.get('disk_hits',0)),detail='Content/model validated'),
                      dict(label='Encoded texts',value=str(cache.get('encoded_texts',0)),detail='Actual encoder counter')])
        missing=model_status.get('missing_assets',[])
        if missing: st.warning('Missing approved assets: '+', '.join(str(value) for value in missing))
        st.caption('Setup reuses cached assets. A successful check tests the selected device. Offline mode requires the complete approved local model folder.')
        if st.button('Prepare or verify local semantic model',icon=':material/memory:'):
            try:
                with st.spinner('Checking the pinned model and actual local inference…'):
                    command=[sys.executable,str(ROOT/'scripts/setup_model.py'),'--device',settings['device']]
                    if settings.get('model_mode','offline')=='offline': command.append('--offline')
                    process=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=1200,
                                           creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                if process.returncode==0: st.success('Model setup and inference check passed.')
                else: st.error('Model setup failed. Select lexical retrieval explicitly while resolving the error.')
                with st.expander('Setup diagnostic output',expanded=process.returncode!=0):
                    st.code((process.stdout+'\n'+process.stderr)[-12000:])
            except Exception as exc: st.error(f'Model setup failed: {exc}')
        panel_header('Resource cabinet','Resolved from portable configuration; dataset and experiment files are preserved.')
        st.dataframe([{'Resource':name,'Location':path,'Present':Path(path).exists()} for name,path in path_report().items()],
                     hide_index=True,width='stretch')
        st.caption('Use configs/paths.json for project-relative resource locations. Optional SHERLOCKED_* environment overrides take precedence.')
        with st.expander('Raw model state / recorded compatibility checks'):
            st.json(model_status)
            smoke=resource_path('results')/'semantic_smoke.json'
            if smoke.exists(): st.json(json.loads(smoke.read_text(encoding='utf-8')))
    with tabs[2]:
        section_label('DATA CABINET / FICTIONAL REPORTS')
        panel_header('Immutable source records','Imports are atomic new SQLite rows. Duplicate IDs/narratives are rejected; original fixture files are preserved.')
        exported=store.export_jsonl()
        st.download_button('Export local reports as JSONL',exported,'sherlocked_reports.jsonl','application/x-ndjson',
                           on_click=save_export,args=(exported,'sherlocked_reports.jsonl'),icon=':material/download:')
        upload=st.file_uploader('Import fictional dataset (UTF-8 JSONL, max 5 MB)',type=['jsonl'])
        fictional=st.checkbox('I confirm this dataset contains fictional reports only')
        if st.button('Validate and import reports',disabled=upload is None or not fictional,icon=':material/upload_file:'):
            try:
                imported=store.import_reports(parse_jsonl(upload.getvalue()))
                st.success(f'{imported} reports imported. Reopen Report Explorer to inspect the sources.')
            except Exception as exc: st.error(f'Import rejected; existing reports preserved: {exc}')
    with tabs[3]:
        section_label('DIAGNOSTIC NOTES / MEASURED STATE')
        st.caption('Diagnostics inspect dependencies, dataset integrity and hardware availability. This is distinct from an encoder that has actually loaded.')
        if st.button('Run local diagnostics',icon=':material/health_and_safety:'):
            from scripts.health import inspect
            with st.spinner('Inspecting dependencies, resources and hardware…'):
                report=inspect()
                report['database']=store.health()
                st.session_state['diagnostic_report']=report
        report=st.session_state.get('diagnostic_report')
        if report:
            errors=report.get('errors',[]); warnings=report.get('warnings',[])
            st.markdown(status_badge('ATTENTION REQUIRED' if errors else 'CHECKS PASSED','error' if errors else 'success'),unsafe_allow_html=True)
            for error in errors: st.error(error)
            for warning in warnings: st.warning(warning)
            hardware=report.get('acceleration',{})
            metric_strip([
                dict(label='Python',value=report.get('python','unknown'),detail='Local interpreter'),
                dict(label='PyTorch',value=report.get('dependencies',{}).get('torch') or 'missing',detail='Installed package'),
                dict(label='CUDA available',value='YES' if hardware.get('cuda_available') else 'NO',
                     detail=str(hardware.get('gpu') or 'CPU path available'),tone='success' if hardware.get('cuda_available') else 'neutral')])
            st.dataframe([{'Dependency':name,'Installed version':version or 'missing'} for name,version in report.get('dependencies',{}).items()],
                         hide_index=True,width='stretch')
            download('Export health report',report,'sherlocked_health.json')
            with st.expander('Full health computation record'): st.json(report)
        else:
            st.info('No diagnostic run in this session. Run checks to display measured hardware and dependency status.')
    st.caption('Local synthetic research only. No guilt prediction, identity merging or automatic confirmation of suggested relationships.')



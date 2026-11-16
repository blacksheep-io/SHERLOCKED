"""Read-only evidence dossier. All signals originate in existing Engine results."""
from html import escape
import streamlit as st
from .design import source_document,signal_chart,panel_header,status_badge,source_quote,empty_state


def review_gate():
    from .design import human_review_gate
    human_review_gate()


def contradiction(row):
    from .design import contradiction_alert
    contradiction_alert(row)

def render(hit,query):
    report=hit['report']
    language={'en':'English','bn':'Bangla','mixed':'Mixed'}.get(report.get('language'),'Unclassified')
    st.caption('CANDIDATE SOURCE / '+str(report['report_id'])+' · '+language+' · '+str(report.get('source_id','source unavailable')))
    with st.expander('Candidate source document',expanded=False):
        source_document(report)
    review_gate()
    details=hit.get('explanation',{})
    tabs=st.tabs(['Signal profile','Source passages','Entities & context','Computational record'])
    with tabs[0]:
        panel_header('The ranking record',str(hit.get('method','retrieval'))+' / computed similarity, not probability')
        st.plotly_chart(signal_chart(hit),width='stretch',theme=None)
        st.caption('Labels retain raw computed values. BM25 uses query-pool normalization for display; these scores are not calibrated confidence.')
        contributions=details.get('contributions',{})
        if contributions:
            st.dataframe([{'Ranking component':key,'Contribution':value} for key,value in contributions.items()],hide_index=True,width='stretch',column_config={'Contribution':st.column_config.NumberColumn(format='%.4f')})
        missing=details.get('missing',[])
        st.markdown(status_badge('Unknown / unavailable: '+', '.join(missing),'warning') if missing else status_badge('Required signals available'),unsafe_allow_html=True)
        for row in details.get('structured',{}).get('contradictions',[]): contradiction(row)
    with tabs[1]:
        lexical=details.get('keyword_signals',[]) or details.get('bm25_signals',[])
        passage=details.get('semantic_passage')
        if lexical:
            panel_header('Matching passages','Original narratives / exact character spans')
            for record,key,label in [(query,'query_spans','SOURCE DOCUMENT'),(hit['report'],'candidate_spans','CANDIDATE FILE')]:
                spans=[span for signal in lexical for span in signal.get(key,[])]
                source_quote(record['text'],label+' / '+str(record.get('source_id',record.get('report_id','session'))),spans)
            with st.expander('Keyword contributions and original offsets'):
                st.dataframe([{'Term':s['term'],'Contribution':s.get('contribution'),'Query spans':str(s.get('query_spans')),'Candidate spans':str(s.get('candidate_spans'))} for s in lexical],hide_index=True,width='stretch')
        if passage:
            panel_header('Semantic passage alignment',f"Measured sentence-pair cosine / {passage.get('cosine',0):.4f}")
            source_quote(passage.get('query_text',''),str(query.get('source_id','query'))+' / '+str(passage.get('query_span','')))
            source_quote(passage.get('candidate_text',''),str(hit['report'].get('source_id'))+' / '+str(passage.get('candidate_span','')))
            st.caption(passage.get('limitation','Illustrative sentence similarity, not causal attribution of the encoder score.'))
            if details.get('semantic_input'):
                with st.expander('Encoder coverage and truncation record'): st.json(details['semantic_input'])
        if not lexical and not passage:
            empty_state('No passage signal used','This method ranks observed mentions or structured fields. Their source provenance is available in Entities & context.')
    with tabs[2]:
        entity=details.get('entities',{});structured=details.get('structured',{})
        panel_header('Mention comparison','Names remain separate source mentions; no identity is established')
        rows=[]
        for match in entity.get('matches',[]):
            a=match.get('query') or {};b=match.get('candidate') or {}
            rows.append({'Type':match.get('type'),'Source mention':a.get('surface'),'Candidate mention':b.get('surface'),'Comparison':match.get('status'),'Signal':match.get('score')})
        if rows: st.dataframe(rows,hide_index=True,width='stretch',column_config={'Signal':st.column_config.NumberColumn(format='%.3f')})
        else: st.caption('No explicitly extracted comparable mentions were available.')
        panel_header('Structured context','Unknown fields do not vote in the comparison')
        if structured.get('matches'):
            st.dataframe([{key:row.get(key) for key in ['field','query','candidate','score','reason']} for row in structured['matches']],hide_index=True,width='stretch')
        for row in structured.get('missing',[]): st.caption('Unknown: '+str(row))
        for row in structured.get('contradictions',[]): contradiction(row)
        with st.expander('Source provenance and extraction record'):
            st.json({'query':query.get('metadata_provenance',{}),'candidate':hit['report'].get('metadata_provenance',{}),'entity_evidence':entity})
    with tabs[3]:
        panel_header('Computational record','Unedited result fields / exportable evidence')
        st.json({'method':hit.get('method'),'score':hit['score'],'raw_components':hit.get('components'),**details})
    st.caption('Potential report relationship · UNREVIEWED · no identity decision or guilt inference')

"""Independent retrieval signals, documented fusion and auditable explanations."""
import math
from collections import Counter
from .retrieval import KeywordIndex, tokenize, token_spans
from .semantic import get_shared_encoder, SemanticUnavailable
from .signals import compare_entities, compare_structured, enrich_report

METHODS = ['tfidf','bm25','semantic','entity','structured','hybrid','rrf','hybrid_rerank']
DEFAULT_WEIGHTS = dict(tfidf=.2,bm25=.2,semantic=.4,entity=.1,structured=.1)


class BM25Index:
    """Train-only Robertson positive-IDF BM25; no held-out vocabulary fitting."""
    def __init__(self,records,k1=1.5,b=.75):
        if not math.isfinite(k1) or not math.isfinite(b) or k1 <= 0 or not 0 <= b <= 1:
            raise ValueError('BM25 requires k1 > 0 and 0 <= b <= 1')
        documents=[tokenize(r['text']) for r in records]
        if not documents:
            raise ValueError('BM25 requires nonempty training records')
        counts=Counter(token for doc in documents for token in set(doc))
        self.idf={term:math.log(1+(len(documents)-df+.5)/(df+.5)) for term,df in counts.items()}
        self.avg_length=max(1,sum(map(len,documents))/len(documents))
        self.k1,self.b=k1,b

    def explain(self,query,text):
        counts=Counter(tokenize(text)); length=sum(counts.values())
        signals=[]
        for term in sorted(set(tokenize(query)) & counts.keys() & self.idf.keys()):
            tf=counts[term]
            value=self.idf[term]*tf*(self.k1+1)/(tf+self.k1*(1-self.b+self.b*length/self.avg_length))
            signals.append(dict(term=term, contribution=value,
                                query_spans=[[a,b] for t,a,b in token_spans(query) if t==term],
                                candidate_spans=[[a,b] for t,a,b in token_spans(text) if t==term]))
        return sorted(signals,key=lambda s:(-s['contribution'],s['term']))

    def scores(self,query,candidates):
        return [sum(s['contribution'] for s in self.explain(query,r['text'])) for r in candidates]


class Engine:
    def __init__(self,fit_records,config=None,semantic=None):
        self.config=dict(config or {})
        fit_records=list(fit_records)
        if not fit_records or not any(tokenize(r['text']) for r in fit_records):
            raise ValueError('The training corpus must contain reports with usable text tokens')
        self.rrf_k=float(self.config.get('rrf_k',60))
        if not math.isfinite(self.rrf_k) or self.rrf_k<0:
            raise ValueError('RRF rank constant must be finite and nonnegative')
        self.keyword=KeywordIndex(fit_records)
        self.bm25=BM25Index(fit_records,self.config.get('bm25_k1',self.config.get('k1',1.5)),
                            self.config.get('bm25_b',self.config.get('b',.75)))
        self.semantic=semantic if semantic is not None else get_shared_encoder(device=self.config.get('device','auto'),allow_download=self.config.get('allow_download',False))

    @property
    def model_metadata(self):
        return self.semantic.metadata

    def search(self,query,candidates,method='hybrid',k=5,exclude_id=None,include_zero=False,weights=None,rerank=False):
        if method not in METHODS:
            raise ValueError(f'Unknown retrieval method: {method}')
        if not isinstance(k,int) or isinstance(k,bool) or k < 1:
            raise ValueError('k must be positive')
        if isinstance(query,str):
            query={'text':query,'report_id':'query'}
        if not isinstance(query.get('text',''),str):
            raise ValueError('Report text must be a string')
        if not query.get('text','').strip():
            return []
        query=enrich_report(query)
        pool=[enrich_report(r) for r in candidates if r['report_id']!=exclude_id]
        if not pool:
            return []
        if len({r['report_id'] for r in pool})!=len(pool):
            raise ValueError('Candidate report IDs must be unique; duplicate narratives may use distinct IDs')
        weights=dict(weights if weights is not None else self.config.get('weights',DEFAULT_WEIGHTS))
        try:
            weights={key:float(value) for key,value in weights.items()}
        except (TypeError,ValueError) as exc:
            raise ValueError('Fusion weights must be numeric') from exc
        if any(key not in DEFAULT_WEIGHTS or not math.isfinite(value) or value<0 for key,value in weights.items()):
            raise ValueError('Fusion weights must be finite nonnegative values for known components')
        if method in ('hybrid','rrf','hybrid_rerank') and not any(weights.values()):
            raise ValueError('At least one fusion weight must be positive')
        required=set(weights) if method in ('hybrid','rrf','hybrid_rerank') else {method}
        required={name for name in required if method not in ('hybrid','rrf','hybrid_rerank') or weights[name]>0}
        lexical={r['report']['report_id']:r for r in self.keyword.search(query['text'],pool,len(pool),include_zero=True)} if 'tfidf' in required else {}
        bm25=self.bm25.scores(query['text'],pool) if 'bm25' in required else [None]*len(pool)
        dense=self.semantic.scores(query['text'],[r['text'] for r in pool]) if 'semantic' in required else [None]*len(pool)
        max_bm25=max((s for s in bm25 if s is not None),default=0)
        rows=[]
        for i,report in enumerate(pool):
            # Every method can expose observed metadata, without using it in a lexical score.
            entity=compare_entities(query,report)
            structured=compare_structured(query,report)
            raw=dict(tfidf=lexical.get(report['report_id'],{}).get('score'),bm25=bm25[i],
                     semantic=float(dense[i]) if dense[i] is not None else None,entity=entity['score'],structured=structured['score'])
            normalized=dict(raw)
            if bm25[i] is not None:
                normalized['bm25']=bm25[i]/max_bm25 if max_bm25 else 0.
            if dense[i] is not None:
                normalized['semantic']=max(0.,float(dense[i]))
            available={name:value for name,value in normalized.items() if value is not None and weights.get(name,0)>0}
            denominator=sum(weights[name] for name in available)
            contributions={name:weights[name]*value/denominator for name,value in available.items()} if denominator else {}
            score=sum(contributions.values()) if method in ('hybrid','rrf','hybrid_rerank') else raw[method]
            if method not in ('hybrid','rrf','hybrid_rerank'):
                contributions={method:float(score)} if score is not None else {}
            rows.append(dict(report=report,score=float(score or 0),status='potential relationship',method=method,
                             components=raw, normalized_components=normalized,
                             explanation=dict(keyword_signals=lexical.get(report['report_id'],{}).get('signals',[]),
                                              bm25_signals=self.bm25.explain(query['text'],report['text']) if 'bm25' in required else [],
                                              entities=entity,structured=structured,
                                              missing=[name for name in required if raw[name] is None],
                                              contributions=contributions,
                                              limitation='Similarity is advisory, not a probability, identity decision or verified relationship.')))
        if method=='rrf':
            for row in rows:
                row['score']=0.;row['explanation']['contributions']={}
            for name in required:
                ranked=sorted((r for r in rows if r['components'][name] is not None and r['components'][name]>0),
                              key=lambda r:(-r['components'][name],r['report']['report_id']))
                for rank,row in enumerate(ranked,1):
                    value=weights[name]/(self.rrf_k+rank)
                    row['score']+=value
                    row['explanation']['contributions'][name]=value
        rows.sort(key=lambda r:(-r['score'],r['report']['report_id']))
        if method=='hybrid_rerank' or rerank:
            # Optional source-consistency reranking; deliberately not called a cross-encoder.
            shortlist=rows[:min(len(rows),max(10,k*2))]
            for row in shortlist:
                count=len(row['explanation']['structured'].get('contradictions',[]))
                row['explanation']['pre_rerank_score']=row['score']
                row['explanation']['reranker']='Documented contradiction penalty: score / (1 + 0.15 * contradiction count)'
                row['score']/=1+.15*count
                row['explanation']['contributions']['rerank_adjustment']=row['score']-row['explanation']['pre_rerank_score']
            rows=sorted(shortlist,key=lambda r:(-r['score'],r['report']['report_id']))
        results=[r for r in rows if include_zero or r['score']>0][:k]
        # Expensive sentence evidence is only constructed for visible results, not all candidates.
        if 'semantic' in required and self.config.get('explain_passages',True):
            for row in results:
                row['explanation']['semantic_passage']=self.semantic.passage_evidence(query['text'],row['report']['text'])
                if hasattr(self.semantic,'truncation_info'):
                    row['explanation']['semantic_input']={
                        'query':self.semantic.truncation_info(query['text'],'query'),
                        'candidate':self.semantic.truncation_info(row['report']['text'],'passage')}
        for rank,row in enumerate(results,1):
            row['rank']=rank
        return results

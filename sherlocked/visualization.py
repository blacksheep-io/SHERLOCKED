"""Source-backed graph presentation; mention nodes never merge identities."""
import hashlib
import html
import json
import math
from datetime import datetime
import plotly.graph_objects as go
from .signals import enrich_report

P={'canvas':'#121211','cyan':'#E07A70','violet':'#B08D57','ice':'#ECE6D6',
   'text':'#ECE6D6','muted':'#8C877B','border':'#8C877B','green':'#B08D57','red':'#E07A70'}
LAYERS={'suggested_report','source_mention','suggested_entity','documented','contradiction'}


def safe(value):
    return html.escape(str(value),quote=True)


def mention_id(rid,mention):
    identity=json.dumps([rid,mention['type'],mention['start'],mention['end'],mention['surface']],ensure_ascii=False)
    return 'mention:'+hashlib.sha256(identity.encode()).hexdigest()[:20]


def source_mention(report,mention):
    a,b=mention.get('start'),mention.get('end')
    return (isinstance(a,int) and isinstance(b,int) and 0<=a<b<=len(report['text'])
            and report['text'][a:b]==mention.get('surface')
            and mention.get('source_id',report.get('source_id'))==report.get('source_id'))


def relationship_data(query,results,include_entities=False,entity_types=None,filter_text='',documented_links=None,layers=None,max_mentions=5):
    """Each connection carries retrieval evidence, a literal span or a human record."""
    layers=set(layers if layers is not None else (LAYERS if include_entities else {'suggested_report'}))
    query=enrich_report(query); needle=filter_text.strip().casefold(); hits=[]
    for hit in results:
        report=hit['report']
        if report['report_id']==query['report_id']: continue
        if needle and needle not in (' '.join([report['report_id'],report['text'],report.get('language','')])).casefold(): continue
        if not any(h['report']['report_id']==report['report_id'] for h in hits): hits.append(hit)
    reports={query['report_id']:query,**{h['report']['report_id']:enrich_report(h['report']) for h in hits}}
    nodes={}; edges=[]; by_report={h['report']['report_id']:h for h in hits}
    positions={query['report_id']:(0.,0.)}
    for i,hit in enumerate(hits):
        angle=math.pi/2+i*2*math.pi/max(1,len(hits))
        positions[hit['report']['report_id']]=(2.4*math.cos(angle),2.4*math.sin(angle))
    for rid,report in reports.items():
        key='report:'+rid
        nodes[key]=dict(id=key,type='report',label=rid,report_id=rid,report=report,x=positions[rid][0],y=positions[rid][1],central=rid==query['report_id'])
        if rid!=query['report_id'] and 'suggested_report' in layers:
            hit=by_report[rid]
            if isinstance(hit.get('score'),(int,float)) and math.isfinite(hit['score']) and hit['score']>0:
                edges.append(dict(id='suggestion:'+rid,source='report:'+query['report_id'],target=key,type='suggested_report',
                                  label='Suggested report relationship',score=hit['score'],method=hit.get('method','retrieval'),hit=hit,
                                  evidence=hit.get('explanation',{}),status='AI suggestion; human review required'))
    if 'contradiction' in layers:
        for hit in hits:
            differences=hit.get('explanation',{}).get('structured',{}).get('contradictions',[])
            if differences:
                rid=hit['report']['report_id']
                edges.append(dict(id='difference:'+rid,source='report:'+query['report_id'],target='report:'+rid,
                                  type='contradiction',label='Recorded differences: '+str(len(differences)),
                                  evidence=differences,status='Observed differing fields; not proof of unrelated incidents'))
    lookup={}; omitted=0
    if include_entities:
        for rid,report in reports.items():
            mentions=[m for m in report.get('entities',[]) if source_mention(report,m) and (entity_types is None or m['type'] in entity_types)]
            omitted+=max(0,len(mentions)-max_mentions); mentions=mentions[:max_mentions]
            for i,m in enumerate(mentions):
                key=mention_id(rid,m); x,y=positions[rid]
                base=math.atan2(y,x) if rid!=query['report_id'] else 0
                angle=base+(i-(len(mentions)-1)/2)*.55 if rid!=query['report_id'] else i*2*math.pi/max(1,len(mentions))
                nodes[key]=dict(id=key,type='mention',entity_type=m['type'],label=m['surface'],report_id=rid,mention=m,
                                x=x+.8*math.cos(angle),y=y+.8*math.sin(angle),central=False)
                lookup[(rid,m['type'],m['start'],m['end'],m['surface'])]=key
                if 'source_mention' in layers:
                    edges.append(dict(id='source:'+key,source='report:'+rid,target=key,type='source_mention',label='Literal source mention',
                                      status='Documented text span; identity unverified',evidence=dict(source_id=report.get('source_id'),report_id=rid,
                                      start=m['start'],end=m['end'],text=m['surface'],extraction_method=m.get('method','provided source span'))))
        if 'suggested_entity' in layers:
            for hit in hits:
                for match in hit.get('explanation',{}).get('entities',{}).get('matches',[]):
                    a,b=match.get('query'),match.get('candidate')
                    if not a or not b or match.get('status') not in ('exact','normalized','approximate','possible'): continue
                    first=lookup.get((query['report_id'],a.get('type'),a.get('start'),a.get('end'),a.get('surface')))
                    second=lookup.get((hit['report']['report_id'],b.get('type'),b.get('start'),b.get('end'),b.get('surface')))
                    if first and second:
                        edges.append(dict(id='comparison:'+first+':'+second,source=first,target=second,type='suggested_entity',
                                          label='Mention similarity: '+match['status'],score=match.get('score'),evidence=match,
                                          status='Suggested mention comparison; never shared-identity confirmation'))
    verified=0
    if 'documented' in layers:
        for i,link in enumerate(documented_links or []):
            if not isinstance(link,dict): continue
            a,b=link.get('source_report_id'),link.get('target_report_id'); evidence=link.get('evidence',{}); confirmation=link.get('human_confirmation',{})
            if not isinstance(evidence,dict) or not isinstance(confirmation,dict): continue
            origin=reports.get(evidence.get('report_id')); start,end=evidence.get('start'),evidence.get('end')
            try:
                datetime.fromisoformat(confirmation.get('confirmed_at','').replace('Z','+00:00')); confirmed=bool(confirmation.get('reviewer'))
            except (ValueError,TypeError): confirmed=False
            valid=(a in reports and b in reports and a!=b and link.get('status')=='human_verified' and confirmed and origin
                   and evidence.get('source_id')==origin.get('source_id') and isinstance(start,int) and isinstance(end,int)
                   and 0<=start<end<=len(origin['text']) and evidence.get('text')==origin['text'][start:end])
            if valid:
                verified+=1
                edges.append(dict(id='documented:'+str(i),source='report:'+a,target='report:'+b,type='documented',
                                  label=link.get('relation_type','Human-documented report relationship'),evidence=evidence,
                                  human_confirmation=confirmation,status='Human-verified recorded link'))
    return dict(nodes=nodes,edges=edges,query_id='report:'+query['report_id'],hits=by_report,reports=reports,
                human_verified_count=verified,omitted_mentions=omitted,
                limitation='Mention nodes are source-specific. Similar names never merge identities. Scores are not probabilities.')



def relationship_selection(points,data):
    """Coincident report/mention endpoints identify nodes; only midpoints select links."""
    tokens=[]
    for point in points or []:
        if not isinstance(point,dict): continue
        token=point.get('customdata')
        if isinstance(token,(tuple,list)) and len(token)==1: token=token[0]
        if isinstance(token,str): tokens.append(token)
    for token in tokens:
        if token in data['nodes']: return token
        legacy='report:'+token
        if token in data.get('reports',{}) and legacy in data['nodes']: return legacy
    edge_ids={edge['id'] for edge in data['edges']}
    return next((token for token in tokens if token in edge_ids),None)


def relationship_graph(query,results,include_entities=False,entity_types=None,filter_text='',documented_links=None,layers=None,selected_id=None,height=650,max_mentions=5):
    data=relationship_data(query,results,include_entities,entity_types,filter_text,documented_links,layers,max_mentions)
    fig=go.Figure(); styles={'suggested_report':(P['cyan'],'dash',1.7),'source_mention':(P['border'],'solid',1.1),
                            'suggested_entity':(P['violet'],'dot',1.2),'documented':(P['green'],'solid',2.),'contradiction':(P['red'],'dashdot',2.)}
    for edge in data['edges']:
        a,b=data['nodes'][edge['source']],data['nodes'][edge['target']]; color,dash,width=styles[edge['type']]
        detail=safe(edge['label'])+'<br>'+safe(edge['status'])
        if edge.get('score') is not None: detail+='<br>Ranking signal: '+f"{edge['score']:.4f}"+' · not a probability'
        if edge.get('method'): detail+='<br>Method: '+safe(edge['method'])
        dx,dy=b['x']-a['x'],b['y']-a['y'];length=max(.01,math.hypot(dx,dy))
        offset=.18 if edge['type']=='contradiction' else 0
        fig.add_trace(go.Scatter(x=[a['x'],(a['x']+b['x'])/2-offset*dy/length,b['x']],y=[a['y'],(a['y']+b['y'])/2+offset*dx/length,b['y']],mode='lines+markers',
                                 line=dict(color=color,width=width+(1.8 if edge['id']==selected_id else 0),dash=dash),marker=dict(size=[0,13,0],color='rgba(0,0,0,0)'),
                                 customdata=[edge['source'],edge['id'],edge['target']],hovertext=[detail]*3,hovertemplate='%{hovertext}<extra></extra>',showlegend=False,name=edge['type']))
    nodes=list(data['nodes'].values())
    def hover(node):
        if node['type']=='report':
            r=node['report']; return '<b>'+safe(node['label'])+'</b><br>'+safe(r.get('source_id',''))+'<br>'+safe(r['text'][:180])
        m=node['mention']; return '<b>'+safe(node['label'])+'</b><br>'+safe(node['entity_type'])+' · source-specific mention<br>'+safe(m.get('source_id',''))+f" [{m['start']}:{m['end']}]<br>Identity unverified"
    fig.add_trace(go.Scatter(x=[n['x'] for n in nodes],y=[n['y'] for n in nodes],
                             text=[safe(n['label'][:26]+('…' if len(n['label'])>26 else '')) for n in nodes],
                             customdata=[n['id'] if include_entities else n['report_id'] for n in nodes],hovertext=[hover(n) for n in nodes],
                             hovertemplate='%{hovertext}<extra></extra>',mode='markers+text',textposition='top center',
                             textfont=dict(color=P['ice'],size=12,family='Consolas, monospace'),
                             marker=dict(size=[24 if n['central'] else 16 if n['type']=='report' else 10 for n in nodes],
                                         color=[P['ice'] if n['central'] else '#1D1D19' if n['type']=='report' else '#26251F' for n in nodes],
                                         symbol=['diamond' if n['type']=='report' else 'square' for n in nodes],line=dict(color=[P['ice'] if n['central'] else P['cyan'] if n['type']=='report' else P['violet'] for n in nodes],width=2)),showlegend=False,name='Source-backed nodes'))
    fig.update_layout(height=height,margin=dict(l=18,r=18,t=24,b=20),paper_bgcolor=P['canvas'],plot_bgcolor=P['canvas'],
                      font=dict(color=P['text'],family='Consolas, monospace'),
                      xaxis=dict(showgrid=True,gridcolor='#2B2A24',zeroline=False,showticklabels=False,range=[-3.6,3.6],constrain='domain'),
                      yaxis=dict(showgrid=True,gridcolor='#2B2A24',zeroline=False,showticklabels=False,range=[-3.6,3.6],scaleanchor='x',scaleratio=1),
                      hoverlabel=dict(bgcolor='#22221D',font_color=P['text'],bordercolor=P['border']),dragmode='pan',clickmode='event+select',uirevision='source-backed-relationships')
    return fig

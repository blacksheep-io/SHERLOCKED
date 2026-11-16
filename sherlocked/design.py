"""CASE FILE NOIR presentation primitives. No retrieval or persistence logic."""
from html import escape
import base64
import hashlib,json
import plotly.graph_objects as go
import streamlit as st
from .paths import ROOT,resource_path

TOKENS={'ink':'#121211','ink-card':'#1E1D1B','paper':'#F3EEE0','paper-card':'#FBF8F0','ivory':'#ECE6D6','oxblood':'#9B1C1C','rose':'#E07A70','brass':'#B08D57','grey':'#8C877B','line':'#CFC7B2','muted':'#4A463E'}
# Semantic aliases keep existing page adapters compatible during presentation changes.
PALETTE={'bg':TOKENS['ink'],'panel':TOKENS['paper-card'],'border':TOKENS['line'],'text':TOKENS['ink'],'muted':TOKENS['muted'],'cyan':TOKENS['rose'],'violet':TOKENS['brass'],'amber':TOKENS['brass'],'green':TOKENS['ink'],'red':TOKENS['oxblood'],**TOKENS}
SIGNAL_COLORS={'tfidf':'#121211','bm25':'#4A463E','semantic':'#9B1C1C','entity':'#8C877B','structured':'#B08D57'}
SIGNAL_LABELS={'tfidf':'Keyword / TF-IDF','bm25':'Keyword / BM25','semantic':'Multilingual semantic','entity':'Explicit entities','structured':'Structured context'}

THEMES={
    'light':{'bg':'#F3EEE0','surface':'#FBF8F0','raised':'#ECE6D6','border':'#CFC7B2','text':'#121211','muted':'#4A463E','accent':'#9B1C1C'},
    'dark':{'bg':'#121211','surface':'#1E1D1B','raised':'#292720','border':'#625A49','text':'#ECE6D6','muted':'#C1B9A6','accent':'#E07A70'}
}

def current_theme():
    mode=st.session_state.get('visual_theme','light')
    return mode if mode in THEMES else 'light'

def apply_theme():
    """Shared theme for entry screens, native widgets and research workspaces."""
    requested=st.query_params.get('theme')
    if 'visual_theme' not in st.session_state:st.session_state.visual_theme=requested if requested in THEMES else 'light'
    mode=current_theme();tokens=THEMES[mode]
    css=(ROOT/'assets/interface/sherlocked.css').read_text(encoding='utf-8-sig')
    variables=';'.join('--sk-'+name+':'+value for name,value in tokens.items())
    css+=':root{'+variables+';color-scheme:'+mode+'}'
    css+='[data-testid="stApp"]{--text-color:'+tokens['text']+';--background-color:'+tokens['bg']+';--secondary-background-color:'+tokens['surface']+'}'
    if mode=='dark':css+='[data-testid="stDataFrame"]{background:#FBF8F0}'
    st.markdown('<style>'+css+'</style>',unsafe_allow_html=True)

def switch_theme():
    st.session_state.visual_theme='dark' if current_theme()=='light' else 'light'
    st.query_params['theme']=st.session_state.visual_theme

def theme_control():
    dark=current_theme()=='dark'
    st.button('Light mode' if dark else 'Dark mode',icon=':material/light_mode:' if dark else ':material/dark_mode:',
              key='theme_switch',on_click=switch_theme,width='stretch')


def logo_uri(name='sherlocked-emblem.svg'):
    allowed={'sherlocked-emblem.svg','sherlocked-primary.svg','sherlocked-monochrome.svg','sherlocked-ivory.svg','sherlocked-forensic-red.svg','favicon.svg'}
    if name not in allowed: raise ValueError('Unknown bundled identity asset')
    return 'data:image/svg+xml;base64,'+base64.b64encode((ROOT/'assets/branding'/name).read_bytes()).decode('ascii')

def section_label(label):
    st.markdown('<div class="sk-kicker">'+escape(str(label))+'</div>',unsafe_allow_html=True)

kicker=section_label

def page_title(title,description=''):
    st.title(title)
    if description: st.caption(description)

def panel_header(title,description=None):
    st.markdown('<div class="sk-panel-head"><h3>'+escape(str(title))+'</h3>'+('<span>'+escape(str(description))+'</span>' if description else '')+'</div>',unsafe_allow_html=True)

def status_badge(label,tone='neutral'):
    tone=tone if tone in ('neutral','info','success','warning','error','ai') else 'neutral'
    return '<span class="sk-badge '+tone+'">'+escape(str(label))+'</span>'

def lang_chip(language):
    return status_badge({'en':'ENGLISH','bn':'BANGLA','mixed':'MIXED'}.get(language,'UNCLASSIFIED'))

def metric_strip(items):
    cells=['<div class="sk-stat"><div class="sk-stat-label">'+escape(str(i['label']))+'</div><div class="sk-stat-value">'+escape(str(i['value']))+'</div><div class="sk-stat-detail">'+escape(str(i.get('detail','')))+'</div></div>' for i in items]
    st.markdown('<div class="sk-strip">'+''.join(cells)+'</div>',unsafe_allow_html=True)

def empty_state(title,detail):
    st.markdown('<div class="sk-empty"><strong>'+escape(str(title))+'</strong><p>'+escape(str(detail))+'</p></div>',unsafe_allow_html=True)

def source_document(report,compact=False):
    text=str(report.get('text',''));text=text[:257]+'…' if compact and len(text)>260 else text
    st.markdown('<article class="sk-document"><div class="sk-document-meta"><span class="sk-document-id">'+escape(str(report.get('report_id','QUERY')))+'</span>'+lang_chip(report.get('language'))+'<span>'+escape(str(report.get('occurred_at') or 'Time not recorded'))+'</span></div><div class="sk-document-body">'+escape(text)+'</div><div class="sk-document-source">SOURCE / '+escape(str(report.get('source_id','session input')))+'</div></article>',unsafe_allow_html=True)

def source_quote(text,reference='',spans=None):
    text=str(text);parts=[];cursor=0
    ordered=sorted((a,b) for a,b in (spans or []) if isinstance(a,int) and isinstance(b,int) and 0<=a<b<=len(text))
    for a,b in ordered:
        if a<cursor: continue
        parts.extend([escape(text[cursor:a]),'<mark>'+escape(text[a:b])+'</mark>']);cursor=b
    parts.append(escape(text[cursor:]))
    st.markdown('<div class="sk-source-quote">'+''.join(parts)+'</div><div class="sk-source-ref">'+escape(str(reference))+'</div>',unsafe_allow_html=True)

def ranked_candidate(hit,rank):
    report=hit['report'];preview=report['text'][:155]+('…' if len(report['text'])>155 else '')
    st.markdown('<article class="sk-ranked-file"><div class="rank">'+f'{rank:02d}'+'</div><div><div class="file-id">'+escape(str(report['report_id']))+' <span>/ '+escape(str(report.get('language','unknown')).upper())+'</span></div><div class="preview">'+escape(preview)+'</div><div class="source">'+escape(str(report.get('source_id','source unavailable')))+'</div></div><div class="score">'+f"{hit['score']:.4f}"+'<small>RANKING<br>SIGNAL</small></div></article>',unsafe_allow_html=True)

def human_review_gate():
    st.markdown('<aside class="sk-review-gate"><strong>HUMAN REVIEW / UNREVIEWED</strong><span>Computed suggestion. No analyst confirmation is recorded.</span></aside>',unsafe_allow_html=True)

def contradiction_alert(row):
    field=escape(str(row.get('field','Recorded field')))
    left=escape(str(row.get('query','unknown')));right=escape(str(row.get('candidate','unknown')))
    note=escape(str(row.get('note','Different recorded values; not proof of unrelated incidents.')))
    st.markdown('<aside class="sk-contradiction"><strong>RECORDED DIFFERENCE / '+field+'</strong><br>'+left+' → '+right+'<br>'+note+'</aside>',unsafe_allow_html=True)

def chart_theme(fig,height=None,surface='paper'):
    """Explicit offline Plotly theme; lengths and raw result values are untouched."""
    ink=surface=='ink' or current_theme()=='dark';theme=THEMES['dark' if ink else 'light']
    bg=theme['surface'];text=theme['text'];muted=theme['muted'];line=theme['border']
    # Adapt ink marks without touching coordinates, values or customdata.
    if ink:
        replacements={'#121211':'#ECE6D6','#4A463E':'#C1B9A6','#9B1C1C':'#E07A70'}
        for trace in fig.data:
            if hasattr(trace,'textfont'):trace.textfont.color=TOKENS['ink'] if trace.type=='heatmap' else text
            if hasattr(trace,'marker') and hasattr(trace.marker,'color'):
                color=trace.marker.color
                if isinstance(color,str) and color.upper() in replacements:trace.marker.color=replacements[color.upper()]
                elif isinstance(color,(tuple,list)):trace.marker.color=[replacements.get(str(c).upper(),c) for c in color]
            if hasattr(trace,'marker') and hasattr(trace.marker,'colors') and trace.marker.colors:
                trace.marker.colors=[replacements.get(str(c).upper(),c) for c in trace.marker.colors]
            if hasattr(trace,'line') and trace.line.color and str(trace.line.color).upper() in replacements:trace.line.color=replacements[str(trace.line.color).upper()]
            if hasattr(trace,'error_x') and trace.error_x.color:trace.error_x.color=muted
            if hasattr(trace,'error_y') and trace.error_y.color:trace.error_y.color=muted
        for annotation in fig.layout.annotations:annotation.font.color=text
    fig.update_layout(template='plotly_dark' if ink else 'plotly_white',paper_bgcolor=bg,plot_bgcolor=bg,
        font={'family':'Segoe UI, Nirmala UI, Noto Sans Bengali, sans-serif','color':text,'size':14},
        margin={'l':14,'r':18,'t':30,'b':30},hoverlabel={'bgcolor':TOKENS['ink-card'],'font_color':TOKENS['ivory'],'bordercolor':TOKENS['brass']},
        legend={'bgcolor':'rgba(0,0,0,0)','font':{'size':12,'color':text}})
    if height:fig.update_layout(height=height)
    fig.update_xaxes(gridcolor=line,zerolinecolor=line,linecolor=line,tickfont={'color':muted,'size':12},title_font={'size':12,'color':text},automargin=True)
    fig.update_yaxes(gridcolor=line,zerolinecolor=line,linecolor=line,tickfont={'color':muted,'size':12},title_font={'size':12,'color':text},automargin=True)
    return fig

def signal_chart(hit):
    raw=hit.get('components',{});normalized=hit.get('normalized_components',raw)
    names=[name for name in SIGNAL_LABELS if raw.get(name) is not None]
    values=[max(0,min(1,float(normalized.get(name) or 0))) for name in names]
    fig=go.Figure(go.Bar(y=[SIGNAL_LABELS[n] for n in names],x=values,orientation='h',marker_color=[SIGNAL_COLORS[n] for n in names],customdata=[float(raw[n]) for n in names],hovertemplate='%{y}<br>Display scale: %{x:.3f}<br>Raw signal: %{customdata:.4f}<extra></extra>',text=[f'{float(raw[n]):.3f}' for n in names],textposition='outside',textfont={'color':TOKENS['ink'],'size':12},cliponaxis=False))
    chart_theme(fig,250);fig.update_layout(margin={'l':0,'r':62,'t':8,'b':38},showlegend=False)
    fig.update_xaxes(range=[0,1.05],title_text='Normalized signal / not probability',tickvals=[0,.5,1]);fig.update_yaxes(autorange='reversed')
    return fig

@st.cache_data(ttl=30,show_spinner=False)
def dataset_health():
    try:
        path=resource_path('dataset')/'reports.jsonl';manifest=resource_path('dataset')/'manifest.json'
        expected=json.loads(manifest.read_text(encoding='utf-8-sig'))['sha256'];digest=hashlib.sha256(path.read_bytes()).hexdigest()
        return {'valid':digest==expected,'hash':digest,'label':'Manifest verified' if digest==expected else 'Manifest mismatch'}
    except (OSError,ValueError,KeyError) as error:
        return {'valid':False,'label':'Dataset check unavailable','error':str(error)}

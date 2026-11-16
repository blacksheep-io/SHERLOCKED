"""Branded landing and local sign-in screens for the research workspace."""
import streamlit as st
from .design import logo_uri,theme_control,section_label,metric_strip
from .paths import resource_path

def enter(view):
    st.session_state.entry_view=view
    if view=='login':st.session_state.pop('login_error',None)

def attempt_login():
    from .auth import authenticate
    username=st.session_state.get('login_username','')
    if authenticate(username,st.session_state.get('login_password','')):
        st.session_state.access_user=username.strip().casefold()
        st.session_state.entry_view='workspace'
        st.session_state.pop('login_error',None)
        st.session_state.login_password=''
    else:st.session_state.login_error=True

def sign_out():
    theme=st.session_state.get('visual_theme','light')
    for key in list(st.session_state):
        if key!='visual_theme':del st.session_state[key]
    st.session_state.visual_theme=theme
    st.session_state.entry_view='landing'

def entry_header(login=False):
    with st.container(key='entry_header'):
        brand,nav,theme=st.columns([5,1.5,1.5],vertical_alignment='center')
        with brand:
            st.markdown('<div class="sk-entry-brand"><img src="'+logo_uri()+'" alt="SHERLOCKED detective emblem"><div><strong>SHERLOCKED</strong><small>THE MULTILINGUAL CASE LINKAGE LAB</small></div></div>',unsafe_allow_html=True)
        with nav:
            if login:st.button('Overview',icon=':material/arrow_back:',on_click=enter,args=('landing',),width='stretch')
            else:st.button('Investigator access',icon=':material/key:',on_click=enter,args=('login',),width='stretch')
        with theme:theme_control()

def _bookplate():
    return '<div class="sk-bookplate"><i class="sk-thread" aria-hidden="true"></i><i class="sk-thread second" aria-hidden="true"></i><img src="'+logo_uri()+'" alt="Original deerstalker, detective profile and curved pipe"><strong>OBSERVE. CONNECT. QUESTION.</strong><small>CASE FILE NOIR / RESEARCH EDITION<br>AN OPEN FILE. A HUMAN DECISION.</small></div>'

def landing(records):
    entry_header()
    st.markdown('<div class="sk-landing-hero"><div><div class="sk-hero-kicker">EXPLAINABLE AI / ENGLISH · বাংলা · MIXED</div><h1>Every fragment<br>has a <em>story.</em></h1><p>Find the thread between multilingual reports. Follow each suggested connection back to the words that support it.</p><div class="sk-hero-note">FICTIONAL RECORDS. SOURCE-LINKED REASONING.<br>YOUR JUDGEMENT REMAINS THE FINAL WORD.</div></div>'+_bookplate()+'</div>',unsafe_allow_html=True)
    cta,note=st.columns([1,2],vertical_alignment='center')
    with cta:st.button('Enter the research lab',type='primary',icon=':material/arrow_forward:',on_click=enter,args=('login',),width='stretch')
    with note:st.caption('A local research instrument for potential report relationships. Every lead requires human review.')
    families={r.get('family_id') for r in records if r.get('family_id')}
    metric_strip([{'label':'Fictional reports','value':len(records),'detail':'Bundled research corpus'},
                  {'label':'Language labels','value':len({r.get('language') for r in records}),'detail':'English / Bangla / mixed'},
                  {'label':'Scenario families','value':len(families),'detail':'Authored synthetic scenarios'},
                  {'label':'Retrieval methods','value':8,'detail':'Keyword / semantic / hybrid'}])
    st.markdown('<div class="sk-entry-brief"><div><small>01 / DISCOVER</small><b>Across words and languages.</b><p>Compare keyword retrieval, multilingual embeddings and hybrid rankings on the same report.</p></div><div><small>02 / EXAMINE</small><b>Keep the source in sight.</b><p>Inspect matching passages, entity mentions and recorded differences alongside every candidate.</p></div><div><small>03 / QUESTION</small><b>Make the reasoning visible.</b><p>Explore suggested relationships and reproduce measured experiments. Similarity is a lead, never a verdict.</p></div></div>',unsafe_allow_html=True)
    st.markdown('<footer class="sk-module-footer">SHERLOCKED / LOCAL RESEARCH / FICTIONAL CORPUS / NO AUTOMATIC IDENTITY OR GUILT DECISIONS</footer>',unsafe_allow_html=True)

def login():
    from .auth import ensure_demo_account
    import sqlite3
    entry_header(login=True)
    cover,access=st.columns([1,1.1],gap='large',vertical_alignment='center')
    with cover:
        st.markdown('<section class="sk-login-cover"><img src="'+logo_uri()+'" alt="SHERLOCKED detective emblem"><h2>The game<br>is afoot.</h2><p>A quiet desk. An open file. A connection waiting to be examined.</p><small>SHERLOCKED / CASE FILE NOIR<br>LOCAL RESEARCH WORKSTATION</small></section>',unsafe_allow_html=True)
    with access:
        with st.container(key='access_card'):
            section_label('INVESTIGATOR ACCESS / LOCAL SESSION')
            st.title('Open your casebook.')
            st.caption('Sign in to the investigative research workspace.')
            try:ensure_demo_account()
            except (OSError,ValueError,sqlite3.Error):
                st.error('The local access store could not be opened. Check that the configured data folder is writable.')
                return
            with st.form('investigator_access',clear_on_submit=False):
                st.text_input('Username',autocomplete='username',max_chars=128,key='login_username')
                st.text_input('Password',type='password',autocomplete='current-password',max_chars=1024,key='login_password')
                st.form_submit_button('Unlock the workspace',type='primary',icon=':material/key:',width='stretch',on_click=attempt_login)
            if st.session_state.get('login_error'):
                st.error('Sign-in unsuccessful. Check your details or wait a minute before trying again.')
            with st.expander('Local demonstration access'):
                st.markdown('Username: **demo**');st.markdown('Password: **sherlocked-demo**')
                st.caption('Public demonstration account for fictional research. An existing changed password is preserved.')
            st.caption('Local session access only. Passwords are salted and hashed on this computer. Sign out when finished; reloading may require sign-in again.')
    st.markdown('<footer class="sk-module-footer">A RESEARCH DEMONSTRATION / HUMAN OVERSIGHT AT EVERY STEP / LOCAL ACCESS IS NOT ENTERPRISE AUTHENTICATION</footer>',unsafe_allow_html=True)

def gateway():
    """Return true only for an authenticated Streamlit session."""
    if st.session_state.get('access_user'):return True
    if st.session_state.get('entry_view','landing')=='login':login()
    else:
        from .dataset import load
        landing(load(resource_path('dataset')/'reports.jsonl'))
    return False

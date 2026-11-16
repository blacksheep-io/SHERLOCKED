"""Source-grounded heuristic extraction and comparison; no identity decisions."""
from copy import deepcopy
from datetime import datetime
from difflib import SequenceMatcher
import hashlib
import re
import unicodedata

ALIASES = {
    'location': {'lotus': ['Lotus','পদ্ম'], 'river': ['River','নদী'], 'cedar': ['Cedar','দেবদারু'],
                 'moon': ['Moon','চাঁদ'], 'garden': ['Garden','বাগান'], 'hill': ['Hill','পাহাড়']},
    'object': {'bicycle': ['bicycle','bike','সাইকেল'], 'parcel': ['parcel','package','পার্সেল'],
               'lantern': ['lantern','লণ্ঠন'], 'laptop': ['laptop','ল্যাপটপ'],
               'camera': ['camera','ক্যামেরা'], 'wallet': ['wallet','মানিব্যাগ']},
    'vehicle': {'cart': ['cart','trolley','ঠেলাগাড়ি','thelagari'],
                'motorcycle': ['motorcycle','মোটরসাইকেল'], 'van': ['van','ভ্যান']},
}
LABELS = {'person': r'person|witness|ব্যক্তি|সাক্ষী',
          'organization': r'organization|organisation|company|সংস্থা|প্রতিষ্ঠান',
          'location': r'location|place|স্থান', 'vehicle': r'vehicle|যানবাহন',
          'identifier': r'identifier|registration|serial|আইডি|নিবন্ধন', 'object': r'object|item|বস্তু'}
INCIDENT_RULES = {'missing_property': r'\bmissing\b|\bdisappeared\b|হারিয়ে|নিখোঁজ|hariye',
                  'theft': r'\btheft\b|\bstolen\b|চুরি', 'fire': r'\bfire\b|\bsmoke\b|আগুন|ধোঁয়া',
                  'damage': r'\bdamage\b|\bbroken\b|ভাঙা|ক্ষতি', 'lost_property': r'\blost\b|পাওয়া গেছে'}


def canonical_entity(value, entity_type):
    value = unicodedata.normalize('NFC', str(value)).casefold().strip()
    for canonical, aliases in ALIASES.get(entity_type, {}).items():
        if any(value == unicodedata.normalize('NFC', a).casefold() for a in aliases):
            return canonical
    return ' '.join(''.join(c for c in value if unicodedata.category(c)[0] in 'LNM' or c.isspace()).split())


def identify_language(text):
    bn = sum('\u0980' <= c <= '\u09ff' and unicodedata.category(c)[0] == 'L' for c in text)
    latin = sum('a' <= c.lower() <= 'z' for c in text)
    return 'mixed' if bn and latin else 'bn' if bn else 'en' if latin else 'unknown'


def extract_entities(text, source_id):
    mentions = []
    def add(kind, start, end, method):
        if not text[start:end].strip() or any(m['type']==kind and m['start']==start and m['end']==end for m in mentions):
            return
        mentions.append(dict(type=kind, surface=text[start:end], normalized=canonical_entity(text[start:end],kind),
                             start=start, end=end, source_id=source_id, method=method, confidence=None,
                             status='explicit mention; identity unverified'))
    for kind, labels in LABELS.items():
        for match in re.finditer(rf'(?:{labels})\s*[:：]\s*([^\n;।.]+)', text, re.I):
            start,end = match.span(1)
            while end>start and text[end-1].isspace():
                end-=1
            add(kind,start,end,'explicit_label_rule')
    for kind, entries in ALIASES.items():
        for aliases in entries.values():
            for alias in aliases:
                for match in re.finditer(r'(?<!\w)'+re.escape(alias)+r'(?!\w)',text,re.I):
                    if not any(m['type']==kind and m['start']<=match.start() and m['end']>=match.end() for m in mentions):
                        add(kind,match.start(),match.end(),'fictional_lexicon_rule')
    return sorted(mentions,key=lambda m:(m['start'],m['end'],m['type']))


def analyze_report(text, report_id=None, metadata=None):
    if not isinstance(text,str) or not text.strip():
        raise ValueError('A non-empty fictional report is required')
    if len(text)>100000:
        raise ValueError('Report exceeds 100,000 characters')
    record = deepcopy(metadata or {})
    digest = hashlib.sha256(text.encode('utf-8')).hexdigest()
    record.update(text=text, report_id=report_id or record.get('report_id') or f'U-{digest[:12]}', fictional=True)
    record.setdefault('source_id',f"user-fictional:{record['report_id']}")
    for key,value in [('family_id',None),('split','unassigned'),('variant','submitted'),('generator_version','user-fictional-v1')]:
        record.setdefault(key,value)
    record.setdefault('language',identify_language(text))
    record['language_detection'] = dict(value=identify_language(text), method='script_heuristic',
                                         limitation='Latin-only Banglish is classified en; this identifies scripts')
    if not record.get('entities'):
        record['entities'] = extract_entities(text,record['source_id'])
    provenance = deepcopy(record.get('metadata_provenance',{}))
    for field in ['incident_type','location','occurred_at']:
        if record.get(field) is not None:
            provenance.setdefault(field,dict(method='provided_annotation',source_id=record['source_id'],
                                              note='Annotation; may not be stated in narrative'))
    if not record.get('incident_type'):
        for incident,pattern in INCIDENT_RULES.items():
            match = re.search(pattern,text,re.I)
            if match:
                record['incident_type'] = incident
                provenance['incident_type'] = dict(method='keyword_rule',start=match.start(),end=match.end(),surface=match.group(),source_id=record['source_id'])
                break
    if not record.get('location'):
        mention = next((m for m in record['entities'] if m.get('type')=='location'),None)
        if mention:
            record['location'] = mention.get('normalized',mention.get('surface'))
            provenance['location'] = {key:mention[key] for key in ['method','start','end','surface','source_id'] if key in mention}
    if not record.get('occurred_at'):
        match = re.search(r'\b\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2}(?::\d{2})?(?:Z|[+-]\d{2}:\d{2})?)?\b',text)
        if match:
            try:
                datetime.fromisoformat(match.group().replace('Z','+00:00'))
                record['occurred_at'] = match.group()
                provenance['occurred_at'] = dict(method='iso_date_rule',start=match.start(),end=match.end(),surface=match.group(),source_id=record['source_id'])
            except ValueError:
                pass
    for field in ['incident_type','location','occurred_at']:
        record.setdefault(field,None)
    record['metadata_provenance'] = provenance
    return record


def enrich_report(record):
    return analyze_report(record['text'],record.get('report_id'),record)


def compare_entities(a,b):
    a,b = enrich_report(a),enrich_report(b)
    left,right = a['entities'],b['entities']
    if not left or not right:
        return dict(score=None,matches=[],missing=['entities absent in query' if not left else 'entities absent in candidate'],contradictions=[],status='unknown')
    matches,scores,seen = [],[],set()
    for first in left:
        kind = first.get('type','unknown')
        surface = first.get('surface',first.get('value',''))
        norm = canonical_entity(first.get('normalized',surface),kind)
        if (kind,norm) in seen:
            continue
        seen.add((kind,norm))
        candidates = [e for e in right if e.get('type')==kind]
        best = (0.,None,'no match')
        for second in candidates:
            other = second.get('surface',second.get('value',''))
            other_norm = canonical_entity(second.get('normalized',other),kind)
            if surface==other:
                score,status = 1.,'exact'
            elif norm and norm==other_norm:
                score,status = 1.,'normalized'
            else:
                ratio = SequenceMatcher(None,norm,other_norm).ratio() if norm and other_norm else 0.
                if min(len(norm),len(other_norm))>=5 and kind!='identifier' and ratio>=.88:
                    score,status = .65,'approximate'
                elif min(len(norm),len(other_norm))>=5 and kind!='identifier' and ratio>=.7:
                    score,status = .3,'possible'
                else:
                    score,status = 0.,'no match'
            if score>best[0] or best[1] is None:
                best = score,second,status
        if not candidates:
            matches.append(dict(type=kind,query=first,candidate=None,status='unknown',score=None))
            continue
        score,second,status = best
        scores.append(score)
        matches.append(dict(type=kind,query=first,candidate=second,status=status,score=score,warning='Mention similarity does not establish shared identity'))
    return dict(score=sum(scores)/len(scores) if scores else None,matches=matches,
                missing=[f"candidate has no {m['type']} mention" for m in matches if m['status']=='unknown'],contradictions=[],status='possible report signal')


def compare_structured(a,b):
    a,b = enrich_report(a),enrich_report(b)
    matches,missing,contradictions,values = [],[],[],[]
    for field in ['incident_type','location','occurred_at']:
        x,y = a.get(field),b.get(field)
        if x is None or y is None:
            missing.append(dict(field=field,query=x,candidate=y,status='unknown'))
            continue
        if field=='occurred_at':
            try:
                dx,dy = datetime.fromisoformat(x.replace('Z','+00:00')),datetime.fromisoformat(y.replace('Z','+00:00'))
                if (dx.tzinfo is None)!=(dy.tzinfo is None):
                    missing.append(dict(field=field,status='unknown',reason='timezone precision differs'))
                    continue
                days = abs((dx-dy).total_seconds())/86400
                value,reason = max(0.,1-days/7.),f'{days:.2f} days apart; linear 7-day compatibility window'
            except (ValueError,TypeError):
                missing.append(dict(field=field,status='unknown',reason='invalid date'))
                continue
        else:
            kind = 'location' if field=='location' else 'incident_type'
            value,reason = float(canonical_entity(x,kind)==canonical_entity(y,kind)),'normalized equality'
        row = dict(field=field,query=x,candidate=y,score=value,reason=reason,
                   query_provenance=a['metadata_provenance'].get(field),candidate_provenance=b['metadata_provenance'].get(field))
        values.append(value); matches.append(row)
        if value==0:
            contradictions.append(dict(field=field,query=x,candidate=y,note='Different recorded values; not proof of unrelated incidents'))
    return dict(score=sum(values)/len(values) if values else None,matches=matches,missing=missing,contradictions=contradictions,
                policy='Equal weight over observed fields only; missing fields do not vote')

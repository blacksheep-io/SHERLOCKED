"""Validated UTF-8 fictional dataset ingestion and export."""
import json
from .signals import enrich_report

MAX_UPLOAD_BYTES = 5_000_000


def decode_text(payload):
    if len(payload)>MAX_UPLOAD_BYTES:
        raise ValueError('Upload exceeds the 5 MB limit')
    try:
        return payload.decode('utf-8-sig')
    except UnicodeDecodeError as exc:
        raise ValueError('Upload must be UTF-8 text') from exc


def validate_records(records):
    if not isinstance(records,list) or not records:
        raise ValueError('Dataset must be a non-empty list of reports')
    if len(records)>10000:
        raise ValueError('Dataset exceeds 10,000 reports')
    ids,families,result = set(),{},[]
    for item in records:
        if not isinstance(item,dict):
            raise ValueError('Each report must be an object')
        rid = item.get('report_id')
        if not isinstance(rid,str) or not rid.strip() or len(rid)>128:
            raise ValueError('Each report requires a stable report_id (1-128 characters)')
        if rid in ids:
            raise ValueError(f'Duplicate report_id: {rid}')
        ids.add(rid)
        if item.get('fictional') is not True:
            raise ValueError(f'{rid}: fictional must be true')
        if not isinstance(item.get('text'),str) or not item['text'].strip() or len(item['text'])>100000:
            raise ValueError(f'{rid}: text must contain 1-100,000 characters')
        if item.get('split','unassigned') not in ['train','dev','test','unassigned']:
            raise ValueError(f'{rid}: invalid split')
        if item.get('language','unknown') not in ['en','bn','mixed','unknown']:
            raise ValueError(f'{rid}: invalid language')
        if item.get('entities') is not None and not isinstance(item['entities'],list):
            raise ValueError(f'{rid}: entities must be a list')
        for entity in item.get('entities') or []:
            if not isinstance(entity,dict) or not isinstance(entity.get('type'),str):
                raise ValueError(f'{rid}: each entity requires a type')
            if 'start' in entity or 'end' in entity:
                start,end = entity.get('start'),entity.get('end')
                if not isinstance(start,int) or not isinstance(end,int) or not 0<=start<end<=len(item['text']):
                    raise ValueError(f'{rid}: invalid entity source span')
                if entity.get('surface',item['text'][start:end])!=item['text'][start:end]:
                    raise ValueError(f'{rid}: entity surface does not match original source')
        family = item.get('family_id')
        if family is not None:
            if not isinstance(family,str) or not family:
                raise ValueError(f'{rid}: family_id must be a string or null')
            split = item.get('split','unassigned')
            if family in families and families[family]!=split:
                raise ValueError(f'Family {family} crosses splits')
            families[family] = split
        for field in ['location','occurred_at','incident_type']:
            if item.get(field) is not None and not isinstance(item[field],str):
                raise ValueError(f'{rid}: {field} must be text or null')
        result.append(enrich_report(item))
    return result


def parse_jsonl(payload):
    text = decode_text(payload) if isinstance(payload,bytes) else payload
    if not isinstance(text,str) or len(text.encode('utf-8'))>MAX_UPLOAD_BYTES:
        raise ValueError('Dataset must be UTF-8 JSONL below 5 MB')
    records = []
    for line_number,line in enumerate(text.splitlines(),1):
        if not line.strip():
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise ValueError(f'Invalid JSON at line {line_number}: {exc.msg}') from exc
    return validate_records(records)


def export_jsonl(records):
    return ''.join(json.dumps(r,ensure_ascii=False,sort_keys=True)+'\n' for r in records)

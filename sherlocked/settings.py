"""Local, non-secret application settings; no changes to source datasets."""
import json
from pathlib import Path
import math
import uuid
from .paths import ROOT

DEFAULTS = {'model_mode':'offline', 'device': 'auto', 'k1': 1.5, 'b': 0.75, 'rrf_k': 60,
            'weights': {'tfidf': 0.2, 'bm25': 0.2, 'semantic': 0.4, 'entity': 0.1, 'structured': 0.1}}


def read_settings():
    path = ROOT / 'configs/app.json'
    if not path.exists():
        return json.loads(json.dumps(DEFAULTS))
    return {**DEFAULTS, **json.loads(path.read_text(encoding='utf-8-sig'))}


def save_settings(settings):
    if settings.get('model_mode','offline') not in ('online','offline'):
        raise ValueError('Select online setup or offline portable mode')
    if settings['device'] not in ('auto', 'cpu', 'cuda'):
        raise ValueError('Select auto, cpu or cuda')
    if not 0 <= settings['b'] <= 1 or not 0 < settings['k1'] <= 3:
        raise ValueError('BM25 parameters are out of range')
    weights = settings['weights']
    if any(not math.isfinite(v) or v < 0 for v in weights.values()) or sum(weights.values()) <= 0:
        raise ValueError('Weights must be nonnegative, with at least one positive value')
    path = ROOT / 'configs/app.json'
    path.parent.mkdir(exist_ok=True)
    temporary = path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp')
    temporary.write_text(json.dumps(settings, indent=2), encoding='utf-8')
    temporary.replace(path)

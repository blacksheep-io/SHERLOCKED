"""Fixed train-fit, within-held-out-split retrieval protocol."""
import hashlib
import json
import math
import platform
import time
from pathlib import Path
from datetime import datetime, timezone
import uuid
from .paths import resource_path
import sklearn
from .dataset import load
from .retrieval import KeywordIndex


def metrics(ranked_ids, relevant, k=5):
    hits = [int(r in relevant) for r in ranked_ids[:k]]
    dcg = sum(hit / math.log2(i+2) for i, hit in enumerate(hits))
    ideal = sum(1 / math.log2(i+2) for i in range(min(k, len(relevant))))
    return dict(precision_at_5=sum(hits)/k, recall_at_5=sum(hits)/len(relevant) if relevant else 0,
                mrr_at_5=next((1/(i+1) for i,h in enumerate(hits) if h), 0),
                ndcg_at_5=dcg/ideal if ideal else 0)


def run(split='dev'):
    if split not in ('dev', 'test'):
        raise ValueError('Evaluation split must be dev or test')
    dataset_path = resource_path('dataset') / 'reports.jsonl'
    records = load(dataset_path)
    digest = hashlib.sha256(dataset_path.read_bytes()).hexdigest()
    manifest = json.loads((resource_path('dataset') / 'manifest.json').read_text(encoding='utf-8-sig'))
    if digest != manifest['sha256']:
        raise ValueError('Dataset hash differs from manifest; regenerate or version your edited dataset')
    index = KeywordIndex([r for r in records if r['split'] == 'train'])
    pool = [r for r in records if r['split'] == split]
    rows = []
    for query in pool:
        relevant = {r['report_id'] for r in pool if r['family_id'] == query['family_id'] and r != query}
        started = time.perf_counter()
        ranked = index.search(query['text'], pool, exclude_id=query['report_id'], include_zero=True)
        elapsed = (time.perf_counter()-started)*1000
        rows.append(dict(query_id=query['report_id'], family_id=query['family_id'], language=query['language'],
                         variant=query['variant'], latency_ms=elapsed,
                         ranked_ids=[r['report']['report_id'] for r in ranked],
                         ranked_scores=[r['score'] for r in ranked],
                         false_positive_ids=[r['report']['report_id'] for r in ranked if r['report']['report_id'] not in relevant],
                         **metrics([r['report']['report_id'] for r in ranked], relevant)))
    def aggregate(items):
        return {key: sum(r[key] for r in items)/len(items) for key in
                ['precision_at_5','recall_at_5','mrr_at_5','ndcg_at_5','latency_ms']}
    result = dict(method='word-tfidf-cosine', split=split, fit_split='train', k=5,
                  protocol='within-split leave-one-report-out; zero scores tie by report_id',
                  python=platform.python_version(), sklearn=sklearn.__version__,
                  dataset_sha256=digest, seed=manifest['seed'],
                  configuration=dict(tokenizer='Unicode L/N/M, NFC, casefold', norm='l2', smooth_idf=True,
                                     sublinear_tf=False, use_idf=True, stop_words=None),
                  platform=platform.platform(),
                  latency_p95_ms=sorted(r['latency_ms'] for r in rows)[math.ceil(.95*len(rows))-1],
                  query_count=len(rows), aggregate=aggregate(rows),
                  by_language={lang:aggregate([r for r in rows if r['language']==lang]) for lang in sorted({r['language'] for r in rows})},
                  by_variant={v:aggregate([r for r in rows if r['variant']==v]) for v in sorted({r['variant'] for r in rows})},
                  queries=rows)
    directory = resource_path('results') / 'reports'
    directory.mkdir(parents=True, exist_ok=True)
    run_id = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S') + '-' + uuid.uuid4().hex[:8]
    destination = directory / f'tfidf_{split}_{run_id}.json'
    result.update(dataset_path=str(dataset_path.resolve()), output_path=str(destination.resolve()))
    with destination.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(result, stream, indent=2)
    return result


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--split', choices=['dev','test'], default='dev')
    print(json.dumps(run(parser.parse_args().split)['aggregate'], indent=2))

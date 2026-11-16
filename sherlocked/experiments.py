"""Reproducible, family-isolated retrieval experiments and exports.

The historical TF-IDF algorithm is retained in evaluate.py; resources resolve portably.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.metadata
import io
import json
import math
import platform
import random
import statistics
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .paths import ROOT, resource_path
METHODS = ['tfidf', 'bm25', 'semantic', 'entity', 'structured', 'hybrid', 'rrf', 'hybrid_rerank']
METRIC_KEYS = ['precision', 'recall', 'mrr', 'ndcg']
DEFAULT_ABLATIONS = {
    'hybrid_without_entity': {'entity': 0},
    'hybrid_without_structured': {'structured': 0},
    'hybrid_without_semantic': {'semantic': 0},
    'lexical_semantic': {'entity': 0, 'structured': 0},
}


def retrieval_metrics(ranked_ids, relevant, k=5):
    """Fixed-K binary relevance. No-positive recall/nDCG are undefined (None)."""
    if k < 1:
        raise ValueError('k must be positive')
    if len(ranked_ids) != len(set(ranked_ids)):
        raise ValueError('Ranked report IDs must be unique')
    relevant = set(relevant)
    hits = [int(report_id in relevant) for report_id in ranked_ids[:k]]
    ideal = sum(1 / math.log2(i + 2) for i in range(min(k, len(relevant))))
    return dict(precision=sum(hits) / k,
                recall=sum(hits) / len(relevant) if relevant else None,
                mrr=next((1 / (i + 1) for i, hit in enumerate(hits) if hit), 0.0),
                ndcg=sum(hit / math.log2(i + 2) for i, hit in enumerate(hits)) / ideal if ideal else None)


def aggregate(rows):
    out = {'query_count': len(rows)}
    for key in METRIC_KEYS + ['latency_ms']:
        values = [r[key] for r in rows if r.get(key) is not None]
        out[key] = statistics.mean(values) if values else None
    times = sorted(r['latency_ms'] for r in rows)
    out['latency_p95_ms'] = times[math.ceil(.95 * len(times)) - 1] if times else None
    negatives = [r for r in rows if r.get('relevant_count') == 0]
    out['no_match_query_count'] = len(negatives)
    out['no_match_false_positive_query_rate'] = (
        sum(bool(r['positive_score_ids']) for r in negatives) / len(negatives) if negatives else None)
    out['mean_unrelated_results_at_k'] = statistics.mean(len(r['false_positive_ids']) for r in rows) if rows else None
    return out


def family_bootstrap(rows, seed=20261104, samples=1000):
    """Cluster bootstrap: sample whole families, preserving correlated siblings."""
    groups = {}
    for row in rows:
        groups.setdefault(row['family_id'] or row['query_id'], []).append(row)
    if not groups:
        return {}
    rng = random.Random(seed)
    families = sorted(groups)
    values = {key: [] for key in METRIC_KEYS}
    for _ in range(samples):
        sample = [r for family in rng.choices(families, k=len(families)) for r in groups[family]]
        stats = aggregate(sample)
        for key in METRIC_KEYS:
            if stats[key] is not None:
                values[key].append(stats[key])
    def interval(numbers):
        ordered = sorted(numbers)
        if not ordered:
            return None
        return [ordered[int(.025 * (len(ordered) - 1))], ordered[int(.975 * (len(ordered) - 1))]]
    return {'unit': 'scenario family', 'seed': seed, 'resamples': samples,
            'family_count': len(families), 'warning': 'Small family counts give unstable confidence intervals.',
            'intervals_95': {key: interval(numbers) for key, numbers in values.items()}}


def validate_partitions(records):
    ids, families = set(), {}
    for row in records:
        if row['report_id'] in ids:
            raise ValueError('Duplicate report ID in experiment dataset')
        ids.add(row['report_id'])
        if not row.get('fictional'):
            raise ValueError('Experiments accept explicitly fictional reports only')
        family = row.get('family_id')
        split = row.get('split')
        if split not in {'train', 'dev', 'test'}:
            raise ValueError('Experiment rows need train/dev/test split annotations')
        if family is not None:
            families.setdefault(family, set()).add(split)
    if any(len(splits) != 1 for splits in families.values()):
        raise ValueError('Scenario family leakage across partitions')
    if not any(r['split'] == 'train' for r in records):
        raise ValueError('A training partition is required for lexical index fitting')


def code_hash():
    digest = hashlib.sha256()
    for path in sorted((ROOT / 'sherlocked').glob('*.py')):
        digest.update(path.name.encode('utf-8'))
        digest.update(path.read_bytes())
    return digest.hexdigest()


def dependencies():
    return {name: importlib.metadata.version(name) for name in
            ['numpy', 'scikit-learn', 'streamlit', 'plotly', 'torch', 'sentence-transformers']
            if _installed(name)}


def _installed(name):
    try:
        importlib.metadata.version(name)
        return True
    except importlib.metadata.PackageNotFoundError:
        return False


def summary_csv(artifact):
    stream = io.StringIO(newline='')
    writer = csv.DictWriter(stream, fieldnames=['method', 'status', 'k', 'precision', 'recall', 'mrr', 'ndcg',
                                                'latency_ms', 'latency_p95_ms', 'query_count', 'error'])
    writer.writeheader()
    for method, result in artifact['methods'].items():
        stats = result.get('aggregate', {})
        writer.writerow(dict(method=method, status=result['status'], k=artifact['k'],
                             error=result.get('error', ''),
                             **{key: stats.get(key) for key in writer.fieldnames
                                if key not in {'method', 'status', 'k', 'error'}}))
    return stream.getvalue()


def _slice(rows, field):
    return {str(value): aggregate([row for row in rows if row.get(field) == value])
            for value in sorted({row.get(field) for row in rows}, key=str)}


def run_experiment(methods=None, split='dev', k=5, config=None, dataset_path=None,
                   output_dir=None, ablations=False, engine=None):
    """Run and save actual rankings. Failed methods remain explicit failed entries.

    `engine` is an injectable retrieval service for isolated test fixtures. It is not
    serialized. Test split execution is explicit and never used for weight selection.
    """
    if split not in {'dev', 'test'}:
        raise ValueError('Choose dev or test; training reports are never scored as evaluation queries')
    if not 1 <= k <= 100:
        raise ValueError('k must be between 1 and 100')
    methods = list(dict.fromkeys(methods or ['tfidf', 'bm25']))
    if any(method not in METHODS for method in methods):
        raise ValueError('Unknown retrieval method')
    config = dict(config or {})
    config.setdefault('explain_passages', False)
    path = Path(dataset_path) if dataset_path is not None else resource_path('dataset') / 'reports.jsonl'
    payload = path.read_bytes()
    records = [json.loads(line) for line in payload.decode('utf-8-sig').splitlines() if line.strip()]
    validate_partitions(records)
    digest = hashlib.sha256(payload).hexdigest()
    manifest_path = path.with_name('manifest.json')
    if path.name == 'reports.jsonl' and manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding='utf-8-sig'))
        if manifest.get('sha256') != digest:
            raise ValueError('Dataset manifest checksum mismatch')
    if config.get('source_only', False):
        # A controlled ablation prevents generator-provided timestamps and other
        # annotations acting as near-perfect family proxies. Re-extract from text.
        records = [{key: value for key, value in row.items()
                    if key not in {'incident_type', 'location', 'occurred_at', 'entities', 'metadata_provenance'}}
                   for row in records]
    train = [row for row in records if row['split'] == 'train']
    pool = [row for row in records if row['split'] == split]
    if len(pool) < 2:
        raise ValueError('Evaluation partition must have at least two reports')
    if engine is None:
        from .engine import Engine
        engine = Engine(train, config=config)
    model_metadata = getattr(engine, 'model_metadata', {}) or {}
    for config_key, metadata_key in [('model_id', 'model_id'), ('model_revision', 'revision')]:
        if config.get(config_key) and config[config_key] != model_metadata.get(metadata_key):
            raise ValueError(f'Frozen {config_key} differs from the retrieval engine model')
    now = datetime.now(timezone.utc)
    run_id = now.strftime('%Y%m%dT%H%M%S') + '-' + uuid.uuid4().hex[:8]
    result = dict(schema_version=1, experiment_id=run_id, created_at_utc=now.isoformat(),
                  dataset_path=str(path.resolve()), dataset_sha256=digest, code_sha256=code_hash(),
                  split=split, fit_split='train', k=k, seed=20261104, configuration=config,
                  protocol='Within held-out partition leave-one-report-out; fixed K; zero scores tie by ID.',
                  label_definition='Relevant iff same non-null synthetic scenario family; query self excluded.',
                  platform=platform.platform(), python=platform.python_version(), dependencies=dependencies(),
                  methods={})
    plans = [(method, method, None) for method in methods]
    if ablations:
        defaults = {'tfidf': .2, 'bm25': .2, 'semantic': .4, 'entity': .1, 'structured': .1}
        defaults.update(config.get('weights', {}))
        plans += [(name, 'hybrid', dict(defaults, **overrides)) for name, overrides in DEFAULT_ABLATIONS.items()]
    for label, method, weights in plans:
        rows = []
        try:
            for query in pool:
                relevant = {r['report_id'] for r in pool if r['report_id'] != query['report_id']
                            and query.get('family_id') is not None and r.get('family_id') == query['family_id']}
                started = time.perf_counter()
                kwargs = dict(method=method, k=k, exclude_id=query['report_id'], include_zero=True)
                if weights is not None:
                    kwargs['weights'] = weights
                ranked = engine.search(query, pool, **kwargs)
                elapsed = (time.perf_counter() - started) * 1000
                ranked_ids = [item['report']['report_id'] for item in ranked]
                rows.append(dict(query_id=query['report_id'], family_id=query.get('family_id'),
                                 language=query.get('language', 'unknown'), variant=query.get('variant', 'unknown'),
                                 latency_ms=elapsed, relevant_count=len(relevant),
                                 ranked_ids=ranked_ids, ranked_scores=[item['score'] for item in ranked],
                                 positive_score_ids=[item['report']['report_id'] for item in ranked if item['score'] > 0],
                                 false_positive_ids=[rid for rid in ranked_ids if rid not in relevant],
                                 missed_relevant_ids=sorted(relevant - set(ranked_ids)),
                                 candidate_languages=[item['report'].get('language', 'unknown') for item in ranked],
                                 **retrieval_metrics(ranked_ids, relevant, k)))
            language_pairs = {}
            for query in pool:
                row = next(r for r in rows if r['query_id'] == query['report_id'])
                for candidate_language in sorted({r.get('language', 'unknown') for r in pool}):
                    relevant_in_language = {r['report_id'] for r in pool if r['report_id'] != query['report_id']
                                           and query.get('family_id') is not None
                                           and r.get('family_id') == query['family_id']
                                           and r.get('language', 'unknown') == candidate_language}
                    found = {rid for rid, language in zip(row['ranked_ids'], row['candidate_languages'])
                             if language == candidate_language and rid in relevant_in_language}
                    pair = query.get('language', 'unknown') + '→' + candidate_language
                    language_pairs.setdefault(pair, []).append(len(found) / len(relevant_in_language)
                                                               if relevant_in_language else None)
            result['methods'][label] = dict(status='completed', weights=weights,
                                            aggregate=aggregate(rows), family_bootstrap=family_bootstrap(rows),
                                            by_language=_slice(rows, 'language'), by_variant=_slice(rows, 'variant'),
                                            by_family=_slice(rows, 'family_id'),
                                            recall_by_language_pair={pair: statistics.mean([v for v in values if v is not None])
                                                                     if any(v is not None for v in values) else None
                                                                     for pair, values in language_pairs.items()},
                                            queries=rows)
        except Exception as exc:
            result['methods'][label] = dict(status='failed', error=f'{type(exc).__name__}: {exc}',
                                            completed_query_count=len(rows), queries=rows)
    result['model'] = getattr(engine, 'model_metadata', None)
    completed = {name: entry for name, entry in result['methods'].items()
                 if entry['status'] == 'completed' and entry['aggregate']['ndcg'] is not None}
    result['development_recommendation'] = (
        max(completed, key=lambda name: completed[name]['aggregate']['ndcg']) if split == 'dev' and completed else None)
    result['selection_note'] = 'Highest observed dev nDCG only; small synthetic sample, no significance or generalization claim.'
    fingerprint_payload = {name: [{key: row[key] for key in ['query_id', 'ranked_ids', 'ranked_scores']}
                                 for row in entry['queries']]
                           for name, entry in result['methods'].items() if entry['status'] == 'completed'}
    result['ranking_fingerprint'] = hashlib.sha256(json.dumps(fingerprint_payload, sort_keys=True).encode()).hexdigest()
    directory = Path(output_dir) if output_dir is not None else resource_path('results') / 'experiments'
    directory.mkdir(parents=True, exist_ok=True)
    result['json_path'] = str((directory / f'{run_id}.json').resolve())
    result['csv_path'] = str((directory / f'{run_id}.csv').resolve())
    def project_relative(value):
        try:
            return str(Path(value).resolve().relative_to(ROOT)).replace('\\', '/')
        except ValueError:
            return None
    result['portable_provenance'] = dict(dataset_filename=path.name,
                                         dataset_project_relative=project_relative(path),
                                         json_project_relative=project_relative(result['json_path']),
                                         csv_project_relative=project_relative(result['csv_path']))
    with Path(result['json_path']).open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
    with Path(result['csv_path']).open('xb') as stream:
        stream.write(summary_csv(result).encode('utf-8-sig'))
    return result


def list_experiments(directory=None):
    return [json.loads(path.read_text(encoding='utf-8')) for path in
            sorted((Path(directory) if directory is not None else resource_path('results') / 'experiments').glob('*.json'), reverse=True)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--methods', nargs='+', choices=METHODS, default=['tfidf', 'bm25'])
    parser.add_argument('--split', choices=['dev', 'test'], default='dev')
    parser.add_argument('--k', type=int, default=5)
    parser.add_argument('--device', choices=['auto', 'cpu', 'cuda'], default='auto')
    parser.add_argument('--config', type=Path)
    parser.add_argument('--dataset', type=Path)
    parser.add_argument('--ablations', action='store_true')
    parser.add_argument('--source-only', action='store_true', help='Discard provided metadata before source-text extraction')
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding='utf-8-sig')) if args.config else {}
    config['device'] = args.device
    config['source_only'] = args.source_only or config.get('source_only', False)
    artifact = run_experiment(args.methods, args.split, args.k, config, args.dataset, ablations=args.ablations)
    print(summary_csv(artifact))
    print('Saved:', artifact['json_path'])
    if any(entry['status'] == 'failed' for entry in artifact['methods'].values()):
        raise SystemExit(1)


if __name__ == '__main__':
    main()

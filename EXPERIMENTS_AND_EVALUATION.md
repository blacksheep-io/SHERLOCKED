> Phase 2 portability verification (5 November 2026): historical frozen test artifacts above are preserved; no new test-based tuning was performed. Two independent CPU development runs in a genuinely fresh environment produced identical ranked IDs for all eight methods. Experiment artifacts now include both resolved execution locations and portable relative provenance; defaults honor configurable dataset/results directories. Legacy evaluate.py writes unique results/reports files rather than replacing tfidf_dev.json. These are reproducibility/compatibility checks, not a new research-performance claim.

# Experiments and evaluation

SHERLOCKED measures retrieval of related **fictional reports**, not the correctness of real investigative conclusions. The original 90-report fixture remains available. Its preserved development result is `results/tfidf_dev.json`: Recall@5 0.35 and nDCG@5 0.2283. An inherited prompt called the latter nDCG@10; the original code and artifact verify that it is **@5**.

## Run a comparison

From the project directory in PowerShell:

```powershell
.venv/Scripts/python.exe -m sherlocked.experiments --methods tfidf bm25 --split dev --k 5
.venv/Scripts/python.exe -m sherlocked.experiments --methods tfidf bm25 semantic entity structured hybrid rrf hybrid_rerank --split dev --k 5 --ablations
.venv/Scripts/python.exe -m sherlocked.experiments --methods tfidf bm25 entity structured --split dev --source-only
```

Semantic methods require the pinned local model to be set up first in System Settings or with `scripts/setup_model.py`. A missing/unloadable model causes an explicit failed experiment entry; the runner never labels lexical results semantic. Each run saves a new JSON artifact and summary CSV under `results/experiments/`. Existing results are preserved. UI exports use actual results, not illustrative chart data.

The JSON stores dataset SHA-256, source-code SHA-256, dependency versions, platform, model revision, configuration, split, cutoff, seed, per-query ranked IDs and scores, missed related reports, unrelated returned IDs, query-language/variant/family slices, language-pair recall and latency. Unique run IDs preserve executions; `ranking_fingerprint` checks whether rankings reproduce independently of timings.

## Partition and label protocol

Every scenario family stays wholly in train, development or test. Lexical vocabulary and IDF fit **train only**. The selected held-out partition supplies both queries and candidate documents; each query excludes itself. A candidate is relevant if and only if it shares the query's non-null synthetic `family_id`; null-family queries have no positives. The runner validates IDs, fictional labels and family isolation and checks the original dataset manifest checksum.

The original fixture has 50 train and 20 dev/test reports. Its twenty dev queries each rank nineteen candidates with four relevant siblings. Shared templates still create style leakage. User-submitted unassigned reports are excluded from controlled experiments. The UI exploratory index is separate from train-fitted experiments.

Generator annotations include a unique date per family. Identical sibling timestamps can make structured retrieval appear perfect without testing narrative understanding. Always compare the annotation-assisted run with `--source-only`, which removes provided entities, incident type, location, timestamp and metadata provenance, then lets the same extractor recover only source-text signals. Ground-truth family labels remain evaluation-only. A high annotation-assisted score is a synthetic shortcut, not evidence of realistic AI performance.

## Metrics

- Precision@K: positives retrieved within K divided by K, even if fewer documents are returned.
- Recall@K: retrieved positives divided by all relevant candidates; JSON `null` for no-positive queries.
- MRR@K: reciprocal rank of the first positive within K, or zero.
- nDCG@K: binary discounted gain divided by ideal gain; JSON `null` for no-positive queries.
- Unrelated-result count: explicit false-positive IDs and mean unrelated results at K, rather than pretending unreturned documents were classified negative.
- No-match false-positive query rate: fraction of no-positive queries having at least one **positive-score** candidate. Threshold zero is permissive, not a calibrated operating point.

Zero-score documents remain in fixed-K evaluation with report-ID ties. The UI may hide them; evaluation does not silently drop difficult queries. Language-pair recall conditions on positives in the candidate language and records `null` if no such positives exist.

## Fusion selection and ablations

`--ablations` adds weighted hybrid without entities, without structured data, without semantic embeddings, and lexical+semantic. A JSON config passed with `--config path.json` supplies weights and retrieval settings. `development_recommendation` identifies the completed method with highest observed dev nDCG. This small-sample comparison does not automatically modify application weights. Freeze model, preprocessing and configuration before explicitly running `--split test`; test results must never select weights.

`hybrid_rerank` is the implemented transparent deterministic reranker described in AI_PIPELINE.md. It is not a neural cross-encoder. Uncertainty uses a seeded 1,000-resample **scenario-family cluster bootstrap**, sampling related reports together. Four dev families give unstable intervals. Pairwise significance and independently authored, human-reviewed labels remain future research work.

## Errors and timing

In Research Evaluation Lab, select a saved run or inspect JSON `methods.<name>.queries`. Compare unrelated returned IDs and `missed_relevant_ids`, then read original narratives. Inspect generic vocabulary, script mismatch, missing detail, annotation conflicts and alias ambiguity. Explanations are actual similarity signals, not verified relationships.

Latency includes search and component explanation construction. By default the experiment runner sets `explain_passages=false` to avoid separate per-result sentence-pair inference; this setting is saved. First-load/cache conditions vary. It is not a concurrent load test. Compare warmed and cold runs separately. GPU/CPU numerics can differ; ranked IDs and fingerprint make discrepancies visible. Executed-run summaries and exact verification status are recorded in `docs/STATUS.md`; unexecuted/failed methods remain explicit. New-runner results need not equal the preserved historical baseline if retrieval configurations differ.

## Executed comparisons, 4 November 2026

All eight methods and four ablations actually ran on the original fixture development partition with narrative-only extraction, CUDA on the RTX 3060, the pinned multilingual E5-small encoder and default weights. Final frozen artifact: `results/experiments/20261104T133815-3d47c9f5.json` (matching CSV alongside it). It reproduces the earlier development ranking metrics after the final engine review.

| Method | Recall@5 | nDCG@5 |
|---|---:|---:|
| TF-IDF | 0.3500 | 0.2283 |
| BM25 | 0.4125 | 0.2708 |
| Semantic E5-small | 0.3750 | 0.2847 |
| Entity | 0.7500 | 0.6902 |
| Structured | 0.7500 | 0.6303 |
| Weighted hybrid | 0.4750 | 0.3299 |
| Weighted RRF | 0.4250 | 0.3550 |
| Hybrid contradiction reranking | 0.5375 | 0.4540 |
| Hybrid without entities | 0.4625 | 0.3019 |
| Hybrid without structured fields | 0.4625 | 0.3046 |
| Hybrid without semantic | 0.4875 | 0.3443 |
| Lexical + semantic | 0.4000 | 0.2619 |

Entity-only wins this particular lexicon-heavy fixture. Removing semantic slightly improves the weighted hybrid. Neither observation establishes a generally superior method. Among fusion variants, reranking beats RRF and plain weighted fusion on observed development nDCG, but parameters were not tuned through an independent selection study and defaults remain transparent configurable defaults.

The annotation-assisted initial experiment (`20261104T132956-6b9b3f2d`) gave structured retrieval Recall@5/nDCG@5 of 1.0/1.0. The source-only counterpart (`20261104T133053-7e97f168`) dropped to 0.75/0.6303. This directly exposes the synthetic timestamp shortcut.

The auxiliary challenge dataset also ran all eight methods, source-only CUDA, artifact `20261104T133328-537d1d6c`. Its ten dev queries include one no-match query. TF-IDF/BM25 Recall@5 was 0.6111; semantic/entity/structured/hybrid/RRF/reranking recall was 1.0. Semantic and structured nDCG was 1.0 on the positive-query subset. **Every method returned a positive-score false suggestion on the no-match query: no-match false-positive query rate 1.0 at threshold zero.** There is no calibrated abstention system. These tiny results demonstrate software execution and failure modes, not real-world accuracy.

## Frozen configuration and final held-out test

Before final test execution, `configs/frozen_research.json` fixed the model ID and revision, narrative-only extraction, BM25 k1=1.5/b=0.75, RRF constant 60, weights TF-IDF/BM25/semantic/entity/structured=0.2/0.2/0.4/0.1/0.1, CUDA and disabled sentence-pair explanation timing. The runner verifies that the actual model identity/revision agrees with this config. Weights remain **unoptimized defaults**; no grid search or test-based selection is claimed.

Original development nDCG favored RRF (0.3550) over weighted fusion (0.3299), while challenge development favored weighted fusion (0.8731) over RRF (0.8458). The contradiction reranker gave the highest original development score among the hybrid variants (0.4540). These dataset-dependent findings motivate keeping both fusion approaches configurable; they do not justify a universal winner.

The final original-fixture dev suite ran under the frozen config. Then each test partition ran **once**, without changing model, weights, extraction or fusion parameters between them. Files:

- Final development + ablations: `results/experiments/20261104T133815-3d47c9f5.json`.
- Original fixture test, 20 queries: `results/experiments/20261104T133849-981eeabb.json`.
- Challenge test, 10 queries including one no-match query: `results/experiments/20261104T133913-9a40269a.json`.

All three final artifacts record the same source-code SHA-256, `0130e5a505c5ebe88d71995adb95ee420bc9d1d584fa59a0bef5200752d0130c`, and pinned model revision `614241f622f53c4eeff9890bdc4f31cfecc418b3`. They include exact per-query rankings and hardware/configuration details.

| Method | Original test Recall@5 | Original test nDCG@5 | Challenge test Recall@5 | Challenge test nDCG@5 |
|---|---:|---:|---:|---:|
| TF-IDF | 0.3500 | 0.2360 | 0.6111 | 0.4835 |
| BM25 | 0.4000 | 0.2662 | 0.6111 | 0.5427 |
| Semantic E5-small | 0.3750 | 0.3066 | 1.0000 | 1.0000 |
| Entity | 0.9500 | 0.9500 | 1.0000 | 1.0000 |
| Structured | 0.8875 | 0.7209 | 1.0000 | 1.0000 |
| Weighted hybrid | 0.5250 | 0.3641 | 1.0000 | 0.8957 |
| Weighted RRF | 0.4750 | 0.4220 | 0.8889 | 0.7854 |
| Hybrid contradiction reranking | 0.5750 | 0.5239 | 1.0000 | 0.9822 |

On the challenge **test** no-match query, entity and structured signals produced no positive-score suggestion (false-positive query rate 0.0), while TF-IDF, BM25, semantic, hybrid, RRF and reranking did (rate 1.0). Each estimate is based on a single no-match query, not a stable operating characteristic. No-positive recall/nDCG remain excluded as undefined; no-match failure is reported separately. The original test contains no no-match queries.

Reproduce the frozen final development comparison with:

```powershell
.venv/Scripts/python.exe -m sherlocked.experiments --methods tfidf bm25 semantic entity structured hybrid rrf hybrid_rerank --split dev --ablations --config configs/frozen_research.json --device cuda
```

Test reproduction uses the same command with `--split test` and without `--ablations`; the challenge run additionally uses `--dataset data/challenge_reports.jsonl`. Future model/configuration development must use a new held-out dataset rather than repeatedly tuning against these now-observed test results. Recorded CPU/CUDA smoke checks in `results/semantic_smoke.json` are separate compatibility checks, not retrieval benchmarks.

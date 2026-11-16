> Phase 2 adds portable resource configuration, separate setup/start, offline inference, shared model/data caching, safe generators and clean distribution. See PHASE2_VERIFICATION.md for observed acceptance evidence; the research scope below is retained.

# SHERLOCKED AI Lab technical specification

Release 0.2 · 4 November 2026 · implemented local research application. This revision supersedes the original four-screen baseline contract; the old files are preserved in backups/pre-upgrade-20261104.zip.

## Objective

Retrieve potentially related fictional Bangla, English and mixed reports with inspectable lexical, semantic, entity and structured evidence. Preserve original text. No guilt prediction, automatic identity merging or confirmed relationships. Long-term case/evidence management, shared ontology, OSINT, narrative/witness analysis, 3D/photogrammetry, Hypothesis Spectrum and simulation remain documentation only.

## Architecture and interface

app.py launches six functional Streamlit sections: Intelligence Dashboard, Report Explorer, AI Analysis Workspace, Relationship Explorer, Research Evaluation Lab and System Settings. Services separate storage/ingestion, source-preserving processing, retrieval, model caches, ranking, explanations, evaluation and visualization. Detailed boundaries: TECHNICAL_ARCHITECTURE.md; formulas/model rationale: AI_PIPELINE.md.

`Engine(fit_records,config).search(query,candidates,method,k,exclude_id,include_zero,weights,rerank)` returns rank, report, score, potential status, method, raw/normalized components and explanation. Labels never become features. Demo fits workspace records; experiments fit lexical vocabulary/IDF/length statistics on train only. Methods are TF-IDF, BM25, pinned multilingual E5, entity similarity, structured compatibility, weighted fusion, RRF and transparent heuristic contradiction reranking. Reranking is not a neural cross-encoder. Missing signals are unknown; observed weights are renormalized. Scores are not probabilities.

Explicit model setup caches pinned safetensors without remote code. Auto uses CUDA or CPU. Semantic failure is visible without substitution. Embedding caches distinguish content/model revision/role and are validated/atomic. Keyword evidence uses original character spans and real contributions. Source sentence-pair semantic similarity is illustrative, not causal attribution; truncation and originals remain visible.

## Dataset schema

Unique report_id; immutable text; fictional=true; stable source_id; optional family_id; split=train/dev/test/unassigned; language=en/bn/mixed/unknown; variant; generator_version; nullable incident_type/location/occurred_at; entities. Mentions include type,surface,normalized,start,end,source_id,method. Half-open offsets refer to original Unicode characters. Metadata provenance distinguishes source rules, supplied annotations and human confirmation. Fuzzy matches never merge identities.

Original fixture: 90 reports,18 families,50/20/20 train/dev/test, seed20261104, unchanged SHA-256 manifest. Separate challenge:39 reports,12 three-report families plus3 no-match singleton families,19/10/10. All family paraphrases/translations remain together. Explicit within-split qrels record synthetic same-family relationships. Submitted reports are unassigned and excluded from benchmarks. Entire import batches are validated atomically; conflicts never overwrite. DATASET_DOCUMENTATION.md contains full schema/generation/provenance.

## Workflow and evaluation

Browse/filter/submit/import/export fictional reports in immutable SQLite. Select/paste/upload queries; choose retrieval method/K and optional confirmed metadata. Inspect ranked signals, lexical spans, semantic passages, entity statuses and missing/contradictory fields. Export evidence JSON/ranking CSV. Graphs show suggested report edges with method/score hover and connected-report comparison. Research controls execute real saved comparisons, ablations, charts, slices and error analysis. Settings configures device/BM25/RRF/weights, model setup and health checks. USER_GUIDE.md documents all six sections.

Fixed-K precision,recall,MRR,nDCG; no-positive recall/nDCG undefined with separate false-positive analysis. Save exact rankings/scores, missed/unrelated IDs, language/variant/family slices, candidate-language distributions, family bootstrap intervals, latency, hashes, model/config/dependencies. Source-only mode excludes supplied annotation shortcuts and is default in research UI. Dev precedes frozen test; no test-based tuning. Actual results and protocol: EXPERIMENTS_AND_EVALUATION.md.

## Measurable release gates

- Original manifest valid; generators reproducible; unique IDs and disjoint family partitions.
- Exact lexical fixture cosine1 within1e-8; unrelated0; deterministic ties/self exclusion; empty input yields no results.
- Every retrieval method executes; unavailable semantic raises an error without keyword fallback.
- Real keyword sums/spans and semantic source references; missing metadata never fabricated.
- Idempotent SQLite initialization and atomic conflict rejection; canonical files unchanged.
- Six screens execute; Bangla/English/mixed query workflow, graphs and JSON/CSV exports operate.
- Launcher, dependency integrity, compilation, HTTP health, CPU/CUDA inference and actual browser review pass.
- Development comparisons/ablations and frozen test artifacts exist; negative findings retained.

Observed checks: docs/STATUS.md. Independent annotation, calibrated no-match abstention, a second encoder experiment and large-scale load tests remain research backlog work. Small synthetic results do not establish real investigative accuracy. LIMITATIONS_AND_ETHICS.md describes limitations.

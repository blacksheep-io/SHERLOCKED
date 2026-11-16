> Historical release 0.2 record. Current Phase 2 verification is in PHASE2_VERIFICATION.md; research result files below remain unchanged.

# SHERLOCKED implementation status

4 November 2026 · release 0.2 local AI Laboratory · implemented and verified, with explicit research limitations.

## Audit and preservation

Inspected existing README/specification/backlog/status, all source files, tests, configurations and dataset before modification. Entry point was and remains app.py. The original eight tests passed;90 IDs were unique, manifest valid and family splits intact. Folder is not a Git repository, so no Git changes, commits or pushes were made. The inherited prompt's nDCG@10 value was a transcription error: saved baseline is nDCG@5=0.2283. Original source, tests, docs, data and result snapshot is backups/pre-upgrade-20261104.zip. Original reports.jsonl, manifest.json, retrieval.py, evaluate.py and tfidf_dev.json remain preserved.

## Already working

The original90 fictional reports, deterministic family splitting, word TF-IDF, original-character keyword spans, four baseline screens, evaluation helper and eight tests were functional. Cross-language semantic ranking, BM25, entity/structured signals, hybrids, persistent storage and browser review were absent.

## Implemented

- Six integrated Streamlit sections with restrained navy/teal design, working loading/error states, real distributions/experiment charts and no fake predictions.
- Immutable SQLite workspace; source-preserving fictional submissions, validated atomic JSONL imports, full/filtered exports and duplicate/conflict protection.
- Script/language heuristic, Unicode tokenization, explicit entity extraction for six types, exact/normalized/approximate/possible/no-match/unknown comparison states, metadata extraction/provenance and missing-aware structured signals.
- Train-statistics BM25, pinned multilingual E5-small, configurable weighted fusion/RRF, transparent optional contradiction-penalty reranking and full evidence exports.
- Real semantic sentence evidence, original spans and tokenizer/truncation provenance; explicit setup/errors; locally cached weights/embeddings; CPU and CUDA compatibility.
- Separate reproducible39-report challenge corpus with varied events, ambiguity and no-match singleton families; explicit qrels for both corpora. Original90 preserved.
- Reproducible development/test experiments, ablations, family bootstrap, language/variant/family and language-pair analysis, per-query errors, JSON/CSV exports and frozen configurations.
- Windows batch/PowerShell launchers, idempotent database initialization, health checks, pinned portable and exact installed CUDA dependencies, complete guides.

## Fixes and hardening

Corrected inherited metric label. Fixed SQLite connection lifetime on Windows, PowerShell5.1 quote handling, CSV newline handling, invalid/duplicate candidate validation, finite parameter checks, unknown-signal handling and role/revision cache separation. Concurrent embedding writes are atomic and model inference is locked. Browser review found header clipping and the top padding was corrected. No reference repository was merged, modified or copied.

## Actual verification

- `python -m unittest discover -s tests -v`: **30 tests passed** on final services/UI.
- `python -m compileall -q app.py sherlocked scripts tests`: passed.
- `python -m pip check`: no broken requirements.
- `START_SHERLOCKED.bat -Check -SkipInstall`: actual Windows batch/PowerShell startup checks passed; dataset hash and SQLite initialization valid.
- `python scripts/check_server.py`: actual temporary localhost HTTP200 `ok`, clean shutdown.
- `scripts/check_semantic.py`: actual uncached English/Bangla/mixed inference on CPU and NVIDIA RTX3060 CUDA passed; torch2.6.0+cu124. Saved results/semantic_smoke.json, not an accuracy benchmark.
- Actual Streamlit server launched on127.0.0.1:8501. All six sections opened and visually inspected in the in-app browser. A pasted Bangla semantic query returned actual results and source sentences; relationship graph and pair evidence rendered; Research Evaluation Lab executed a browser-triggered run. Settings model readiness, import/health controls and saved results rendered. The final dashboard was left open. Current browser review is a narrow desktop viewport, not a full accessibility/responsive certification. Automated form/import/export coverage supplements the manual path; not every control permutation was manually exercised.
- A benign missing-ScriptRunContext warning occurs during AppTest initialization; no test exception results.

## Measured research results

Frozen source-only config in configs/frozen_research.json fixed model revision, default weights, BM25/RRF and device before final test. Final dev and both test artifacts share one code hash. Each test partition ran once with no subsequent tuning.

| Original fixture test method | Recall@5 | nDCG@5 |
|---|---:|---:|
| TF-IDF | .3500 | .2360 |
| BM25 | .4000 | .2662 |
| Semantic | .3750 | .3066 |
| Entity | .9500 | .9500 |
| Structured | .8875 | .7209 |
| Weighted hybrid | .5250 | .3641 |
| Weighted RRF | .4750 | .4220 |
| Hybrid heuristic reranking | .5750 | .5239 |

Final dev+ablations: results/experiments/20261104T133815-3d47c9f5.json. Original final test:20261104T133849-981eeabb.json. Challenge final test:20261104T133913-9a40269a.json. Exact tables, intervals, per-query rankings, failures and protocol are in EXPERIMENTS_AND_EVALUATION.md and matching artifacts.

Negative findings are retained: entity heuristics dominate the templated fixture; removing semantic slightly improves default weighted hybrid on original dev. Annotation-assisted structured matching reached1.0 due synthetic per-family timestamp shortcuts, so source-only is the research UI default. All methods made positive false suggestions for the challenge dev no-match query. In challenge test, entity/structured abstained but lexical/semantic/hybrid variants still suggested false positives. Each no-match estimate has only one query. No calibrated abstention or real-world accuracy is claimed.

## Remaining limits

This is runnable local research software, not an independently validated operational system. Only E5 was experimentally tested; alternative model cards were investigated, not benchmarked. Entity/language extraction is heuristic; Latin-only Banglish is treated as English and negation/coreference are unresolved. The optional reranker is deterministic, not a cross-encoder. Larger independent annotation, robust no-match calibration, repeated-seed/template-author holdouts, comprehensive browser regression/accessibility and large-scale performance tests remain. Original and challenge test results are now observed; future tuning requires new held-out data. Detailed backlog and ethical limits remain explicit.

## Project structure

```
SHERLOCKED/
  app.py
  START_SHERLOCKED.bat / start.ps1
  requirements.txt / requirements-lock.txt / requirements-cuda-lock.txt
  .streamlit/config.toml
  configs/                   model identity, frozen experiment, optional app settings
  sherlocked/                domain services, models, ranking, experiments, six-section UI
  data/                      original90, challenge39, manifests, qrels, SQLite workspace
  models/                    cached pinned model assets
  cache/                     content/revision/role embedding cache
  results/                   preserved baseline, semantic smoke, measured experiments
  scripts/                   setup_model, check_semantic, health, check_server
  tests/                     baseline, data, engine, experiments, application checks
  docs/                      current specification, backlog, status
  backups/                   original implementation snapshot
  README.md and seven topical guides
```

No .env file or paid API key is needed. Run/test commands and troubleshooting are in README.md.

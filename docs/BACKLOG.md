# Current prioritized backlog

The requested local AI Lab workflow is implemented: six screens, SQLite ingestion/export, lexical/dense/entity/structured retrieval, weighted/RRF fusion, transparent heuristic reranking, source-grounded explanations, graphs, reproducible saved experiments, Windows startup and CPU/CUDA operation. See STATUS.md for final measured verification.

Remaining research and quality work:

| Priority | Work | Why / acceptance |
|---|---|---|
| P0 research | Independently authored and reviewed larger scenario corpus | Reduce template/alias/date shortcuts; double annotation and adjudicated graded judgements |
| P0 research | Learn and validate abstention on dev-only no-match families | Current all-method challenge no-match false-positive query rate is 1.0 at score >0 |
| P1 research | Compare a second multilingual encoder empirically | E5/BGE-M3/MiniLM cards investigated; only E5 executed |
| P1 research | Dev model/weight tuning with nested family/template holdout | Defaults are transparent, not claimed optimal; semantic ablation regresses/improves depending corpus |
| Complete | Frozen configuration and final test protocol | Both original and challenge test partitions executed once; future tuning needs new holdouts |
| P1 quality | Automated browser regression at multiple viewport sizes | Actual manual browser review performed; current automated UI checks use Streamlit AppTest |
| P2 research | Negation-aware extraction, spelling/transliteration expansion | Current literal rules can treat negated mentions as overlap |
| P2 performance | Benchmark 1,000+ reports and bounded model caches | Current timings cover small fixtures and are not load tests |
| Optional | Cross-encoder reranking comparison | Current optional reranker is a documented contradiction penalty, not a learned cross-encoder |

Full case management, OSINT collection, enterprise authorization, 3D, photogrammetry, witness psychology, Hypothesis Spectrum and game engines remain deferred. Guilt prediction and automatic identity merging remain excluded.


Phase 2 local portability gates completed on5 November2026: configurable resources,separate setup/start,CPU/CUDA/offline operation,shared caches,safe generators,allowlisted distribution,and same-PC clean installation/relocation. Current evidence: PHASE2_VERIFICATION.md. Remaining research/backlog items below are unchanged.

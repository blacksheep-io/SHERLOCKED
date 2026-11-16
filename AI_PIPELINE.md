> Phase 2 execution: complete local-asset validation distinguishes ready assets from a loaded model. Offline mode forbids model downloads; online mode can download the approved pinned encoder explicitly. Auto device retries the same semantic encoder on CPU after a CUDA failure and exposes fallback_reason; forced CUDA remains an error. Cache v2 includes normalization/dimension/pooling identity, deduplicates batch texts and retains a bounded RAM layer (2048 vectors). Old cached files are retained and safely regenerated under the new identity. Real CPU/CUDA execution and warm-cache reuse are recorded in timestamped logs; historical research results are unchanged.

# AI pipeline and model selection

SHERLOCKED ranks fictional reports. No signal is a guilt score, identity decision, or verified relationship.

## Traceable preprocessing

The original report text is immutable. Unicode letter, number and combining-mark spans are normalized with NFC and casefold for lexical matching; offsets always refer to the original source. Rule-based extraction and manually confirmed fields retain method/source provenance. Labels such as scenario family and split never enter vectorizer or ranking features.

## Independent retrieval methods

- **TF-IDF** retains the audited `KeywordIndex`: raw term count, smoothed train-only IDF, L2 norm and cosine. Each term contribution is the product of query/document weights.
- **BM25** uses train-only document frequencies and average length, positive Robertson IDF `log(1+(N-df+0.5)/(df+0.5))`, default k1=1.5 and b=0.75. Query term frequency is binary. The token contribution values sum to the raw BM25 score. An unseen training term contributes zero. This deliberately matches the fixed-vocabulary evaluation protocol; it is not a transductive BM25 index fitted on held-out documents.
- **Semantic** uses normalized multilingual E5 embeddings and query-to-passage cosine. Scores are not calibrated probabilities. The most similar original sentence pair supplies source spans and its separately measured cosine; it is illustrative evidence, not causal attribution of the report embedding.
- **Entity** compares explicit source mentions or confirmed fields, returning unknown for unobserved evidence. Approximate spelling is only a possible association, never identity merging.
- **Structured** compares observed event type, location and date/time with explicit missingness and contradiction labels. Fixture metadata is synthetic annotation, not automatically verified fact.

## Model choice and setup

The default model is `intfloat/multilingual-e5-small`, pinned to revision `614241f622f53c4eeff9890bdc4f31cfecc418b3`. It emits 384 dimensions and supports 512 tokens. Query and passage prefixes are applied even to Bangla. The configuration is in `configs/model.json`; model weights are downloaded once as safetensors with remote code disabled. CPU and CUDA are supported; `auto` chooses CUDA only if PyTorch can use it. A requested unavailable CUDA device produces a clear error.

This is a resource choice supported by the E5 model card's multilingual retrieval training and Bangla evaluation, not proof of performance on SHERLOCKED. [The E5 model card](https://huggingface.co/intfloat/multilingual-e5-small) identifies an MIT license and a 384-dimensional architecture, describes language coverage and low-resource limitations, and reports Bangla in Mr. TyDi. The card's retrieval instructions inform prefixing and normalization.

Two alternatives were investigated. [BGE-M3](https://huggingface.co/BAAI/bge-m3) is MIT-licensed, supports 1,024-dimensional dense embeddings and a long context, and is substantially heavier than the small E5 model; its extra sparse/multi-vector machinery is unnecessary for this local first comparison. [Multilingual MiniLM](https://huggingface.co/sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2) is an Apache-2.0, 384-dimensional sentence model with a 128-token default context and narrower declared language coverage. Neither alternative is claimed to have been experimentally compared unless an actual saved experiment says so. E5's retrieval-specific design and explicit Bangla benchmark make it the more defensible initial small model. A full comparative model-selection study remains a research extension.

Use `python scripts/setup_model.py --device auto` for explicit first-run network setup. Application import never starts a download. If setup or inference fails, semantic and semantic-enabled hybrid methods fail visibly; users may explicitly select TF-IDF or BM25. They are never silently substituted for a semantic prediction. No paid API or cloud inference is used. The setup script performs a small English/Bangla inference smoke check; the cosine printed there is illustrative and is not a retrieval evaluation.

Models live under `models/`; derived embeddings live under `cache/embeddings/`. Cache identities include model ID, immutable revision, truncation length, query/passage prefix and exact text. Cached vectors do not contain labels. Deleting an embedding cache is safe; weights do not download again when already initialized.

## Fusion and optional reranking

The configurable weighted hybrid defaults to TF-IDF=.2, BM25=.2, semantic=.4, entity=.1, structured=.1. BM25 is divided by the maximum score in the current candidate pool; semantic cosine is floored at zero; other nonnegative scores are used directly. Missing components are excluded and weights renormalize over observed components per candidate. These are declared experimental defaults, not learned probabilities. Record all weights and normalization with experiments. Candidate-pool BM25 normalization means scores across independent searches are not directly comparable.

Weighted Reciprocal Rank Fusion uses `weight/(60+rank)` for observed positive signals, excludes unknown/zero lists, and sums contributions. Ties break on stable report ID. RRF values differ in scale from weighted fusion. The Research Lab compares them before a selected configuration is frozen.

`hybrid_rerank` is an optional **source-consistency heuristic**, not a neural cross-encoder: take the top max(10,2K), capped by pool size, and divide each hybrid score by `1+0.15*identified structured contradiction count`, then sort again. The explanation records pre-rerank score and formula. The experiment runner can measure its effect; no gain is assumed. A trained cross-encoder is not included.

## Explanations and uncertainty

Every result includes method, rank, raw components, normalized components, actual weighted/rank contributions, source keyword offsets, entity/metadata evidence, missing fields and contradictions. Original source IDs remain inspectable. Unknown evidence is not a negative or positive identity claim. Generic descriptions, same-name collisions, templated synthetic reports, script differences and truncation are documented limitations. User review is always required before treating any suggested report relationship as meaningful.

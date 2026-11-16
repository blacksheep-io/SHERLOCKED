# Limitations, ethics and research integrity

SHERLOCKED suggests potentially related **fictional reports**. Its ranking scores are neither probabilities nor assessments of a person. Every result is advisory and must remain human-reviewable. The application must not determine guilt, criminality, truthfulness, identity or a verified connection.

## Synthetic data and evaluation validity

The original benchmark contains 90 template-generated records in 18 scenario families. Its languages, variation types, labels and provenance are documented and reproducible. Family-based splitting prevents siblings or translations from being placed in different partitions. It does not remove template/style leakage, vocabulary artifacts, unrealistic incident distributions or the gap to naturally authored Bangla/English reports.

Ground truth is assigned by generator scenario membership, not by model output or post-hoc metric optimization. Shared templates and generic cart/gate descriptions create misleading similarities. The benchmark overrepresents missing-property incidents. Its original four-positive-siblings-per-query design contains no independently authored no-match queries; added challenge fixtures must be reported as their own version rather than silently modifying old experiments. Human linguistic and relevance annotation review has not been established. Consequently, the benchmark is useful for engineering regression and controlled method comparison, not operational accuracy claims.

Generator-provided dates and locations can be scenario-family proxies. Structured metadata scores may therefore be artificially strong. Run source-only ablations that discard provided annotations and re-extract only what the narrative states. Do not present high metadata-assisted metrics as proof of semantic understanding. The experiment runner preserves which protocol was used. Development selection and test confirmation are separate; test data must not tune model choice, weights or heuristics. A test run may be requested explicitly after configuration freezing, not repeatedly used as a development loop.

## Language and model limits

The script detector is a transparent heuristic. It identifies Bangla and Latin characters; Latin-only Banglish is classified as English and is not reliably language-identified. Small controlled aliases cover only the fictional lexicon. Rule-based labeled entity extraction is not a trained multilingual NER system. It can miss unlabeled people/organizations, confuse common nouns and fail on spelling or punctuation not covered by the rules. Missing extracted entities should not be read as absence of real-world entities.

Multilingual E5 provides actual English/Bangla semantic inference and was selected initially for manageable resources, a retrieval-specific architecture and documented Bangla benchmark coverage. This does not establish quality on every dialect, transliteration or report style. Model-card benchmarks are external evidence, not SHERLOCKED results. Other candidate models were investigated but must not be described as experimentally compared without saved runs.

The semantic encoder truncates at 512 tokens including prefixes. Original source text is preserved and truncation is reported, but important later details can be excluded from the report embedding. A most-similar sentence pair is an illustrative supporting comparison; it does not explain every causal feature used by a neural model. Sentence evidence may include a passage outside the report-level window, which is disclosed. E5 cosine values can be high even for unrelated text, so a high number is not calibrated confidence.

## Entity similarity and uncertainty

Exact surface, normalized alias, approximate spelling and possible similarity remain distinct explanation states. Approximate matches are heuristic scores, not probabilities. Identifiers do not receive fuzzy matching. An identical name, object or location can occur in separate incidents. No record or entity is automatically merged because of a match. Candidate reports with missing fields remain unknown for that signal; unknown data is excluded from score averaging, not rewarded or penalized. Renormalizing available weights can still favor sparse records, so missingness slices and ablations are necessary.

Structured date compatibility uses a declared seven-day linear window. Different supplied fields are labeled observed differences, not proof that two incidents are unrelated. The optional reranker is a documented contradiction penalty, not a learned cross-encoder. Fusion weights and thresholds are experimental configuration; they are not calibrated risk scores. RRF and weighted scores use different scales and should not be compared numerically as confidence.

## Storage, privacy and safety boundaries

Use fictional material only. No real personal, confidential investigative or evidentiary records should be submitted. Reports may persist in unencrypted local SQLite when explicitly saved, and derived vectors persist in the local cache. The cache uses hashed identities rather than storing full narrative strings in filenames, but embeddings can still reveal information and are not an anonymization guarantee. Local files and exports are the user's responsibility to protect.

There is no enterprise authorization, tamper-evident audit trail, evidentiary chain of custody or production security review. Localhost binding is intended for a single-user demonstration. Do not expose the server publicly or treat local report provenance as legal evidence custody. Source rules and annotations are inspectable provenance records, not verification of the narrative's factual truth.

Model downloads are explicit, pinned and use safetensors with remote code disabled. A semantic failure is shown clearly; users may choose TF-IDF/BM25 explicitly, and the system never labels keyword output as semantic inference. Models run locally without paid API keys. No unauthorized collection, surveillance, facial/behavioral lie detection, suspect scoring or autonomous investigative action is implemented.

## Honest reporting

Keep failed experiments, false positives, weak language slices and regressions visible. Report the actual K for each metric: the inherited first-increment value 0.2283 was nDCG@5, not nDCG@10. Distinguish an automated UI execution check, HTTP health check, real browser review, model smoke check and retrieval benchmark; none substitutes for the others. Smoke-test cosine examples are not retrieval accuracy. CUDA availability alone does not prove actual GPU inference; the dedicated cache-bypassing device check provides that evidence.

Small family counts yield unstable confidence intervals, even when bootstrap code is correct. Hardware timings depend on batch size, warm/cold caches and model loading; report those boundaries rather than promising broad performance. No novelty, real-world effectiveness or institutional approval is claimed from assembling established methods. The long-term investigative platform vision remains documentation only.

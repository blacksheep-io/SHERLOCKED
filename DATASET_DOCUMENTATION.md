# Dataset and ingestion

SHERLOCKED uses fictional reports only. The original `data/reports.jsonl` and `data/manifest.json` remain byte-for-byte intact: 90 reports, 18 scenario families, a fixed 20261104 generation seed and family-disjoint train/dev/test splits (50/20/20 records). `python -m sherlocked.dataset` reproduces this fixture in the configured dataset directory. Generation is non-destructive by default: byte-identical reports and semantically identical JSON manifests are left untouched, and conflicting existing files cause a clear error before any output is created. A separate `--directory` is the safest place for new generated fixtures. The `--overwrite` flag is an explicit opt-in for deliberately replacing generated outputs; setup never uses it.

The 90 reports include English, Bangla and mixed-language versions, incomplete variants, paraphrases and Latin transliteration. Every report has an ID, immutable original `text`, a synthetic `source_id`, language annotation, family, partition and structured fixture annotations. Other families are deliberately unrelated in the generator. Family labels are ground truth for experiments only; neither family IDs nor split labels enter ranking features.

The fixture is small and templated. Location/object combinations and generic cart descriptions recur. It is an implementation benchmark, not independently annotated or representative of real investigations. Its labels express generated scenarios, not human certainty. It has no no-match queries: every original report has four relevant siblings. It cannot establish real-world accuracy. Independent scenario authoring, human annotation/adjudication and stronger template holdouts remain necessary for academic generalization claims.

## Optional challenge set and explicit judgements

`python -m sherlocked.research_data` reproducibly writes a separate `data/challenge_reports.jsonl` (39 records) and `challenge_manifest.json`. It never changes the original 90. Twelve authored fictional scenarios each have English, Bangla and mixed-language views, including theft, fire, property damage, found/lost property and incomplete descriptions. Three singleton families (one per split) explicitly have no companion report. Deliberate hard negatives reuse vehicles, locations and objects across events, including a negated vehicle mention. There are 19/10/10 train/dev/test records and 15 disjoint scenario families. These are controlled author-assigned scenarios, not independently reviewed labels. Treat these additional examples as an auxiliary challenge set rather than evidence of external validity.

`data/qrels.jsonl` and `data/challenge_qrels.jsonl` enumerate every ordered, within-split non-self report pair. Fields are query ID, candidate ID, split, binary grade, rationale, synthetic annotator and label version. Grade 1 means same constructed scenario family; grade 0 means different family. Singleton queries have only zero judgements. The challenge set is not silently substituted for the original experiment; import it explicitly for exploration or use a separately identified experiment configuration.

## Original narratives, extracted views and provenance

`analyze_report(text, report_id=None, metadata=None)` preserves the supplied text exactly. It creates a script heuristic (`en`, `bn`, `mixed`, `unknown`), entities with half-open Unicode character offsets, and conservative structured fields. Language is script identification: Latin-only Banglish can be classified as English. It is not a statistical language classifier.

Entity extraction uses explicit labels such as `Person:`, `Organization:`, `Location:`, `Vehicle:`, `Identifier:`, `Object:` and their supported Bangla equivalents, plus a deliberately small fictional location/object/vehicle lexicon. Arbitrary person names are not guessed from capitalization. Entity mentions contain type, surface, normalized string, original start/end, source ID, rule method and an identity-unverified notice. Confidence is null because the rules are not calibrated.

Rule metadata includes original spans. Existing fixture annotations (especially incident dates absent from narrative text) are labelled `provided_annotation`, not presented as extracted passages. Supplied canonical fields are preserved. No extraction changes the original file. Bangla/English aliases such as `পদ্ম` and `Lotus` normalize to a common fictional place term. A lexical alias is a report-matching signal, never proof that two real entities are identical.

Rules detect literal mentions even inside negated statements. They do not resolve negation, coreference or whether an object was present at the incident. Inspect the original passages before interpreting shared mentions; this is a known error mode exercised by the challenge set.

Structured comparison averages only jointly observed incident type, normalized location and date compatibility. Dates use a documented linear 7-day window; incompatible timezone precision is unknown. Missing fields do not vote. Entity comparisons distinguish exact, normalized, approximate, possible, no match and unknown; identifiers are not fuzzily matched. Approximate names use conservative string similarity, have reduced weight and never merge identities.

## SQLite and safe imports

The application seeds `data/sherlocked.sqlite3` from the canonical fixture. JSONL remains the evaluation source of truth. SQLite rows contain original narratives plus derived views and are immutable: there is no overwrite/update/delete report operation. Initialization is idempotent and preserves existing submitted reports.

New fictional reports receive stable content-derived `U-...` IDs unless a unique ID is supplied. They have null family and `unassigned` split and are excluded from the canonical research experiment. Exact duplicate narratives and conflicting IDs are rejected with the existing record reference. Near duplicates remain distinct report candidates; matching is advisory.

Settings can accept UTF-8 JSONL imports up to 5 MB / 10,000 reports. Every imported row must have a unique `report_id`, nonempty original text, and `fictional: true`. Language/split enumerations, field types, source spans, duplicate IDs and family partition integrity are checked. A whole import is atomic: one error adds no rows. Imports cannot overwrite existing IDs or create cross-split families. Export preserves Unicode and returns full JSONL records, including provenance.

## Schema

Core fields: `report_id: string`, `text: string`, `fictional: true`, `source_id: string`, `language: en|bn|mixed|unknown`, `family_id: string|null`, `split: train|dev|test|unassigned`, `variant: string`, `generator_version: string`, `incident_type/location/occurred_at: string|null`, `entities: list`, `metadata_provenance: object`.

Mention fields: `type`, `surface`, `normalized`, `start`, `end`, `source_id`, `method`, `confidence`, `status`. ISO date extraction supports explicit `YYYY-MM-DD` and ISO timestamps; it does not invent missing times or timezone offsets. Human-supplied annotations are distinguishable from extraction.

## Portable resource locations and data preservation

Dataset and database defaults resolve against the project root, never the current working directory. `configs/paths.json` can set `dataset` (directory), `database` (full SQLite path), and `results` (directory). Optional environment overrides are `SHERLOCKED_DATASET_DIR`, `SHERLOCKED_DATABASE_PATH`, and `SHERLOCKED_RESULTS_DIR`. Relative configuration values resolve relative to the copied project root. `Store()` resolves the selected database path at construction, so it does not retain the original machine's path.

Both dataset generators preflight the entire set of target files. A conflicting challenge qrels file therefore prevents the other challenge outputs from being created, preserving researcher edits. Existing canonical reports, manifests, pair labels, SQLite content and historical experiments were checksum-verified unchanged during the Phase 2 migration. Tests generate only isolated temporary fixtures.

The historical `python -m sherlocked.evaluate` baseline retains its ranking algorithm but now saves unique artifacts under the configured `results/reports/` directory. It does not replace `results/tfidf_dev.json`. New multi-method experiments remain under configured `results/experiments/`, with exclusive file creation and unique IDs. They retain resolved execution paths for provenance and add project-relative references where the resource is inside the project. Existing artifacts are never rewritten merely because a project has moved; their original absolute paths describe where that earlier experiment ran.

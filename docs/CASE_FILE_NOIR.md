# CASE FILE NOIR

Design and implementation guide · 13 November 2026

The redesign adapts the existing application at `C:\Users\NOYON\Documents\ChatGPT\SHERLOCKED`. It does not create or migrate to `C:\SHERLOCKED`. The Python retrieval services, immutable source records, synthetic datasets, SQLite reports, model/cache behavior and measured experiment artifacts remain the foundation of the product.

This guide describes the presentation architecture. Current test results, browser observations, screenshots and release checks belong in the separate [NOIR verification record](NOIR_VERIFICATION.md), prepared at handover. No test count or browser-verification outcome is asserted here. The earlier `UI_REDESIGN.md` and `UI_REDESIGN_QA.md` describe the historical November 5 release and remain unchanged.

## Identity and composition

CASE FILE NOIR uses an ink navigation rail around a warm paper document workspace. Serif titles, sharp borders, source references, quiet ledger rules and restrained oxblood actions replace the earlier cyan/violet technical dashboard. Information remains the visual subject: original narratives, computed evidence, unknown fields and actual saved measurements.

The dashboard is composed as a collection cover and register, with actual corpus figures, language distribution, family/partition map, inference ledger, session notes, suggested connections and a measured research ledger. Report Explorer retains the source-index/original-document split. Analysis and relationship pages retain their working source-to-candidate and evidence-inspection workflows. The research page displays saved metrics and explicit execution controls; settings retain the existing resource, model, import/export and diagnostic operations.

Navigation uses native Streamlit buttons grouped under **THE INVESTIGATION**, **THE RESEARCH**, **THE ARCHIVE** and **THE SYSTEM**. The seven modules remain Intelligence Dashboard, Report Explorer, AI Analysis Workspace, Relationship Explorer, Research Evaluation Lab, System Settings and Ashford Manor. Quick jump and Settings are functional navigation controls. `active_section` and the existing widget/session keys remain the routing contract.

## Palette and contrast roles

| Token | Value | Intended role |
|---|---|---|
| Ink | `#121211` | Navigation, primary paper text, graph canvas |
| Ink card | `#1E1D1B` | Dark document headers and review gate |
| Paper | `#F3EEE0` | Main workspace background |
| Paper card | `#FBF8F0` | Source documents, tables and chart surfaces |
| Ivory | `#ECE6D6` | Text on ink, paper dividers and subtle fields |
| Oxblood | `#9B1C1C` | Actions, recorded differences, source highlights |
| Rose | `#E07A70` | Selected navigation and suggestions on ink |
| Brass | `#B08D57` | Archive details, structural accents and uncertainty borders |
| Grey | `#8C877B` | Secondary graph details on ink |
| Line | `#CFC7B2` | Fine rules and paper panel boundaries |
| Muted ink | `#4A463E` | Secondary body text and metadata on paper |

Use ink/muted ink on paper and ivory on ink for readable text. Rose and brass are accent roles, not a substitute for body-text contrast on paper. Status labels, line styles, source IDs and explicit descriptions accompany color. A successful corpus checksum or model-availability check does not confirm an investigative relationship. Recorded differences remain observations, not proof that incidents are unrelated.

Global tokens are declared in `assets/interface/sherlocked.css` and `sherlocked/design.py`. Compatibility aliases in `PALETTE` allow older page adapters to keep their interfaces. Page-specific chart/illustration colors also exist in `ui_data.py`, `ui_research.py`, `ui_ashford.py`, `visualization.py` and the SVG assets; a future palette change must review those rather than editing CSS alone. `chart_theme(fig, height=None, surface='paper')` supplies the shared Plotly appearance; `surface='ink'` supports dark evidence surfaces without changing result values.

## Typography and offline assets

Titles and panel headings use installed Cambria/Georgia serif fallbacks. Body text uses Segoe UI with Nirmala UI, Noto Sans Bengali, Kalpurush and system fallbacks for multilingual content. Metadata uses Consolas/Courier New. The global body is 14 px; original source passages use a more spacious 15 px treatment. Compact metadata and chart labels have separate sizes. No remote font download is required. Available fonts can vary by destination computer, so Bangla shaping, wrapping and wordmark width require review on the actual machine.

CSS keeps corners sharp and transitions restrained, provides visible keyboard focus and honors reduced-motion preferences. These choices do not constitute a complete accessibility certification; contrast, keyboard traversal, chart readability and narrow-screen behavior belong in the final QA record.

## Original SVG logo family

`assets/branding/` contains original project artwork: an invented Victorian detective profile wearing a double-brim deerstalker and holding a curved pipe. It does not depict an actor or reuse a supplied silhouette. Hat, profile, coat and pipe are editable vector paths. The files are self-contained, include accessible titles/descriptions and work without a remote image service.

| Asset | Usage |
|---|---|
| `sherlocked-primary.svg` | Ink emblem and serif wordmark on paper |
| `sherlocked-emblem.svg` | Compact ivory emblem in the ink sidebar |
| `sherlocked-monochrome.svg` | Single-color identity variant |
| `sherlocked-ivory.svg` | Inverse monochrome variant |
| `sherlocked-forensic-red.svg` | Oxblood variant |
| `favicon.svg` | Local application icon |

The emblem geometry is vector artwork; SVG wordmark text uses local serif fallbacks. Preserve the deerstalker, profile and curved pipe when producing another size or variant. Validate small-size legibility rather than assuming the full emblem will remain readable at favicon dimensions. See [the asset notes](../assets/branding/README.md) for the editable path structure.

## Editing map

| File | Presentation responsibility |
|---|---|
| `.streamlit/config.toml` | Native light theme and existing local-server defaults |
| `assets/interface/sherlocked.css` | Product tokens, native widget overrides, typography and responsive rules |
| `assets/branding/` | Original logo family and identity notes |
| `sherlocked/design.py` | Shared headers, badges, documents, source quotes, review gate and chart theme |
| `sherlocked/ui.py` | Shell, grouped navigation, favicon and service adapters |
| `sherlocked/ui_data.py` | Collection dashboard, actual session freshness and report explorer |
| `sherlocked/ui_analysis.py` | Source/configuration/candidate composition |
| `sherlocked/evidence_ui.py` | Computed signals, original passages, entities/context and computation record |
| `sherlocked/ui_relationships.py` | Evidence-board controls, selection and connection dossier |
| `sherlocked/visualization.py` | Graph appearance and source-backed node/edge presentation contracts |
| `sherlocked/ui_research.py` | Measured research views and settings presentation |
| `sherlocked/ui_ashford.py` | Separate illustrative demo presentation |
| `assets/illustrative/ashford_manor_plan.svg` | Original architectural illustration, not measured scene geometry |

Prefer the application-owned `sk-*` wrappers and shared helpers for new presentation work. Native controls remain native Streamlit widgets. Overrides targeting `data-testid`, `data-baseweb`, `button[kind]`, `.block-container` or nested wrapper structure depend on Streamlit internals and need browser review when dependencies change. Keep those overrides centralized. Global heading rules use `!important`; review their interaction with page-specific titles. The `ds-*`, `noir-*` and `am-*` rules are page-owned accents, not backend contracts.

Source strings must remain escaped before entering HTML. Preserve original Unicode text and existing source-span offsets. Do not put retrieval formulas, entity normalization or data mutation into a styling helper. Retain stable widget/session keys when adapting layouts so source selection, candidate inspection, graph selection, submission and exports keep their behavior.

## Evidence and review boundaries

The graph distinguishes computed report suggestions, literal source mentions, suggested mention comparisons and recorded field differences. Report and mention nodes remain separate; mention IDs are source-specific. Original spans and computational evidence drive the inspector. Shared names never cause automatic identity merging, and ranking signals are never presented as calibrated probabilities.

The human-review gate is read-only and states **UNREVIEWED**. There is no persisted confirmation/rejection workflow, analyst-notes store or durable relationship-review audit trail. The local database stores reports, not review decisions. The graph's existing optional human-documented-link contract can display a supplied record only when its explicit reviewer/time and source-excerpt requirements are satisfied; it is not a new confirmation-writing feature. Do not imply that a badge, source mention or export creates a verified relationship.

Session search activity is displayed newest-first. The dashboard selects the latest available analysis/graph result using recorded completion time when present, otherwise a matching actual search event. Old undated session results are labelled as such. A newer empty result does not cause older suggestions to be substituted. Session notes are not a persisted investigation history.

## Ashford remains a separate demo corpus

Ashford Manor is explicitly labelled **SEPARATE DEMO CORPUS**. Its six fictional English/Bangla/mixed accounts remain in `assets/illustrative/ashford_manor.json`, separate from the canonical datasets, SQLite report collection and evaluation splits. The content was authored for presentation on 5 November 2026; its text and timestamps were not rewritten for the NOIR styling.

Timeline points reference timestamps actually stated in those authored narratives. Retrieval runs on the six demo sources only. The manor SVG is original illustrative artwork, not photogrammetry, a measured floor plan or proof of movement. Missing or ambiguous observations remain unresolved; the page does not identify a culprit or establish ground-truth report links. Demo exports retain this provenance.

## Verification handoff

Use [NOIR_VERIFICATION.md](NOIR_VERIFICATION.md) for the final integrated checks and screenshots. Preserve the prior design documentation as history. Verification should cover all seven modules, the real launcher, source and selection continuity, English/Bangla/mixed input, evidence tabs, graph controls, empty/error states, exports, keyboard focus and normal laptop widths. Confirm protected data/result/backend hashes separately from presentation changes. A passing Python test suite alone is not a browser visual review, and a local browser review is not cross-computer certification.

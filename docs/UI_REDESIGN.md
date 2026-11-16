# SHERLOCKED visual identity and interface

Implemented 5 November 2026. This presentation release preserves the Python/Streamlit application and local Windows deployment. No reference repository was merged. No React migration, external account, hosted service or paid API was introduced.

## Identity

The interface uses a compact S monogram, grouped navigation and source-first workspaces. Graphite and midnight surfaces provide hierarchy without large empty cards. Segoe UI/Nirmala UI retain Bangla readability; Consolas identifies source references and computational metadata. Material icons replace emoji navigation. Restrained hover/focus treatments respect reduced-motion preferences.

| Role | Color |
|---|---|
| Application background | `#0a1019` |
| Panel surface | `#101a27` |
| Raised surface | `#142030` |
| Border | `#253245` |
| Main text | `#dbe6ef` |
| Secondary text | `#8f9fb1` |
| Active/keyword cyan | `#6de1ed` |
| AI/semantic violet | `#a997ed` |
| Uncertainty amber | `#e8b975` |
| Successful check green | `#76c8a4` |
| Error/contradiction red | `#ee8585` |

Green data-integrity or model-availability checks do not verify an investigative relationship. The graph uses a separate explicit human-confirmation contract.

## Workspaces

- **Intelligence Dashboard:** actual corpus inventory, language donut, family/partition map, integrity checks, inference/hardware state, session activity, recent computed suggestions and saved measured experiments. Activity is session-scoped; an empty session stays empty.
- **Report Explorer:** search IDs/narratives/metadata, language/type filters, compact document index, original source view, literal entity spans, recorded fields and provenance. Fictional submission and export retain their existing behavior.
- **AI Analysis Workspace:** source/configuration column, actual ranked candidates, selected-candidate inspector and four evidence tabs. Raw scores and normalized chart lengths are distinguished. BM25 is normalized within the query for display; no score is called a probability.
- **Relationship Explorer:** native Plotly pan/zoom, searchable/filterable report and source-mention nodes, selectable node/edge midpoints, evidence inspector and export. Dashed cyan is a report suggestion, solid slate is a literal mention, dotted violet is a mention comparison. Source-specific mention IDs prevent automatic identity merging. Green human-documented links require an explicit confirmation record and matching source excerpt. The current corpus contains zero such links. This release does not add a persisted human-verification workflow.
- **Research Evaluation Lab:** actual comparison heatmaps, cutoff metrics, bootstrap intervals, ablation deltas, language-pair slices, false-positive/missed-result ledgers and experiment/configuration history. Failed/undefined results remain missing. Historical results are displayed without recomputation or retuning.
- **System Settings:** existing configuration forms plus compact resource/model/device/DB panels, local diagnostics, model preparation and import/export.
- **Ashford Manor:** separate illustrative archive with six newly authored English/Bangla/mixed sources, original schematic manor plan, explicit source timestamps, actual retrieval over those six records and evidence export. It is not an original uploaded case, benchmark, measured scene reconstruction or validated relationship ground truth. Its reports never enter the canonical dataset, SQLite workspace or evaluation partitions.

## Editing map

| File | Responsibility |
|---|---|
| `assets/interface/sherlocked.css` | Product palette, layout, native widget styling, responsive toolbar/navigation |
| `.streamlit/config.toml` | Native dark theme and local server defaults |
| `sherlocked/design.py` | Shared headers, badges, compact metrics, escaped source panels and Plotly theme |
| `sherlocked/ui.py` | Application shell, navigation and existing service adapters |
| `sherlocked/ui_data.py` | Dashboard and source explorer |
| `sherlocked/ui_analysis.py` | Source-to-candidate workstation |
| `sherlocked/evidence_ui.py` | Shared computed evidence inspector |
| `sherlocked/visualization.py` | Graph presentation, typed selection IDs and evidence layers |
| `sherlocked/ui_relationships.py` | Graph controls and inspector |
| `sherlocked/ui_research.py` | Research and settings presentation |
| `sherlocked/ui_ashford.py` | Separate illustrative archive page |
| `assets/illustrative/` | Editable Ashford sources and original SVG plan |
| `scripts/build_distribution.py` | Existing allowlist extended to ship interface assets |

Keep algorithms in their existing backend modules. Charts must use executed results or actual source records. Escape source text before HTML rendering. Retain explicit missing/failed states. New scores, states or relationships must not be invented for visual balance.

## Scope and limitations

Streamlit remains the host: navigation reruns the script; forms and loading indicators are native; the graph is a selectable Plotly canvas rather than a general graph editor. Large graph management, persisted annotation/verification, authentication, collaborative case management, OSINT, 3D reconstruction and deferred platform modules remain outside this release. The local application remains a research demonstration, not a deployment with production security controls.

The original manor illustration is schematic. No externally licensed photography or proprietary interface assets were copied. The Sites workflow was used for local interface design/preview; this CUDA-capable local app was not published to Sites. Visualize's project-change guidance was applied to the actual product interface rather than creating a second mock application.

See `UI_REDESIGN_QA.md` for actual verification and screenshots.

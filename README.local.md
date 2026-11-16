# SHERLOCKED AI Laboratory

Local explainable retrieval over fictional Bangla, English and mixed reports. Six core Streamlit screens connect browsing/submission, TF-IDF/BM25, pinned multilingual E5, entity/structured signals, hybrid ranking, source-grounded explanations, graphs, experiments and exports. No paid API key. The CASE FILE NOIR interface uses an ink navigation rail, paper source dossiers and an original deerstalker-and-pipe identity. Ashford Manor remains a SEPARATE DEMO CORPUS. See the [design guide](docs/CASE_FILE_NOIR.md), [current verification and screenshots](docs/NOIR_VERIFICATION.md), and [portable release instructions](docs/NOIR_PORTABLE_RELEASE.md). November 5 UI documents remain historical.

## Windows setup and start

On a new computer install64-bit Python3.12 from python.org, extract the project and double-click **SETUP_SHERLOCKED.bat**. Then double-click **START_SHERLOCKED.bat**. Commands also work from another directory when their full paths are quoted.

```powershell
.\SETUP_SHERLOCKED.bat
.\START_SHERLOCKED.bat
```

Open http://127.0.0.1:8501. Setup detects supported Python3.10-3.12, creates an environment, installs missing dependencies, initializes directories/SQLite safely and checks model assets. Start performs lightweight checks and launches; it never installs or downloads. Errors remain visible. Stop with Ctrl+C.

Existing working CUDA packages are preserved. Fresh setup uses CPU PyTorch by default. `SETUP_SHERLOCKED.bat -Cuda` explicitly installs the official CUDA12.4 wheel without touching drivers. Exact dependency locks are tested on Python3.12. Do not copy .venv between computers; moved environments are detected and preserved before recreation.

```powershell
.\START_SHERLOCKED.bat -Check
.\SETUP_SHERLOCKED.bat -DownloadModel
.\SETUP_SHERLOCKED.bat -Offline -SkipInstall
.\SETUP_SHERLOCKED.bat -Cpu
```

## Welcome, sign-in and appearance

The browser opens a clean branded Noir landing page with a static capability overview, sign-in and appearance controls. **Enter the research lab** or **Investigator access** opens local sign-in. Report browsing, source preview and retrieval are available inside the authenticated lab; there is no public working preview or report handoff from the landing page.

Local demonstration access: username **demo**, password **sherlocked-demo** (also shown on the login screen). Existing changed passwords are preserved. This is a local fictional-demo access gate, not enterprise authentication. Its salted PBKDF2 account store is separate at the configured dataset directory's `local_access.sqlite3`.

Use **Dark mode / Light mode** on welcome, login or the workspace. The URL records `theme=light` or `theme=dark` for reload continuity. **Sign out** clears access and analysis session state while retaining appearance; there is no remember-me token. Intentional paper tables/heatmaps and the ink relationship graph remain in both appearances. See [entry and theme notes](docs/ENTRY_AND_THEMES.md) and [entry verification status](docs/ENTRY_VERIFICATION.md). Earlier screenshots that include a working landing preview are historical.

## Models, paths and transfer

Pinned model: intfloat/multilingual-e5-small,MIT,384 dimensions, safetensors without remote code. Default assets: models/multilingual-e5-small. System Settings chooses offline/online mode. Offline requires complete local assets and never downloads. Online can fetch the approved pinned model when semantic retrieval is requested. First online setup uses DownloadModel. Missing assets/errors are visible; lexical retrieval is an explicit alternative, never an implicit replacement.

Auto selects working PyTorch CUDA or CPU. Requested/active device, loading state and any CPU retry reason are visible. Auto can retry the same model on CPU after CUDA failure; forced CUDA fails visibly. Shared model handles persist across reruns/ranking changes. Deduplicated batches and bounded RAM/disk embedding caches avoid redundant inference. Cache identity includes content, model revision, prefixes and normalization settings; old/invalid caches can be regenerated without affecting source data.

Copy configs/paths.example.json to configs/paths.json only to override model/cache/database/dataset/results/logs/exports/temp locations. Relative paths resolve against project root, never current working directory. Optional SHERLOCKED_* environment overrides are documented in .env.example, which is not automatically loaded. No secrets are required. Personal overrides are excluded from the distribution.

Transfer the source ZIP, extract, install Python, run SETUP then START. Transfer models/multilingual-e5-small separately for offline model inference, or download it on the destination. **The source ZIP is not fully offline:** neither dependencies nor model files are included. Offline initial installation additionally needs a prepared dependency wheelhouse. See docs/WINDOWS_SETUP_AND_PORTABILITY.md and docs/DISTRIBUTION.md.

## Data, results and checks

Canonical90 reports/manifest remain under data; the separate39-report challenge and explicit qrels remain distinct. SQLite workspace defaults to data/sherlocked.sqlite3. User submissions do not enter benchmark labels. Generators preserve identical files and refuse conflicting overwrites unless explicitly requested. Historical experiment results are preserved under results/experiments. UI evidence downloads also save local copies under exports. Logs rotate under logs. Source-only evaluation remains default; previous frozen test results are historical and must not guide new tuning.

```powershell
.venv/Scripts/python.exe -m unittest discover -s tests -v
.venv/Scripts/python.exe -m pip check
.venv/Scripts/python.exe scripts/check_server.py
.venv/Scripts/python.exe scripts/check_semantic.py
.venv/Scripts/python.exe scripts/build_distribution.py
# Optional separate model archive/history:
.venv/Scripts/python.exe scripts/build_distribution.py --output dist/SHERLOCKED-with-history.zip --include-results
.venv/Scripts/python.exe scripts/build_distribution.py --model-assets
```

Default ZIP: dist/SHERLOCKED-portable.zip. Allowlisting excludes .venv,DB,models,caches,logs,exports,temp,backups,bytecode,secrets,personal settings and Git history. Every included file has a SHA256 entry; existing archives are not overwritten. Preserve the original development folder.

## Troubleshooting and limits

Missing Python: install64-bit3.12 or pass `SETUP_SHERLOCKED.bat -PythonPath "path to python.exe"`. Missing/broken environment: run SETUP; START intentionally does not install. Network failure: retry online or use Offline/Wheelhouse setup. Missing model: DownloadModel online or transfer complete assets. CUDA failure: inspect the reason/use auto or CPU; a driver alone does not prove PyTorch works. Port occupied: `START_SHERLOCKED.bat -Port 8502`. Dataset mismatch: preserve edits and import reports rather than replacing the benchmark. The first search may rebuild versioned caches after upgrades.

Small synthetic datasets, heuristic extraction, unresolved negation/coreference, no validated abstention and one experimentally tested encoder remain limitations. This is a local research tool; do not enter real sensitive reports or expose it publicly. Similarity never determines guilt, verifies identity or confirms a relationship.

Corrected source release target: `dist/CASE-FILE-NOIR-20261113/no-preview/SHERLOCKED-PORTABLE.zip`. Reuse the separate model archive at `dist/CASE-FILE-NOIR-20261113/final/SHERLOCKED-MODEL-ASSETS.zip`. The source ZIP includes the historical measured runs but excludes the local database, model weights and dependency environment.

Guides: USER_GUIDE.md,TECHNICAL_ARCHITECTURE.md,AI_PIPELINE.md,DATASET_DOCUMENTATION.md,EXPERIMENTS_AND_EVALUATION.md,DEVELOPMENT_GUIDE.md,LIMITATIONS_AND_ETHICS.md,docs/PHASE2_VERIFICATION.md. Earlier status/results remain historical. No deferred platform modules added.

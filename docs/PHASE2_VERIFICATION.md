# Phase 2 verification and handover

5 November 2026 · SHERLOCKED local readiness and portable distribution

## Outcome

The existing local application was audited, backed up and improved in place. It runs through the Windows launcher with the original CUDA environment. A separate source-only distribution was installed into a genuinely new CPU environment, tested offline with transferred model assets, moved to a different folder and started through its Windows launcher from an unrelated working directory. This is same-PC relocation verification, not a claim of cross-computer testing.

## Hardware and runtime actually observed

- Windows10 build19044, AMD Ryzen5 5600 six-core,34276421632 bytes physical memory (approximately32GB).
- Original environment: Python3.12.14,PyTorch2.6.0+cu124,PyTorch CUDA12.4, NVIDIA GeForce RTX3060. Actual uncached CPU and CUDA inference passed.
- Running application semantic query displayed active_device=cuda with requested device=auto; model status loaded=true and missing_assets empty.
- Fresh test environment: Python3.12.14,PyTorch2.6.0+cpu,cuda_available=false. Auto selected CPU and actual offline inference passed despite the PC having an NVIDIA GPU.
- Model: intfloat/multilingual-e5-small, revision614241f622f53c4eeff9890bdc4f31cfecc418b3,384 dimensions,MIT. Default local model folder: models/multilingual-e5-small.

## Preservation and audit

Before changes, all30 existing tests passed, original dataset hash was valid, and the pinned model was usable. The folder remains outside Git; no commit/push or reference-repository modification occurred. Backup: backups/phase2-before-20261105.zip. Baseline inventory: backups/phase2-preservation.json.

Final preservation check confirms **all25 original data/database/result files have identical SHA256 hashes**, including original90 reports,39-report challenge,manifests,qrels,SQLite and historical experiments. New verification outputs go under logs or the separate test copy. No frozen test set was used for new tuning.

## Implemented improvements

paths.py provides one project-root-relative configuration system for models,cache,database,dataset,results,logs,exports,temp. Optional configs/paths.json overrides and SHERLOCKED_* environment variables are documented; personal overrides are excluded from ZIPs. No application/launcher logic depends on a username or original checkout path. Historical artifacts may retain execution paths as provenance.

Separate SETUP/START batch and PowerShell scripts detect supported Python3.10-3.12, initialize missing resources safely, use CPU dependencies on a fresh machine, preserve a healthy existing CUDA environment, and offer explicit CUDA/online/offline modes. Python3.12 has exact CPU/CUDA lock profiles. A moved environment is detected, preserved under backups/environments, and recreated at the destination. START validates resources without installing packages. The ready server opens the browser unless NoBrowser is requested.

Two actual startup issues were found and fixed: Streamlit first-run onboarding could stop an unattended start, so the server is headless and browser opening occurs only after readiness; an unavailable PowerShell Get-FileHash command could prevent the environment marker from being saved, so hashing now uses .NET SHA256. A regression test disables utility-module autoload to exercise the latter fix.

Model status validates all weights/tokenizer/pooling assets and reports requested/active device,loading,missing assets and fallback reason. Offline mode never downloads. Auto retries the same model on CPU after CUDA failure and exposes the reason; forced CUDA fails explicitly. No semantic-to-keyword substitution occurs. Policy-specific wrappers share the loaded neural model safely without sharing download permission.

Cache identity is versioned and includes content/model/revision/role/pooling/normalization. Duplicate texts are batched once; a bounded2048-vector RAM cache supplements validated atomic disk entries. Repeated real searches reused embeddings: encoded_texts stayed95 while memory hits increased3 to101. SQLite-derived views are cached using database/WAL modification signatures. Ranking setting changes reuse the loaded model.

Generators are idempotent and refuse conflicting overwrites unless explicitly requested. Legacy/new experiment outputs are unique. UI evidence downloads persist unique local exports with available configuration/model provenance. Bounded rotating logs and source/data errors remain explicit. The selected-report-to-analysis navigation bug was fixed and regression-tested.

## Actual checks

- Original final suite: **52 tests passed**, logs/phase2-tests.txt. Compilation and pip check passed.
- Fresh source-only CPU environment:51 tests passed before the final hashing regression was added; moved/recreated CPU environment:52 tests passed afterward.
- Actual setup -Offline -SkipInstall on the original PC passed without reinstalling its working CUDA packages.
- Clean CPU dependency installation completed through setup using the CPU lockfile and official PyTorch CPU wheel. No original environment was copied.
- Missing dependency reporting was exercised during the clean setup and dedicated tests. Missing model offline load failed explicitly without downloading; copying the complete approved model assets enabled offline inference.
- All8 methods (TF-IDF,BM25,semantic,entity,structured,weighted,RRF,heuristic reranking),graph construction,exports and source evidence executed in the clean CPU copy.
- Two independent development experiment runs produced identical ranked IDs for every method. This is a reproducibility check, not a new accuracy claim.
- Two HTTP stop/start checks passed. After moving the test project, START correctly refused its stale environment. Setup preserved the old environment and recreated a clean CPU environment. Final offline model check,52-test suite and actual Windows launcher returned HTTP200 from outside the project directory.
- All6 screens were opened and visually inspected in the actual browser at a1280x720 viewport. A mixed Bangla/English semantic query produced source-linked results with active CUDA; the report graph rendered, saved experiment tables appeared, an actual experiment export created a local file, and settings showed offline mode and resolved resource paths. This is not comprehensive accessibility certification or every viewport/control combination.

Machine-readable relocation evidence is logs/phase2-phase2-verification.json; detailed test-copy logs are retained in the separate phase2-relocation workspace. Hardware/inference compatibility evidence is logs/semantic-devices-20261105T031609737735.json. The original results/semantic_smoke.json remains unchanged.

## Run and transfer

Current folder: run START_SHERLOCKED.bat. On a new destination: install64-bit Python3.12, extract the source package, run SETUP_SHERLOCKED.bat then START_SHERLOCKED.bat. Use -PythonPath when Python is not discoverable, -Cuda only for the intended NVIDIA package profile, and -DownloadModel for explicit online model setup. No GPU drivers/system security settings are changed.

Default resource locations:

| Resource | Location relative to project |
|---|---|
| Model assets | models/multilingual-e5-small |
| Embeddings | cache/embeddings |
| Dataset | data/ |
| Database | data/sherlocked.sqlite3 |
| Experiments | results/experiments/ |
| Logs | logs/ |
| Exports | exports/ |
| Temporary resources | tmp/ |

Source ZIP: dist/SHERLOCKED-portable.zip. It includes source,setup/start scripts,dependencies/locks,synthetic data,tests,docs and safe config templates with a file-hash manifest. It excludes .venv,database,model weights,caches,logs,exports,temp,backups,secrets,personal overrides and Git history. Saved historical experiments are opt-in. A separate model ZIP can be generated with scripts/build_distribution.py --model-assets; it includes the pinned assets/model card/MIT attribution.

**The source ZIP needs internet for first dependency installation and model download.** Once dependencies and separately transferred complete model assets are present, offline inference is supported and was actually tested. Fully offline first installation additionally requires a compatible dependency wheelhouse; no Python runtime,wheelhouse or driver is bundled. Another Windows laptop needs supported64-bit Python/Windows,adequate disk/RAM,and its own validated environment. CUDA is optional. Cross-computer execution has not been tested.

## Remaining limitations

The corpus is small and synthetic; extraction remains heuristic,Latin-only Banglish detection is limited,negation/coreference remain unresolved,no validated abstention threshold exists,and only one encoder has been experimentally evaluated. Reranking is a documented heuristic,not a learned cross-encoder. The unauthenticated app is intended for local fictional research,not public deployment or sensitive operational records. No claim of real-world investigative accuracy or enterprise readiness is made.

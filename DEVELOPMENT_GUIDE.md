> Phase 2 supersedes the original launcher instructions: SETUP_SHERLOCKED.bat installs/initializes; START_SHERLOCKED.bat performs lightweight checks only. There is no Codex-specific Python discovery path in launch logic. Supply -PythonPath when no ordinary Python launcher is installed. Python3.12 CPU and CUDA locks are separate. Use scripts/build_distribution.py for an allowlisted source ZIP; never transfer .venv. Model files may transfer separately for offline inference. Resource configuration, actual clean-install/relocation results and known limits are in docs/WINDOWS_SETUP_AND_PORTABILITY.md and docs/PHASE2_VERIFICATION.md.

# Development guide

This local Python/Streamlit research application uses no paid API key. Reference repositories are not part of its runtime.

## Environment and commands

Python 3.12 is tested. The Windows launcher detects `.venv`, the Python launcher, an ordinary Python executable or the Codex bundled runtime, avoiding the Windows Store alias. On a clean machine install Python from python.org, then run `START_SHERLOCKED.bat`. Missing Python dependencies are installed, and missing resources initialized. It never automatically downloads a model or regenerates existing reports.

```powershell
./start.ps1 -Check
.venv/Scripts/python.exe scripts/health.py --initialize
.venv/Scripts/python.exe -m pip check
.venv/Scripts/python.exe -m unittest discover -s tests -v
.venv/Scripts/python.exe scripts/check_server.py
```

`-Check` validates startup without starting a server. `-SkipInstall` prevents automatic dependency installation. `-Port 8502` resolves a port conflict. The `.bat` keeps errors visible. Direct launch:

```powershell
.venv/Scripts/python.exe -m streamlit run app.py --server.address 127.0.0.1
```

## Code boundaries

- `dataset.py` and original JSONL/manifest preserve the first reproducible fixture.
- `ingestion.py`, `storage.py`, `signals.py`: validated fictional reports, SQLite, traceable extraction and comparison.
- `retrieval.py`: preserved original TF-IDF service and compatibility tests.
- `semantic.py`, `engine.py`: actual model inference, BM25 and hybrid retrieval.
- `experiments.py`: train-fit evaluation, split validation, metrics, artifacts and exports.
- `app.py`: interface composition; keep ranking algorithms in services.

Never use family IDs, partitions or relation labels as ranking features. Preserve original text and source offsets. Ranking changes require relevant tests and dev comparisons; never tune on test.

## Verification and dependencies

Tests use deterministic fixtures for metric math, source offsets, data validation and ranking. A fixture model/engine in tests is a labelled test double; production semantic results must use the pinned real encoder. Loading failure must remain explicit with a user-selected lexical alternative, never a silent TF-IDF substitution.

`scripts/check_server.py` starts a temporary localhost process, checks HTTP health and stops only that process. It does not verify appearance. Browser visual verification and CPU/GPU inference are reported separately. AppTest and HTTP status alone cannot establish them.

`requirements.txt` defines direct packages; `requirements-lock.txt` captures the verified environment. Recreate and test a clean environment before changing distribution pins. GPU PyTorch wheels may require a platform-specific source; keep CPU usable. Explicit model setup downloads once; embedding caches depend on content/model identity. Read model licensing and prefix notes in AI_PIPELINE.md before changing model families.

## Data preservation

Do not overwrite originals with regenerated content. `python -m sherlocked.dataset` intentionally rewrites its two known generated files; avoid it on edited data. The launcher initializes fixtures only when both are absent, validates the manifest and uses insertion rules preserving existing SQLite records. Back up SQLite before large fictional-data imports.

No Git commit/push is automated. The original workspace was not a Git repository at audit time. If PyTorch fails with a Windows DLL error, inspect the installed CPU/CUDA wheel and supported Microsoft C++ runtime; the launcher reports this through health checks rather than claiming GPU availability.

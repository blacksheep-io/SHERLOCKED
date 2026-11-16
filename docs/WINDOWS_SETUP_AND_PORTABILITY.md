# Windows setup and portability

## Start on the current desktop

Run `SETUP_SHERLOCKED.bat` once, then `START_SHERLOCKED.bat`. The existing prepared CUDA environment is retained when healthy. Setup checks dependencies, initializes only missing resource directories/database rows, validates the original fixture hash, checks local model assets, and records an environment-location marker. It does not overwrite reports or experiment results.

START never installs packages, downloads models or recreates an environment. It locates its own folder, validates Python/dependencies/resources, displays the localhost address and starts Streamlit. It works independently of the caller's working directory. Errors remain visible in the batch window. Stop with Ctrl+C.

## Another Windows computer

Install **64-bit Python 3.12** from python.org with the Python launcher. Supported interpreter range is 3.10-3.12; the tested exact dependency snapshots target Windows Python 3.12. Python 3.10/3.11 use the direct pinned requirements and are supported by version checks but have not been independently tested here.

Extract the source distribution into an ordinary writable folder. Paths with spaces are supported. Run:

```powershell
.\SETUP_SHERLOCKED.bat -DownloadModel
.\START_SHERLOCKED.bat
```

A fresh setup installs the CPU PyTorch wheel from the official CPU package index, then the project dependencies. Python 3.12 uses `requirements-cpu-lock.txt`; other supported minors use `requirements.txt`. Missing model assets download only when `-DownloadModel` (alias `-Online`) is selected. Prepared local assets are reused.

The model is multilingual E5-small, pinned to the revision documented in `configs/model.json`, with MIT licensing. Assets occupy roughly 470 MB for weights plus tokenizer/configuration files. Transfer its entire model folder, including the SHERLOCKED revision marker and pooling configuration, rather than only the weights.

### Optional NVIDIA acceleration

```powershell
.\SETUP_SHERLOCKED.bat -Cuda -DownloadModel
```

This installs the supported PyTorch CUDA 12.4 wheel from its official package index. It does not install or alter GPU drivers. CUDA requires a compatible NVIDIA GPU and driver; merely seeing an NVIDIA adapter does not establish PyTorch CUDA availability. Inspect System Settings or run the full health check. If automatic CUDA initialization is unusable, the semantic layer reports a CPU fallback using the same encoder; it does not substitute lexical retrieval.

Existing healthy CUDA setups are not replaced with CPU by default. `-Cpu` explicitly requests the CPU wheel. These profile switches are optional and do not repeatedly reinstall an already matching wheel.

### Explicit interpreter selection

If Python is not discoverable:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\setup.ps1 -PythonPath 'C:\Python312\python.exe'
```

Discovery uses the installed Python launcher or ordinary PATH interpreter. It ignores the Windows Store alias and contains no hardcoded original-user/Codex-runtime location.

## Moving the folder

The source, fixtures, settings templates, and optional model assets can move. **Virtual environments are not portable** and are excluded from the distribution.

If a copied environment is detected, START refuses it with setup instructions. SETUP checks the saved project-location marker or legacy activation path, preserves the old `.venv` under `backups/environments/venv-<timestamp>-<id>`, and creates a fresh local environment. It never deletes the previous environment. Backup targets are checked to remain inside the selected project; linked environment directories are refused. `-RecreateEnvironment` explicitly requests the same preservation/recreation process.

Keep an installed supported base Python on each destination machine. Relocation tests on the current PC do not constitute verification on a second computer.

## Online and offline model modes

Default setup only checks existing model assets; it does not contact the model repository. For online setup use `-DownloadModel`. In offline operation transfer the approved complete model directory to the configured model resource folder. Inference loads local files only and does not require an API key.

```powershell
.\SETUP_SHERLOCKED.bat -Offline
```

Offline setup refuses network dependency installation. It succeeds with an already prepared compatible environment. A clean offline machine also needs Python and a prepared matching wheelhouse:

```powershell
.\SETUP_SHERLOCKED.bat -Offline -Wheelhouse 'E:\SHERLOCKED wheels'
```

On an internet-connected matching Windows/Python 3.12 machine, a CPU wheelhouse can be prepared from the pinned files:

```powershell
python -m pip download --no-deps --only-binary=:all: 'torch==2.6.0+cpu' --index-url https://download.pytorch.org/whl/cpu --dest wheelhouse
python -m pip download --no-deps --only-binary=:all: -r requirements-cpu-lock.txt --find-links wheelhouse --dest wheelhouse
```

Transfer the wheelhouse separately along with model assets and the source distribution. The pinned snapshot supplies the transitive dependency list; validate it with `pip check` during setup. Wheels must match destination OS, architecture and Python minor version. Do not call a source-only ZIP fully offline: without model assets and dependency wheels, initial setup needs internet.

## Resource configuration

Defaults are project-relative: models in `models/`, embeddings in `cache/`, SQLite in `data/sherlocked.sqlite3`, fixtures in `data/`, experiments under `results/`, and `logs/`, `exports/`, `tmp/`.

Override resource locations using optional `configs/paths.json` keys `models`, `cache`, `database`, `dataset`, `results`, `logs`, `exports`, `temp`. Relative values resolve against the project root, not the terminal directory. `database` is a file path; all other resources are directories. Prefer relative settings in transferred projects.

Environment overrides take precedence: `SHERLOCKED_MODEL_DIR`, `SHERLOCKED_CACHE_DIR`, `SHERLOCKED_DATABASE_PATH`, `SHERLOCKED_DATASET_DIR`, `SHERLOCKED_RESULTS_DIR`, `SHERLOCKED_LOG_DIR`, `SHERLOCKED_EXPORT_DIR`, `SHERLOCKED_TEMP_DIR`. No secrets are required. Setting these variables does not mean a `.env` file is automatically loaded.

When a new custom dataset directory is empty, setup copies the shipped canonical fixtures into it. If either fixture or manifest already exists, setup validates them and never regenerates over them. Existing mismatched data results in an actionable error.

## Verification and troubleshooting

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\start.ps1 -Check
.venv/Scripts/python.exe -B scripts/health.py --verify-imports
.venv/Scripts/python.exe -B scripts/check_server.py
.venv/Scripts/python.exe -B -m unittest discover -s tests -v
```

`start.ps1 -Check` is a lightweight read-only startup validation; it deliberately does not load PyTorch or run inference. Full health reports installed package versions, manifest/hash, resource paths, database and CUDA availability. Model status distinguishes available assets from a model that has actually loaded. HTTP server health is not browser visual verification.

For missing dependencies rerun SETUP. For a Windows PyTorch DLL error, review the selected CPU/CUDA wheel and the supported Windows C++ runtime; do not change drivers automatically. For a missing model use online setup or transfer the complete approved assets. For a busy port run `START_SHERLOCKED.bat -Port 8502`. Use `-SkipInstall` on setup to validate without package changes; START accepts that legacy flag but never installs in any mode.

Automated launcher tests set `SHERLOCKED_NO_PAUSE=1` to prevent an error pause; ordinary interactive batch errors stay visible.

Actual original-machine and relocation test outcomes, distribution contents, and any remaining limitations are recorded in the phase-two verification report. The small synthetic dataset, heuristic extraction and uncalibrated no-match threshold remain research limitations.


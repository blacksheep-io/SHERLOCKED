# SHERLOCKED

**A local, explainable retrieval laboratory for fictional reports.**

SHERLOCKED is a Python/Streamlit research application for browsing and comparing Bangla, English and mixed-language reports. It combines TF-IDF, BM25, multilingual E5 embeddings, entity/structured signals and hybrid ranking with source-grounded explanations, relationship graphs, experiments and exports. No paid API key is required.

The CASE FILE NOIR interface provides a branded entry screen, local sign-in, light/dark appearance and an authenticated research workspace. The bundled corpora are fictional; the separate Ashford Manor demo remains distinct from the main benchmark.

## Windows quick start

Install 64-bit Python **3.12**. The setup scripts support Python 3.10–3.12; the exact dependency locks target Python 3.12. From the repository root in PowerShell:

```powershell
.\SETUP_SHERLOCKED.bat
.\START_SHERLOCKED.bat
```

Open `http://127.0.0.1:8501`. Setup creates a project-local environment, installs dependencies and initializes missing local storage safely. Start checks the environment and launches the application; it does not install dependencies or download models. Stop with Ctrl+C.

The deliberately public local demonstration login is **`demo` / `sherlocked-demo`**. Existing changed passwords are preserved. This gate is intended for the local fictional demo, with no enterprise identity or account-recovery claim. See [local access](docs/LOCAL_ACCESS.md).

Useful options:

```powershell
.\START_SHERLOCKED.bat -Check
.\START_SHERLOCKED.bat -Port 8502
.\SETUP_SHERLOCKED.bat -DownloadModel
.\SETUP_SHERLOCKED.bat -Cpu
# Optional supported GPU profile; does not install or alter GPU drivers:
.\SETUP_SHERLOCKED.bat -Cuda
```

Fresh setup uses CPU PyTorch by default and preserves an existing working CUDA environment unless a different profile is requested. Do not copy `.venv` between machines; run setup on the destination. See [Windows setup and portability](docs/WINDOWS_SETUP_AND_PORTABILITY.md).

## Models and offline use

The pinned encoder is `intfloat/multilingual-e5-small` at revision `614241f622f53c4eeff9890bdc4f31cfecc418b3`: 384 dimensions, MIT-licensed, safetensors, with remote model code disabled. Its default asset directory is `models/multilingual-e5-small`; see [model configuration](configs/model.json).

Model weights and Python dependencies are not included in the source checkout. Use `-DownloadModel` while online to prepare the approved model. Offline semantic retrieval requires complete local assets; lexical retrieval remains an explicit alternative when assets are missing. Offline initial dependency installation additionally requires a prepared wheelhouse. Startup does not silently download or substitute a different method.

```powershell
# For an already prepared environment:
.\SETUP_SHERLOCKED.bat -Offline -SkipInstall
# For offline dependency installation using prepared packages:
.\SETUP_SHERLOCKED.bat -Offline -Wheelhouse "C:\path\to\wheelhouse"
```

Optional local path overrides use `configs/paths.json`, copied from [configs/paths.example.json](configs/paths.example.json). Relative paths resolve against the project root. Environment overrides are listed in [.env.example](.env.example); that file is not automatically loaded. Personal settings and secrets should stay local.

## Source and data

| Path | Contents |
| --- | --- |
| `sherlocked/` | Application, retrieval, explanations, storage and interface |
| `scripts/` | Setup, health checks and source/model packaging |
| `tests/` | Automated application and portability checks |
| `data/` | Fictional benchmark reports, manifests and relevance labels |
| `assets/` | Interface styles and artwork |
| `configs/` | Shared model configuration and example local paths |
| `docs/` | Design, operation and dated verification evidence |
| `results/` | Historical research outputs, where included |

The main 90-report corpus and separate 39-report challenge have distinct relevance labels. User submissions do not become benchmark labels. Local SQLite stores, model weights, environments, caches, backups, logs, exports and personal settings are excluded from version control. Preserve edited reports and historical experiments; do not replace them with regenerated data.

## Private hosted demonstration

An isolated [Streamlit Community Cloud profile](docs/STREAMLIT_DEPLOYMENT.md) uses `deploy/streamlit/app.py`, Python 3.12 and CPU-only PyTorch. Keep the deployment private to trusted viewers: the application shares its reports and settings, and generated cloud files have no persistence guarantee. The desktop setup and offline defaults remain unchanged.

## Development checks

After setup, from the repository root:

```powershell
.venv/Scripts/python.exe -m unittest discover -s tests -v
.venv/Scripts/python.exe -m pip check
.venv/Scripts/python.exe scripts/check_server.py
.venv/Scripts/python.exe scripts/check_semantic.py
```

Semantic checks require the configured model assets. The [distribution guide](docs/DISTRIBUTION.md) explains source and separate model archives; building an archive is a separate operation from cloning this repository.

## Guides and limitations

- [User guide](USER_GUIDE.md), [technical architecture](TECHNICAL_ARCHITECTURE.md) and [AI pipeline](AI_PIPELINE.md)
- [Dataset documentation](DATASET_DOCUMENTATION.md) and [experiments/evaluation](EXPERIMENTS_AND_EVALUATION.md)
- [Development guide](DEVELOPMENT_GUIDE.md) and [limitations and ethics](LIMITATIONS_AND_ETHICS.md)
- [Entry/theme notes](docs/ENTRY_AND_THEMES.md), [dated verification](docs/ENTRY_VERIFICATION.md) and [historical local-release README](README.local.md)

The datasets are small and synthetic; extraction uses heuristics, negation/coreference remain limited, and similarity is not a calibrated relationship probability. Similarity does not determine guilt, verify identity or confirm a real connection. Keep the desktop application on loopback, restrict a hosted demonstration to trusted viewers, and do not enter real sensitive reports.

Test counts, screenshots, archive names and acceptance statements in the imported documents describe their dated local checkpoints. They do not establish a new test run, fresh-machine verification or a downloadable GitHub release. Earlier screenshots showing an interactive public preview are historical; report analysis belongs inside the signed-in workspace.

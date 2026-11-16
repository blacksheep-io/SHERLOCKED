# Portable distribution

The project supports a compact source ZIP and a separate optional pinned-model ZIP. Neither ZIP contains a virtual environment, Python installer, dependency wheelhouse, CUDA driver or paid API integration. First dependency installation requires internet access unless you separately prepare compatible offline wheels. The source ZIP alone does not provide offline semantic inference.

From the project folder after validation:

```powershell
.venv/Scripts/python.exe scripts/build_distribution.py
.venv/Scripts/python.exe scripts/build_distribution.py --model-assets
```

Default outputs are `dist/SHERLOCKED-portable.zip` and `dist/SHERLOCKED-model-assets.zip`. Existing outputs are never overwritten; use a fresh filename with `--output dist/SHERLOCKED-portable-next.zip` for another build. Source contents are allowlisted: application/package source, scripts, tests, documentation, setup/start launchers, dependency files, configuration templates and the six fictional dataset/manifest/qrels files. The builder does not delete or move anything from the development project.

By default the source ZIP excludes `.venv`, bytecode, model assets, embedding/Hub caches, SQLite user reports, logs, exports, temporary files, backups, Git history, `.env`, secrets and personal `configs/app.json` / `configs/paths.json` / setup state. It also excludes saved research results. `--include-results` explicitly includes existing result JSON/CSV files and the frozen research configuration; those artifacts may retain the original machine's execution paths as historical provenance. Review this optional content before sharing.

Each ZIP contains `SHERLOCKED/DISTRIBUTION_MANIFEST.json` with a per-file SHA-256 and size, package kind, dependency requirements and model information where applicable. Entries use stable ordering and fixed timestamps, so identical selected source bytes produce the same ZIP hash. These checksums detect modification; they are not a digital signature or third-party security certification.

## Transferring to another Windows computer

1. Install a supported 64-bit Python version as documented in README; do not copy `.venv` from the original machine.
2. Extract the source ZIP into a writable folder. Entries are under a `SHERLOCKED/` directory.
3. Optionally extract the model-assets ZIP into the same parent folder; the two `SHERLOCKED/` trees merge. For a custom models root, move the model subfolder into that configured root instead.
4. Run `SETUP_SHERLOCKED.bat` to create the destination's own environment and initialize local resources without replacing existing reports.
5. If no model ZIP was transferred, explicitly prepare the approved model using the setup instructions. Downloads are cached locally; they are not repeated on every launch.
6. Run `START_SHERLOCKED.bat` and follow the displayed local browser address.

With dependencies installed and complete model assets present, model inference requires no network. CPU execution remains available on machines without a compatible CUDA setup. Actual CUDA availability depends on the installed PyTorch build and a compatible NVIDIA driver, not simply an NVIDIA device name.

## Model license and storage

The separate package accepts the configured audited MIT model only and requires its local setup marker to match the pinned model ID and revision. It includes the original model card, a Microsoft MIT license copy and a transfer guide. It excludes Hugging Face `.cache` metadata and credentials. The current multilingual-e5-small weights occupy roughly 470 MB before compression; inspect the actual generated ZIP size rather than assuming it matches another model. Pin and licensing information is in `configs/model.json` and the packaged manifest. Sources: [model card](https://huggingface.co/intfloat/multilingual-e5-small) and [upstream MIT license](https://github.com/microsoft/unilm/blob/master/LICENSE).

Copying the source archive into another local directory tests path independence on the current computer. It does not establish cross-computer compatibility. A destination still needs supported Windows/Python, sufficient disk and RAM, installable dependencies, and its own environment verification.

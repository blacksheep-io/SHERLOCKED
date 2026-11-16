# CASE FILE NOIR — portable release guide

Corrected source release target: `dist/CASE-FILE-NOIR-20261113/no-preview/SHERLOCKED-PORTABLE.zip`. Reused model assets: `dist/CASE-FILE-NOIR-20261113/final/SHERLOCKED-MODEL-ASSETS.zip`.

The working installation stays at `C:\Users\NOYON\Documents\ChatGPT\SHERLOCKED`. Packaging does not relocate it. Release preparation reused the installed dependencies and existing pinned model; no package reinstall or model download was performed.

## Release files

| File | Contents |
|---|---|
| `no-preview/SHERLOCKED-PORTABLE.zip` | Corrected clean-landing source, Windows setup/start scripts, dependency specifications, configuration templates, documentation, fictional datasets and saved experiment history. New source checksums and verification are recorded with this rebuilt package; earlier source hashes do not verify it. |
| `final/SHERLOCKED-MODEL-ASSETS.zip` | Reused separately transferable pinned multilingual model, original model card, MIT license/attribution and transfer instructions. Previously verified archive size: **283,949,105 bytes**. |

The source archive excludes the virtual environment, personal report and access SQLite databases, model weights, embedding caches, secrets, logs and temporary work. A destination creates its own environment and database from the shipped fictional records. Saved experiments are historical measurements, not newly recomputed results.

The model is `intfloat/multilingual-e5-small`, revision `614241f622f53c4eeff9890bdc4f31cfecc418b3`, with 384-dimensional embeddings. The original model files total **493,293,143 bytes uncompressed**, before the additional package manifest, license and transfer guide. The model ZIP contains assets rather than Python or installed dependencies.

## Transfer and start on Windows

1. Install **64-bit Python 3.12** on the destination. See [Windows setup and portability](WINDOWS_SETUP_AND_PORTABILITY.md) for prerequisites and troubleshooting.
2. Extract **both ZIPs into the same parent directory**. Both contain a `SHERLOCKED/` tree, so the resulting layout is:

   ```text
   Chosen parent/
     SHERLOCKED/
       SETUP_SHERLOCKED.bat
       START_SHERLOCKED.bat
       app.py
       data/
       models/
         multilingual-e5-small/
   ```

3. Open that resulting `SHERLOCKED` folder and run:

   ```powershell
   .\SETUP_SHERLOCKED.bat
   .\START_SHERLOCKED.bat
   ```

A fresh environment uses CPU PyTorch by default. Setup retains a healthy existing CUDA environment. To explicitly install the supported CUDA profile on a suitable NVIDIA system, use `SETUP_SHERLOCKED.bat -Cuda`; `-Cpu` explicitly selects CPU. Setup pins and verifies the requested CPU/CUDA package variant. It does not change GPU drivers.

The landing page contains the original branding, a static capability overview, sign-in and appearance controls. It has no public working preview, report selectors or report handoff. Choose Investigator access and use the local demonstration account **demo / sherlocked-demo** (unless already changed). Source preview and actual retrieval remain inside the authenticated research workspace. Light mode / Dark mode is available on landing, login and inside the lab. See [Entry and appearance guide](ENTRY_AND_THEMES.md).

The default local address is [http://127.0.0.1:8501](http://127.0.0.1:8501). If that port is occupied, run `START_SHERLOCKED.bat -Port 8502` and use [http://127.0.0.1:8502](http://127.0.0.1:8502). The launcher displays errors and the actual address. Stop it with Ctrl+C.

## Internet and offline operation

**First dependency setup needs internet**, unless compatible dependency wheels have been prepared separately. The model ZIP supplies existing model assets, so those assets need not download again. If transferring only the source ZIP, `SETUP_SHERLOCKED.bat -DownloadModel` explicitly prepares the approved model online.

**Offline runtime** is supported once Python, dependencies and complete model assets are present. Keep the application’s model mode set to offline. No paid API key is required.

For a clean offline installation, first install Python and provide a trusted wheelhouse matching the destination’s Windows architecture, Python minor version and CPU/CUDA profile:

```powershell
.\SETUP_SHERLOCKED.bat -Offline -Wheelhouse 'E:\SHERLOCKED wheels'
```

For an already prepared environment, `SETUP_SHERLOCKED.bat -Offline -SkipInstall` validates setup without installing packages. Missing dependencies produce an actionable error. A source ZIP plus model ZIP alone is **not** a complete offline dependency installer.

## Verification and limits

The reused model archive was previously built and actually extracted into a new folder on the current PC. ZIP paths were checked, all **13 manifest-listed file hashes** passed before and after extraction, and the **11 original model files** remained unchanged. The MIT license and model card were confirmed present.

The corrected landing passed **91 local tests** and received actual paper-landing browser review; see [the clean-landing change record](NO_PREVIEW_CHANGE.md) and [entry verification](ENTRY_VERIFICATION.md) for the current capture and clearly labelled historical preview-enabled screenshots. Corrected source-package checksums and extraction evidence are recorded with the rebuilt `no-preview/` archive; earlier source hashes are not reused. [NOIR_VERIFICATION.md](NOIR_VERIFICATION.md) describes the earlier base-Noir verification. Same-PC checks do not establish operation on a second physical computer.

The application remains a local fictional research prototype. Its small synthetic corpus, heuristic extraction and uncalibrated no-match handling remain limitations; packaging does not improve research accuracy or provide production security controls.


The source manifest is `DISTRIBUTION_MANIFEST.json`; the model manifest is `MODEL_DISTRIBUTION_MANIFEST.json`. Both are designed to survive a combined extraction. Use the new `SHA256SUMS.txt` and `RELEASE_VERIFICATION.json` produced alongside the corrected source package; earlier files under `final/` describe the previous source build.

# Private Streamlit Community Cloud demonstration

This profile runs the existing application for trusted viewers. It keeps the desktop entrypoint, Windows launchers, dependency files and local defaults unchanged. It is a shared fictional research workspace, not a public service or an isolated workspace for each viewer.

## Deployment settings

In Streamlit Community Cloud, select:

| Setting | Value |
| --- | --- |
| Repository | `blacksheep-io/SHERLOCKED` |
| Branch | `main` |
| Main file path | `deploy/streamlit/app.py` |
| Python version, under Advanced settings | `3.12` |
| Sharing | **Only specific people can view this app** |

Keep the hosted app private and grant access only to trusted viewers. Community Cloud apps deployed from public GitHub repositories are public by default; check Sharing before distributing the URL. The built-in `demo` / `sherlocked-demo` login is deliberately public and does not replace the host's private-viewer access control. No paid API key or model credential is required for the approved public encoder.

Community Cloud selects the `requirements.txt` next to this entrypoint. It reuses the existing application pins and explicitly selects `torch==2.6.0+cpu` from the official PyTorch CPU package index. The entrypoint adds the repository root to Python's import path. Its adjacent `.streamlit/config.toml` permits the cloud server to listen on its network interface; the root desktop configuration retains its loopback binding.

## Cold start and model behavior

On a fresh cloud filesystem, the entrypoint creates the existing supported `configs/app.json` with CPU inference and online model mode. It preserves an existing settings file byte-for-byte. The regular desktop entrypoint still defaults to offline mode.

The model is not downloaded merely to display the landing page. When a semantic method is first requested, the existing encoder can download only its configured `intfloat/multilingual-e5-small` model at revision `614241f622f53c4eeff9890bdc4f31cfecc418b3`. Its approved files occupy approximately 493 MB; first inference can take longer while downloading and loading them. Later searches reuse the existing shared model and embedding caches. TF-IDF and BM25 remain explicit choices. Download or model errors remain visible; the app does not silently substitute another method.

Use CPU on Community Cloud. The normal application settings remain available to trusted viewers. The existing System Settings model action uses the current online/offline setting; do not select CUDA on this CPU deployment. Verify login, lexical retrieval and a real semantic query after deployment. Passing a local source check does not establish cloud runtime or memory compatibility.

## Shared state and temporary storage

All signed-in viewers share the server's SQLite reports, model files, saved settings, experiment results and exported files. A report import/submission or settings change can affect other viewers. Session login and appearance state do not provide tenant isolation. Use fictional information only.

Community Cloud's generated local files have no persistence guarantee. A restart, rebuild or replacement of the runtime can discard added reports, changed settings, local access hashes, downloaded models, caches, new experiments and exports. Bundled benchmark fixtures and committed historical results remain in GitHub. Download any results you need; do not use this instance as the only copy of research or report data. Durable multi-user storage and authorization require separate application work.

The source includes no personal access database, local report database, secrets or model weights. Do not upload the original development environment or its private data to deploy this profile.

## References

- [Community Cloud deployment and Python selection](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy)
- [Entrypoint, configuration and dependency file placement](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/file-organization)
- [Python dependency selection](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/app-dependencies)
- [Private viewer access](https://docs.streamlit.io/deploy/streamlit-community-cloud/share-your-app)
- [Generated file persistence limitations](https://docs.streamlit.io/develop/concepts/configuration/serving-static-files)
- [Official PyTorch CPU installation index](https://pytorch.org/get-started/previous-versions/)

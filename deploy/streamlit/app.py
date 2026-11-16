"""Private Community Cloud entrypoint; desktop defaults remain unchanged."""
from copy import deepcopy
import json
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def prepare_cloud_settings(project_root=PROJECT_ROOT):
    """Initialize cloud-only defaults once, preserving any existing settings."""
    from sherlocked.settings import DEFAULTS

    settings = deepcopy(DEFAULTS)
    settings.update(device="cpu", model_mode="online")
    path = Path(project_root) / "configs" / "app.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("x", encoding="utf-8") as stream:
            json.dump(settings, stream, indent=2)
            stream.write("\n")
    except FileExistsError:
        pass
    return path


def main():
    prepare_cloud_settings()
    from sherlocked.ui import main as run_lab

    run_lab()


if __name__ == "__main__":
    main()

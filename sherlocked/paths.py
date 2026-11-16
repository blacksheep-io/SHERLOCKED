"""Portable resource locations. Relative settings resolve against the source root."""
import json
import os
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DEFAULT_PATHS={'models':'models','cache':'cache','database':'data/sherlocked.sqlite3','dataset':'data',
               'results':'results','logs':'logs','exports':'exports','temp':'tmp'}
ENVIRONMENT={'models':'SHERLOCKED_MODEL_DIR','cache':'SHERLOCKED_CACHE_DIR','database':'SHERLOCKED_DATABASE_PATH',
             'dataset':'SHERLOCKED_DATASET_DIR','results':'SHERLOCKED_RESULTS_DIR','logs':'SHERLOCKED_LOG_DIR',
             'exports':'SHERLOCKED_EXPORT_DIR','temp':'SHERLOCKED_TEMP_DIR'}


def configured_paths():
    config=ROOT/'configs/paths.json'
    values=dict(DEFAULT_PATHS)
    if config.exists():
        supplied=json.loads(config.read_text(encoding='utf-8-sig'))
        if not isinstance(supplied,dict) or set(supplied)-set(values):
            raise ValueError('configs/paths.json must contain known resource names only')
        values.update(supplied)
    for name,variable in ENVIRONMENT.items():
        if variable in os.environ: values[name]=os.environ[variable]
    if any(not isinstance(value,str) or not value.strip() for value in values.values()):
        raise ValueError('Resource paths must be nonempty strings')
    return values


def resource_path(name):
    values=configured_paths()
    if name not in values: raise ValueError(f'Unknown resource: {name}')
    value=Path(os.path.expandvars(values[name])).expanduser()
    return (value if value.is_absolute() else ROOT/value).resolve()


def ensure_directories():
    for name in DEFAULT_PATHS:
        path=resource_path(name)
        (path.parent if name=='database' else path).mkdir(parents=True,exist_ok=True)


def path_report():
    return {name:str(resource_path(name)) for name in DEFAULT_PATHS}


def portable_path(value):
    path=Path(value).resolve()
    try: return str(path.relative_to(ROOT)).replace('\\','/')
    except ValueError: return str(path)

"""Portable health checks; no downloads or model inference."""
import argparse
import hashlib
import importlib.metadata
import importlib.util
import json
import platform
import shutil
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
DEPENDENCIES={'streamlit':'streamlit','scikit-learn':'sklearn','plotly':'plotly',
              'sentence-transformers':'sentence_transformers','transformers':'transformers',
              'sentencepiece':'sentencepiece','torch':'torch'}


def dependency_state(verify_imports=False):
    versions,errors,pins={},{},{}
    errors=[]
    for line in (ROOT/'requirements.txt').read_text(encoding='utf-8-sig').splitlines():
        if '==' in line and not line.strip().startswith('#'):
            name,version=line.strip().split('==',1)
            pins[name.lower().replace('_','-')]=version
    for name,module in DEPENDENCIES.items():
        try:
            version=importlib.metadata.version(name)
            versions[name]=version
            if pins.get(name) and version.split('+')[0]!=pins[name]:
                errors.append(f'{name} {version} differs from supported {pins[name]}; run SETUP_SHERLOCKED.bat')
            if importlib.util.find_spec(module) is None:
                errors.append(f'{name} is installed incompletely; run SETUP_SHERLOCKED.bat')
            if verify_imports:
                __import__(module)
        except Exception as exc:
            versions[name]=None
            errors.append(f'{name}: {type(exc).__name__}: {exc}; run SETUP_SHERLOCKED.bat')
    return versions,errors


def inspect(initialize=False,lightweight=False,verify_imports=False):
    details={'python':platform.python_version(),'platform':platform.platform(),'errors':[],'warnings':[]}
    if not (3,10)<=sys.version_info[:2]<=(3,12):
        details['errors'].append('Supported Python: 3.10-3.12; Python 3.12 is recommended')
    details['dependencies'],errors=dependency_state(verify_imports)
    details['errors'].extend(errors)
    try:
        from sherlocked.paths import resource_path,ensure_directories,path_report
        if initialize:
            ensure_directories()
        details['resources']=path_report()
        directory=resource_path('dataset')
        dataset,manifest=directory/'reports.jsonl',directory/'manifest.json'
        if initialize and not dataset.exists() and not manifest.exists():
            directory.mkdir(parents=True,exist_ok=True)
            shipped=ROOT/'data'
            if (shipped/'reports.jsonl').exists() and directory.resolve()!=shipped.resolve():
                shutil.copy2(shipped/'reports.jsonl',dataset)
                shutil.copy2(shipped/'manifest.json',manifest)
            else:
                from sherlocked.dataset import write_dataset
                write_dataset(directory)
        payload=dataset.read_bytes()
        records=[json.loads(line) for line in payload.decode('utf-8-sig').splitlines() if line.strip()]
        if not records: raise ValueError('Dataset is empty')
        ids,families=set(),{}
        for row in records:
            if row['report_id'] in ids: raise ValueError('Duplicate dataset report ID')
            ids.add(row['report_id'])
            if row.get('fictional') is not True: raise ValueError('Dataset must be explicitly fictional')
            if row.get('family_id'): families.setdefault(row['family_id'],set()).add(row.get('split'))
        if any(len(splits)>1 for splits in families.values()):
            raise ValueError('Scenario family crosses partitions')
        expected=json.loads(manifest.read_text(encoding='utf-8-sig'))['sha256']
        digest=hashlib.sha256(payload).hexdigest()
        details['dataset']={'path':str(dataset),'count':len(records),'sha256':digest,'manifest_valid':digest==expected}
        if digest!=expected: details['errors'].append('Dataset manifest mismatch; existing data was preserved')
        database=resource_path('database')
        details['database']={'path':str(database),'exists':database.exists()}
        if initialize and digest==expected:
            from sherlocked.storage import Store
            store=Store(database)
            store.initialize(records)
            details['database']=store.health()
        elif not database.exists():
            details['errors'].append('Database is absent; run SETUP_SHERLOCKED.bat')
    except Exception as exc:
        details['errors'].append(f'Dataset/database/resources: {type(exc).__name__}: {exc}')
    details['acceleration']={'inspected':False,'note':'Lightweight startup avoids PyTorch initialization; active model device is reported in the application.'}
    if not lightweight:
        try:
            import torch
            available=torch.cuda.is_available()
            details['acceleration']={'inspected':True,'cuda_available':available,'torch_cuda':torch.version.cuda,
                                     'gpu':torch.cuda.get_device_name(0) if available else None}
        except Exception as exc:
            details['errors'].append(f'PyTorch load failed: {type(exc).__name__}: {exc}. Check wheel/Windows runtime compatibility and run SETUP_SHERLOCKED.bat.')
    try:
        from sherlocked.semantic import SemanticEncoder
        details['model']=SemanticEncoder(device='auto').status()
        if not details['model'].get('available'):
            details['warnings'].append('Model assets are incomplete. Use SETUP_SHERLOCKED.bat -DownloadModel or transfer the documented model folder for offline inference. Explicit TF-IDF/BM25 remain available.')
    except Exception as exc:
        details['errors'].append(f'Model configuration: {type(exc).__name__}: {exc}')
    details['model_note']='Health checks do not download models or run inference.'
    return details


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--initialize',action='store_true')
    parser.add_argument('--lightweight',action='store_true')
    parser.add_argument('--verify-imports',action='store_true')
    parser.add_argument('--dependencies-only',action='store_true')
    args=parser.parse_args()
    if args.dependencies_only:
        versions,errors=dependency_state(args.verify_imports)
        result={'dependencies':versions,'errors':errors}
    else:
        result=inspect(args.initialize,args.lightweight,args.verify_imports)
    print(json.dumps(result,ensure_ascii=False,indent=2))
    raise SystemExit(bool(result['errors']))


"""Build deterministic source or separately transferable pinned-model ZIPs.

No dependency environment, user database, local settings or cache is distributed.
Existing ZIPs are never replaced; choose a fresh --output path for another build.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
from pathlib import Path
import zipfile

ROOT=Path(__file__).resolve().parents[1]
PREFIX='SHERLOCKED/'
FIXED_DATE=(2026,1,1,0,0,0)
ROOT_FILES=['app.py','START_SHERLOCKED.bat','SETUP_SHERLOCKED.bat','start.ps1','setup.ps1',
            'README.md','requirements.txt','requirements-lock.txt','requirements-cpu-lock.txt',
            'requirements-cuda-lock.txt','.env.example','.gitignore','LICENSE',
            'TECHNICAL_ARCHITECTURE.md','AI_PIPELINE.md','DATASET_DOCUMENTATION.md',
            'EXPERIMENTS_AND_EVALUATION.md','USER_GUIDE.md','DEVELOPMENT_GUIDE.md','LIMITATIONS_AND_ETHICS.md']
DATA_FILES=['reports.jsonl','manifest.json','qrels.jsonl','challenge_reports.jsonl','challenge_manifest.json','challenge_qrels.jsonl']
EXCLUDED={'.venv','__pycache__','.cache','cache','.git','backups','logs','exports','tmp','temp','dist',
          'proposal_work','node_modules','.pytest_cache','.mypy_cache','.ruff_cache','.tox','private','secrets','credentials'}
PRIVATE_FILES={'.env','secrets.toml','credentials.toml','credentials.json','tokens.json','token.json'}


def _excluded_path(relative):
    """Generated work, private material and development caches never ship."""
    return bool({part.casefold() for part in relative.parts}&EXCLUDED) or relative.name.casefold() in PRIVATE_FILES or relative.name.casefold().startswith('.env.')

MODEL_FILES=['config.json','modules.json','sentence_bert_config.json','model.safetensors',
             'tokenizer.json','tokenizer_config.json','special_tokens_map.json','sentencepiece.bpe.model',
             '1_Pooling/config.json','README.md','sherlocked_model.json']
MIT='''The MIT License (MIT)

Copyright (c) Microsoft Corporation

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:
The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

Upstream source: https://github.com/microsoft/unilm/blob/master/LICENSE
Model card: https://huggingface.co/intfloat/multilingual-e5-small
'''


def _check_file(path,root):
    if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
        raise ValueError(f'Distribution source must remain inside project: {path}')
    return path.is_file()


def _source_entries(root,include_results):
    required=['app.py','START_SHERLOCKED.bat','SETUP_SHERLOCKED.bat','README.md','requirements.txt',
              'configs/model.json','configs/paths.example.json']+[f'data/{name}' for name in DATA_FILES]
    for name in required:
        if not _check_file(root/name,root): raise FileNotFoundError(f'Required distribution file is missing: {name}')
    entries={}
    for name in ROOT_FILES+['assets/branding/README.md','configs/model.json','configs/paths.example.json','.streamlit/config.toml']:
        path=root/name
        if _check_file(path,root): entries[name]=path
    for directory,suffixes in [('sherlocked',{'.py'}),('scripts',{'.py','.ps1'}),('tests',{'.py'}),('docs',{'.md','.svg','.png','.jpg'}),('assets',{'.css','.svg','.json','.png','.jpg','.woff2'})]:
        for path in sorted((root/directory).rglob('*')):
            relative=path.relative_to(root)
            if _excluded_path(relative): continue
            if path.suffix.lower() in suffixes and _check_file(path,root): entries[relative.as_posix()]=path
    for name in DATA_FILES: entries[f'data/{name}']=root/'data'/name
    if include_results:
        # Existing absolute paths are historical provenance, never rewritten.
        for path in sorted((root/'results').rglob('*')):
            if path.suffix.lower() in {'.json','.csv'} and not _excluded_path(path.relative_to(root)):
                if _check_file(path,root): entries[path.relative_to(root).as_posix()]=path
        if _check_file(root/'configs/frozen_research.json',root): entries['configs/frozen_research.json']=root/'configs/frozen_research.json'
    return entries


def _model_entries(root):
    config=json.loads((root/'configs/model.json').read_text(encoding='utf-8-sig'))
    if config.get('model_id')!='intfloat/multilingual-e5-small' or not re.fullmatch(r'[0-9a-f]{40}',config.get('revision','')):
        raise ValueError('Model redistribution requires the audited model ID and an immutable 40-character revision')
    local=Path(config['local_directory'])
    if local.is_absolute() or '..' in local.parts: raise ValueError('Model local_directory must be a safe project-relative path')
    # Root override keeps fixture tests isolated; normal packaging honors configured model root.
    if root.resolve()==ROOT.resolve():
        import sys
        sys.path.insert(0,str(root))
        from sherlocked.paths import resource_path
        directory=resource_path('models')/local.name
    else: directory=root/local
    marker=directory/'sherlocked_model.json'
    if not marker.exists(): raise FileNotFoundError('Pinned model setup marker is missing; prepare model assets first')
    saved=json.loads(marker.read_text(encoding='utf-8-sig'))
    if any(saved.get(name)!=config.get(name) for name in ['model_id','revision']):
        raise ValueError('Local model marker does not match the configured pinned model')
    if config.get('license')!='MIT': raise ValueError('Only the audited MIT model can be redistributed by this builder')
    required=MODEL_FILES
    for name in required:
        if not (directory/name).is_file(): raise FileNotFoundError(f'Required model asset is missing: {name}')
    entries={}
    for name in MODEL_FILES:
        path=directory/name
        if path.is_symlink() or not path.resolve().is_relative_to(directory.resolve()):
            raise ValueError('Model assets cannot reference files outside their model directory')
        if path.is_file(): entries[f'models/{local.name}/{name}']=path
    entries[f'models/{local.name}/LICENSE-MIT.txt']=MIT.encode('utf-8')
    entries['MODEL_TRANSFER_README.md']=(
        '# Pinned SHERLOCKED model assets\n\n'
        f"Model: {config['model_id']}\nRevision: {config['revision']}\nLicense: MIT\n\n"
        'Extract this ZIP and the source ZIP into the same parent directory. '
        'The SHERLOCKED/models directory will merge. For a custom model directory, '
        'copy the model subfolder into your configured models root. Model weights '
        'are not a Python environment: first install dependencies on the destination. '
        'Once dependencies and these assets are present, inference does not require network access. '
        'Do not distribute private Hugging Face caches or credentials.\n').encode('utf-8')
    return entries,config


def _digest(value):
    if isinstance(value,bytes): return len(value),hashlib.sha256(value).hexdigest()
    digest=hashlib.sha256();size=0
    with value.open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):
            size+=len(block);digest.update(block)
    return size,digest.hexdigest()


def build_distribution(output=None,include_results=False,model_assets=False,root=ROOT):
    root=Path(root).resolve()
    output=Path(output).resolve() if output is not None else root/'dist'/('SHERLOCKED-model-assets.zip' if model_assets else 'SHERLOCKED-portable.zip')
    if output.exists(): raise FileExistsError(f'Existing distribution preserved: {output}. Choose a new --output path.')
    if model_assets and include_results: raise ValueError('--include-results applies to source packages, not model packages')
    model=None
    if model_assets: entries,model=_model_entries(root)
    else: entries=_source_entries(root,include_results)
    files=[]
    for name,value in sorted(entries.items()):
        size,digest=_digest(value)
        files.append(dict(path=PREFIX+name,bytes=size,sha256=digest))
    manifest=dict(schema_version=1,kind='model-assets' if model_assets else 'source',
                  archive_prefix=PREFIX,requires_internet_for_first_dependency_setup=True,
                  dependencies_included=False,model_assets_included=model_assets,
                  saved_experiment_results_included=include_results,files=files)
    if model: manifest['model']={key:model[key] for key in ['model_id','revision','license','dimensions']}
    # Both archives merge into SHERLOCKED/. Their manifests must remain
    # independently verifiable after extracting the pair into the same folder.
    manifest_name='MODEL_DISTRIBUTION_MANIFEST.json' if model_assets else 'DISTRIBUTION_MANIFEST.json'
    entries[manifest_name]=json.dumps(manifest,ensure_ascii=False,indent=2,sort_keys=True).encode('utf-8')
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open('xb') as stream:
        try:
            with zipfile.ZipFile(stream,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
                for name,value in sorted(entries.items()):
                    info=zipfile.ZipInfo(PREFIX+name,FIXED_DATE)
                    info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644<<16
                    with archive.open(info,'w',force_zip64=True) as destination:
                        if isinstance(value,bytes): destination.write(value)
                        else:
                            with value.open('rb') as source:
                                for block in iter(lambda:source.read(1024*1024),b''): destination.write(block)
        except Exception:
            # The exclusive output is this invocation's incomplete file only.
            stream.close();output.unlink();raise
    size,digest=_digest(output)
    return dict(path=str(output),bytes=size,sha256=digest,file_count=len(entries),
                kind=manifest['kind'],requires_internet_for_first_dependency_setup=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path)
    parser.add_argument('--include-results',action='store_true')
    parser.add_argument('--model-assets',action='store_true')
    args=parser.parse_args()
    print(json.dumps(build_distribution(args.output,args.include_results,args.model_assets),indent=2))


if __name__=='__main__': main()

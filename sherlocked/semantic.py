"""Portable pinned local encoder, persistent reuse and explicit failure behavior."""
from collections import OrderedDict
import hashlib
import json
import logging
import os
import re
import threading
import uuid
from pathlib import Path
import numpy as np
from .paths import ROOT, resource_path

CONFIG = json.loads((ROOT/'configs/model.json').read_text(encoding='utf-8'))
logger = logging.getLogger(__name__)
REQUIRED_ASSETS = ('config.json','modules.json','sentence_bert_config.json','model.safetensors',
                   'tokenizer.json','tokenizer_config.json','special_tokens_map.json',
                   'sentencepiece.bpe.model','1_Pooling/config.json')
CACHE_FORMAT = 'normalized-mean-v2'
_SHARED = {}
_SHARED_LOCK = threading.RLock()
_MODEL_HANDLES = {}
_MODEL_LOCK = threading.RLock()


class SemanticUnavailable(RuntimeError):
    """The requested semantic method failed; no lexical substitution occurred."""


class SemanticEncoder:
    def __init__(self, device='auto', allow_download=False, model_id=None, revision=None):
        if device not in ('auto','cpu','cuda'):
            raise ValueError('Device must be auto, cpu or cuda')
        self.config = dict(CONFIG)
        if model_id and model_id != CONFIG['model_id']:
            raise ValueError('Only the audited multilingual-e5-small configuration is supported. New models require explicit pooling, prefix, dimension and license review.')
        if revision and not re.fullmatch(r'[0-9a-f]{40}',revision):
            raise ValueError('Use an immutable 40-character model revision')
        if model_id:
            self.config['model_id']=model_id
        if revision:
            self.config['revision']=revision
        self.requested_device=device
        self.device=None
        self.allow_download=bool(allow_download)
        self.model=None
        self.error=None
        self.fallback_reason=None
        self._lock=threading.RLock()
        self.cache_directory=resource_path('cache')/'embeddings'
        self.directory=resource_path('models')/'multilingual-e5-small'
        self._memory=OrderedDict()
        self._memory_limit=2048
        self.cache_stats={'memory_hits':0,'disk_hits':0,'encoded_texts':0,'invalid_disk_entries':0}

    @property
    def metadata(self):
        return {**self.config,'device':self.device or self.requested_device,
                'requested_device':self.requested_device,'active_device':self.device,
                'fallback_reason':self.fallback_reason,'local_directory':str(self.directory),
                'cache_directory':str(self.cache_directory),'loaded':self.model is not None,
                'cache_format':CACHE_FORMAT}

    def status(self):
        missing=[name for name in REQUIRED_ASSETS if not (self.directory/name).is_file()]
        marker=self.directory/'sherlocked_model.json'
        valid=False
        if marker.is_file():
            try:
                saved=json.loads(marker.read_text(encoding='utf-8'))
                valid=all(saved.get(k)==self.config[k] for k in ('model_id','revision'))
            except (OSError,ValueError):
                pass
        return dict(available=valid and not missing,local_model=str(self.directory),
                    device=self.device or self.requested_device,requested_device=self.requested_device,
                    active_device=self.device,loaded=self.model is not None,error=self.error,
                    fallback_reason=self.fallback_reason,missing_assets=missing,revision_marker_valid=valid,
                    download_allowed=self.allow_download,cache_stats=dict(self.cache_stats),
                    **{k:self.config[k] for k in ('model_id','revision','dimensions')})

    def download(self):
        # A complete portable directory needs no Hub cache and no network check.
        if self.status()['available']:
            return self
        try:
            os.environ.setdefault('HF_HUB_DISABLE_XET','1')
            from huggingface_hub import snapshot_download
            self.directory.mkdir(parents=True,exist_ok=True)
            snapshot_download(self.config['model_id'],revision=self.config['revision'],
                              local_dir=str(self.directory),allow_patterns=[*REQUIRED_ASSETS,'README.md'])
            missing=[name for name in REQUIRED_ASSETS if not (self.directory/name).is_file()]
            if missing:
                raise OSError('Downloaded model is incomplete: '+', '.join(missing))
            marker=self.directory/'sherlocked_model.json'
            temporary=marker.with_suffix(f'.{uuid.uuid4().hex}.tmp')
            temporary.write_text(json.dumps(self.config,indent=2),encoding='utf-8')
            temporary.replace(marker)
        except Exception as exc:
            self.error=str(exc)
            raise SemanticUnavailable(f'Model download failed: {exc}. TF-IDF and BM25 remain available explicitly.') from exc
        return self

    def load(self):
        with self._lock:
            if self.model is not None:
                return self
            if not self.status()['available']:
                if self.allow_download:
                    self.download()
                else:
                    missing=self.status().get('missing_assets',[])
                    self.error=('Multilingual model is not initialized or is incomplete. '
                                'Run scripts/setup_model.py online, or transfer the complete approved model directory. '
                                'Offline inference cannot download assets. '+('Missing: '+', '.join(missing) if missing else 'Revision marker does not match.'))
                    raise SemanticUnavailable(self.error)
            try:
                import torch
                from sentence_transformers import SentenceTransformer
                if self.requested_device=='cuda' and not torch.cuda.is_available():
                    raise SemanticUnavailable('CUDA was requested but PyTorch CUDA is unavailable. Select CPU/auto or install the documented optional CUDA wheel.')
                target=('cuda' if torch.cuda.is_available() else 'cpu') if self.requested_device=='auto' else self.requested_device
                try:
                    self._initialize(SentenceTransformer,torch,target)
                except Exception as cuda_error:
                    if self.requested_device!='auto' or target!='cuda':
                        raise
                    self.fallback_reason=f'CUDA initialization failed; the same multilingual encoder is running on CPU: {cuda_error}'
                    logger.warning(self.fallback_reason)
                    self._initialize(SentenceTransformer,torch,'cpu')
                self.error=None
            except Exception as exc:
                self.error=str(exc)
                logger.exception('Semantic model load failed')
                raise SemanticUnavailable(f'Cannot load multilingual encoder: {exc}. Choose an explicit keyword method while resolving setup.') from exc
            return self

    def _initialize(self,factory,torch,device):
        if device=='cpu':
            torch.set_num_threads(min(6,os.cpu_count() or 1))
        key=(self.config['model_id'],self.config['revision'],str(self.directory.resolve()),device,self.config['max_length'])
        with _MODEL_LOCK:
            candidate=_MODEL_HANDLES.get(key)
            if candidate is None:
                candidate=factory(str(self.directory),device=device,local_files_only=True,
                                  trust_remote_code=False,model_kwargs={'use_safetensors':True})
                candidate.max_seq_length=self.config['max_length']
                candidate.eval()
                _MODEL_HANDLES[key]=candidate
        self.model=candidate
        self.device=device

    def _identity(self,text,role):
        payload=[CACHE_FORMAT,self.config['model_id'],self.config['revision'],self.config['dimensions'],
                 self.config['max_length'],role,self.config[f'{role}_prefix'],text]
        return hashlib.sha256(json.dumps(payload,ensure_ascii=False).encode('utf-8')).hexdigest()

    def _remember(self,key,value):
        self._memory[key]=value
        self._memory.move_to_end(key)
        while len(self._memory)>self._memory_limit:
            self._memory.popitem(last=False)

    def _infer(self,texts):
        try:
            with _MODEL_LOCK:
                return self.model.encode(texts,batch_size=self.config['batch_size'],
                                         normalize_embeddings=True,convert_to_numpy=True,show_progress_bar=False)
        except Exception as cuda_error:
            if self.requested_device!='auto' or self.device!='cuda':
                raise
            self.fallback_reason=f'CUDA inference failed; retrying the same multilingual model on CPU: {cuda_error}'
            logger.warning(self.fallback_reason)
            import torch
            from sentence_transformers import SentenceTransformer
            self.model=None
            self._initialize(SentenceTransformer,torch,'cpu')
            with _MODEL_LOCK:
                return self.model.encode(texts,batch_size=self.config['batch_size'],
                                         normalize_embeddings=True,convert_to_numpy=True,show_progress_bar=False)

    def encode(self,texts,role='passage'):
        if role not in ('query','passage'):
            raise ValueError('role must be query or passage')
        if not texts:
            return np.empty((0,self.config['dimensions']),dtype=np.float32)
        if any(not isinstance(text,str) for text in texts):
            raise ValueError('Semantic inputs must be strings')
        self.load()
        with self._lock:
            self.cache_directory.mkdir(parents=True,exist_ok=True)
            keys=[self._identity(text,role) for text in texts]
            vectors={}
            missing={}
            for key,text in zip(keys,texts):
                if key in vectors or key in missing:
                    continue
                if key in self._memory:
                    vectors[key]=self._memory[key]
                    self._memory.move_to_end(key)
                    self.cache_stats['memory_hits']+=1
                    continue
                path=self.cache_directory/f'{key}.npy'
                if path.is_file():
                    try:
                        value=np.load(path,allow_pickle=False)
                        if value.shape==(self.config['dimensions'],) and np.isfinite(value).all() and np.isclose(np.linalg.norm(value),1,atol=1e-4):
                            vectors[key]=value.astype(np.float32)
                            self._remember(key,vectors[key])
                            self.cache_stats['disk_hits']+=1
                            continue
                    except (OSError,ValueError):
                        pass
                    self.cache_stats['invalid_disk_entries']+=1
                missing[key]=text
            if missing:
                try:
                    encoded=np.asarray(self._infer([self.config[f'{role}_prefix']+text for text in missing.values()]))
                    if (encoded.shape!=(len(missing),self.config['dimensions']) or not np.isfinite(encoded).all()
                            or not np.allclose(np.linalg.norm(encoded,axis=1),1,atol=1e-4)):
                        raise ValueError('Encoder returned invalid/non-normalized vectors')
                except Exception as exc:
                    self.error=str(exc)
                    raise SemanticUnavailable(f'Multilingual inference failed: {exc}. No alternate retrieval pipeline was substituted.') from exc
                self.cache_stats['encoded_texts']+=len(missing)
                for key,value in zip(missing,encoded):
                    value=value.astype(np.float32)
                    vectors[key]=value
                    self._remember(key,value)
                    path=self.cache_directory/f'{key}.npy'
                    temporary=path.with_suffix(f'.{os.getpid()}.{uuid.uuid4().hex}.tmp')
                    with temporary.open('wb') as stream:
                        np.save(stream,value,allow_pickle=False)
                    os.replace(temporary,path)
                self.error=None
            return np.asarray([vectors[key] for key in keys],dtype=np.float32)

    def clear_memory_cache(self):
        with self._lock:
            self._memory.clear()

    def truncation_info(self,text,role='passage'):
        if role not in ('query','passage'):
            raise ValueError('role must be query or passage')
        self.load()
        prefix=self.config[f'{role}_prefix']
        tokenizer=self.model.tokenizer
        all_tokens=tokenizer(prefix+text,truncation=False,return_attention_mask=False,verbose=False)
        token_count=len(all_tokens['input_ids'])
        retained_end=None
        if tokenizer.is_fast:
            clipped=tokenizer(prefix+text,truncation=True,max_length=self.config['max_length'],
                              return_offsets_mapping=True,return_attention_mask=False)
            retained_end=max(0,min(len(text),max((end for _,end in clipped['offset_mapping']),default=0)-len(prefix)))
        return dict(token_count=token_count,max_tokens=self.config['max_length'],
                    truncated=token_count>self.config['max_length'],retained_source_character_end=retained_end,
                    role=role,prefix=prefix,
                    note='Original source is preserved. Sentence evidence is illustrative and may include text beyond the report-level encoder window.')

    def scores(self,query,candidates):
        return (self.encode(candidates,'passage') @ self.encode([query],'query')[0]).astype(float)

    def passage_evidence(self,query,candidate):
        def passages(text):
            return [(m.group(),m.start(),m.end()) for m in re.finditer(r'[^.!?।\n]+[.!?।]?',text) if m.group().strip()]
        a,b=passages(query),passages(candidate)
        if not a or not b:
            return None
        scores=self.encode([t for t,_,_ in a],'query') @ self.encode([t for t,_,_ in b],'passage').T
        i,j=np.unravel_index(np.argmax(scores),scores.shape)
        return dict(query_text=a[i][0],query_span=list(a[i][1:]),candidate_text=b[j][0],candidate_span=list(b[j][1:]),
                    cosine=float(scores[i,j]),limitation='Most similar source sentence pair; illustrative evidence, not causal attribution of the report score.')


def get_shared_encoder(device='auto',allow_download=False):
    """Share a lazy encoder across corpus/weight changes, independent of Streamlit."""
    key=(CONFIG['model_id'],CONFIG['revision'],device,bool(allow_download),
         str(resource_path('models').resolve()),str(resource_path('cache').resolve()))
    with _SHARED_LOCK:
        if key not in _SHARED:
            _SHARED[key]=SemanticEncoder(device=device,allow_download=allow_download)
        return _SHARED[key]


def get_model(device='auto',allow_download=False):
    return get_shared_encoder(device,allow_download).load()


def setup_model(device='auto',offline=False):
    encoder=SemanticEncoder(device=device,allow_download=not offline).load()
    vectors=encoder.encode(['A bicycle is missing.','একটি সাইকেল হারিয়ে গেছে।'],'query')
    return {**encoder.metadata,'setup_mode':'offline' if offline else 'online',
            'smoke_shape':list(vectors.shape),'cross_language_cosine':float(vectors[0] @ vectors[1]),'status':'ready'}

"""Uncached real device verification. Preserves all historical research results."""
import json
import sys
import time
from datetime import datetime,timezone
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
from sherlocked.semantic import SemanticEncoder
from sherlocked.paths import resource_path


def main():
    import torch
    observations=[]
    texts=['query: A bicycle is missing from the square.',
           'passage: চত্বর থেকে একটি সাইকেল হারিয়ে গেছে।',
           'passage: bicycle হারিয়ে গেছে square থেকে।',
           'passage: A telescope observed distant stars in the night sky.']
    for device in ['cpu']+(['cuda'] if torch.cuda.is_available() else []):
        encoder=SemanticEncoder(device=device).load()
        start=time.perf_counter()
        vectors=encoder.model.encode(texts,normalize_embeddings=True,convert_to_numpy=True,show_progress_bar=False)
        if device=='cuda':
            torch.cuda.synchronize()
        cosine=(vectors[1:] @ vectors[0]).tolist()
        assert vectors.shape==(4,384) and np.isfinite(vectors).all()
        assert np.allclose(np.linalg.norm(vectors,axis=1),1,atol=1e-5)
        assert cosine[0]>cosine[2],'Related Bangla fixture should outrank unrelated English fixture'
        observations.append(dict(device=device,elapsed_ms=(time.perf_counter()-start)*1000,
                                 shape=list(vectors.shape),cosines=dict(bangla=cosine[0],mixed=cosine[1],unrelated=cosine[2]),
                                 metadata=encoder.metadata,status='passed'))
        del encoder
    now=datetime.now(timezone.utc)
    result=dict(created_at_utc=now.isoformat(),torch=torch.__version__,cuda_available=torch.cuda.is_available(),
                gpu=torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
                limitation='Handcrafted device smoke checks, not a new research metric; embedding cache bypassed.',checks=observations)
    directory=resource_path('logs')
    directory.mkdir(parents=True,exist_ok=True)
    path=directory/(now.strftime('semantic-devices-%Y%m%dT%H%M%S%f')+'.json')
    path.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))
    print('Verification log:',path)


if __name__=='__main__':
    main()

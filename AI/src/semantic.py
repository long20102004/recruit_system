"""One cached BERTScorer per process; no lexical fallback in semantic mode."""
from __future__ import annotations
import os
import threading
from functools import lru_cache
import numpy as np

LOCK = threading.RLock()
DEFAULT_MODEL = 'bert-base-multilingual-cased'

@lru_cache(maxsize=1)
def get_scorer(model_type: str, device: str):
    import torch
    from bert_score import BERTScorer
    torch.set_num_threads(max(1, int(os.getenv('HIRELENS_THREADS', '2'))))
    return BERTScorer(model_type=model_type, lang='vi', device=device,
        batch_size=int(os.getenv('HIRELENS_BATCH_SIZE', '4')), nthreads=2,
        rescale_with_baseline=False)

def score_pairs(answers, references, model_type=DEFAULT_MODEL, batch_size=4, device=None):
    if len(answers) != len(references): raise ValueError('answer/reference counts differ')
    if not answers: return np.array([]), np.array([]), np.array([])
    selected_device = device or os.getenv('HIRELENS_DEVICE', 'cpu')
    with LOCK:
        scorer = get_scorer(model_type, selected_device)
        values = scorer.score(answers, references, batch_size=batch_size)
        return tuple(value.detach().cpu().numpy() for value in values)

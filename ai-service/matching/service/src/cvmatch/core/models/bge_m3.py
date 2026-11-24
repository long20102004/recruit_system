"""BGE-M3 nap MOT lan moi tien trinh (thiet ke 04 A10, 05 B7, 07 muc 2 + RR2).

Cai bang `transformers` truc tiep (khong can FlagEmbedding) de lay duoc ca hai dau ra tu mot model:

- `encode`: dense = vector CLS cua lop cuoi, chuan L2 (cach BGE-M3 tao dense);
  sparse = relu(sparse_linear(hidden)) theo tung token, gop max theo token (lexical weights),
  bo token dac biet. `sparse_linear.pt` tai tu cung repo, cung revision.
- `token_embeddings`: hidden state cua `layer` (24 = lop cuoi), bo <s>, </s>, chuan L2 tung token,
  kem offset ky tu - day la dau vao BERTScore.

Ghim `revision` (commit `5617a9f61b`) de tai lap. Van ban dai hon `max_len` o `encode`: chia theo
doan (xuong dong), trung binh vector cac phan roi chuan hoa lai (A10).
"""

from __future__ import annotations

import logging
import threading
from functools import lru_cache

import numpy as np

from cvmatch.core.models.base import EncodeResult, TokenEmb, l2_normalize

log = logging.getLogger(__name__)
_LOCK = threading.Lock()


class BgeM3:
    dim = 1024

    def __init__(self, model_id: str = "BAAI/bge-m3", revision: str = "5617a9f61b",
                 device: str = "cuda", dtype: str = "fp32", batch_size: int = 16, max_len: int = 8192,
                 key: str | None = None):
        import torch
        from huggingface_hub import hf_hub_download
        from transformers import AutoModel, AutoTokenizer

        if device == "cuda" and not torch.cuda.is_available():
            log.warning("CUDA khong co, BgeM3 chay tren CPU (cham)")
            device = "cpu"
        self.torch = torch
        self.device = device
        self.model_id, self.revision = model_id, revision
        self.batch_size, self.max_len = batch_size, max_len
        self._key = key or f"{model_id.split('/')[-1]}@{revision}"
        self.tokenizer = AutoTokenizer.from_pretrained(model_id, revision=revision)
        tdtype = torch.float16 if (dtype == "fp16" and device == "cuda") else torch.float32
        self.model = AutoModel.from_pretrained(model_id, revision=revision, dtype=tdtype).to(device).eval()
        self.sparse_linear = torch.nn.Linear(self.model.config.hidden_size, 1)
        state = torch.load(hf_hub_download(model_id, "sparse_linear.pt", revision=revision), map_location="cpu")
        self.sparse_linear.load_state_dict(state)
        self.sparse_linear = self.sparse_linear.to(device=device, dtype=tdtype).eval().requires_grad_(False)
        self._special_ids = set(self.tokenizer.all_special_ids)

    def key(self) -> str:
        return self._key

    # ----------------------------------------------------------------- tien ich

    def _batches(self, texts: list[str], batch_size: int):
        """Sap theo do dai de do ton padding; tra ve (vi tri goc, lo van ban)."""
        order = sorted(range(len(texts)), key=lambda i: len(texts[i]))
        for s in range(0, len(order), batch_size):
            idx = order[s:s + batch_size]
            yield idx, [texts[i] for i in idx]

    def _forward(self, batch: list[str], max_len: int, *, hidden_states: bool, offsets: bool = False):
        enc = self.tokenizer(batch, padding=True, truncation=True, max_length=max_len,
                             return_tensors="pt", return_offsets_mapping=offsets)
        offs = enc.pop("offset_mapping", None)
        enc = {k: v.to(self.device) for k, v in enc.items()}
        with self.torch.inference_mode():
            out = self.model(**enc, output_hidden_states=hidden_states, return_dict=True)
        return enc, out, offs

    def _run_with_oom_retry(self, fn, texts, batch_size):
        bs = batch_size
        while True:
            try:
                return fn(texts, bs)
            except self.torch.cuda.OutOfMemoryError:
                if bs == 1:
                    raise
                bs = max(1, bs // 2)
                log.warning("GPU het bo nho, giam batch xuong %d", bs)
                self.torch.cuda.empty_cache()

    # ----------------------------------------------------------------- dense + sparse

    def _chunks(self, text: str) -> list[str]:
        """Chia van ban dai theo doan sao cho moi phan <= max_len token."""
        if len(self.tokenizer(text, add_special_tokens=True)["input_ids"]) <= self.max_len:
            return [text]
        chunks, cur = [], ""
        for para in text.split("\n"):
            cand = f"{cur}\n{para}" if cur else para
            if cur and len(self.tokenizer(cand)["input_ids"]) > self.max_len:
                chunks.append(cur)
                cur = para
            else:
                cur = cand
        if cur:
            chunks.append(cur)
        return chunks

    def _encode_raw(self, texts: list[str], batch_size: int) -> EncodeResult:
        dense = np.zeros((len(texts), self.dim), dtype=np.float32)
        sparse: list[dict[str, float]] = [{} for _ in texts]
        for idx, batch in self._batches(texts, batch_size):
            enc, out, _ = self._forward(batch, self.max_len, hidden_states=False)
            last = out.last_hidden_state
            with self.torch.inference_mode():
                cls = self.torch.nn.functional.normalize(last[:, 0].float(), dim=-1).cpu().numpy()
                w = self.torch.relu(self.sparse_linear(last)).squeeze(-1).float().cpu().numpy()
            ids = enc["input_ids"].cpu().numpy()
            mask = enc["attention_mask"].cpu().numpy()
            for row, i in enumerate(idx):
                dense[i] = cls[row]
                weights: dict[str, float] = {}
                for tid, wt, mk in zip(ids[row], w[row], mask[row]):
                    if not mk or tid in self._special_ids or wt <= 0:
                        continue
                    tok = self.tokenizer.convert_ids_to_tokens(int(tid)).replace("▁", "")
                    if tok and wt > weights.get(tok, 0.0):
                        weights[tok] = round(float(wt), 4)
                sparse[i] = weights
        return EncodeResult(dense=dense, sparse=sparse)

    def encode(self, texts: list[str], batch_size: int | None = None) -> EncodeResult:
        bs = batch_size or self.batch_size
        pieces, owner = [], []
        for i, t in enumerate(texts):
            for c in self._chunks(t or ""):
                pieces.append(c)
                owner.append(i)
        with _LOCK:
            raw = self._run_with_oom_retry(self._encode_raw, pieces, bs)
        if len(pieces) == len(texts):
            return raw
        dense = np.zeros((len(texts), self.dim), dtype=np.float32)
        sparse: list[dict[str, float]] = [{} for _ in texts]
        for p, i in enumerate(owner):
            dense[i] += raw.dense[p]
            for k, v in raw.sparse[p].items():
                sparse[i][k] = max(v, sparse[i].get(k, 0.0))
        return EncodeResult(dense=l2_normalize(dense), sparse=sparse)

    # ----------------------------------------------------------------- token embeddings

    def _tokens_raw(self, texts: list[str], batch_size: int, layer: int, max_len: int) -> list[TokenEmb]:
        out: list[TokenEmb | None] = [None] * len(texts)
        for idx, batch in self._batches(texts, batch_size):
            enc, res, offs = self._forward(batch, max_len, hidden_states=True, offsets=True)
            hs = res.hidden_states[layer]  # hidden_states[0] = embedding, [24] = lop cuoi
            hs = self.torch.nn.functional.normalize(hs.float(), dim=-1).cpu().numpy()
            ids = enc["input_ids"].cpu().numpy()
            mask = enc["attention_mask"].cpu().numpy()
            offs = offs.numpy()
            for row, i in enumerate(idx):
                keep = [j for j in range(ids.shape[1]) if mask[row, j] and ids[row, j] not in self._special_ids]
                out[i] = TokenEmb(
                    tokens=self.tokenizer.convert_ids_to_tokens([int(ids[row, j]) for j in keep]),
                    offsets=[(int(offs[row, j, 0]), int(offs[row, j, 1])) for j in keep],
                    emb=hs[row, keep],
                )
        return out  # type: ignore[return-value]

    def token_embeddings(self, texts: list[str], layer: int = 24, max_len: int = 2048,
                         batch_size: int | None = None) -> list[TokenEmb]:
        bs = batch_size or self.batch_size
        with _LOCK:
            return self._run_with_oom_retry(
                lambda t, b: self._tokens_raw(t, b, layer, max_len), texts, bs)


@lru_cache(maxsize=4)
def load_bge_m3(model_id: str, revision: str, device: str, dtype: str, batch_size: int, max_len: int,
                key: str) -> BgeM3:
    """Singleton theo (model, revision, device, dtype...): nap model mot lan."""
    return BgeM3(model_id, revision, device, dtype, batch_size, max_len, key)

"""Cache embedding token cua BERTScore (thiet ke 07 RR2 muc 4, muc 6).

Khoa = sha256(van ban SAU buoc chuan bi) + `bertscore_config` -> doi model/layer/chuan bi dau vao thi
khong trung cache cu. Embedding gach CV KHONG phu thuoc JD nen dung lai cho moi JD sau.
Hai tang: LRU trong RAM (gioi han dung luong) + tuy chon Postgres (`bertscore_token_cache`, float16).
Xoa CV -> `purge(text_hashes)` (thiet ke 03 "Quyen rieng tu").
"""

from __future__ import annotations

import hashlib
import json
from collections import OrderedDict

import numpy as np

from cvmatch.core.models.base import TokenEmb


def text_hash(prepared_text: str) -> str:
    return hashlib.sha256(prepared_text.encode("utf-8")).hexdigest()


class TokenCache:
    def __init__(self, config_key: str, max_bytes: float = 2 * 2**30, conn=None):
        self.config_key = config_key
        self.max_bytes = max_bytes
        self.conn = conn                     # None -> chi RAM
        self._mem: OrderedDict[str, TokenEmb] = OrderedDict()
        self._bytes = 0
        self.hits = self.misses = 0

    def _put_mem(self, h: str, t: TokenEmb) -> None:
        if h in self._mem:
            return
        self._mem[h] = t
        self._bytes += t.emb.nbytes
        while self._bytes > self.max_bytes and self._mem:
            _, old = self._mem.popitem(last=False)
            self._bytes -= old.emb.nbytes

    def get_many(self, hashes: list[str]) -> dict[str, TokenEmb]:
        out: dict[str, TokenEmb] = {}
        missing = []
        for h in hashes:
            t = self._mem.get(h)
            if t is not None:
                self._mem.move_to_end(h)
                out[h] = t
            else:
                missing.append(h)
        if missing and self.conn is not None:
            rows = self.conn.execute(
                "SELECT text_hash, tokens_json, emb FROM bertscore_token_cache"
                " WHERE bertscore_config = %s AND text_hash = ANY(%s)", (self.config_key, missing)).fetchall()
            for r in rows:
                meta = r["tokens_json"]
                emb = np.frombuffer(r["emb"], dtype=np.float16).reshape(len(meta["tokens"]), -1).astype(np.float32)
                t = TokenEmb(tokens=meta["tokens"], offsets=[tuple(o) for o in meta["offsets"]], emb=emb)
                out[r["text_hash"]] = t
                self._put_mem(r["text_hash"], t)
        self.hits += len(out)
        self.misses += len(hashes) - len(out)
        return out

    def put_many(self, items: dict[str, TokenEmb]) -> None:
        for h, t in items.items():
            self._put_mem(h, t)
        if self.conn is not None and items:
            from psycopg.types.json import Jsonb

            from cvmatch.core.db import insert_rows

            with self.conn.transaction():
                with self.conn.cursor() as cur:
                    insert_rows(cur, "bertscore_token_cache",
                                ("text_hash", "bertscore_config", "n_tokens", "tokens_json", "emb"),
                                [(h, self.config_key, len(t.tokens),
                                  Jsonb({"tokens": t.tokens, "offsets": [list(o) for o in t.offsets]}),
                                  t.emb.astype(np.float16).tobytes()) for h, t in items.items()],
                                chunk=200, suffix="ON CONFLICT DO NOTHING")

    def purge(self, hashes: list[str]) -> None:
        for h in hashes:
            t = self._mem.pop(h, None)
            if t is not None:
                self._bytes -= t.emb.nbytes
        if self.conn is not None and hashes:
            with self.conn.transaction():
                self.conn.execute("DELETE FROM bertscore_token_cache WHERE text_hash = ANY(%s)", (hashes,))
                self.conn.execute("DELETE FROM bertscore_pair_cache WHERE cv_text_hash = ANY(%s)", (hashes,))

    def stats(self) -> dict:
        return {"hits": self.hits, "misses": self.misses, "entries": len(self._mem),
                "mem_mb": round(self._bytes / 2**20, 1), "config": json.dumps(self.config_key)}

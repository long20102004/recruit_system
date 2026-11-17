"""BERTScore voi backbone bge-m3 (thiet ke 07 muc 2, 4 RR2; 01 muc 11).

    R(j, i) = mean_{token t cua cau JD j} max_{token u cua gach CV i} cos(E_t, E_u)     (Recall, JD tham chieu)
    P(j, i) = mean_u max_t cos(E_t, E_u)                                                 (Precision)
Embedding token = hidden state layer 24, bo <s>/</s>, chuan L2; KHONG IDF, KHONG rescale.

`recall_matrix(jd, cv)` tinh ca ma tran |J| x |I| mot lan: moi cau chi embed MOT lan (co cache), roi
voi moi cau JD: S = E_j . C^T tren toan bo token CV ghep lai, max theo tung gach bang reduceat.
"""

from __future__ import annotations

import numpy as np

from cvmatch.core.config import BertScoreConfig
from cvmatch.core.kb.matcher import SkillMatcher
from cvmatch.core.models.base import Encoder, TokenEmb
from cvmatch.rerank.bertscore.cache import TokenCache, text_hash
from cvmatch.rerank.bertscore.prepare import Prepared, prepare

_TOKEN_CHUNK = 200_000


class BertScorer:
    def __init__(self, encoder: Encoder, cfg: BertScoreConfig, matcher: SkillMatcher | None = None,
                 cache: TokenCache | None = None):
        self.encoder = encoder
        self.cfg = cfg
        self.matcher = matcher
        self.cache = cache or TokenCache(cfg.key())

    # ----------------------------------------------------------------- dau vao + embedding

    def prepare(self, texts: list[str]) -> list[Prepared]:
        return [prepare(t, self.matcher, canonicalize_aliases=self.cfg.canonicalize_aliases,
                        mask_numbers=self.cfg.mask_numbers) for t in texts]

    def embed(self, prepared: list[Prepared]) -> list[TokenEmb]:
        hashes = [text_hash(p.text) for p in prepared]
        got = self.cache.get_many(list(dict.fromkeys(hashes)))
        todo = {h: p.text for h, p in zip(hashes, prepared) if h not in got}
        if todo:
            hs = list(todo)
            embs = self.encoder.token_embeddings([todo[h] for h in hs], layer=self.cfg.layer,
                                                 max_len=self.cfg.max_len)
            new = dict(zip(hs, embs))
            self.cache.put_many(new)
            got.update(new)
        return [got[h] for h in hashes]

    # ----------------------------------------------------------------- diem

    @staticmethod
    def _pack(embs: list[TokenEmb]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        lens = np.array([len(e.tokens) for e in embs], dtype=np.int64)
        dim = next((e.emb.shape[1] for e in embs if len(e.tokens)), 1024)
        mat = (np.concatenate([e.emb for e in embs if len(e.tokens)]).astype(np.float32)
               if lens.sum() else np.zeros((0, dim), np.float32))
        starts = np.concatenate([[0], np.cumsum(lens)[:-1]])
        return mat, lens, starts

    def score_embs(self, jd: list[TokenEmb], cv: list[TokenEmb], *, precision: bool = False):
        """-> R (|J| x |I|) [, P]. Cau / gach rong -> 0."""
        R = np.zeros((len(jd), len(cv)), dtype=np.float32)
        P = np.zeros_like(R) if precision else None
        if not jd or not cv:
            return (R, P) if precision else R
        C, lens, starts = self._pack(cv)
        nonempty = np.flatnonzero(lens > 0)
        for j, e in enumerate(jd):
            if not len(e.tokens) or not len(nonempty):
                continue
            S = e.emb.astype(np.float32) @ C.T                       # (n_j, tong token CV)
            mx = np.maximum.reduceat(S, starts[nonempty], axis=1)    # (n_j, so gach khong rong)
            R[j, nonempty] = mx.mean(axis=0)
            if precision:
                colmax = S.max(axis=0)                               # moi token CV: max theo token JD
                P[j, nonempty] = np.add.reduceat(colmax, starts[nonempty]) / lens[nonempty]
        return (R, P) if precision else R

    def recall_matrix(self, jd_texts: list[str], cv_texts: list[str], *, precision: bool = False):
        jd = self.embed(self.prepare(jd_texts))
        cv = self.embed(self.prepare(cv_texts))
        return self.score_embs(jd, cv, precision=precision)

    def purge_texts(self, texts_raw: list[str]) -> None:
        """Xoa cache cua cac gach (theo van ban sau chuan bi) - dung khi xoa CV."""
        self.cache.purge([text_hash(p.text) for p in self.prepare(list(texts_raw))])

    def attach_events(self) -> None:
        """Nghe `cv_deleted` (core.events): xoa cache embedding token cua cac gach cua CV do."""
        from cvmatch.core import events

        events.on("cv_deleted", lambda ev: self.purge_texts(list(ev.bullet_texts_raw)))

    def pair(self, jd_text: str, cv_text: str) -> dict:
        """Mot cap: recall, precision, f1 (dung cho golden test, S1/S3)."""
        R, P = self.recall_matrix([jd_text], [cv_text], precision=True)
        r, p = float(R[0, 0]), float(P[0, 0])
        return {"recall": r, "precision": p, "f1": 0.0 if r + p == 0 else 2 * r * p / (r + p)}

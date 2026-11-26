"""Cau truc trong RAM cua Retrieve (thiet ke 03 "Cau truc trong bo nho", 06 muc 2 va 7).

Dung tu Postgres (nguon su that), chi CV `status = active`, `is_latest`, va CUNG bo phien ban
(ontology_version, pipeline_version, embed_model) voi cau hinh dang chay.

    doc_matrix       n_cv x 1024 float16 (chuan L2)        view dense
    bullet_matrix    n_bullet x 1024 float16 + bullet_cv_index (gach i -> hang CV) + bullet_ids
                     gach SAP THEO HANG CV (de "max theo nhom" bang np.maximum.reduceat)
    skill_matrix     csr n_cv x n_skill, o = ev             view ky nang
    bm25             Bm25Index tren bm25_noacc|acc (+ skill_tokens)
    active           bool n_cv: tat ban cu / CV xoa NGAY, khong phai dung lai ma tran

CV moi (su kien `cv_committed`) duoc NOI THEM vao cuoi (bo dem tang gap doi), BM25 dung IDF cu.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

import numpy as np
import psycopg
import scipy.sparse as sp

from cvmatch.core.config import AppConfig
from cvmatch.retrieve.bm25 import Bm25Index

log = logging.getLogger(__name__)
DIM = 1024


class _Growable:
    """Ma tran float16 noi them hang voi dung luong tang gap doi (khong copy toan bo moi lan them)."""

    def __init__(self, dim: int, init: np.ndarray | None = None):
        self.dim = dim
        self.n = 0
        self.buf = np.zeros((0, dim), dtype=np.float16)
        if init is not None and len(init):
            self.buf = np.ascontiguousarray(init, dtype=np.float16)
            self.n = len(init)

    def append(self, rows: np.ndarray) -> None:
        k = len(rows)
        if self.n + k > len(self.buf):
            cap = max(self.n + k, 2 * len(self.buf), 1024)
            nb = np.zeros((cap, self.dim), dtype=np.float16)
            nb[: self.n] = self.buf[: self.n]
            self.buf = nb
        self.buf[self.n: self.n + k] = rows
        self.n += k

    @property
    def view(self) -> np.ndarray:
        return self.buf[: self.n]


@dataclass
class _CvRows:
    cv_ids: list[str]
    doc: np.ndarray
    bullet_cv: list[int]        # chi so CV trong lo
    bullet_ids: list[int]
    bullet: np.ndarray
    skills: list[tuple[int, str, float]]   # (chi so CV trong lo, skill_id, ev)
    bm25_docs: list[list[str]]
    recommendable: list[bool]


class CvIndex:
    def __init__(self, cfg: AppConfig):
        self.cfg = cfg
        v = cfg.versions
        self.versions = (v.ontology_version, v.pipeline_version, v.embed_model)
        self.cv_ids: list[str] = []
        self.row_of: dict[str, int] = {}
        self.active = np.zeros(0, dtype=bool)
        self.recommendable = np.zeros(0, dtype=bool)      # S07: ung vien nhan goi y viec lam
        self._doc = _Growable(DIM)
        self._bullet = _Growable(DIM)
        self.bullet_cv_index = np.zeros(0, dtype=np.int64)
        self.bullet_ids = np.zeros(0, dtype=np.int64)
        self.skill_col: dict[str, int] = {}
        self._skill_base = sp.csr_matrix((0, 0), dtype=np.float32)
        self._skill_extra: list[tuple[int, int, float]] = []
        self._skill_cache: sp.csr_matrix | None = None
        bm = cfg.retrieve.bm25
        self.bm25 = Bm25Index(bm.k1, bm.b)
        self.built_at: float | None = None

    # ----------------------------------------------------------------- doc tu Postgres

    def _bm25_tokens(self, row: dict) -> list[str]:
        bm = self.cfg.retrieve.bm25
        toks = list(row["bm25_noacc"] if bm.field == "noacc" else row["bm25_acc"])
        if bm.use_skill_tokens:
            toks += list(row["skill_tokens"])
        return toks

    def _load(self, conn: psycopg.Connection, cv_ids: list[str] | None = None) -> _CvRows:
        ov, pv, em = self.versions
        where = ("c.status = 'active' AND c.is_latest AND c.ontology_version = %s AND c.pipeline_version = %s"
                 " AND c.embed_model = %s")
        params: list = [ov, pv, em]
        if cv_ids is not None:
            where += " AND c.cv_id = ANY(%s::uuid[])"
            params.append(cv_ids)
        with conn.cursor(binary=True) as cur:
            cur.execute(f"SELECT c.cv_id, c.recommendable, v.dense, d.bm25_noacc, d.bm25_acc, d.skill_tokens FROM cv c"
                        f" JOIN cv_vector v USING (cv_id) JOIN cv_bm25_doc d USING (cv_id)"
                        f" WHERE {where} ORDER BY c.cv_id", params)
            rows = cur.fetchall()
            ids = [str(r["cv_id"]) for r in rows]
            pos = {c: i for i, c in enumerate(ids)}
            doc = (np.stack([r["dense"].to_numpy() for r in rows]).astype(np.float16)
                   if rows else np.zeros((0, DIM), np.float16))
            bm25_docs = [self._bm25_tokens(r) for r in rows]
            cur.execute("SELECT b.cv_id, b.bullet_id, bv.dense FROM cv_bullet b JOIN cv_bullet_vector bv"
                        " USING (bullet_id) WHERE b.cv_id = ANY(%s::uuid[]) ORDER BY b.cv_id, b.bullet_id", (ids,))
            brows = cur.fetchall()
            cur.execute("SELECT cv_id, skill_id, ev FROM cv_skill WHERE cv_id = ANY(%s::uuid[])", (ids,))
            srows = cur.fetchall()
        return _CvRows(
            cv_ids=ids, doc=doc,
            bullet_cv=[pos[str(r["cv_id"])] for r in brows], bullet_ids=[int(r["bullet_id"]) for r in brows],
            bullet=(np.stack([r["dense"].to_numpy() for r in brows]).astype(np.float16)
                    if brows else np.zeros((0, DIM), np.float16)),
            skills=[(pos[str(r["cv_id"])], r["skill_id"], float(r["ev"])) for r in srows],
            bm25_docs=bm25_docs, recommendable=[bool(r["recommendable"]) for r in rows])

    # ----------------------------------------------------------------- dung / cap nhat

    def build(self, conn: psycopg.Connection) -> "CvIndex":
        t0 = time.perf_counter()
        d = self._load(conn)
        self.cv_ids = d.cv_ids
        self.row_of = {c: i for i, c in enumerate(d.cv_ids)}
        self.active = np.ones(len(d.cv_ids), dtype=bool)
        self.recommendable = np.asarray(d.recommendable, dtype=bool)
        self._doc = _Growable(DIM, d.doc)
        self._bullet = _Growable(DIM, d.bullet)
        self.bullet_cv_index = np.asarray(d.bullet_cv, dtype=np.int64)
        self.bullet_ids = np.asarray(d.bullet_ids, dtype=np.int64)
        self.skill_col = {s: j for j, s in enumerate(sorted({s for _, s, _ in d.skills}))}
        self._skill_base = self._skill_csr(d.skills, 0, len(d.cv_ids))
        self._skill_extra, self._skill_cache = [], None
        self.bm25.build(d.bm25_docs)
        self.built_at = time.time()
        log.info("CvIndex: %d CV, %d gach, %d ky nang trong %.1fs", len(self.cv_ids), len(self.bullet_ids),
                 len(self.skill_col), time.perf_counter() - t0)
        return self

    def _skill_csr(self, triples, offset: int, n_rows: int) -> sp.csr_matrix:
        if not triples:
            return sp.csr_matrix((n_rows, len(self.skill_col)), dtype=np.float32)
        r = [i - offset for i, _, _ in triples]
        c = [self.skill_col[s] for _, s, _ in triples]
        v = [e for _, _, e in triples]
        return sp.csr_matrix((v, (r, c)), shape=(n_rows, len(self.skill_col)), dtype=np.float32)

    def rebuild_bm25(self, conn: psycopg.Connection) -> None:
        """Dung lai BM25 theo lo (vd moi dem) - tu vung, IDF moi, gom ca CV nap trong ngay."""
        rows = conn.execute("SELECT cv_id, bm25_noacc, bm25_acc, skill_tokens FROM cv_bm25_doc"
                            " WHERE cv_id = ANY(%s::uuid[])", (self.cv_ids,)).fetchall()
        by_id = {str(r["cv_id"]): self._bm25_tokens(r) for r in rows}
        self.bm25.build([by_id.get(c, []) for c in self.cv_ids])

    def add(self, conn: psycopg.Connection, cv_ids: list[str], replaced: list[str] | None = None) -> int:
        """Them CV vua commit (noi vao cuoi), tat ban cu. Tra ve so CV them duoc."""
        for old in replaced or []:
            self.deactivate(old)
        new = [c for c in cv_ids if c not in self.row_of]
        if not new:
            return 0
        d = self._load(conn, new)
        base = len(self.cv_ids)
        for c in d.cv_ids:
            self.row_of[c] = len(self.cv_ids)
            self.cv_ids.append(c)
        self.active = np.concatenate([self.active, np.ones(len(d.cv_ids), dtype=bool)])
        self.recommendable = np.concatenate([self.recommendable, np.asarray(d.recommendable, dtype=bool)])
        self._doc.append(d.doc)
        if len(d.bullet_ids):
            self._bullet.append(d.bullet)
            self.bullet_cv_index = np.concatenate([self.bullet_cv_index, np.asarray(d.bullet_cv) + base])
            self.bullet_ids = np.concatenate([self.bullet_ids, np.asarray(d.bullet_ids, dtype=np.int64)])
        for i, s, ev in d.skills:
            if s not in self.skill_col:
                self.skill_col[s] = len(self.skill_col)
            self._skill_extra.append((base + i, self.skill_col[s], ev))
        self._skill_cache = None
        self.bm25.append(d.bm25_docs)
        return len(d.cv_ids)

    def set_recommendable(self, cv_ids: list[str], value: bool) -> None:
        for c in cv_ids:
            i = self.row_of.get(c)
            if i is not None:
                self.recommendable[i] = value

    def deactivate(self, cv_id: str) -> None:
        i = self.row_of.get(cv_id)
        if i is not None:
            self.active[i] = False

    def attach_events(self, conn_factory) -> None:
        """Nghe `cv_committed` / `cv_deleted` (core.events). `conn_factory()` tra ve ket noi moi."""
        from cvmatch.core import events

        def on_commit(ev):
            with conn_factory() as conn:
                self.add(conn, [ev.cv_id], [ev.replaced_cv_id] if ev.replaced_cv_id else None)

        events.on("cv_committed", on_commit)
        events.on("cv_deleted", lambda ev: self.deactivate(ev.cv_id))

    # ----------------------------------------------------------------- truy cap

    @property
    def n_cv(self) -> int:
        return len(self.cv_ids)

    @property
    def doc_matrix(self) -> np.ndarray:
        return self._doc.view

    @property
    def bullet_matrix(self) -> np.ndarray:
        return self._bullet.view

    @property
    def skill_matrix(self) -> sp.csr_matrix:
        if self._skill_cache is None:
            n, m = self.n_cv, len(self.skill_col)
            base = self._skill_base
            base = sp.csr_matrix((base.data, base.indices, base.indptr), shape=(base.shape[0], m))
            if self._skill_extra:
                r, c, v = zip(*self._skill_extra)
                extra = sp.csr_matrix((v, (np.asarray(r) - base.shape[0], c)), shape=(n - base.shape[0], m),
                                      dtype=np.float32)
            else:
                extra = sp.csr_matrix((n - base.shape[0], m), dtype=np.float32)
            self._skill_cache = sp.vstack([base, extra], format="csr")
        return self._skill_cache

    def bullets_sorted_by_cv(self) -> bool:
        return bool(np.all(np.diff(self.bullet_cv_index) >= 0))

    def memory_mb(self) -> dict[str, float]:
        sm = self.skill_matrix
        bm = self.bm25.matrix
        return {"doc": self.doc_matrix.nbytes / 2**20, "bullet": self.bullet_matrix.nbytes / 2**20,
                "skill": (sm.data.nbytes + sm.indices.nbytes + sm.indptr.nbytes) / 2**20,
                "bm25": (bm.data.nbytes + bm.indices.nbytes + bm.indptr.nbytes) / 2**20}

    # ----------------------------------------------------------------- kiem nhat quan

    def verify(self, conn: psycopg.Connection) -> list[str]:
        """So voi Postgres; tra ve danh sach lech (rong = khop)."""
        ov, pv, em = self.versions
        rows = conn.execute("SELECT cv_id FROM cv WHERE status = 'active' AND is_latest AND ontology_version = %s"
                            " AND pipeline_version = %s AND embed_model = %s", (ov, pv, em)).fetchall()
        db_ids = {str(r["cv_id"]) for r in rows}
        mem_ids = {c for c, a in zip(self.cv_ids, self.active) if a}
        issues = []
        if db_ids - mem_ids:
            issues.append(f"{len(db_ids - mem_ids)} CV co trong Postgres nhung khong co trong RAM")
        if mem_ids - db_ids:
            issues.append(f"{len(mem_ids - db_ids)} CV trong RAM khong con active trong Postgres")
        n_b = conn.execute("SELECT count(*) AS n FROM cv_bullet WHERE cv_id = ANY(%s::uuid[])",
                           (list(mem_ids),)).fetchone()["n"]
        n_mem_b = int(self.active[self.bullet_cv_index].sum()) if len(self.bullet_cv_index) else 0
        if n_b != n_mem_b:
            issues.append(f"so gach lech: Postgres {n_b}, RAM {n_mem_b}")
        return issues

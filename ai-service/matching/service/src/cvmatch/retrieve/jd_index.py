"""Chi muc trong RAM phia JD cho Luong D (thiet ke 06 muc 5.4).

Chi JD `status = open` + phien ban moi nhat + CUNG bo phien ban voi cau hinh. Ba cau truc them (khong tinh
embedding lai - dung vector cua Luong B):

    doc        n_jd x 1024 (jd_vector.dense)                  view dense
    bm25       Bm25Index tren `jd_vector.bm25_query_tokens`    view BM25 (IDF tren KHO JD)
    reqs       moi JD: [(w_imp, [skill_id lua chon])] ky nang BAT BUOC + tong_w_imp      view ky nang
    resp       n_resp x 1024 + resp_jd_index                   view trach nhiem

Kho JD nho (vai chuc - vai tram) nen dung lai TOAN BO khi co `jd_committed` / `jd_status_changed`.
"""

from __future__ import annotations

import time

import numpy as np
import psycopg

from cvmatch.core.config import AppConfig
from cvmatch.retrieve.bm25 import Bm25Index

DIM = 1024


class JdIndex:
    def __init__(self, cfg: AppConfig):
        self.cfg = cfg
        v = cfg.versions
        self.versions = (v.ontology_version, v.pipeline_version, v.embed_model)
        bm = cfg.retrieve.bm25
        self.bm25 = Bm25Index(bm.k1, bm.b)
        self.jd_ids: list[str] = []
        self.version_of: dict[str, int] = {}
        self.row_of: dict[str, int] = {}
        self.doc = np.zeros((0, DIM), np.float16)
        self.reqs: list[list[tuple[float, list[str]]]] = []
        self.meta: list[dict] = []
        self.resp = np.zeros((0, DIM), np.float16)
        self.resp_jd_index = np.zeros(0, np.int64)
        self.resp_idx: list[int] = []
        self.resp_text: list[str] = []
        self.built_at: float | None = None

    def build(self, conn: psycopg.Connection) -> "JdIndex":
        ov, pv, em = self.versions
        with conn.cursor(binary=True) as cur:
            # moi tin: ban moi nhat CUNG bo khoa phien ban (ban song song sau reprocess van match duoc)
            cur.execute("SELECT DISTINCT ON (j.jd_id) j.jd_id, j.version, v.dense, v.bm25_query_tokens FROM jd j"
                        " JOIN jd_vector v USING (jd_id, version)"
                        " WHERE j.status = 'open' AND j.ontology_version = %s"
                        " AND j.pipeline_version = %s AND j.embed_model = %s ORDER BY j.jd_id, j.version DESC",
                        (ov, pv, em))
            rows = cur.fetchall()
            keys = [(r["jd_id"], r["version"]) for r in rows]
            self.jd_ids = [k[0] for k in keys]
            self.version_of = dict(keys)
            self.row_of = {j: i for i, j in enumerate(self.jd_ids)}
            self.doc = (np.stack([r["dense"].to_numpy() for r in rows]).astype(np.float16)
                        if rows else np.zeros((0, DIM), np.float16))
            self.bm25.build([list(r["bm25_query_tokens"] or []) for r in rows])
            cur.execute("SELECT r.jd_id, r.idx, r.text_raw, r.dense FROM jd_responsibility r"
                        " WHERE (r.jd_id, r.version) IN (SELECT unnest(%s::text[]), unnest(%s::int[]))"
                        " AND NOT r.is_generic AND r.dense IS NOT NULL ORDER BY r.jd_id, r.idx",
                        ([k[0] for k in keys], [k[1] for k in keys]))
            rr = cur.fetchall()
        self.resp = (np.stack([r["dense"].to_numpy() for r in rr]).astype(np.float16)
                     if rr else np.zeros((0, DIM), np.float16))
        self.resp_jd_index = np.array([self.row_of[r["jd_id"]] for r in rr], dtype=np.int64)
        self.resp_idx = [r["idx"] for r in rr]
        self.resp_text = [r["text_raw"] for r in rr]
        reqs: dict[str, dict[object, tuple[float, list[str]]]] = {j: {} for j in self.jd_ids}
        for r in conn.execute("SELECT jd_id, skill_id, w_imp, group_id FROM jd_skill WHERE required AND"
                              " (jd_id, version) IN (SELECT unnest(%s::text[]), unnest(%s::int[]))"
                              " ORDER BY jd_id, skill_id", ([k[0] for k in keys], [k[1] for k in keys])):
            key = ("g", r["group_id"]) if r["group_id"] is not None else ("s", r["skill_id"])
            w0, mem = reqs[r["jd_id"]].get(key, (0.0, []))
            reqs[r["jd_id"]][key] = (max(w0, float(r["w_imp"])), mem + [r["skill_id"]])
        self.reqs = [list(reqs[j].values()) for j in self.jd_ids]
        meta = {r["jd_id"]: dict(r) for r in conn.execute(
            "SELECT jd_id, location, work_mode, role_group, level_rank, min_years FROM jd_meta WHERE"
            " (jd_id, version) IN (SELECT unnest(%s::text[]), unnest(%s::int[]))",
            ([k[0] for k in keys], [k[1] for k in keys]))}
        self.meta = [meta.get(j, {}) for j in self.jd_ids]
        self.built_at = time.time()
        return self

    @property
    def n_jd(self) -> int:
        return len(self.jd_ids)

    def attach_events(self, conn_factory) -> list:
        """Dung lai khi JD moi / doi trang thai. Tra danh sach (event, handler) de go (`events.off`)."""
        from cvmatch.core import events

        def rebuild(_ev):
            with conn_factory() as conn:
                self.build(conn)

        hs = [("jd_committed", rebuild), ("jd_status_changed", rebuild)]
        for e, h in hs:
            events.on(e, h)
        return hs

"""Bon goc nhin re cua Retrieve (thiet ke 06 muc 1, C3). Moi ham cham TOAN BO hang cua CvIndex
(hang khong active bi loai o buoc sau bang mask) va tra ve mang float32 dai n_cv.

- `None` = goc nhin KHONG kha dung cho JD nay (vd JD khong co ky nang bat buoc) -> bo khoi trung binh.
- `NaN` o mot CV = thieu du lieu phia CV (vd CV khong co gach o view trach nhiem): KHONG phai 0;
  diem tong cua CV do lay trung binh tren cac view con lai.
"""

from __future__ import annotations

import numpy as np

from cvmatch.retrieve.index import CvIndex

_CHUNK = 50_000


def view_dense(idx: CvIndex, jd_dense: np.ndarray) -> np.ndarray:
    """(a) cosine vector JD voi vector tai lieu cua moi CV (deu da chuan L2)."""
    q = np.asarray(jd_dense, dtype=np.float32)
    m = idx.doc_matrix
    out = np.empty(len(m), dtype=np.float32)
    for s in range(0, len(m), _CHUNK):
        out[s:s + _CHUNK] = m[s:s + _CHUNK].astype(np.float32) @ q
    return out


def view_bm25(idx: CvIndex, query_tokens: list[str]) -> np.ndarray | None:
    """(b) BM25 voi token truy van cua JD tren chi muc CV."""
    if not query_tokens:
        return None
    return idx.bm25.scores(query_tokens)


def view_skill(idx: CvIndex, required: list[tuple[str, float, int | None]]) -> np.ndarray | None:
    """(c) do phu ky nang bat buoc: sum_r w_imp_r * ev / sum_r w_imp_r.

    `required`: [(skill_id, w_imp, group_id)] cac ky nang BAT BUOC da gan ma. Nhom "A hoac B" tinh
    la MOT yeu cau (w = max trong nhom, ev = max tren cac lua chon) - nhat quan voi feature A1.
    Ky nang khong CV nao co van nam o mau so (CV nao cung 0 o yeu cau do).
    """
    if not required:
        return None
    reqs: dict[object, tuple[float, list[str]]] = {}
    for sid, w, gid in required:
        key = ("g", gid) if gid is not None else ("s", sid)
        w0, members = reqs.get(key, (0.0, []))
        reqs[key] = (max(w0, w), members + [sid])
    total = sum(w for w, _ in reqs.values())
    sm = idx.skill_matrix.tocsc()
    score = np.zeros(idx.n_cv, dtype=np.float32)
    for w, members in reqs.values():
        cols = [idx.skill_col[s] for s in members if s in idx.skill_col]
        if not cols:
            continue
        ev = sm[:, cols].max(axis=1).toarray().ravel() if len(cols) > 1 else sm[:, cols[0]].toarray().ravel()
        score += w * ev.astype(np.float32)
    return score / total


def per_cv_max(idx: CvIndex, sims: np.ndarray) -> np.ndarray:
    """sims: (n_bullet, R) -> (n_cv, R) max theo CV; CV khong co gach -> NaN."""
    out = np.full((idx.n_cv, sims.shape[1]), np.nan, dtype=np.float32)
    if not len(idx.bullet_cv_index):
        return out
    bci = idx.bullet_cv_index
    starts = np.flatnonzero(np.r_[True, bci[1:] != bci[:-1]])
    out[bci[starts]] = np.maximum.reduceat(sims, starts, axis=0)
    return out


def bullet_sims(idx: CvIndex, resp_dense: np.ndarray) -> np.ndarray:
    """Cosine moi gach CV voi moi trach nhiem: (n_bullet, R) float32, tinh theo khoi."""
    r = np.asarray(resp_dense, dtype=np.float32).T
    b = idx.bullet_matrix
    out = np.empty((len(b), r.shape[1]), dtype=np.float32)
    for s in range(0, len(b), _CHUNK):
        out[s:s + _CHUNK] = b[s:s + _CHUNK].astype(np.float32) @ r
    return out


def view_resp(idx: CvIndex, resp_dense: np.ndarray) -> np.ndarray | None:
    """(d) do phu trach nhiem: voi moi trach nhiem (da bo `is_generic`) lay gach giong nhat cua tung
    CV, roi trung binh qua cac trach nhiem. CV khong co gach -> NaN (thieu du lieu)."""
    if resp_dense is None or len(resp_dense) == 0:
        return None
    return per_cv_max(idx, bullet_sims(idx, resp_dense)).mean(axis=1)

"""Thu nghiem bat bien cong bang (thiet ke 09 muc 6).

Tu ~50 CV goc sinh ban doi chung CHI doi thuoc tinh nhay cam, chay CA pipeline tu JSON (Luong A ->
Retrieve -> Rerank) trong cung mot lan match, roi so diem:

| bien doi             | ky vong                                                           |
| ho ten               | delta = 0                                                         |
| gioi tinh            | delta = 0 (truong gender, danh xung Anh/Chi, Mr/Ms o ho ten)      |
| ten truong           | delta = 0                                                         |
| nam sinh / tot nghiep| delta = 0 (doi nam sinh; doi nam tot nghiep nhung van da tot nghiep)|
| thu tu muc / gach    | delta = 0 (S2 khong phu thuoc thu tu, F04)                        |
| bo dau + chu thuong  | ghi lai; CV phai co co `no_diacritics`                            |

Moi tang tren duong chinh la code tat dinh nen delta phai DUNG BANG 0; khac 0 la ro ri can sua.
Ban doi chung duoc cap email / so dien thoai rieng (de khong bi coi la ban moi cua cung nguoi) - email da bi
an danh luc nap nen day khong phai la bien doi.
"""

from __future__ import annotations

import copy
import re
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from cvmatch.core.text.normalize import strip_diacritics

NAMES = ["Trần Thị Bích", "Lê Hoàng Nam", "Phạm Minh Châu", "Võ Thanh Hà"]
SCHOOLS = ["Trường Cao đẳng Kỹ thuật Cao Thắng", "Đại học Quốc gia Hà Nội", "Học viện Bưu chính Viễn thông"]
TRANSFORMS = ("name", "gender", "school", "birth_grad_year", "order", "no_diacritics")


def _map_text(obj: Any, fn) -> Any:
    if isinstance(obj, str):
        return fn(obj)
    if isinstance(obj, list):
        return [_map_text(x, fn) for x in obj]
    if isinstance(obj, dict):
        return {k: _map_text(v, fn) for k, v in obj.items()}
    return obj


def _shift_year(v: Any, d: int) -> Any:
    if isinstance(v, int):
        return v + d
    if isinstance(v, str):
        return re.sub(r"(19|20)\d{2}", lambda m: str(int(m.group(0)) + d), v)
    return v


def transform(cv: dict, kind: str, k: int = 0) -> dict:
    """Mot ban doi chung cua `cv` theo bien doi `kind` (k: bien the thu may)."""
    c = copy.deepcopy(cv)
    if kind == "name":
        c["full_name"] = NAMES[k % len(NAMES)]
    elif kind == "gender":
        g = str(c.get("gender") or "").lower()
        c["gender"] = "Nữ" if g in ("", "nam", "male", "m") else "Nam"
        name = c.get("full_name") or ""
        c["full_name"] = ("Chị " if not name.startswith("Chị") else "Anh ") + re.sub(r"^(Anh|Chị|Mr\.?|Ms\.?)\s+", "", name)
    elif kind == "school":
        for e in c.get("education") or []:
            e["school"] = SCHOOLS[k % len(SCHOOLS)]
    elif kind == "birth_grad_year":
        for key in ("birth_year", "dob", "birth_date", "date_of_birth"):
            if key in c:
                c[key] = _shift_year(c[key], -7)
        if "birth_year" not in c and "dob" not in c:
            c["birth_year"] = 1990
        for e in c.get("education") or []:
            if e.get("end"):
                e["end"] = _shift_year(e["end"], -3)      # van da tot nghiep (truoc ngay di lam)
            if e.get("start"):
                e["start"] = _shift_year(e["start"], -3)
    elif kind == "order":
        for sec in ("experiences", "projects"):
            items = c.get(sec) or []
            c[sec] = list(reversed(items))
            for it in c[sec]:
                if isinstance(it.get("description"), list):
                    it["description"] = list(reversed(it["description"]))
        if isinstance(c.get("skills"), list):
            c["skills"] = list(reversed(c["skills"]))
    elif kind == "no_diacritics":
        keep = {k2: c.get(k2) for k2 in ("email", "phone")}
        c = _map_text(c, lambda s: strip_diacritics(s).lower())
        c.update({k2: v for k2, v in keep.items() if v is not None})
    else:
        raise ValueError(kind)
    return c


def _unique_contact(cv: dict, tag: str) -> dict:
    c = dict(cv)
    base = (cv.get("email") or "cv@example.com").split("@")
    c["email"] = f"{base[0]}+{tag}@{base[1] if len(base) > 1 else 'example.com'}"
    c["phone"] = None
    return c


@dataclass
class InvarianceReport:
    rows: list[dict] = field(default_factory=list)      # transform, cv, query, delta_score, delta_s_raw, flags
    by_transform: dict[str, dict] = field(default_factory=dict)

    def ok(self, tol: float = 0.0) -> bool:
        return all(v["max_abs_delta_score"] <= tol and v["max_abs_delta_s_raw"] <= 1e-6
                   for t, v in self.by_transform.items() if t != "no_diacritics")

    def to_markdown(self) -> str:
        out = ["# Thử nghiệm bất biến (thiết kế 09 mục 6)", "",
               "| Biến đổi | Số cặp | max Δ điểm (tuyệt đối) | max Δ S_raw (tuyệt đối) | số cặp Δ ≠ 0 | ghi chú |", "| --- | --- | --- | --- | --- | --- |"]
        for t in TRANSFORMS:
            v = self.by_transform.get(t)
            if not v:
                continue
            note = (f"cờ no_diacritics: {v['flag_rate']:.0%}" if t == "no_diacritics" else
                    ("đạt (Δ = 0)" if v["n_nonzero"] == 0 else "**rò rỉ - cần sửa**"))
            out.append(f"| {t} | {v['n']} | {v['max_abs_delta_score']} | {v['max_abs_delta_s_raw']:.2e} |"
                       f" {v['n_nonzero']} | {note} |")
        bad = [r for r in self.rows if r["transform"] != "no_diacritics" and (r["delta_score"] or r["delta_s_raw"] > 1e-6)]
        if bad:
            out += ["", "## Cặp lệch", "", "| Biến đổi | CV | Truy vấn | Δ điểm | Δ S_raw |", "| --- | --- | --- | --- | --- |"]
            out += [f"| {r['transform']} | {r['cv']} | {r['query']} | {r['delta_score']} | {r['delta_s_raw']:.2e} |"
                    for r in bad[:50]]
        return "\n".join(out) + "\n"


def run_invariance(svc, cvs: list[tuple[str, dict]], jds: list[dict], *, transforms=TRANSFORMS,
                   ref_ym: str | None = None) -> InvarianceReport:
    """`svc`: api.services.Services tren DB rieng. Nap CV goc + moi ban doi chung, nap JD, match
    voi K = N = toan kho (khong ai bi cat), so diem tung cap goc/bien the."""
    items, origin = [], {}
    for name, cv in cvs:
        items.append((f"{name}", cv))
        for t in transforms:
            v = _unique_contact(transform(cv, t, len(items)), t)
            items.append((f"{name}#{t}", v))
    outs = svc.ingest_cvs(items)
    ids = {}
    for (src, _), o in zip(items, outs):
        if o.status not in ("ok", "duplicate"):     # duplicate: CV goc da co trong kho -> dung cv_id do
            raise RuntimeError(f"nap {src} that bai: {o.status} {o.detail}")
        ids[src] = o.cv_id
        origin[o.cv_id] = src
    with svc.connect() as conn:
        flags = {str(r["cv_id"]): list(r["flags"] or []) for r in conn.execute(
            "SELECT cv_id, flags FROM cv WHERE cv_id = ANY(%s::uuid[])", (list(ids.values()),))}
    for jd in jds:
        o = svc.ingest_jd(copy.deepcopy(jd))
        if o.status not in ("ok", "unchanged"):
            raise RuntimeError(f"nap JD {jd.get('jd_id')} that bai: {o.status}")
    n_all = len(ids)
    rep = InvarianceReport()
    for jd in jds:
        m = svc.match_jd(str(jd["jd_id"]), K=n_all, N=n_all, ref_ym=ref_ym)
        by = {it.cv_id: it for it in m.final_items}
        for name, _ in cvs:
            base = by.get(ids[name])
            for t in transforms:
                var = by.get(ids[f"{name}#{t}"])
                if base is None or var is None:
                    continue
                rep.rows.append({"transform": t, "cv": name, "query": jd["jd_id"],
                                 "delta_score": var.score - base.score,
                                 "delta_s_raw": abs(var.score_raw - base.score_raw),
                                 "flags": flags.get(ids[f"{name}#{t}"], [])})
    agg: dict[str, list[dict]] = defaultdict(list)
    for r in rep.rows:
        agg[r["transform"]].append(r)
    for t, rs in agg.items():
        rep.by_transform[t] = {
            "n": len(rs), "max_abs_delta_score": max(abs(r["delta_score"]) for r in rs),
            "max_abs_delta_s_raw": max(r["delta_s_raw"] for r in rs),
            "n_nonzero": sum(1 for r in rs if r["delta_score"] != 0 or r["delta_s_raw"] > 1e-6),
            "flag_rate": sum("no_diacritics" in r["flags"] for r in rs) / len(rs)}
    return rep

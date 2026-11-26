"""Bo kich ban goi API THAT qua HTTP (server dang chay tren DB demo), ghi ket qua + do tre tung endpoint.

    cvmatch demo serve                      # cua so 1
    cvmatch demo scenarios [--only a,b]     # cua so 2 -> bang ket qua + research/reports/demo/scenarios.md

Kich ban thay doi du lieu (CV moi / ban moi / xoa / JD moi / dong JD) dung du lieu RIENG cua lan chay va
don dep o cuoi, nen kho CV demo giu nguyen giua cac lan chay. Doc `state.json` de biet vai tro / nhom that
cua tung CV / JD (de kiem do hop ly cua ket qua, khong chi kiem ma HTTP).
"""

from __future__ import annotations

import random
import statistics
import threading
import time
import uuid
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

import httpx

RELATED = {"Backend": {"Backend", "Fullstack"}, "Frontend": {"Frontend", "Fullstack"},
           "Fullstack": {"Fullstack", "Backend", "Frontend"}, "Data": {"Data", "AI/ML"}, "AI/ML": {"AI/ML", "Data"},
           "Mobile": {"Mobile"}, "DevOps": {"DevOps", "Backend"}, "QA": {"QA"}, "Security": {"Security", "DevOps"},
           "Business": {"Business"}, "Design": {"Design", "Frontend"}}


@dataclass
class Result:
    name: str
    ok: bool
    seconds: float
    detail: str


@dataclass
class Runner:
    base: str
    state: dict
    timeout: float = 300.0
    latency: dict[str, list[float]] = field(default_factory=lambda: defaultdict(list))
    created_cvs: list[str] = field(default_factory=list)
    tag: str = field(default_factory=lambda: uuid.uuid4().hex[:6])

    def __post_init__(self):
        self.http = httpx.Client(base_url=self.base, timeout=self.timeout)
        self._lock = threading.Lock()
        self.cv_group = {v["cv_id"]: v["group"] for v in self.state["cv"].values()}
        self.cv_meta = {v["cv_id"]: v for v in self.state["cv"].values()}
        self.open_jds = [j for j, v in self.state["jd"].items() if v["status"] == "open"]
        self.rng = random.Random(7)

    def call(self, method: str, path: str, key: str | None = None, **kw) -> httpx.Response:
        t = time.perf_counter()
        r = self.http.request(method, path, **kw)
        with self._lock:
            self.latency[key or f"{method} {path.split('/')[1] if '/' in path else path}"].append(time.perf_counter() - t)
        return r

    def ok(self, r: httpx.Response, code: int = 200) -> dict:
        assert r.status_code == code, f"{r.request.method} {r.request.url.path} -> {r.status_code}: {r.text[:300]}"
        return r.json()

    def match(self, jd_id: str, **body) -> dict:
        return self.ok(self.call("POST", f"/match/jd/{jd_id}", "POST /match/jd", json=body))

    def match_cv(self, cv_id: str, **body) -> dict:
        return self.ok(self.call("POST", f"/match/cv/{cv_id}", "POST /match/cv", json=body))

    def new_cv(self, role: str, k: int = 0, level_idx: int | None = 3) -> dict:
        from cvmatch.demo.generate import make_cv

        cv, _ = make_cv(9000 + k, random.Random(f"{self.tag}-{k}"), role=role, level_idx=level_idx)
        cv.pop("name", None)
        cv["full_name"] = cv.get("full_name") or "Ứng viên kịch bản"
        cv["email"] = f"scenario-{self.tag}-{k}@example.com"
        cv["phone"] = None
        return cv

    def cleanup(self) -> None:
        for c in self.created_cvs:
            self.http.delete(f"/cv/{c}")
        self.created_cvs.clear()


SCENARIOS: list[tuple[str, Callable[[Runner], str]]] = []


def scenario(fn):
    SCENARIOS.append((fn.__name__, fn))
    return fn


# --------------------------------------------------------------------------- doc


@scenario
def health(r: Runner) -> str:
    h = r.ok(r.call("GET", "/health", "GET /health"))
    assert h["status"] == "ok" and h["n_cv"] >= len(r.state["cv"]) - 5, h
    assert h["n_jd_open"] == len(r.open_jds), (h["n_jd_open"], len(r.open_jds))
    assert h["versions"]["ontology_version"] == r.state["kb_version"]
    return f"{h['n_cv']} CV · {h['n_jd_open']} JD mở · {h['encoder']}"


@scenario
def match_all_open_jds(r: Runner) -> str:
    """Moi JD mo: top 20 hop le; top 10 phan lon cung nhom (hoac nhom lien quan) voi JD."""
    precs = {}
    for jd in r.open_jds:
        out = r.match(jd, N=20, ref_ym="2026-11")
        items = out["items"]
        assert items and len(items) <= 20 and [i["rank"] for i in items] == list(range(1, len(items) + 1))
        scores = [i["score"] for i in items]
        assert scores == sorted(scores, reverse=True), scores
        for i in items:
            want = "high" if i["score"] >= 80 else "mid" if i["score"] >= 60 else "low"
            assert i["band"] == want
        g = r.state["jd"][jd]["group"]
        if g:
            top = [r.cv_group.get(i["cv_id"]) for i in items[:10]]
            precs[jd] = sum(1 for x in top if x in RELATED.get(g, {g})) / len(top)
    mean = statistics.fmean(precs.values())
    worst = min(precs, key=precs.get)
    assert mean >= 0.6, f"P@10 cung nhom trung binh {mean:.2f}"
    return f"{len(r.open_jds)} JD · P@10 cùng/lân cận nhóm TB {mean:.2f} · tệ nhất {worst} {precs[worst]:.2f}"


@scenario
def match_params(r: Runner) -> str:
    jd = next(j for j in r.open_jds if r.state["jd"][j]["role"] == "java")
    base = r.match(jd, ref_ym="2026-11")
    assert len(base["items"]) == 30                                   # mac dinh rerank.N
    small = r.match(jd, K=40, N=5)
    assert len(small["items"]) == 5
    dense = r.match(jd, N=10, views=["dense"])
    assert len(dense["items"]) == 10
    top1 = base["items"][0]["cv_id"]
    ex = r.match(jd, N=30, exclude_cv_ids=[top1])
    assert top1 not in [i["cv_id"] for i in ex["items"]]
    loc = r.match(jd, N=30, hard_filters={"location": "Hà Nội", "allow_remote": False})
    yrs = r.match(jd, N=30, hard_filters={"min_years": 5})
    n_hn = sum(1 for v in r.cv_meta.values() if v["location"] == "Hà Nội")
    # CV thieu dia diem duoc cho qua -> pool >= so CV Ha Noi; khong duoc bang 0 (loi chuan hoa dia diem)
    assert n_hn <= loc["n_pool"] < base["n_pool"], (n_hn, loc["n_pool"])
    assert 0 < yrs["n_pool"] < base["n_pool"], yrs["n_pool"]
    bad_loc = [i for i in loc["items"] if r.cv_meta.get(i["cv_id"], {}).get("location") not in ("Hà Nội", None)]
    assert not bad_loc, bad_loc[:2]
    return (f"pool {base['n_pool']} · lọc Hà Nội {loc['n_pool']} · ≥5 năm {yrs['n_pool']} · loại top1 OK ·"
            f" dense-only OK")


@scenario
def explain_hr(r: Runner) -> str:
    jd = next(j for j in r.open_jds if r.state["jd"][j]["role"] == "frontend")
    small = r.match(jd, N=5, ref_ym="2026-11")
    big = r.match(jd, N=60, ref_ym="2026-11")
    for it in small["items"][:3]:
        e = r.ok(r.call("GET", f"/match/{small['run_id']}/cv/{it['cv_id']}/explain", "GET explain"))
        assert e["text"].startswith(f"Điểm {it['score']}/100") and e["band"] == it["band"]
        again = r.ok(r.call("GET", f"/match/{small['run_id']}/cv/{it['cv_id']}/explain", "GET explain"))
        assert again["cache_key"] == e["cache_key"]
    forced = r.ok(r.call("GET", f"/match/{small['run_id']}/cv/{small['items'][0]['cv_id']}/explain?force=true",
                         "GET explain"))
    assert forced["cache_key"] == e["cache_key"] or forced["text"]
    # CV ngoai top N cua run nho (hang 40 o run lon) -> dung lai tu rerank_feature
    far = big["items"][39]["cv_id"]
    e2 = r.ok(r.call("GET", f"/match/{small['run_id']}/cv/{far}/explain", "GET explain"))
    assert e2["cv_id"] == far and e2["text"]
    return f"top 3 + cache + force + CV hạng 40 ngoài top 5 · {len(e['text'])} ký tự"


@scenario
def background_job(r: Runner) -> str:
    jd = r.open_jds[0]
    job = r.ok(r.call("POST", f"/match/jd/{jd}", "POST /match/jd", json={"N": 10, "background": True}), 202)
    t = time.perf_counter()
    while True:
        j = r.ok(r.call("GET", f"/jobs/{job['job_id']}", "GET /jobs"))
        if j["status"] in ("done", "failed"):
            break
        assert time.perf_counter() - t < r.timeout, "job qua lau"
        time.sleep(0.3)
    assert j["status"] == "done" and len(j["result"]["items"]) == 10, j.get("error")
    return f"job {j['status']} sau {time.perf_counter() - t:.1f}s"


# --------------------------------------------------------------------------- Luong D


@scenario
def reverse_match(r: Runner) -> str:
    by_group = defaultdict(list)
    for v in r.state["cv"].values():
        if v["group"] in ("Backend", "Frontend", "Data", "Mobile", "DevOps", "QA") and v["level"] >= 2 \
                and "no_diacritics" not in v["flags"] and v["status"] == "ok":
            by_group[v["group"]].append(v["cv_id"])
    hits, n = 0, 0
    closed = {j for j, v in r.state["jd"].items() if v["status"] != "open"}
    for g, ids in sorted(by_group.items()):
        for cv in r.rng.sample(ids, min(3, len(ids))):
            out = r.match_cv(cv, ref_ym="2026-11")
            jds = [i["jd_id"] for i in out["items"]]
            assert jds and len(jds) <= 10 and not (set(jds) & closed), jds
            n += 1
            hits += r.state["jd"][jds[0]]["group"] in RELATED.get(g, {g})
    e = r.ok(r.call("GET", f"/match/{out['run_id']}/jd/{jds[0]}/explain", "GET explain (ứng viên)"))
    assert e["audience"] == "candidate" and "/100" not in e["text"] and "CV của bạn" in e["text"]
    assert hits / n >= 0.6, f"top 1 dung nhom {hits}/{n}"
    return f"{n} CV · top 1 JD cùng/lân cận nhóm {hits}/{n} · JD đóng/nháp không xuất hiện"


@scenario
def reverse_filters(r: Runner) -> str:
    cv = next(v["cv_id"] for v in r.state["cv"].values() if v["role"] == "java" and v["level"] >= 3)
    base = r.match_cv(cv, ref_ym="2026-11")
    top = base["items"][0]["jd_id"]
    ex = r.match_cv(cv, exclude_jd_ids=[top])
    assert top not in [i["jd_id"] for i in ex["items"]]
    rem = r.match_cv(cv, hard_filters={"work_mode": "remote"})
    assert rem["n_pool"] < base["n_pool"]
    return f"pool {base['n_pool']} JD · remote {rem['n_pool']} · loại top 1 OK"


@scenario
def jd_close_reopen(r: Runner) -> str:
    cv = next(v["cv_id"] for v in r.state["cv"].values() if v["role"] == "frontend" and v["level"] >= 3)
    first = r.match_cv(cv)["items"][0]["jd_id"]
    r.ok(r.call("PATCH", f"/jd/{first}/status", "PATCH /jd/status", json={"status": "closed"}))
    try:
        after = [i["jd_id"] for i in r.match_cv(cv)["items"]]
        assert first not in after
        h = r.ok(r.call("GET", "/health", "GET /health"))
        assert h["n_jd_open"] == len(r.open_jds) - 1
    finally:
        r.ok(r.call("PATCH", f"/jd/{first}/status", "PATCH /jd/status", json={"status": "open"}))
    assert first in [i["jd_id"] for i in r.match_cv(cv)["items"]]
    return f"đóng {first} -> biến mất khỏi gợi ý; mở lại -> xuất hiện lại"


@scenario
def preview_no_trace(r: Runner) -> str:
    before = r.ok(r.call("GET", "/health", "GET /health"))["n_cv"]
    cv = r.new_cv("data_eng", 1)
    p = r.ok(r.call("POST", "/match/cv:preview", "POST /match/cv:preview", json={"cv": cv, "N": 5}))
    assert p["status"] == "ok" and p["items"] and len(p["explanations"]) == len(p["items"])
    assert r.state["jd"][p["items"][0]["jd_id"]]["group"] in RELATED["Data"], p["items"][0]
    after = r.ok(r.call("GET", "/health", "GET /health"))["n_cv"]
    assert after == before
    return f"top 1 {p['items'][0]['jd_id']} ({r.state['jd'][p['items'][0]['jd_id']]['title']}) · kho không đổi"


# --------------------------------------------------------------------------- thay doi du lieu


@scenario
def cv_lifecycle(r: Runner) -> str:
    jd = next(j for j in r.open_jds if r.state["jd"][j]["role"] == "devops")
    cv = r.new_cv("devops", 2, level_idx=4)
    o = r.ok(r.call("POST", "/cv", "POST /cv", json=cv))
    assert o["status"] == "ok" and o["version"] == 1
    cid = o["cv_id"]
    r.created_cvs.append(cid)
    dup = r.ok(r.call("POST", "/cv", "POST /cv", json=cv))
    assert dup["status"] == "duplicate" and dup["cv_id"] == cid
    m = r.match(jd, N=60)
    assert cid in [i["cv_id"] for i in m["items"]], "CV moi chua vao chi muc"
    v2 = dict(cv, summary=(cv.get("summary") or "") + " Mới cập nhật chứng chỉ CKA.")
    o2 = r.ok(r.call("POST", "/cv", "POST /cv", json=v2))
    assert o2["status"] == "ok" and o2["version"] == 2 and o2["cv_id"] != cid
    r.created_cvs.append(o2["cv_id"])
    ids = [i["cv_id"] for i in r.match(jd, N=60)["items"]]
    assert o2["cv_id"] in ids and cid not in ids, "ban cu van con trong ket qua"
    assert r.ok(r.call("DELETE", f"/cv/{o2['cv_id']}", "DELETE /cv"))["deleted"]
    assert o2["cv_id"] not in [i["cv_id"] for i in r.match(jd, N=60)["items"]]
    bad = r.call("POST", "/cv", "POST /cv", json={"experiences": "khong phai danh sach"})
    assert bad.status_code == 422 and bad.json()["status"] == "invalid"
    return "nạp mới → trùng → vào chỉ mục → bản 2 thay bản 1 → xoá → biến mất · CV sai schema 422"


@scenario
def jd_lifecycle(r: Runner) -> str:
    jid = f"SCN-{r.tag}"
    jd = {"jd_id": jid, "title": "Senior Backend Developer (Java)", "location": "TP.HCM", "min_years": 4,
          "skills": [{"name": "Java", "required": True, "importance": "core"},
                     {"name": "Spring Boot", "required": True, "importance": "core"},
                     {"name": "Kafka", "required": False, "importance": "minor"}],
          "requirements": ["Có kinh nghiệm thiết kế hệ thống chịu tải cao"],
          "responsibilities": ["Thiết kế và phát triển REST API cho hệ thống thanh toán",
                               "Tối ưu hiệu năng truy vấn cơ sở dữ liệu"]}
    o = r.ok(r.call("POST", "/jd", "POST /jd", json=jd))
    assert o["status"] == "ok" and o["version"] == 1
    assert r.ok(r.call("POST", "/jd", "POST /jd", json=jd))["status"] == "unchanged"
    m1 = r.match(jid, N=10)
    top = [r.cv_group.get(i["cv_id"]) for i in m1["items"]]
    assert sum(g in RELATED["Backend"] for g in top) >= 7, top
    jd2 = dict(jd, responsibilities=jd["responsibilities"] + ["Xây dựng luồng xử lý sự kiện với Kafka"])
    o2 = r.ok(r.call("POST", "/jd", "POST /jd", json=jd2))
    assert o2["version"] == 2
    assert r.match(jid, N=5)["jd_version"] == 2
    bad = r.call("POST", "/jd", "POST /jd", json={"jd_id": "X"})
    assert bad.status_code == 422
    r.ok(r.call("PATCH", f"/jd/{jid}/status", "PATCH /jd/status", json={"status": "closed"}))   # don dep
    return f"v1 → unchanged → top 10 Backend/Fullstack {sum(g in RELATED['Backend'] for g in top)}/10 → v2 → đóng"


@scenario
def batch_ingest(r: Runner) -> str:
    before = r.ok(r.call("GET", "/health", "GET /health"))["n_cv"]
    roles = ["java", "frontend", "qa", "data_analyst", "android"]
    items = [r.new_cv(roles[k % len(roles)], 100 + k) for k in range(20)]
    job = r.ok(r.call("POST", "/cv/batch", "POST /cv/batch", json={"items": items}), 202)
    t = time.perf_counter()
    while (j := r.ok(r.call("GET", f"/jobs/{job['job_id']}", "GET /jobs")))["status"] not in ("done", "failed"):
        assert time.perf_counter() - t < r.timeout
        time.sleep(0.5)
    assert j["status"] == "done", j["error"]
    res = j["result"]["results"]
    assert all(x["status"] == "ok" for x in res), [x for x in res if x["status"] != "ok"][:2]
    r.created_cvs += [x["cv_id"] for x in res]
    after = r.ok(r.call("GET", "/health", "GET /health"))["n_cv"]
    assert after == before + 20, (before, after)
    return f"20 CV chạy nền trong {time.perf_counter() - t:.1f}s · chỉ mục {before} → {after}"


@scenario
def errors(r: Runner) -> str:
    checks = [("POST", "/match/jd/KHONG-CO", 404, {}), ("POST", "/match/cv/00000000-0000-0000-0000-000000000000", 404, {}),
              ("POST", f"/match/jd/{r.open_jds[0]}", 422, {"json": {"K": 0}}),
              ("POST", f"/match/jd/{r.open_jds[0]}", 422, {"json": {"ref_ym": "11-2026"}}),
              ("GET", "/jobs/khong-co", 404, {}), ("PATCH", "/jd/KHONG-CO/status", 404, {"json": {"status": "closed"}}),
              ("PATCH", f"/jd/{r.open_jds[0]}/status", 422, {"json": {"status": "xoa"}}),
              ("GET", "/match/00000000-0000-0000-0000-000000000000/cv/00000000-0000-0000-0000-000000000000/explain",
               404, {}), ("DELETE", "/cv/00000000-0000-0000-0000-000000000000", 404, {})]
    for m, p, code, kw in checks:
        got = r.call(m, p, "lỗi", **kw).status_code
        assert got == code, f"{m} {p} -> {got} (can {code})"
    return f"{len(checks)} lỗi trả đúng mã"


@scenario
def concurrent_requests(r: Runner) -> str:
    jds = (r.open_jds * 2)[:8]
    errs: list[str] = []

    def go(j):
        try:
            r.match(j, N=10)
        except AssertionError as e:
            errs.append(str(e))

    t = time.perf_counter()
    ths = [threading.Thread(target=go, args=(j,)) for j in jds]
    for th in ths:
        th.start()
    for th in ths:
        th.join()
    assert not errs, errs[:2]
    return f"8 request song song OK trong {time.perf_counter() - t:.1f}s (khoá chung -> chạy tuần tự)"


# --------------------------------------------------------------------------- chay


def run_all(base: str, state: dict, only: list[str] | None = None, log=print) -> tuple[list[Result], dict]:
    r = Runner(base, state)
    results = []
    try:
        for name, fn in SCENARIOS:
            if only and name not in only:
                continue
            t = time.perf_counter()
            try:
                detail, ok = fn(r), True
            except Exception as e:  # noqa: BLE001
                detail, ok = f"{type(e).__name__}: {e}", False
            res = Result(name, ok, round(time.perf_counter() - t, 2), detail)
            results.append(res)
            log(f"{'PASS' if ok else 'FAIL'} {name:22s} {res.seconds:6.1f}s  {detail}")
    finally:
        r.cleanup()
    lat = {k: {"n": len(v), "p50_ms": round(statistics.median(v) * 1000),
               "p95_ms": round(sorted(v)[max(0, int(len(v) * 0.95) - 1)] * 1000), "max_ms": round(max(v) * 1000)}
           for k, v in sorted(r.latency.items())}
    return results, lat


def to_markdown(results: list[Result], lat: dict, base: str, state: dict) -> str:
    ok = sum(r.ok for r in results)
    out = [f"# Kịch bản API trên DB demo `{state['db_name']}` ({base})", "",
           f"- {ok}/{len(results)} kịch bản đạt · KB `{state['kb_version']}` · encoder"
           f" {'FakeEncoder' if state['fake_encoder'] else 'bge-m3'} · {len(state['cv'])} CV gốc, {len(state['jd'])} JD", "",
           "| Kịch bản | Kết quả | Thời gian (s) | Chi tiết |", "| --- | --- | --- | --- |"]
    out += [f"| {r.name} | {'✅' if r.ok else '❌'} | {r.seconds} | {r.detail.replace('|', '/')} |" for r in results]
    out += ["", "## Độ trễ theo endpoint", "", "| Endpoint | Số lần | p50 (ms) | p95 (ms) | max (ms) |",
            "| --- | --- | --- | --- | --- |"]
    out += [f"| {k} | {v['n']} | {v['p50_ms']} | {v['p95_ms']} | {v['max_ms']} |" for k, v in lat.items()]
    return "\n".join(out) + "\n"


def write_report(path: str | Path, md: str) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(md, encoding="utf-8")

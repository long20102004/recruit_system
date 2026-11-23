"""Doi chieu ket qua API voi JSON GOC cua CV / JD demo (data/demo/), de tu danh gia loc co tot khong.

    cvmatch demo show <cv_id | jd_id | ten file>     -> JSON goc + vai tro / cap bac / so nam "that" (manifest)
    cvmatch demo inspect <run_id>                    -> bang top N cua mot lan match (run_id tra ve tu API):
                                                        moi dong kem file goc, vai tro that, so nam, dia diem,
                                                        ky nang trong CV, diem tung feature; cuoi bang thong ke
                                                        dung nhom va CV dung nhom bi xep ngoai top N.

Doc ket qua tu Postgres (rerank_run / rerank_result / rerank_feature) - khong goi lai API, khong thay doi gi.
"""

from __future__ import annotations

import json
from pathlib import Path

from cvmatch.core.db import connect

RELATED = {"Backend": {"Backend", "Fullstack"}, "Frontend": {"Frontend", "Fullstack"},
           "Fullstack": {"Fullstack", "Backend", "Frontend"}, "Data": {"Data", "AI/ML"}, "AI/ML": {"AI/ML", "Data"},
           "Mobile": {"Mobile"}, "DevOps": {"DevOps", "Backend"}, "QA": {"QA"}, "Security": {"Security", "DevOps"},
           "Business": {"Business"}, "Design": {"Design", "Frontend"}}
LEVEL = {0: "Intern", 1: "Fresher", 2: "Junior", 3: "Mid", 4: "Senior", 5: "Lead"}


class Demo:
    def __init__(self, state: dict):
        self.state = state
        self.dir = Path(state["data_dir"])
        self.cv_by_id = {}
        for sub in ("cv", "cv_updates"):
            for name, v in state.get(sub, {}).items():
                self.cv_by_id[v["cv_id"]] = {**v, "file": f"{sub}/{name}"}

    def cv_json(self, cv_id: str) -> dict | None:
        m = self.cv_by_id.get(cv_id)
        return json.loads((self.dir / m["file"]).read_text(encoding="utf-8")) if m else None

    def jd_json(self, jd_id: str) -> dict | None:
        m = self.state["jd"].get(jd_id)
        return json.loads((self.dir / "jd" / m["file"]).read_text(encoding="utf-8")) if m else None

    def show(self, key: str) -> str:
        if key in self.state["jd"]:
            return json.dumps({"_demo": self.state["jd"][key], **self.jd_json(key)}, ensure_ascii=False, indent=2)
        cid = key
        if key not in self.cv_by_id:                                      # ten file
            cid = next((c for c, v in self.cv_by_id.items() if v["file"].endswith(key)), None)
        if cid is None:
            return f"khong thay {key} trong du lieu demo (CV / JD tao qua API khong co file goc)"
        return json.dumps({"_demo": self.cv_by_id[cid], **self.cv_json(cid)}, ensure_ascii=False, indent=2)


def _skills_of(cv: dict | None) -> list[str]:
    return list((cv or {}).get("skills") or [])


def _fmt(x) -> str:
    return "–" if x is None else f"{x:.2f}"


def inspect_run(state: dict, run_id: str, *, show_all: bool = False) -> str:
    d = Demo(state)
    with connect(state["db_url"]) as conn:
        run = conn.execute("SELECT direction, n, config_json FROM rerank_run WHERE run_id = %s", (run_id,)).fetchone()
        if run is None:
            return f"khong co rerank run {run_id} (dung `run_id` trong ket qua POST /match/...)"
        feats = conn.execute("SELECT item_id, features_json, missing_json, detail_json, gate_cap FROM rerank_feature"
                             " WHERE run_id = %s", (run_id,)).fetchall()
    cj = run["config_json"]
    rows = sorted(feats, key=lambda r: r["detail_json"]["rank"])
    N = run["n"]
    if run["direction"] == "cv_to_jd":
        return _inspect_reverse(d, cj, rows, N)
    jd_id = cj["jd_id"]
    jd = d.jd_json(jd_id) or {}
    jm = state["jd"].get(jd_id, {})
    g = jm.get("group")
    req = [s["name"] if isinstance(s, dict) else s for s in jd.get("skills", [])
           if not isinstance(s, dict) or s.get("required", True)]
    out = [f"# Run `{run_id}` · JD {jd_id} v{cj['jd_version']}: {jd.get('title', '?')}", "",
           f"- JD: nhóm **{g or '?'}** · cấp {jm.get('level')} · min_years {jd.get('min_years')} · {jd.get('location')}"
           f" ({jd.get('work_mode', '-')}) · kỹ năng bắt buộc: {', '.join(req) or '-'}",
           f"- Pool rerank: {len(rows)} CV · top N = {N} · file gốc: `data/demo/jd/{jm.get('file', '?')}`", "",
           "| Hạng | Điểm | Trần | File gốc | Nhóm thật | Cấp | Năm | Địa điểm | Kỹ năng CV | A1 | B4 | B1 | B2 | Cờ |",
           "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    shown = rows if show_all else rows[:N]
    for r in shown:
        m = d.cv_by_id.get(r["item_id"], {})
        f = r["features_json"]
        ok = "✅" if m.get("group") in RELATED.get(g, {g}) else "❌"
        out.append(f"| {r['detail_json']['rank']} | {r['detail_json']['score']} | {r['gate_cap']} |"
                   f" {m.get('file', r['item_id'][:8]).split('/')[-1]} | {ok} {m.get('group')} |"
                   f" {LEVEL.get(m.get('level'), '?')} | {m.get('years', '?')} | {m.get('location', '?')} |"
                   f" {', '.join(_skills_of(d.cv_json(r['item_id']))[:6])} | {_fmt(f.get('A1'))} | {_fmt(f.get('B4'))} |"
                   f" {_fmt(f.get('B1'))} | {_fmt(f.get('B2'))} | {', '.join(r['detail_json'].get('flags', []))} |")
    if g:
        rel = RELATED.get(g, {g})
        top = [d.cv_by_id.get(r["item_id"], {}).get("group") for r in rows[:N]]
        p10 = sum(1 for x in top[:10] if x in rel) / max(1, min(10, len(top)))
        pN = sum(1 for x in top if x in rel) / max(1, len(top))
        replaced = {f"cv/{v['updates']}" for v in state.get("cv_updates", {}).values()}   # ban cu da co ban 2
        same_all = [c for c, v in d.cv_by_id.items() if v.get("group") == g and v.get("status") == "ok"
                    and v["file"] not in replaced]
        in_pool = {r["item_id"] for r in rows}
        missed = [r for r in rows[N:] if d.cv_by_id.get(r["item_id"], {}).get("group") == g]
        out += ["", "## Thống kê lọc", "",
                f"- Top 10 đúng nhóm (hoặc lân cận {sorted(rel)}): **{p10:.0%}** · top {N}: **{pN:.0%}**",
                f"- CV cùng nhóm {g} trong kho: {len(same_all)} · lọt vào pool rerank: "
                f"{sum(1 for c in same_all if c in in_pool)} · nằm ngoài top {N}: {len(missed)}"]
        if missed:
            out.append("- CV cùng nhóm bị xếp ngoài top N (xem có hợp lý không - vd cấp bậc / số năm thấp):")
            for r in missed[:10]:
                m = d.cv_by_id[r["item_id"]]
                out.append(f"  - hạng {r['detail_json']['rank']} · điểm {r['detail_json']['score']} · {m['file']} ·"
                           f" {LEVEL.get(m['level'])} · {m['years']} năm · cờ {', '.join(r['detail_json'].get('flags', [])) or '-'}")
    out += ["", "Xem JSON gốc một CV: `python -m cvmatch.cli demo show <cv_id hoặc tên file>`."]
    return "\n".join(out) + "\n"


def _inspect_reverse(d: Demo, cj: dict, rows: list, N: int) -> str:
    cv_id = cj["cv_id"]
    m = d.cv_by_id.get(cv_id, {})
    cv = d.cv_json(cv_id) or {}
    out = [f"# CV → JD · CV `{cv_id}` ({m.get('file', 'không có file gốc')})", "",
           f"- CV: nhóm **{m.get('group')}** · {LEVEL.get(m.get('level'), '?')} · {m.get('years')} năm ·"
           f" {m.get('location')} · kỹ năng: {', '.join(_skills_of(cv)[:8])}", "",
           "| Hạng | Điểm | JD | Tiêu đề | Nhóm JD | Cấp JD | A1 | B4 | B2 | Cờ |",
           "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    g = m.get("group")
    for r in rows:
        jm = d.state["jd"].get(r["item_id"], {})
        f = r["features_json"]
        ok = "" if g is None else ("✅" if jm.get("group") in RELATED.get(g, {g}) else "❌")
        out.append(f"| {r['detail_json']['rank']}{' (ngoài N)' if r['detail_json']['rank'] > N else ''} |"
                   f" {r['detail_json']['score']} | {r['item_id']} | {jm.get('title', '?')} | {ok} {jm.get('group')} |"
                   f" {LEVEL.get(jm.get('level'), '?')} | {_fmt(f.get('A1'))} | {_fmt(f.get('B4'))} | {_fmt(f.get('B2'))} |"
                   f" {', '.join(r['detail_json'].get('flags', []))} |")
    return "\n".join(out) + "\n"

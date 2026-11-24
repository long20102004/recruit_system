"""Sinh Postman collection (v2.1) + environment cho API demo, dung cv_id / jd_id THAT trong `state.json`.

    cvmatch demo postman      -> data/demo/postman/cvmatch_demo.postman_collection.json
                                 data/demo/postman/cvmatch_demo.postman_environment.json
Import ca hai file vao Postman, chon environment "cvmatch demo", chay tung request hoac Run collection.

Cac request noi nhau qua bien: match -> luu `run_id`, `top_cv_id`; tao CV -> luu `new_cv_id`... Moi request co
`pm.test` kiem ma HTTP va dang du lieu. Request thay doi du lieu dung email / jd_id co dau thoi gian (chay lai
khong bi trung) va thu muc cuoi don dep (xoa CV vua tao, dong JD vua tao).
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

SCHEMA = "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"


def _req(name: str, method: str, path: str, *, body=None, tests: list[str] | None = None, pre: list[str] | None = None,
         desc: str = "", query: dict | None = None) -> dict:
    raw = "{{baseUrl}}" + path + ("?" + "&".join(f"{k}={v}" for k, v in query.items()) if query else "")
    url = {"raw": raw, "host": ["{{baseUrl}}"], "path": [p for p in path.strip("/").split("/") if p]}
    if query:
        url["query"] = [{"key": k, "value": str(v)} for k, v in query.items()]
    item = {"name": name, "request": {"method": method, "header": [], "url": url, "description": desc}, "event": []}
    if body is not None:
        item["request"]["header"].append({"key": "Content-Type", "value": "application/json"})
        item["request"]["body"] = {"mode": "raw", "raw": json.dumps(body, ensure_ascii=False, indent=2),
                                   "options": {"raw": {"language": "json"}}}
    if pre:
        item["event"].append({"listen": "prerequest", "script": {"type": "text/javascript", "exec": pre}})
    if tests:
        item["event"].append({"listen": "test", "script": {"type": "text/javascript", "exec": tests}})
    return item


def _status(code: int) -> str:
    return f'pm.test("HTTP {code}", () => pm.response.to.have.status({code}));'


def _folder(name: str, items: list[dict], desc: str = "") -> dict:
    return {"name": name, "description": desc, "item": items}


def build(state: dict, base_url: str = "http://127.0.0.1:8090") -> tuple[dict, dict]:
    data_dir = Path(state["data_dir"])
    jd_open = [j for j, v in state["jd"].items() if v["status"] == "open"]
    pick_jd = lambda role: next(j for j in jd_open if state["jd"][j]["role"] == role)  # noqa: E731
    jd_java, jd_fe, jd_data = pick_jd("java"), pick_jd("frontend"), pick_jd("data_eng")
    cvs = state["cv"]
    pick_cv = lambda role: next(v["cv_id"] for v in cvs.values()  # noqa: E731
                                if v["role"] == role and v["level"] >= 3 and v["status"] == "ok"
                                and "no_diacritics" not in v["flags"])
    sample_name = next(n for n, v in cvs.items() if v["role"] == "frontend" and v["level"] >= 3
                       and "alt_fields" not in v["flags"] and "no_diacritics" not in v["flags"])
    sample_cv = json.loads((data_dir / "cv" / sample_name).read_text(encoding="utf-8"))
    sample_cv["email"] = "{{new_email}}"
    sample_cv["phone"] = None
    sample_cv["full_name"] = "Ứng viên Postman"
    cv_v2 = copy.deepcopy(sample_cv)
    cv_v2["summary"] = (cv_v2.get("summary") or "") + " Mới bổ sung dự án Next.js."
    preview_cv = copy.deepcopy(sample_cv)
    preview_cv["email"] = "preview@example.com"
    jd_body = {"jd_id": "{{new_jd_id}}", "title": "Senior Backend Developer (Java)", "location": "TP.HCM",
               "work_mode": "hybrid", "min_years": 4, "level": "Senior",
               "skills": [{"name": "Java", "required": True, "importance": "core"},
                          {"name": "Spring Boot", "required": True, "importance": "core"},
                          {"name": "PostgreSQL", "required": True, "importance": "medium"},
                          {"name": "Kafka", "required": False, "importance": "minor"}],
               "requirements": ["Tối thiểu 4 năm kinh nghiệm backend", "Có kinh nghiệm thiết kế hệ thống chịu tải cao"],
               "responsibilities": ["Thiết kế và phát triển REST API cho hệ thống thanh toán",
                                    "Tối ưu hiệu năng truy vấn cơ sở dữ liệu PostgreSQL",
                                    "Xây dựng luồng xử lý sự kiện bất đồng bộ với Kafka"],
               "status": "open"}
    jd_v2 = copy.deepcopy(jd_body)
    jd_v2["responsibilities"].append("Hướng dẫn thành viên mới trong nhóm backend")

    save_match = [_status(200),
                  "const b = pm.response.json();",
                  'pm.test("co ket qua, hang 1..n", () => { pm.expect(b.items.length).to.be.above(0);'
                  ' b.items.forEach((it, i) => pm.expect(it.rank).to.eql(i + 1)); });',
                  'pm.test("diem giam dan", () => { for (let i = 1; i < b.items.length; i++)'
                  ' pm.expect(b.items[i].score).to.be.at.most(b.items[i-1].score); });',
                  'pm.collectionVariables.set("run_id", b.run_id);',
                  'pm.collectionVariables.set("top_cv_id", b.items[0].cv_id);',
                  'if (b.items.length > 1) pm.collectionVariables.set("second_cv_id", b.items[1].cv_id);']
    job_poll = [_status(200), "const j = pm.response.json();",
                'pm.test("job co trang thai", () => pm.expect(["queued","running","done","failed"]).to.include(j.status));',
                'if (j.status === "queued" || j.status === "running") { setTimeout(() => {}, 1000);'
                ' pm.execution && pm.execution.setNextRequest ? pm.execution.setNextRequest(pm.info.requestName)'
                ' : postman.setNextRequest(pm.info.requestName); }']

    items = [
        _folder("0. Suc khoe", [
            _req("GET /health", "GET", "/health", tests=[
                _status(200), "const h = pm.response.json();",
                'pm.test("status ok + co CV", () => { pm.expect(h.status).to.eql("ok"); pm.expect(h.n_cv).to.be.above(0); });'],
                desc="Phien ban (KB, pipeline, model, BERTScore, rerank), so CV trong chi muc, so JD mo."),
        ]),
        _folder("1. HR: JD -> CV", [
            _req("Match JD Java (N=10)", "POST", "/match/jd/{{jd_java}}", body={"N": 10, "ref_ym": "2026-11"},
                 tests=save_match, desc="Retrieve top K -> Rerank -> top N. Luu run_id, top_cv_id cho request sau."),
            _req("Giai thich CV hang 1", "GET", "/match/{{run_id}}/cv/{{top_cv_id}}/explain", tests=[
                _status(200), "const e = pm.response.json();",
                'pm.test("van ban bat dau bang Diem", () => pm.expect(e.text).to.match(/^Điểm \\d+\\/100/));',
                'pm.test("dung CV", () => pm.expect(e.cv_id).to.eql(pm.collectionVariables.get("top_cv_id")));',
                'console.log(e.text);']),
            _req("Giai thich (bo qua cache)", "GET", "/match/{{run_id}}/cv/{{second_cv_id}}/explain",
                 query={"force": "true"}, tests=[_status(200)]),
            _req("Match JD Frontend, loc Ha Noi + >= 3 nam", "POST", "/match/jd/{{jd_fe}}",
                 body={"N": 20, "hard_filters": {"location": "Hà Nội", "min_years": 3, "allow_remote": False}},
                 tests=[_status(200), "const b = pm.response.json();",
                        'pm.test("pool nho hon toan kho", () => pm.expect(b.n_pool).to.be.above(0));']),
            _req("Match JD Java, loai tru CV hang 1", "POST", "/match/jd/{{jd_java}}",
                 body={"N": 10, "exclude_cv_ids": ["{{top_cv_id}}"]},
                 tests=[_status(200), "const b = pm.response.json();",
                        'pm.test("khong con CV bi loai", () => pm.expect(b.items.map(i => i.cv_id))'
                        '.to.not.include(pm.collectionVariables.get("top_cv_id")));']),
            _req("Match JD Data, K=50 N=5, chi dense + bm25", "POST", "/match/jd/{{jd_data}}",
                 body={"K": 50, "N": 5, "views": ["dense", "bm25"]},
                 tests=[_status(200), 'pm.test("5 ket qua", () => pm.expect(pm.response.json().items.length).to.eql(5));']),
            _req("Match chay nen (202 + job_id)", "POST", "/match/jd/{{jd_java}}", body={"N": 30, "background": True},
                 tests=[_status(202), 'pm.collectionVariables.set("job_id", pm.response.json().job_id);']),
            _req("Xem job (lap lai toi khi done)", "GET", "/jobs/{{job_id}}", tests=job_poll),
        ], "Chieu cho HR: mot JD tim CV phu hop."),
        _folder("2. Ung vien: CV -> JD", [
            _req("Goi y JD cho CV Java", "POST", "/match/cv/{{cv_java}}", body={"N": 5, "ref_ym": "2026-11"}, tests=[
                _status(200), "const b = pm.response.json();",
                'pm.test("co JD goi y", () => pm.expect(b.items.length).to.be.above(0));',
                'pm.collectionVariables.set("rev_run_id", b.run_id);',
                'pm.collectionVariables.set("top_jd_id", b.items[0].jd_id);']),
            _req("Giai thich cho ung vien", "GET", "/match/{{rev_run_id}}/jd/{{top_jd_id}}/explain", tests=[
                _status(200), "const e = pm.response.json();",
                'pm.test("giong ung vien, khong hien diem", () => { pm.expect(e.audience).to.eql("candidate");'
                ' pm.expect(e.text).to.not.include("/100"); });', 'console.log(e.text);']),
            _req("Goi y JD, chi remote, loai JD hang 1", "POST", "/match/cv/{{cv_java}}",
                 body={"hard_filters": {"work_mode": "remote"}, "exclude_jd_ids": ["{{top_jd_id}}"]},
                 tests=[_status(200)]),
            _req("Xem truoc CV tam (khong luu)", "POST", "/match/cv:preview",
                 body={"cv": preview_cv, "N": 5, "n_explain": 2}, tests=[
                     _status(200), "const b = pm.response.json();",
                     'pm.test("co goi y + giai thich", () => { pm.expect(b.status).to.eql("ok");'
                     ' pm.expect(b.explanations.length).to.be.at.most(2); });']),
        ], "Chieu cho ung vien: mot CV tim JD dang mo."),
        _folder("3. Vong doi CV", [
            _req("Nap CV moi", "POST", "/cv", body=sample_cv,
                 pre=['pm.collectionVariables.set("new_email", "postman-" + Date.now() + "@example.com");'],
                 tests=[_status(200), "const b = pm.response.json();",
                        'pm.test("ok, version 1", () => { pm.expect(b.status).to.eql("ok"); pm.expect(b.version).to.eql(1); });',
                        'pm.collectionVariables.set("new_cv_id", b.cv_id);'],
                 desc="Email co dau thoi gian -> moi lan chay la nguoi moi."),
            _req("Nap lai y het -> duplicate", "POST", "/cv", body=sample_cv, tests=[
                _status(200), "const b = pm.response.json();",
                'pm.test("duplicate, cung cv_id", () => { pm.expect(b.status).to.eql("duplicate");'
                ' pm.expect(b.cv_id).to.eql(pm.collectionVariables.get("new_cv_id")); });']),
            _req("Ban moi cung email -> version 2", "POST", "/cv", body=cv_v2, tests=[
                _status(200), "const b = pm.response.json();",
                'pm.test("version 2, cv_id moi", () => { pm.expect(b.version).to.eql(2);'
                ' pm.expect(b.cv_id).to.not.eql(pm.collectionVariables.get("new_cv_id")); });',
                'pm.collectionVariables.set("new_cv_id_v2", b.cv_id);']),
            _req("Goi y JD cho CV vua nap", "POST", "/match/cv/{{new_cv_id_v2}}", body={"N": 3}, tests=[_status(200)]),
            _req("CV sai schema -> 422", "POST", "/cv", body={"experiences": "khong phai danh sach"}, tests=[
                _status(422), 'pm.test("invalid", () => pm.expect(pm.response.json().status).to.eql("invalid"));']),
            _req("Nap lo 2 CV (chay nen)", "POST", "/cv/batch", body={"items": [
                {**sample_cv, "email": "{{new_email}}.b1", "summary": "Lập trình viên frontend, React."},
                {**sample_cv, "email": "{{new_email}}.b2", "summary": "Lập trình viên frontend, Vue."}]},
                 tests=[_status(202), 'pm.collectionVariables.set("job_id", pm.response.json().job_id);']),
            _req("Xem job nap lo", "GET", "/jobs/{{job_id}}", tests=job_poll + [
                'if (j.status === "done") { const ids = j.result.results.map(r => r.cv_id);'
                ' pm.collectionVariables.set("batch_cv_ids", JSON.stringify(ids)); }']),
        ]),
        _folder("4. Vong doi JD", [
            _req("Nap JD moi", "POST", "/jd", body=jd_body,
                 pre=['pm.collectionVariables.set("new_jd_id", "PM-" + Date.now());'],
                 tests=[_status(200), 'pm.test("ok v1", () => pm.expect(pm.response.json().version).to.eql(1));']),
            _req("Nap lai y het -> unchanged", "POST", "/jd", body=jd_body, tests=[
                _status(200), 'pm.test("unchanged", () => pm.expect(pm.response.json().status).to.eql("unchanged"));']),
            _req("Sua JD -> version 2", "POST", "/jd", body=jd_v2, tests=[
                _status(200), 'pm.test("v2", () => pm.expect(pm.response.json().version).to.eql(2));']),
            _req("Match JD vua tao", "POST", "/match/jd/{{new_jd_id}}", body={"N": 10}, tests=[
                _status(200), 'pm.test("dung version 2", () => pm.expect(pm.response.json().jd_version).to.eql(2));']),
            _req("Dong JD", "PATCH", "/jd/{{new_jd_id}}/status", body={"status": "closed"}, tests=[
                _status(200), 'pm.test("closed", () => pm.expect(pm.response.json().status).to.eql("closed"));']),
        ]),
        _folder("5. Loi", [
            _req("JD khong ton tai -> 404", "POST", "/match/jd/KHONG-CO", body={}, tests=[_status(404)]),
            _req("CV khong ton tai -> 404", "POST", "/match/cv/00000000-0000-0000-0000-000000000000", body={},
                 tests=[_status(404)]),
            _req("K = 0 -> 422", "POST", "/match/jd/{{jd_java}}", body={"K": 0}, tests=[_status(422)]),
            _req("ref_ym sai dinh dang -> 422", "POST", "/match/jd/{{jd_java}}", body={"ref_ym": "11-2026"},
                 tests=[_status(422)]),
            _req("Trang thai JD sai -> 422", "PATCH", "/jd/{{jd_java}}/status", body={"status": "xoa"},
                 tests=[_status(422)]),
            _req("Job khong ton tai -> 404", "GET", "/jobs/khong-co", tests=[_status(404)]),
        ]),
        _folder("6. Don dep", [
            _req("Xoa CV v2 vua tao", "DELETE", "/cv/{{new_cv_id_v2}}", tests=[_status(200)]),
            _req("Xoa CV v1 vua tao", "DELETE", "/cv/{{new_cv_id}}", tests=[
                'pm.test("200 hoac 404", () => pm.expect([200, 404]).to.include(pm.response.code));']),
            _req("Xoa 2 CV nap lo", "DELETE", "/cv/{{batch_cv_id}}",
                 pre=['let ids = JSON.parse(pm.collectionVariables.get("batch_cv_ids") || "[]");',
                      'pm.collectionVariables.set("batch_cv_id", ids.length ? ids[0] : "00000000-0000-0000-0000-000000000000");'],
                 tests=['let ids = JSON.parse(pm.collectionVariables.get("batch_cv_ids") || "[]"); ids.shift();',
                        'pm.collectionVariables.set("batch_cv_ids", JSON.stringify(ids));',
                        'if (ids.length) { pm.execution && pm.execution.setNextRequest ?'
                        ' pm.execution.setNextRequest(pm.info.requestName) : postman.setNextRequest(pm.info.requestName); }']),
        ], "Chay cuoi de kho demo giu nguyen."),
    ]
    variables = {"jd_java": jd_java, "jd_fe": jd_fe, "jd_data": jd_data, "cv_java": pick_cv("java"),
                 "cv_frontend": pick_cv("frontend"), "run_id": "", "top_cv_id": "", "second_cv_id": "", "job_id": "",
                 "rev_run_id": "", "top_jd_id": "", "new_email": "", "new_cv_id": "", "new_cv_id_v2": "",
                 "new_jd_id": "", "batch_cv_ids": "[]", "batch_cv_id": ""}
    collection = {"info": {"name": "cvmatch demo", "schema": SCHEMA,
                           "description": f"API cvmatch tren DB demo `{state['db_name']}` (KB {state['kb_version']}). "
                                          "Chay `cvmatch demo serve` truoc. Chay theo thu tu thu muc 0 -> 6."},
                  "item": items, "variable": [{"key": k, "value": v} for k, v in variables.items()]}
    env = {"name": "cvmatch demo", "values": [{"key": "baseUrl", "value": base_url, "enabled": True}],
           "_postman_variable_scope": "environment"}
    return collection, env


def write(state: dict, out_dir: str | Path, base_url: str = "http://127.0.0.1:8090") -> list[Path]:
    col, env = build(state, base_url)
    d = Path(out_dir)
    d.mkdir(parents=True, exist_ok=True)
    p1, p2 = d / "cvmatch_demo.postman_collection.json", d / "cvmatch_demo.postman_environment.json"
    p1.write_text(json.dumps(col, ensure_ascii=False, indent=1), encoding="utf-8")
    p2.write_text(json.dumps(env, ensure_ascii=False, indent=1), encoding="utf-8")
    return [p1, p2]

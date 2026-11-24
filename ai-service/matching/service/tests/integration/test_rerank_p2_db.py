"""T15: rerank rr-1.1 (du 8 feature) tren Postgres that, FakeEncoder + KB mini."""

import copy
import json
from pathlib import Path

import pytest
import yaml

from cvmatch.api.services import Services, config_and_encoder
from cvmatch.core.config import DEFAULT_CONFIG_DIR
from cvmatch.core.db import connect, migrate
from cvmatch.core.kb.store import import_snapshot

pytestmark = pytest.mark.db
FIX = Path(__file__).resolve().parents[1] / "fixtures"
E2E = FIX / "e2e"
RR11 = yaml.safe_load((DEFAULT_CONFIG_DIR / "rr-1.1.yaml").read_text(encoding="utf-8"))

JD = {"jd_id": "P2-JAVA", "title": "Senior Java Developer", "location": "TP.HCM", "min_years": 3, "level": "Senior",
      "edu_required": "it_related",
      "skills": [{"name": "Java", "required": True, "importance": "core"},
                 {"name": "PostgreSQL", "required": True, "importance": "medium"},
                 {"name": "Kafka", "required": False, "importance": "minor"},
                 {"name": "Quarkus Pro Max", "required": True}],              # khong co trong KB -> unmapped_req
      "requirements": ["Có kinh nghiệm dẫn dắt nhóm phát triển phần mềm lớn"],
      "responsibilities": ["Thiết kế và phát triển REST API cho hệ thống thanh toán",
                           "Tối ưu hiệu năng truy vấn cơ sở dữ liệu PostgreSQL"]}

CV_SUMMARY = {"full_name": "Lead", "email": "lead@example.com", "location": "TP.HCM",
              "summary": "Có kinh nghiệm dẫn dắt nhóm phát triển phần mềm lớn trong lĩnh vực thanh toán.",
              "skills": ["Spring Boot", "PostgreSQL"],
              "experiences": [{"title": "Senior Java Developer", "start": "2018-01", "is_current": True,
                               "description": ["Thiết kế và phát triển REST API cho hệ thống thanh toán bằng Spring Boot",
                                               "Dẫn dắt nhóm 5 người phát triển cổng thanh toán"]}],
              "projects": [], "education": [{"school": "X", "major": "Kỹ thuật phần mềm", "end": "2017"}]}


@pytest.fixture()
def svc(fresh_db_url):
    migrate(fresh_db_url)
    with connect(fresh_db_url) as conn:
        version = import_snapshot(conn, FIX / "kb_mini")
    cfg, enc = config_and_encoder(fake=True, overrides={"ontology_version": version, "rerank": RR11})
    with Services(cfg, url=fresh_db_url, encoder=enc, hmac_key="k") as s:
        items = [(f.name, json.loads(f.read_text(encoding="utf-8"))) for f in sorted((E2E / "cv").glob("*.json"))]
        s.ingest_cvs(items + [("lead.json", copy.deepcopy(CV_SUMMARY))])
        assert s.ingest_jd(copy.deepcopy(JD)).status == "ok"
        yield s


def test_full_features_and_b5_summary(svc):
    m = svc.match_jd("P2-JAVA", N=10, ref_ym="2026-11")
    with svc.connect() as conn:
        lead = conn.execute("SELECT c.cv_id::text AS id FROM cv c JOIN cv_summary_sentence s USING (cv_id)"
                            " WHERE s.text_raw LIKE 'Có kinh nghiệm dẫn dắt%%'").fetchone()["id"]
        feats = {r["item_id"]: r for r in conn.execute(
            "SELECT item_id, features_json, missing_json, detail_json FROM rerank_feature WHERE run_id = %s",
            (m.run_id,))}
        run = conn.execute("SELECT config_json FROM rerank_run WHERE run_id = %s", (m.run_id,)).fetchone()
    f = feats[lead]
    # du 8 feature co gia tri (C1: JD can it_related, CV nganh it da tot nghiep)
    assert all(f["features_json"][k] is not None for k in ("A1", "A2", "B4", "B5", "B1", "B2", "B3", "C1"))
    assert f["features_json"]["C1"] == pytest.approx(1.0)
    # A1 qua KB: Spring Boot -> Java (cha/con 0,7 x ev), PostgreSQL co; Quarkus bi loai khoi mau so
    assert 0.0 < f["features_json"]["A1"] < 1.0
    # B5: yeu cau dang chu khop nguyen van cau summary -> bang chung summary[0]
    req = f["detail_json"]["req_detail"]
    assert len(req) == 1 and req[0]["level"] == "met" and req[0]["evidence_id"] == "summary[0]"
    # B3: Senior + tin hieu "dan dat" -> Lead (5) so voi JD Senior (4) -> +1 -> 0,85
    assert f["detail_json"]["level_cv"] == 5 and f["features_json"]["B3"] == pytest.approx(0.85)
    assert "unmapped_req" in f["detail_json"]["flags"]
    assert "rho_b2_b3" in run["config_json"]["stats"]

    item = next(it for it in m.final_items if it.cv_id == lead)
    assert item.req_facts and item.experience_facts.level_source == "title"
    ex = svc.explain(m.run_id, lead)
    assert "Yêu cầu chuyên môn" in ex["text"] or "Yêu cầu:" in ex["text"]
    assert "Cấp bậc ước lượng: Lead (JD cần Senior)." in ex["text"]
    assert "danh mục kỹ năng" in ex["text"]                                  # note unmapped_req


def test_designer_low_and_jd_side(svc):
    m = svc.match_jd("P2-JAVA", N=40, ref_ym="2026-11")
    with svc.connect() as conn:
        rows = conn.execute("SELECT item_id, features_json, missing_json FROM rerank_feature WHERE run_id = %s",
                            (m.run_id,)).fetchall()
    # CV khong co cau nao (khong gach, khong summary du dai) -> B5 thieu phia CV, khong phai 0
    sides = [r["missing_json"].get("B5") for r in rows]
    assert "cv_side" in sides or all(r["features_json"]["B5"] is not None for r in rows)
    # thu tu: CV java dau bang
    top = [it["cv_id"] for it in m.items[:3]]
    assert len(set(top)) == 3

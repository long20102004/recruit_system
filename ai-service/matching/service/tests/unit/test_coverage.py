"""T07: do phu Module 1 tren CV/JD tong hop co / thieu truong."""

import json
from pathlib import Path

import pytest

from cvmatch.core.config import load_config
from cvmatch.evaluation.coverage import coverage_from_dirs, cv_stats, date_shape, jd_stats, run_coverage

FIX = Path(__file__).resolve().parents[1] / "fixtures"

FULL = {   # du moi truong; description dang mang
    "full_name": "A", "summary": "Lập trình viên backend",
    "experiences": [{"title": "Java Developer", "start": "03/2021", "end": "Hiện tại",
                     "description": ["Xây dựng API thanh toán bằng Spring Boot", "Tối ưu truy vấn PostgreSQL cho báo cáo"],
                     "technologies": ["Java"]}],
    "projects": [{"name": "Shop", "description": "Làm web bán hàng bằng React. Viết test tự động cho giao diện."}],
    "education": [{"school": "ĐH X", "major": "CNTT", "end": "2020"}],
}
PARTIAL = {  # co kinh nghiem du ngay nhung khong co gach (qua ngan), hoc van thieu major, ngay la
    "full_name": "B",
    "experiences": [{"title": "Tester", "start": "2022-01", "end": "2023-06", "description": ["Test"]},
                    {"title": "QA", "start": "mùa hè 2019", "end": "2020"}],
    "education": [{"school": "ĐH Y", "end": "2021"}],
}
EMPTY = {"full_name": "C", "skills": ["Python"],   # chi co ky nang; kinh nghiem thieu end/is_current
         "experiences": [{"title": "Dev", "start": "2021"}]}
BAD = {"experiences": "khong phai danh sach"}

JD_FULL = {"jd_id": "J1", "title": "Backend", "min_years": 3, "level": "Senior", "role_group": "Backend",
           "edu_required": "Đại học CNTT", "responsibilities": ["Phát triển API"],
           "skills": [{"name": "Java", "required": True, "importance": "core"}]}
JD_MIN = {"jd_id": "J2", "title": "Dev", "skills": ["Java", "SQL"]}


@pytest.fixture(scope="module")
def cfg():
    return load_config()


def _report(cfg, cvs, jds):
    from cvmatch.evaluation.coverage import load_coverage_config

    return run_coverage([(f"cv{i}", c) for i, c in enumerate(cvs)], [(f"jd{i}", j) for i, j in enumerate(jds)],
                        cov_cfg=load_coverage_config(cfg.config_dir), min_words=cfg.prep.bullet.min_words,
                        no_diac_threshold=cfg.prep.no_diacritics.threshold,
                        current_features=list(cfg.rerank.features_enabled))


def test_cv_stats_rows(cfg):
    f = cv_stats(FULL, min_words=4, no_diac_threshold=0.05)
    assert f.has == {"cv_exp_dated": True, "cv_has_bullet": True, "cv_edu_major_end": True, "cv_item_kind": True,
                     "cv_has_technologies": True, "cv_date_unparsed": False, "cv_no_diacritics": False}
    assert f.n_bullets == 4 and f.desc_forms == {"list": 1, "str": 1}
    p = cv_stats(PARTIAL, min_words=4, no_diac_threshold=0.05)
    assert p.has["cv_exp_dated"] and not p.has["cv_has_bullet"] and not p.has["cv_edu_major_end"]
    assert p.has["cv_date_unparsed"] and not p.has["cv_item_kind"]
    e = cv_stats(EMPTY, min_words=4, no_diac_threshold=0.05)
    assert not e.has["cv_exp_dated"] and not any(e.has.values())
    assert not cv_stats(BAD, min_words=4, no_diac_threshold=0.05).valid


def test_rates_and_feature_decisions(cfg):
    rep = _report(cfg, [FULL, PARTIAL, EMPTY, BAD], [JD_FULL, JD_MIN])
    assert (rep.n_cv, rep.n_cv_files, rep.n_jd) == (3, 4, 2)
    assert rep.rates["cv_exp_dated"] == pytest.approx(2 / 3)
    assert rep.rates["cv_has_bullet"] == pytest.approx(1 / 3)
    assert rep.rates["cv_edu_major_end"] == pytest.approx(1 / 3)
    assert rep.rates["cv_date_unparsed"] == pytest.approx(1 / 3)
    assert rep.rates["jd_responsibilities"] == 0.5 and rep.rates["jd_skill_required"] == 0.5
    assert rep.rates["jd_min_years"] == 0.5
    assert rep.feature_on("B4") == (False, ["cv_has_bullet", "jd_responsibilities"])
    assert rep.feature_on("B1") == (False, ["cv_exp_dated"])     # 66,7% < 80%
    assert rep.feature_on("A1") == (True, [])
    assert rep.suggested_features() == ["A1"]
    assert len(rep.invalid) == 1 and rep.invalid[0][0] == "cv3"
    md = rep.to_markdown()
    assert "features_enabled: [A1]" in md and "66.7%" in md


def test_all_full_keeps_features(cfg):
    rep = _report(cfg, [FULL] * 3, [JD_FULL])
    assert rep.suggested_features() == list(cfg.rerank.features_enabled)
    assert rep.bullets_per_cv == 4 and rep.bullet_len_p50 is not None


def test_no_jd_keeps_jd_dependent(cfg):
    rep = _report(cfg, [FULL], [])
    assert rep.rates["jd_responsibilities"] is None
    assert rep.feature_on("B4") == (True, [])  # dong phia CV dat, dong JD chua co du lieu -> khong tat


def test_date_shapes():
    assert date_shape("Tháng 3/2022") == "tháng 9/9999"
    assert date_shape("Mar 2021") == "Mon 9999"
    assert date_shape(2020) == "int:9999"
    assert jd_stats({"jd_id": 1, "title": "x"}).valid is False


def test_fixture_dirs(cfg, tmp_path):
    rep = coverage_from_dirs(FIX / "cv", FIX / "jd", cfg)
    assert rep.n_cv == 1 and rep.n_jd == 1 and rep.rates["cv_has_bullet"] == 1.0
    (tmp_path / "bad.json").write_text("{not json", encoding="utf-8")
    assert coverage_from_dirs(tmp_path, None, cfg).invalid[0][1].startswith("JSON lỗi")

"""T15: feature P2 - A1/A2 qua KB, B3, C1, B5/engine (thiet ke 07 muc 5.4-5.7, 5.10)."""

import numpy as np
import pytest

from cvmatch.core.config import load_config
from cvmatch.core.kb.rel import SkillRelations
from cvmatch.rerank.features import skill_match, sentence_match
from cvmatch.rerank.features.experience_fit import b3_level, cv_level, level_fit, level_from_years, spearman
from cvmatch.rerank.features.education import Edu, c1_education, degree_status
from cvmatch.rerank.scoring import Scored, finalize


@pytest.fixture(scope="module")
def cfg11():
    return load_config(overrides={"rerank": _rr11()})


def _rr11():
    import yaml

    from cvmatch.core.config import DEFAULT_CONFIG_DIR

    rr = yaml.safe_load((DEFAULT_CONFIG_DIR / "rr-1.1.yaml").read_text(encoding="utf-8"))
    rr["missing"] |= {"jd_side_policy": "drop"}    # ghi de len active (rr-1.2): giu chinh sach cua rr-1.1
    return rr


@pytest.fixture(scope="module")
def rels(kb_mini, cfg11):
    return SkillRelations.from_config(kb_mini, cfg11.rerank.rel)


# --------------------------------------------------------------------------- A1 / A2 qua KB


def test_rel_parent_child_score_req(rels):
    """CV co Spring Boot (con cua Java), JD can Java -> score_req = 0,7 x ev."""
    cv = {"S0002": skill_match.CvSkill("S0002", 0.8, 1, "experiences[0].description[0]")}
    v, used, opt = skill_match.score_req(["S0001"], cv, rels.rel)
    assert v == pytest.approx(0.7 * 0.8) and used.skill_id == "S0002" and opt == "S0001"
    facts = skill_match.skill_facts([skill_match.JdSkill("S0001", True, 1.0)], cv, rels.relation)
    assert facts.partial[0].relation == "child" and facts.missing == []


def test_a2_and_min_den(rels):
    jd = [skill_match.JdSkill("S0001", True, 1.0), skill_match.JdSkill("S0021", False, 0.4)]
    cv = {"S0001": skill_match.CvSkill("S0001", 1.0), "S0022": skill_match.CvSkill("S0022", 1.0)}  # RabbitMQ anh em Kafka
    assert skill_match.coverage(jd, cv, True, rels.rel) == 1.0
    assert skill_match.coverage(jd, cv, False, rels.rel) == pytest.approx(0.4)             # sibling 0,4
    assert skill_match.coverage(jd, cv, False) == 0.0                                      # khong qua KB
    assert skill_match.coverage([jd[0]], {}, False) is None                                # khong co ky nang uu tien
    # chieu CV -> JD: JD chi 1 ky nang, min_imp_sum = 3 -> 1/3 (vi du 06 muc 5.6)
    assert skill_match.coverage([jd[0]], cv, True, min_den=3.0) == pytest.approx(1 / 3)


# --------------------------------------------------------------------------- B3


def test_b3_fit_examples(cfg11):
    b3 = cfg11.rerank.b3
    assert level_fit(-1, b3) == pytest.approx(0.70) and level_fit(-2, b3) == pytest.approx(0.40)
    assert level_fit(+1, b3) == pytest.approx(0.85) and level_fit(+2, b3) == pytest.approx(0.70)
    assert level_fit(+5, b3) == pytest.approx(0.40) and level_fit(-4, b3) == 0.0
    assert level_fit(+2, b3, overqual_penalty=False) == 1.0
    assert b3_level(3, None, b3) == (None, "jd_side") and b3_level(None, 3, b3) == (None, "cv_side")


def test_cv_level_order(cfg11):
    b3, table = cfg11.rerank.b3, cfg11.prep.level_from_years
    assert cv_level(3, "title", False, 1.0, False, table, b3) == (3, "title")           # 1. chuc danh
    assert cv_level(3, "title", True, 1.0, False, table, b3) == (4, "title")            # 2. +1 pham vi
    assert cv_level(None, None, False, 3.5, False, table, b3) == (3, "years")           # 3. so nam B2
    assert cv_level(1, "inferred", False, 5.2, False, table, b3) == (4, "years")        #    bo bac suy tu tong nam
    assert cv_level(3, "title", False, 1.0, True, table, b3) == (1, "title")            # 4. tran Fresher
    assert cv_level(3, "title", False, 2.5, True, table, b3) == (3, "title")
    assert cv_level(None, None, False, None, False, table, b3) == (None, None)
    assert level_from_years(0.5, table) == 1 and level_from_years(None, table) is None


def test_spearman():
    assert spearman([0.1, 0.5, 0.9, 1.0], [0.2, 0.4, 0.8, 1.0]) == pytest.approx(1.0)
    assert spearman([1, 1, 1], [0, 1, 2]) is None and spearman([0.1, 0.2], [0.3, 0.4]) is None


# --------------------------------------------------------------------------- C1


def test_c1_examples(cfg11):
    c1 = cfg11.rerank.c1
    assert c1_education([Edu("it", "graduated")], "it_related", "2026-11", c1) == (pytest.approx(1.0), None)
    v, _ = c1_education([Edu("related", "studying", "2027-07")], "any_degree", "2026-11", c1)   # con 8 thang
    assert v == pytest.approx(0.6 * 0.7 + 0.4 * 0.7)
    v, _ = c1_education([Edu("it", "studying", "2028-06")], "any_degree", "2026-11", c1)        # con 19 thang
    assert v == pytest.approx(0.6 + 0.4 * 0.3)
    assert c1_education([Edu("it", "graduated")], None, "2026-11", c1) == (None, "jd_side")
    assert c1_education([Edu("it", "graduated")], "none", "2026-11", c1) == (None, "jd_side")
    assert c1_education([Edu(None, "graduated")], "any_degree", "2026-11", c1) == (None, "cv_side")
    # tot nghiep lau van 1,0 (khong thanh bien thay the tuoi); unknown -> coi nhu tot nghiep
    assert degree_status(Edu("it", "graduated"), "2026-11", c1) == 1.0
    assert degree_status(Edu("it", "unknown"), "2026-11", c1) == 1.0
    # lay muc tot nhat
    v, _ = c1_education([Edu("other", "graduated"), Edu("it", "graduated")], "any_degree", "2026-11", c1)
    assert v == pytest.approx(1.0)


# --------------------------------------------------------------------------- B4 engine (R-E2, R-E10)


def test_engine_cosine_and_max(cfg11):
    R = np.array([[0.70, 0.95]], np.float32)
    cos = np.array([[0.85, 0.40]], np.float32)
    b4 = cfg11.rerank.b4
    assert sentence_match.calibrated(R, b4, cos)[0].tolist() == pytest.approx([0.2, 1.0])           # bertscore
    cos_cfg = b4.model_copy(update={"engine": "cosine"})
    assert sentence_match.calibrated(R, cos_cfg, cos)[0].tolist() == pytest.approx([1.0, 0.0])
    mx = b4.model_copy(update={"engine": "max"})
    assert sentence_match.calibrated(R, mx, cos)[0].tolist() == pytest.approx([1.0, 1.0])
    ss = sentence_match.sentence_scores(R, np.ones(2, np.float32), mx, cal_base=sentence_match.calibrated(R, mx, cos))
    assert ss.c[0] == pytest.approx(1.0) and ss.best[0] == 1                               # hoa -> R lon hon


# --------------------------------------------------------------------------- 5.10 voi du 8 feature


def test_5_10_full_features(cfg11):
    assert set(cfg11.rerank.features_enabled) == {"A1", "A2", "B4", "B5", "B1", "B2", "B3", "C1"}
    r = Scored("cv", dict(A1=0.80, A2=0.50, B4=0.74, B5=0.60, B1=1.0, B2=1.0, B3=1.0, C1=None), {"C1": "jd_side"})
    finalize([r], cfg11.rerank)
    assert r.score == 79 and not r.cap_applied
    r2 = Scored("cv2", dict(A1=0.60, A2=0.50, B4=0.74, B5=0.60, B1=1.0, B2=1.0, B3=1.0, C1=None), {"C1": "jd_side"})
    finalize([r2], cfg11.rerank)
    assert r2.score == 70 and r2.cap_applied

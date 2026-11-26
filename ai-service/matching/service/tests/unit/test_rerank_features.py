"""T11: feature P1 va chot diem (thiet ke 07 muc 5.3, 5.6, 5.8-5.10)."""

import numpy as np
import pytest

from cvmatch.core.config import load_config
from cvmatch.core.contracts import FEATURES
from cvmatch.rerank.features import skill_match, sentence_match
from cvmatch.rerank.features.experience_fit import Exp, b1_role, b2_years, relevant_years, years_fit
from cvmatch.rerank.scoring import Scored, finalize, gate_cap


# chinh sach du lieu thieu cua rr-1.0 (trung vi pool, bo feature thieu phia JD); rr-1.2 thu o cuoi file (S02)
OLD_MISSING = {"rerank": {"missing": {"cv_side_policy": "pool_median", "jd_side_policy": "drop"}}}


@pytest.fixture(scope="module")
def rc():
    return load_config(overrides=OLD_MISSING).rerank


@pytest.fixture(scope="module")
def rc_all():
    return load_config(overrides={"rerank": {"features_enabled": list(FEATURES), **OLD_MISSING["rerank"]}}).rerank


def M(a, b):
    table = {frozenset(("backend", "fullstack")): 0.8, frozenset(("backend", "devops")): 0.4,
             frozenset(("backend", "frontend")): 0.3}
    if a is None or b is None:
        return None
    return 1.0 if a == b else table.get(frozenset((a, b)), 0.0)


# --------------------------------------------------------------------------- 5.10


def test_golden_formula_5_10(rc_all):
    f = dict(A1=0.80, A2=0.50, B4=0.74, B5=0.60, B1=1.0, B2=1.0, B3=1.0, C1=None)
    r = Scored("cv", f, {"C1": "jd_side"})
    finalize([r], rc_all)
    assert r.s_raw == pytest.approx(0.7542 / 0.95)          # tai lieu lam tron tu so thanh 0,754
    assert round(r.s_raw, 3) == 0.794 and r.score == 79 and r.gate_cap == 100 and not r.cap_applied

    r2 = Scored("cv", {**f, "A1": 0.6}, {"C1": "jd_side"})
    finalize([r2], rc_all)
    assert r2.gate_cap == 70 and r2.score == 70 and r2.cap_applied and "cap_applied" in r2.flags


def test_gate_thresholds(rc):
    assert [gate_cap(x, rc) for x in (None, 0.0, 0.49, 0.5, 0.69, 0.7, 1.0)] == [100, 50, 50, 70, 70, 100, 100]


def test_ranking_tiebreak(rc):
    rows = [Scored("b", {"A1": 0.8, "B4": 0.5}, {}), Scored("a", {"A1": 0.8, "B4": 0.5}, {}),
            Scored("c", {"A1": 0.9, "B4": 0.45}, {})]
    order = [r.item_id for r in finalize(rows, rc)]
    assert order == ["c", "a", "b"]           # a, b cung score/S_raw/A1 -> cv_id tang
    assert {r.item_id: r.rank for r in rows} == {"c": 1, "a": 2, "b": 3}


# --------------------------------------------------------------------------- 5.3 B4


def test_b4_example_5_3(rc):
    R = np.array([[0.84, 0.70], [0.69, 0.83]], np.float32)
    m = sentence_match.bullet_multipliers(np.array([False, False]), np.array([False, False]), rc.b4)
    ss = sentence_match.sentence_scores(R, m, rc.b4)
    assert ss.c == pytest.approx([0.76, 0.72], abs=1e-5)
    assert ss.cal[0, 1] == pytest.approx(0.20, abs=1e-5) and ss.cal[1, 0] == pytest.approx(0.16, abs=1e-5)
    ids = np.array([90001, 90002])
    assert list(ids[ss.best]) == [90001, 90002]
    assert sentence_match.aggregate(ss.c, np.ones(2, np.float32)) == pytest.approx(0.74, abs=1e-5)
    assert [sentence_match.level_of(float(c), rc.b4) for c in (0.76, 0.45, 0.1)] == ["met", "partial", "not_evidenced"]


def test_b4_multipliers_and_no_evidence(rc):
    R = np.array([[0.90, 0.80]], np.float32)
    m = sentence_match.bullet_multipliers(np.array([True, False]), np.array([False, True]), rc.b4)
    assert list(m) == pytest.approx([0.3, 0.6])
    ss = sentence_match.sentence_scores(R, m, rc.b4)
    assert ss.best[0] == 1 and ss.c[0] == pytest.approx(0.6 * 0.6)      # 0,3 x 1,0 < 0,6 x 0,6
    low = sentence_match.sentence_scores(np.array([[0.5, 0.6]], np.float32), np.ones(2, np.float32), rc.b4)
    assert low.best[0] == -1 and low.c[0] == 0 and low.R_best[0] == 0     # khong co bang chung


def test_b4_generic_weight():
    w = sentence_match.sentence_weights([False, True], 0.0)
    assert sentence_match.aggregate(np.array([0.8, 0.2]), w) == pytest.approx(0.8)
    assert sentence_match.aggregate(np.array([0.2]), sentence_match.sentence_weights([True], 0.0)) is None   # jd_side


# --------------------------------------------------------------------------- B1, B2


def test_b2_fit_examples():
    assert [years_fit(y, 3, 5) for y in (2.4, 4, 7, 12)] == pytest.approx([0.8, 1.0, 0.8, 0.6])
    assert years_fit(12, 3, None) == 1.0 and years_fit(1.5, 3, None) == pytest.approx(0.5)   # chi min
    assert years_fit(7, 3, 5, overqual_penalty=False) == 1.0
    assert years_fit(4, None, None) is None


def test_b2_months_max_overlap(rc):
    exps = [Exp("job", "backend", "2020-01", "2021-12"),                 # 24 thang cung nhom (w 1)
            Exp("job", "fullstack", "2021-01", "2022-12"),               # M 0,8 -> 0,5; chong 12 thang
            Exp("project_personal", "backend", "2023-01", "2023-12"),    # 0,3
            Exp("job", "backend", None, None)]                           # thieu ngay -> 0
    y = relevant_years(exps, "backend", M, rc.b2)
    assert y == pytest.approx((24 * 1.0 + 12 * 0.5 + 12 * 0.3) / 12)
    assert relevant_years([], "backend", M, rc.b2) == 0.0
    assert relevant_years([Exp("job", "backend", None, None)], "backend", M, rc.b2) is None
    v, side, _ = b2_years([Exp("job", "backend", None, None)], "backend", M, rc.b2, 3, None)
    assert v is None and side == "cv_side"
    v, side, _ = b2_years(exps, "backend", M, rc.b2, None, None)
    assert v is None and side == "jd_side"


def test_b1_role(rc):
    exps = [Exp("job", "backend", "2024-01", "2025-12"),       # 24 thang, gan -> x2 = 48
            Exp("job", "frontend", "2015-01", "2016-12")]      # 24 thang, cu = 24
    v, side, shares = b1_role(exps, "backend", M, rc.b1, rc.b2, "2026-11")
    assert side is None and shares == pytest.approx({"backend": 2 / 3, "frontend": 1 / 3})
    assert v == pytest.approx(2 / 3 * 1.0 + 1 / 3 * 0.3)
    # sinh vien chi co du an
    v, side, _ = b1_role([Exp("project_team", "backend", "2025-01", "2025-06")], "devops", M, rc.b1, rc.b2, "2026-11")
    assert v == pytest.approx(0.4) and side is None
    # khong ro nhom -> M = 0 (khong phai thieu du lieu); khong co ngay -> thieu phia CV
    assert b1_role([Exp("job", None, "2020-01", "2021-01")], "backend", M, rc.b1, rc.b2, "2026-11")[:2] == (0.0, None)
    v, side, _ = b1_role(exps + [Exp("job", None, "2024-01", "2025-12")], "backend", M, rc.b1, rc.b2, "2026-11")
    assert v == pytest.approx(48 / 120 * 1.0 + 24 / 120 * 0.3)
    assert b1_role([Exp("job", "backend", None, None)], "backend", M, rc.b1, rc.b2, "2026-11")[1] == "cv_side"
    assert b1_role(exps, None, M, rc.b1, rc.b2, "2026-11")[1] == "jd_side"


# --------------------------------------------------------------------------- A1 + skill facts


def test_a1_coverage_groups_and_facts():
    jd = [skill_match.JdSkill("java", True, 1.0), skill_match.JdSkill("spring", True, 1.0),
          skill_match.JdSkill("pg", True, 0.7, group_id=1), skill_match.JdSkill("mysql", True, 0.4, group_id=1),
          skill_match.JdSkill("kafka", False, 0.4)]
    cv = {"java": skill_match.CvSkill("java", 0.6, None, "skills[0]"), "mysql": skill_match.CvSkill("mysql", 1.0, 7, "x"),
          "kotlin": skill_match.CvSkill("kotlin", 1.0, 8, "y")}
    assert skill_match.coverage(jd, cv, True) == pytest.approx((0.6 + 0 + 0.7 * 1.0) / 2.7)
    assert skill_match.coverage(jd, cv, False) == 0.0
    assert skill_match.coverage([skill_match.JdSkill("kafka", False, 0.4)], cv, True) is None
    rel = lambda a, b: 0.4 if {a, b} == {"kotlin", "spring"} else (1.0 if a == b else 0.0)  # noqa: E731
    assert skill_match.coverage(jd, cv, True, rel) == pytest.approx((0.6 + 0.4 + 0.7) / 2.7)
    relation = lambda a, b: "sibling" if {a, b} == {"kotlin", "spring"} else None  # noqa: E731
    f = skill_match.skill_facts(jd, cv, relation)
    assert [(m.skill, m.evidence_id) for m in f.met] == [("java", "skills[0]"), ("mysql", "7")]
    assert [(p.required, p.found, p.relation) for p in f.partial] == [("spring", "kotlin", "sibling")]
    assert f.missing == []
    assert skill_match.skill_facts(jd, cv).missing == ["spring"]


# --------------------------------------------------------------------------- 5.8


def test_missing_policies(rc):
    def rows():
        return [Scored("a", {"A1": 0.9, "B4": 0.8}, {}), Scored("b", {"A1": 0.9, "B4": 0.4}, {}),
                Scored("c", {"A1": 0.9, "B4": 0.6}, {}), Scored("nd", {"A1": 0.9, "B4": None}, {"B4": "cv_side"})]
    rs = rows()
    finalize(rs, rc)
    nd = next(r for r in rs if r.item_id == "nd")
    assert nd.used["B4"] == pytest.approx(0.6)                  # trung vi pool (0,4 0,6 0,8)
    zero = load_config(overrides={"rerank": {"missing": {"cv_side_policy": "zero", "jd_side_policy": "drop"}}}).rerank
    rs = rows()
    finalize(rs, zero)
    assert next(r for r in rs if r.item_id == "nd").used["B4"] == 0.0
    drop = load_config(overrides={"rerank": {"missing": {"cv_side_policy": "drop", "jd_side_policy": "drop"}}}).rerank
    rs = rows()
    finalize(rs, drop)
    nd = next(r for r in rs if r.item_id == "nd")
    assert nd.used["B4"] is None and nd.s_raw == pytest.approx(0.9)


def test_jd_side_reweights(rc):
    r = Scored("a", {"A1": 0.8, "B4": None, "B1": 1.0, "B2": None}, {"B4": "jd_side", "B2": "jd_side"})
    finalize([r], rc)
    assert r.s_raw == pytest.approx((0.25 * 0.8 + 0.10 * 1.0) / 0.35)


def test_low_data_quality(rc):
    r = Scored("a", {"A1": 0.8, "B4": None, "B1": None, "B2": None},
               {"B4": "cv_side", "B1": "cv_side", "B2": "cv_side"})
    finalize([r, Scored("b", {"A1": 0.5, "B4": 0.5, "B1": 0.5, "B2": 0.5}, {})], rc)
    assert "low_data_quality" in r.flags


def test_align_word_grouping_and_literal_rule():
    from cvmatch.core.models.base import TokenEmb
    from cvmatch.core.text.segment import make_segmenter
    from cvmatch.rerank.bertscore.align import align_words, word_spans
    from cvmatch.rerank.bertscore.prepare import prepare

    seg = make_segmenter("pyvi", [])
    jd = prepare("Thiết kế và phát triển API cho hệ thống thanh toán", None, canonicalize_aliases=False,
                 mask_numbers=False)
    assert [jd.text[a:b] for a, b in word_spans(jd.text, seg)] == \
        ["Thiết kế", "và", "phát triển", "API", "cho", "hệ thống", "thanh toán"]
    # embedding gia: moi token JD cosine 0,8 voi gach (duoi nguong 0,9) -> chi tu xuat hien nguyen van moi khop
    offs = [(m.start(), m.end()) for m in __import__("re").finditer(r"\S+", jd.text)]
    v = np.zeros((len(offs), 2), np.float32)
    v[:, 0] = 1.0
    jd_emb = TokenEmb(tokens=["t"] * len(offs), offsets=offs, emb=v)
    cv_emb = TokenEmb(tokens=["u"], offsets=[(0, 1)], emb=np.array([[0.8, 0.6]], np.float32))
    cv_text = "Phát triển API thanh toán bằng Django"
    m, miss, _ = align_words(jd, jd_emb, cv_emb, 0.9, seg, cv_text=cv_text)
    assert m == ["phát triển", "API", "thanh toán"] and miss == ["Thiết kế", "hệ thống"]
    m, miss, _ = align_words(jd, jd_emb, cv_emb, 0.75, seg)          # nguong cosine du thap -> moi tu khop
    assert miss == [] and len(m) == 5


# --------------------------------------------------------------------------- S02 (rr-1.2): diem khong phu thuoc pool


@pytest.fixture(scope="module")
def rc12():
    return load_config(overrides={"rerank": {"missing": {
        "cv_side_policy": "fixed", "cv_side_fixed": {"A1": 0.2, "B1": 0.4, "B2": 0.0, "B4": 0.2},
        "jd_side_policy": "neutral", "jd_side_neutral": {"B1": 0.5, "B2": 0.5, "B3": 0.5, "C1": 0.5}}}}).rerank


def _pool(n: int) -> list[Scored]:
    rng = np.random.default_rng(n)
    rows = [Scored(f"x{i}", {"A1": float(rng.random()), "B4": float(rng.random()), "B1": 1.0, "B2": float(rng.random())},
                   {}) for i in range(n)]
    return rows


def test_fixed_policy_score_does_not_depend_on_pool(rc12):
    """V-04: cung mot cap (CV thieu B4) cho cung diem trong pool 1, 34, 200."""
    def target():
        return Scored("cv", {"A1": 0.7, "B4": None, "B1": 1.0, "B2": 0.8}, {"B4": "cv_side"})
    scores = set()
    for n in (0, 33, 199):
        rows = _pool(n) + [target()]
        finalize(rows, rc12)
        t = next(r for r in rows if r.item_id == "cv")
        assert t.used["B4"] == pytest.approx(0.2)
        scores.add((t.score, round(t.s_raw, 9)))
    assert len(scores) == 1


def test_pool_median_depends_on_pool(rc):
    """Doi chung: chinh sach cu (rr-1.0) cho diem khac nhau theo pool."""
    scores = set()
    for n in (0, 33):
        rows = _pool(n) + [Scored("cv", {"A1": 0.7, "B4": None, "B1": 1.0, "B2": 0.8}, {"B4": "cv_side"})]
        finalize(rows, rc)
        scores.add(next(r for r in rows if r.item_id == "cv").score)
    assert len(scores) == 2


def test_jd_side_neutral_keeps_feature_set(rc12):
    """V-01: JD khong ghi so nam -> B2 trung tinh 0,5 thay vi bi bo; B4 thieu phia JD van bi bo."""
    r = Scored("jd", {"A1": 0.8, "B4": None, "B1": 1.0, "B2": None}, {"B4": "jd_side", "B2": "jd_side"})
    finalize([r], rc12)
    assert r.used["B2"] == 0.5 and r.used["B4"] is None
    assert r.s_raw == pytest.approx((0.25 * 0.8 + 0.10 * 1.0 + 0.10 * 0.5) / 0.45)


def test_fixed_policy_without_value_drops(rc12):
    """Feature bat them (vd qua ablation) chua co gia tri do san -> bo, khong loi."""
    r = Scored("cv", {"A1": 0.7, "B4": None, "B1": 1.0, "B2": 0.8, "A2": None}, {"A2": "cv_side"})
    rc = rc12.model_copy(update={"features_enabled": ["A1", "A2", "B4", "B1", "B2"]})
    finalize([r], rc)
    assert r.used["A2"] is None


def test_neutral_values_must_be_in_range():
    with pytest.raises(Exception, match="jd_side_neutral"):
        load_config(overrides={"rerank": {"missing": {"jd_side_neutral": {"B1": 1.5}}}})

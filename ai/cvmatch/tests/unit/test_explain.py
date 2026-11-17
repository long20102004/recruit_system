"""T12: Explain bang mau xac dinh (thiet ke 08 muc 3, 4)."""

import os
import re
from pathlib import Path

import pytest

from cvmatch.core.config import load_config
from cvmatch.core.contracts import (
    Evidence, ExperienceFacts, Features, FinalItem, SentenceFact, SkillFacts, SkillMet,
)
from cvmatch.explain import checks
from cvmatch.explain.service import TemplateExplainer, cache_key
from cvmatch.explain.template import fmt_years, question_phrase, word_spans

FIX = Path(__file__).resolve().parents[1] / "fixtures" / "explain"


def sample_item(**over) -> FinalItem:
    """CV mau x JD mau (thiet ke 07 muc 5.3, 5.10)."""
    d = dict(
        cv_id="cv-1", rank=1, score=79, score_raw=0.793895, gate_cap=100, cap_applied=False,
        features=Features(A1=0.8, A2=0.5, B4=0.74, B5=0.6, B1=1.0, B2=1.0, B3=1.0),
        missing={"C1": "jd_side"},
        skill_facts=SkillFacts(met=[SkillMet(skill="S0001", ev=0.6, evidence_id="skills[0]"),
                                    SkillMet(skill="S0002", ev=1.0, evidence_id="90001"),
                                    SkillMet(skill="S0015", ev=1.0, evidence_id="90002")]),
        resp_facts=[
            SentenceFact(resp_id=0, resp_text="Thiết kế và phát triển API cho hệ thống thanh toán", level="met",
                         evidence_id="90001", matched_words=["phát triển", "API", "hệ thống", "thanh toán"],
                         missing_words=["Thiết kế"]),
            SentenceFact(resp_id=1, resp_text="Tối ưu hiệu năng truy vấn cơ sở dữ liệu", level="met",
                         evidence_id="90002", matched_words=["Tối ưu", "truy vấn", "cơ sở dữ liệu"],
                         missing_words=["hiệu năng"]),
        ],
        experience_facts=ExperienceFacts(relevant_years=4.7, level_cv=3, level_jd=4, role_group_cv="Backend",
                                         role_group_jd="Backend"),
        evidence={"90001": Evidence(text_raw="Xây dựng API thanh toán bằng Spring Boot", section="experience",
                                    item_idx=0),
                  "90002": Evidence(text_raw="Tối ưu truy vấn PostgreSQL, giảm 40% thời gian", section="experience",
                                    item_idx=0)},
    )
    d.update(over)
    return FinalItem(**d)


@pytest.fixture(scope="module")
def ex(kb_mini):
    return TemplateExplainer(load_config(), kb_mini)


def test_sample_text(ex):
    out = ex.explain(sample_item())
    t = out["text"]
    assert t.startswith("Điểm 79/100 (cân nhắc, điểm xếp hạng tương đối).")
    assert "Kỹ năng bắt buộc: có 3/3 (Java, Spring Boot, PostgreSQL)." in t
    assert '"Thiết kế và phát triển API cho hệ thống thanh toán" ← "Xây dựng API thanh toán bằng Spring Boot"' in t
    assert "Việc đã làm: 2/2 trách nhiệm có bằng chứng." in t
    assert "Kinh nghiệm liên quan: 4,7 năm, nhóm Backend." in t
    assert "Điểm bị giới hạn" not in t and "ứng viên không có" not in t
    # moi chu so trong van ban deu do code dien: ban che du lieu khong con chu so
    assert not re.search(r"\d", out["masked"] if "masked" in out else ex_masked(ex, sample_item()))
    assert out["band"] == "mid" and out["template_version"] == "tpl-1.0"
    assert out["sections"]["resp"]["examples"][0]["highlight"][1] == (23, 26)   # "API" trong resp_text


def ex_masked(ex, item):
    from cvmatch.explain.template import build_context, render
    ctx = build_context(item, ex.names, "mid", "cân nhắc")
    return render(ctx, ex.template_path).masked


def test_snapshot_text(ex):
    """Phat hien thay doi cau chu ngoai y muon. Cap nhat co chu dich: CVMATCH_UPDATE_SNAPSHOT=1."""
    t = ex.explain(sample_item())["text"]
    path = FIX / "sample_79.txt"
    if os.environ.get("CVMATCH_UPDATE_SNAPSHOT") or not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(t, encoding="utf-8")
    assert t == path.read_text(encoding="utf-8")


def test_cap_sentence(ex):
    item = sample_item(score=70, gate_cap=70, cap_applied=True, features=Features(A1=0.6, B4=0.74, B1=1, B2=1),
                       flags=["cap_applied"])
    t = ex.explain(item)["text"]
    assert "Điểm 70/100" in t and "Điểm bị giới hạn vì mới đáp ứng 60% kỹ năng bắt buộc." in t


def test_negation_evidence_label_and_gaps(ex):
    ev = {"90001": Evidence(text_raw="Chưa từng triển khai API thanh toán", section="experience", item_idx=0,
                            flags=["has_negation"])}
    item = sample_item(
        score=45, evidence=ev, flags=["has_negation_bullets"],
        skill_facts=SkillFacts(met=[SkillMet(skill="S0001", ev=0.6, evidence_id="skills[0]")],
                               missing=["S0002", "S0015"]),
        resp_facts=[
            SentenceFact(resp_id=0, resp_text="Thiết kế và phát triển API cho hệ thống thanh toán", level="met",
                         evidence_id="90001", matched_words=["API"], missing_words=[]),
            SentenceFact(resp_id=1, resp_text="Tối ưu hiệu năng truy vấn cơ sở dữ liệu", level="partial",
                         evidence_id=None, matched_words=[], missing_words=["hiệu năng"]),
            SentenceFact(resp_id=2, resp_text="Vận hành hệ thống giám sát", level="not_evidenced",
                         evidence_id=None, matched_words=[], missing_words=["Vận hành", "giám sát"]),
        ])
    t = ex.explain(item)["text"]
    assert '"Chưa từng triển khai API thanh toán" (câu có phủ định, cần xác minh)' in t
    assert "chưa thấy bằng chứng về Spring Boot, PostgreSQL trong CV." in t
    assert '"Tối ưu hiệu năng truy vấn cơ sở dữ liệu" mới có bằng chứng một phần (chưa thấy phần: hiệu năng).' in t
    assert 'chưa thấy bằng chứng về "Vận hành hệ thống giám sát" trong CV.' in t
    qs = [l for l in t.splitlines() if l.startswith("• Anh/chị")]
    assert len(qs) == 3 and qs[0] == "• Anh/chị đã từng tối ưu hiệu năng truy vấn cơ sở dữ liệu chưa? Hãy kể một ví dụ cụ thể."
    assert "CV có câu mang nghĩa phủ định" in t


def test_missing_bullets_note(ex):
    item = sample_item(resp_facts=[], evidence={}, missing={"B4": "cv_side"}, flags=["no_diacritics"])
    t = ex.explain(item)["text"]
    assert "Việc đã làm: thiếu dữ liệu trong CV" in t and "CV gõ không dấu" in t


def test_checks_catch_bugs(ex, matcher):
    forb = checks.load_forbidden(load_config().config_dir / "patterns" / "explain_forbidden.txt")
    ok = dict(cited_evidence=["1"], cv_evidence={"1"}, cap_applied=False, forbidden=forb)
    assert checks.find_problems("Điểm tốt", "Điểm tốt", **ok) == []
    assert checks.find_problems("x", "x", **{**ok, "cited_evidence": ["9"]})[0].startswith("bang chung")
    assert checks.find_problems("x", "Điểm §/§", **ok) == []
    assert "chu so" in checks.find_problems("x", "Điểm 5 sao", **ok)[0]
    assert "tu bi cam" in checks.find_problems("x", "Không nên tuyển", **ok)[0]
    assert "cap_applied" in checks.find_problems("x", "x", **{**ok, "cap_applied": True})[0]
    p = checks.find_problems('Biết Kubernetes, "dùng Docker"', "", **ok, matcher=matcher, allowed_skills={"S0001"})
    assert p == ["cong nghe khong thuoc JD/CV: ['S0020']"]       # Docker trong ngoac kep la trich dan -> bo qua


def test_explainer_raises_on_foreign_evidence(ex):
    with pytest.raises(checks.ExplainCheckError):
        ex.explain(sample_item(), cv_evidence={"12345"})


def test_helpers():
    assert fmt_years(4.7) == "4,7" and fmt_years(5.0) == "5" and fmt_years(0.04) == "0"
    assert question_phrase("Thiết kế API.") == "thiết kế API" and question_phrase("API thanh toán") == "API thanh toán"
    assert word_spans("phát triển API, API", ["API", "API"]) == [(11, 14), (16, 19)]
    assert cache_key(sample_item(), "tpl-1.0") != cache_key(sample_item(score=80), "tpl-1.0")

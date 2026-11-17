import numpy as np

from cvmatch.core.config import load_config
from cvmatch.core.models import FakeEncoder
from cvmatch.rerank.bertscore.align import align_words
from cvmatch.rerank.bertscore.cache import TokenCache
from cvmatch.rerank.bertscore.engine import BertScorer
from cvmatch.rerank.bertscore.prepare import prepare


def test_prepare_alias_and_numbers(matcher):
    p = prepare("Triển khai K8s, giảm 40% trong 3.5 tháng", matcher)
    assert p.text == "Triển khai Kubernetes, giảm N trong N tháng"
    assert p.raw == "Triển khai K8s, giảm 40% trong 3.5 tháng"
    # ban do vi tri: "Kubernetes" -> "K8s", "giảm" giu nguyen
    k0 = p.text.index("Kubernetes")
    r0, r1 = p.to_raw_span(k0, k0 + len("Kubernetes"))
    assert p.raw[r0:r1] == "K8s"
    g0 = p.text.index("giảm")
    assert p.raw[slice(*p.to_raw_span(g0, g0 + 4))] == "giảm"


def test_prepare_keeps_case_and_tech_digits(matcher):
    p = prepare("Phát triển API bằng Java trên AWS S3, Python3", matcher)
    assert p.text == "Phát triển API bằng Java trên AWS S3, Python3"     # khong doi "Java" -> ten chuan
    assert prepare("Dùng ReactJS", matcher).text == "Dùng React"
    assert prepare("Dùng K8s", matcher, canonicalize_aliases=False, mask_numbers=False).text == "Dùng K8s"


def scorer(matcher=None):
    return BertScorer(FakeEncoder(), load_config().bertscore, matcher)


def test_recall_matrix_shape_identity_and_cache():
    s = scorer()
    R = s.recall_matrix(["Xây dựng API backend", "Tối ưu truy vấn"],
                        ["Xây dựng API backend", "Thiết kế banner", ""])
    assert R.shape == (2, 3)
    assert np.isclose(R[0, 0], 1.0) and R[0, 1] < 1.0 and R[0, 2] == 0.0
    h0 = s.cache.hits
    s.recall_matrix(["Xây dựng API backend"], ["Thiết kế banner"])
    assert s.cache.hits > h0                                       # lan hai trung cache


def test_recall_vs_precision_asymmetry():
    s = scorer()
    out = s.pair("Xây dựng API", "Xây dựng API thanh toán bằng Spring Boot")
    assert np.isclose(out["recall"], 1.0) and out["precision"] < 1.0   # Recall khong phat CV viet dai


def test_score_embs_matches_pairwise():
    s = scorer()
    jd = ["phát triển api thanh toán", "tối ưu cơ sở dữ liệu"]
    cv = ["xây dựng api thanh toán", "tối ưu truy vấn postgresql", "thiết kế banner"]
    R = s.recall_matrix(jd, cv)
    for j, a in enumerate(jd):
        for i, b in enumerate(cv):
            assert np.isclose(R[j, i], s.pair(a, b)["recall"], atol=1e-6)


def test_align_words(matcher):
    s = scorer(matcher)
    (jp,) = s.prepare(["Thiết kế và phát triển API cho hệ thống thanh toán"])
    (je,) = s.embed([jp])
    (ce,) = s.embed(s.prepare(["Xây dựng API thanh toán cho hệ thống"]))
    matched, missing, _ = align_words(jp, je, ce, 0.75)
    assert {"API", "thanh", "toán", "hệ", "thống"} <= set(matched)
    assert {"Thiết", "kế", "phát", "triển"} <= set(missing)
    assert "và" not in matched + missing and "cho" not in matched + missing


def test_cache_lru_limit_and_purge():
    from cvmatch.core.models.base import TokenEmb
    c = TokenCache("cfg", max_bytes=3 * 4 * 1024)
    for k in "abcd":
        c.put_many({k: TokenEmb(["x"], [(0, 1)], np.ones((1, 1024), np.float32))})
    assert list(c._mem) == ["b", "c", "d"]
    c.purge(["c"])
    assert list(c._mem) == ["b", "d"]

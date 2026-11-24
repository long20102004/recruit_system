"""T14: metric tinh tay, kappa, chia dev/test, bootstrap, pooling."""

import math

import pytest

from cvmatch.evaluation import metrics as M
from cvmatch.evaluation.bootstrap import paired_bootstrap
from cvmatch.evaluation.labels import _resolve, cohen_kappa, split_dev_test
from cvmatch.evaluation.labels.pooling import pool_items


def test_recall_at_k_hand():
    labels = {"a": 2, "b": 1, "c": 0, "d": 2}
    ranked = ["c", "a", "x", "b", "d"]
    assert M.recall_at_k(ranked, labels, 2) == pytest.approx(1 / 3)        # {a,b,d} phu hop, top2 co a
    assert M.recall_at_k(ranked, labels, 5) == 1.0
    assert M.recall_at_k(ranked, labels, 2, min_grade=2) == pytest.approx(1 / 2)
    assert M.recall_at_k(ranked, {"c": 0}, 3) is None
    # trong pool: d khong co trong pool -> chi tinh a, b
    assert M.recall_at_k(ranked[:4], labels, 4, universe=ranked[:4]) == 1.0
    assert M.recall_at_k_norm(ranked, labels, 2) == pytest.approx(1 / 2)    # 1 / min(2, 3)


def test_ndcg_hand():
    labels = {"a": 2, "b": 1, "c": 0}
    # thu tu [c, a, b]: DCG = 0 + 3/log2(3) + 1/log2(4); IDCG = 3 + 1/log2(3)
    got = M.ndcg_at_k(["c", "a", "b"], labels, 10)
    assert got == pytest.approx((3 / math.log2(3) + 1 / 2) / (3 + 1 / math.log2(3)))
    assert M.ndcg_at_k(["a", "b", "c"], labels, 10) == pytest.approx(1.0)
    assert M.ndcg_at_k(["a"], {"a": 0}, 10) is None
    # muc phu hop ngoai pool khong vao ly tuong
    assert M.ndcg_at_k(["a", "c"], {**labels, "z": 2}, 10, universe=["a", "c"]) == pytest.approx(1.0)


def test_auc_hand():
    assert M.auc([0.9, 0.8, 0.3, 0.1], [True, True, False, False]) == 1.0
    assert M.auc([0.1, 0.9], [True, False]) == 0.0
    assert M.auc([0.5, 0.5], [True, False]) == 0.5                        # hoa 0,5
    assert M.auc([0.9, 0.4, 0.6, 0.2], [True, True, False, False]) == pytest.approx(0.75)
    assert M.auc([0.1], [True]) is None


def test_summarize_and_unjudged():
    s = M.summarize({"j1": 0.5, "j2": 0.9, "j3": None}, {"j1": "Backend", "j2": "Frontend"})
    assert s["mean"] == pytest.approx(0.7) and s["worst"] == 0.5 and s["worst_query"] == "j1" and s["n"] == 2
    assert s["by_group"] == {"Backend": 0.5, "Frontend": 0.9}
    assert M.unjudged_rate(["a", "b", "c", "d"], {"a": 1, "c": 0}, 4) == 0.5


def test_kappa_and_resolve():
    a = {("q", "1"): 2, ("q", "2"): 0, ("q", "3"): 1, ("q", "4"): 2}
    assert cohen_kappa(a, dict(a)) == pytest.approx(1.0)
    b = {("q", "1"): 2, ("q", "2"): 0, ("q", "3"): 2, ("q", "4"): 1}
    # po = 0,5; pa = (.25,.25,.5) pb = (.25,.25,.5) -> pe = .0625+.0625+.25 = .375 -> k = (0,5-0,375)/0,625 = 0,2
    assert cohen_kappa(a, b) == pytest.approx(0.2)
    assert cohen_kappa(a, b, weights="quadratic") > cohen_kappa(a, b)
    final, dis = _resolve({"r1": a, "r2": b, "final": {("q", "3"): 1}})
    assert final[("q", "3")] == 1 and final[("q", "4")] == 1 and dis == 1      # lech (2,1) -> lam tron xuong 1


def test_split_stratified_deterministic():
    qs = {f"j{i}": ("Backend" if i < 6 else "Frontend" if i < 10 else "Data") for i in range(13)}
    s1, s2 = split_dev_test(qs, seed=7), split_dev_test(qs, seed=7)
    assert s1 == s2
    for g in ("Backend", "Frontend"):
        sub = [s1[q] for q, gg in qs.items() if gg == g]
        assert sub.count("dev") == sub.count("test")
    assert abs(list(s1.values()).count("dev") - list(s1.values()).count("test")) <= 1


def test_paired_bootstrap():
    a = {f"j{i}": 0.5 for i in range(20)}
    b = {f"j{i}": 0.6 for i in range(20)}
    r = paired_bootstrap(a, b, n_boot=500)
    assert r.diff == pytest.approx(0.1) and r.lo == pytest.approx(0.1) and r.significant
    noisy = {f"j{i}": 0.5 + (0.1 if i % 2 else -0.1) for i in range(20)}
    r2 = paired_bootstrap(a, noisy, n_boot=500)
    assert r2.lo < 0 < r2.hi and not r2.significant
    assert paired_bootstrap({}, b) is None


def test_pooling():
    runs = {"RT-E1": {"q": ["a", "b"]}, "R-E1": {"q": ["b", "c"]}}
    out = pool_items(runs, ["a", "b", "c", "d", "e", "f"], n_random=2, seed=1, already={("q", "a")})
    assert set(out["q"]) >= {"b", "c"} and "a" not in out["q"]
    assert out["q"]["b"] == ["RT-E1", "R-E1"]
    assert sum(1 for v in out["q"].values() if v == ["random"]) == 2

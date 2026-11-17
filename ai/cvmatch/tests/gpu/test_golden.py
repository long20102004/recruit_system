"""G1 / G2 (thiet ke 09 muc 4.2): golden test BERTScore voi bge-m3 that - test HOI QUY cho tang ngu nghia.
Chay lai moi khi doi `bertscore_config` (model, layer, IDF, chuan bi dau vao). pytest -m gpu tests/gpu
"""

import pytest

from cvmatch.core.config import load_config
from cvmatch.core.models import get_encoder
from cvmatch.evaluation.golden.runner import run_golden
from cvmatch.rerank.bertscore.engine import BertScorer

pytestmark = pytest.mark.gpu


@pytest.fixture(scope="module")
def encoder():
    return get_encoder(load_config(), fake=False)


def scorer(encoder, matcher, bare):
    ov = {"bertscore": {"canonicalize_aliases": False, "mask_numbers": False}} if bare else {}
    return BertScorer(encoder, load_config(overrides=ov).bertscore, matcher)


def test_g1_bare_reproduces_design_10(encoder, matcher):
    rep = run_golden(scorer(encoder, matcher, True), bare=True)
    assert rep.passed("S2") == (25, 26) and rep.failed_ids("S2") == ["T19"]   # dieu kien giu cau hinh
    diff, where = rep.max_diff_vs_doc()
    assert diff < 0.025, where   # T17 lech ~0,019 vi pipeline luon don ky tu rac PDF


def test_g2_full_pipeline_expectations(encoder, matcher):
    full = run_golden(scorer(encoder, matcher, False), bare=False)
    bare = run_golden(scorer(encoder, matcher, True), bare=True)
    assert full.passed("S2") == (25, 26)
    g = lambda rep, t: next(r for r in rep.results if r.id == t).scores["S2"]  # noqa: E731
    # T06: doi alias K8s -> Kubernetes lam khoang cach tang ro
    assert g(full, "T06")["pos"] - g(full, "T06")["neg"] > 2 * (g(bare, "T06")["pos"] - g(bare, "T06")["neg"])
    # T08: che so -> "1 năm" va "5 năm" nhu nhau (so nam do B2 cham bang luat)
    assert abs(g(full, "T08")["5y"] - g(full, "T08")["1y"]) / full.span["S2"] < 0.02

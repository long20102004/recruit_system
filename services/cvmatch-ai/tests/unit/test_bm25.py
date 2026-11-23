import math

import numpy as np

from cvmatch.retrieve.bm25 import Bm25Index

DOCS = [["java", "spring", "api"], ["python", "django", "api", "api"], ["excel", "báo_cáo"]]


def manual(q, d, docs, k1=1.2, b=0.75):
    n, avgdl = len(docs), sum(map(len, docs)) / len(docs)
    s = 0.0
    for t in q:
        df = sum(t in x for x in docs)
        if df == 0:
            continue
        idf = math.log1p((n - df + 0.5) / (df + 0.5))
        tf = d.count(t)
        s += idf * tf * (k1 + 1) / (tf + k1 * (1 - b + b * len(d) / avgdl))
    return s


def test_scores_match_formula():
    idx = Bm25Index().build(DOCS)
    q = ["api", "java", "khong_co"]
    got = idx.scores(q)
    assert np.allclose(got, [manual(q, d, DOCS) for d in DOCS], atol=1e-5)
    assert got[0] > got[1] > got[2] == 0


def test_rare_term_weighs_more():
    idx = Bm25Index().build(DOCS)
    assert idx.scores(["java"])[0] > idx.scores(["api"])[0]   # java hiem hon api


def test_append_uses_old_idf_and_ignores_new_terms():
    idx = Bm25Index().build(DOCS)
    before = idx.idf.copy()
    idx.append([["java", "kotlin"]])
    assert idx.n_docs == 4 and np.array_equal(idx.idf, before)
    s = idx.scores(["java", "kotlin"])
    assert s[3] > 0 and "kotlin" not in idx.vocab
    idx.build(DOCS + [["java", "kotlin"]])  # dung lai -> tu moi vao tu vung
    assert "kotlin" in idx.vocab


def test_empty_index():
    assert Bm25Index().build([]).scores(["x"]).shape == (0,)

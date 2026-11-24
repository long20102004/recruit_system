"""T16: Luong D - vi du vang 06 muc 5.6, mau so toi thieu, RRF khi kho nho."""

from types import SimpleNamespace

import numpy as np
import pytest

from cvmatch.retrieve import fusion
from cvmatch.retrieve.flow_d import view_resp_jd, view_skill_jd


def test_min_imp_sum_skill_view():
    idx = SimpleNamespace(n_jd=3, reqs=[
        [(1.0, ["S1"]), (1.0, ["S2"]), (1.0, ["S3"]), (1.0, ["S4"])],     # JD doi 4 ky nang, CV co 3
        [(1.0, ["S1"])],                                                  # JD-D chi 1 ky nang, CV co
        [],                                                               # JD khong co ky nang bat buoc
    ])
    cv = {"S1": 1.0, "S2": 1.0, "S3": 1.0}
    s = view_skill_jd(idx, cv, 3.0)
    assert s[0] == pytest.approx(0.75) and s[1] == pytest.approx(1 / 3) and np.isnan(s[2])
    assert view_skill_jd(idx, cv, 0.0)[1] == 1.0                           # khong co mau so toi thieu -> 1,0
    # nhom "A hoac B": mot yeu cau, lay max ev
    g = SimpleNamespace(n_jd=1, reqs=[[(1.0, ["S9", "S1"])]])
    assert view_skill_jd(g, {"S1": 0.8}, 1.0)[0] == pytest.approx(0.8)


def test_golden_example_5_6():
    """Bang 06 muc 5.6: min-max tren 4 JD, cong bang nhau -> A 0,92 · B 0,76 · D 0,42 · C 0,00 -> A, B, D, C."""
    ids = ["JD-A", "JD-B", "JD-C", "JD-D"]
    raw = {"dense": np.array([0.72, 0.66, 0.52, 0.70], np.float32),
           "bm25": np.array([9.0, 12.5, 2.0, 5.5], np.float32),
           "skill": np.array([0.85, 0.60, 0.15, 1 / 3], np.float32),
           "resp": np.array([0.70, 0.62, 0.45, 0.50], np.float32)}
    mask = np.ones(4, bool)
    normed = {k: fusion.normalize(v, mask, "minmax") for k, v in raw.items()}
    fused = fusion.score_sum(normed, {k: 1.0 for k in raw})
    assert [round(float(x), 2) for x in fused] == [0.92, 0.76, 0.00, 0.42]
    order = [ids[i] for i in fusion.rank(fused, raw["skill"], ids, mask, 4)]
    assert order == ["JD-A", "JD-B", "JD-D", "JD-C"]


def test_resp_view_mean_per_jd():
    idx = SimpleNamespace(n_jd=3, resp=np.eye(3, 4, dtype=np.float16), resp_jd_index=np.array([0, 0, 2]))
    bullets = np.array([[1, 0, 0, 0], [0, 0, 0.5, 0]], np.float32)
    r = view_resp_jd(idx, bullets)
    assert r[0] == pytest.approx(0.5) and np.isnan(r[1]) and r[2] == pytest.approx(0.5)
    assert view_resp_jd(idx, np.zeros((0, 4), np.float32)) is None

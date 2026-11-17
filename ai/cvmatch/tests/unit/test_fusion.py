"""Test vang: vi du bang so cua thiet ke 06 muc 4.5."""

import numpy as np

from cvmatch.retrieve import fusion

IDS = ["CV1", "CV2", "CV3", "CV4", "CV5"]
RAW = {
    "dense": np.array([0.71, 0.64, 0.58, 0.69, 0.50], np.float32),
    "bm25": np.array([14.2, 21.0, 6.5, 9.8, 3.1], np.float32),
    "skill": np.array([0.80, 0.55, 0.20, 0.75, 0.10], np.float32),
    "resp": np.array([0.66, 0.60, 0.48, 0.70, 0.40], np.float32),
}
MASK = np.ones(5, bool)


def test_design_example_06_4_5():
    normed = {n: fusion.normalize(x, MASK) for n, x in RAW.items()}
    assert np.allclose(normed["bm25"], [0.62, 1.0, 0.19, 0.37, 0.0], atol=0.01)
    fused = fusion.score_sum(normed, {})
    order = fusion.rank(fused, RAW["skill"], IDS, MASK, 200)
    assert [IDS[i] for i in order] == ["CV1", "CV4", "CV2", "CV3", "CV5"]
    assert np.allclose(fused[order], [0.87, 0.80, 0.74, 0.25, 0.00], atol=0.01)


def test_minmax_constant_view_is_zero_and_nan_kept():
    x = np.array([0.5, 0.5, np.nan], np.float32)
    assert np.array_equal(fusion.normalize(x, MASK[:3])[:2], [0, 0]) and np.isnan(fusion.normalize(x, MASK[:3])[2])


def test_missing_view_for_one_cv_averages_the_rest():
    normed = {"a": np.array([1.0, 0.0], np.float32), "b": np.array([np.nan, 1.0], np.float32)}
    assert np.allclose(fusion.score_sum(normed, {}), [1.0, 0.5])   # NaN = thieu du lieu, khong phai 0


def test_mask_excludes_from_minmax_and_ranking():
    m = np.array([True, True, False, True, True])
    normed = fusion.normalize(RAW["bm25"], m)
    assert np.isnan(normed[2]) and normed[1] == 1.0
    assert 2 not in fusion.rank(normed, None, IDS, m, 10)


def test_tie_break_skill_then_id():
    fused = np.array([0.5, 0.5, 0.5], np.float32)
    skill = np.array([0.2, 0.9, 0.2], np.float32)
    assert list(fusion.rank(fused, skill, ["b", "c", "a"], np.ones(3, bool), 3)) == [1, 2, 0]


def test_rrf_and_dbsf_run():
    assert np.isfinite(fusion.rrf(RAW, MASK)).all()
    d = fusion.normalize(RAW["bm25"], MASK, "dbsf")
    assert ((d >= 0) & (d <= 1)).all()

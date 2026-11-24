import numpy as np

from cvmatch.core.config import load_config
from cvmatch.core.models import FakeEncoder, get_encoder


def test_fake_encode_shape_norm_deterministic():
    enc = FakeEncoder()
    r = enc.encode(["Xây dựng API thanh toán", "", "Xây dựng API thanh toán"])
    assert r.dense.shape == (3, 1024) and r.dense.dtype == np.float32
    assert np.allclose(np.linalg.norm(r.dense, axis=1), 1.0, atol=1e-5)
    assert np.array_equal(r.dense[0], r.dense[2])
    assert r.sparse[0]["api"] > 0


def test_fake_dense_shared_words_closer():
    d = FakeEncoder().encode(["xây dựng api thanh toán", "phát triển api thanh toán",
                              "thiết kế banner photoshop"]).dense
    assert d[0] @ d[1] > d[0] @ d[2]


def test_fake_token_embeddings():
    (a, b) = FakeEncoder().token_embeddings(["Xây dựng API", "API thanh toán"])
    assert a.tokens == ["Xây", "dựng", "API"] and a.offsets[2] == (9, 12)
    assert a.emb.shape == (3, 1024)
    assert np.isclose(a.emb[2] @ b.emb[0], 1.0)   # cung tu -> cosine 1


def test_get_encoder_fake_via_env(monkeypatch):
    monkeypatch.setenv("CVMATCH_FAKE_ENCODER", "1")
    enc = get_encoder(load_config())
    assert isinstance(enc, FakeEncoder) and enc.key().startswith("fake-")

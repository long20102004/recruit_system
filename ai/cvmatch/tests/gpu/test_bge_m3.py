"""Test voi bge-m3 that (tai ~2,3 GB lan dau). Chay: pytest -m gpu tests/gpu"""

import time

import numpy as np
import pytest

pytestmark = pytest.mark.gpu


@pytest.fixture(scope="module")
def enc():
    from cvmatch.core.config import load_config
    from cvmatch.core.models import get_encoder

    return get_encoder(load_config(), fake=False)


def test_dense_semantics(enc):
    d = enc.encode(["Xây dựng API thanh toán", "Phát triển backend giao dịch",
                    "Thiết kế banner quảng cáo, chỉnh sửa ảnh Photoshop"]).dense
    assert d.shape == (3, 1024)
    assert np.allclose(np.linalg.norm(d, axis=1), 1.0, atol=1e-3)
    assert d[0] @ d[1] > d[0] @ d[2]


def test_sparse_has_lexical_weights(enc):
    sp = enc.encode(["Tối ưu truy vấn PostgreSQL"]).sparse[0]
    assert sp and all(v > 0 for v in sp.values())
    assert {"truy", "SQL"} <= set(sp)  # trong so theo sub-word cua tokenizer (nhu lexical_weights)


def test_token_embeddings_no_special_tokens_and_unit_norm(enc):
    (t,) = enc.token_embeddings(["Xây dựng API thanh toán bằng Spring Boot"], layer=24)
    assert "<s>" not in t.tokens and "</s>" not in t.tokens
    assert t.emb.shape == (len(t.tokens), 1024)
    assert np.allclose(np.linalg.norm(t.emb, axis=1), 1.0, atol=1e-3)
    assert len(t.offsets) == len(t.tokens)


def test_speed_report(enc):
    texts = [f"Xây dựng API thanh toán số {i} bằng Spring Boot và PostgreSQL" for i in range(1000)]
    t0 = time.perf_counter()
    enc.encode(texts)
    print(f"\nencode 1000 cau: {time.perf_counter() - t0:.1f}s tren {enc.device}")

"""Encoder dung chung. `get_encoder(cfg)` chon bge-m3 that hoac FakeEncoder (CVMATCH_FAKE_ENCODER=1)."""

from __future__ import annotations

import os

from cvmatch.core.models.base import EncodeResult, Encoder, TokenEmb, l2_normalize
from cvmatch.core.models.fake import FakeEncoder

__all__ = ["EncodeResult", "Encoder", "TokenEmb", "FakeEncoder", "get_encoder", "l2_normalize"]


def get_encoder(cfg=None, *, fake: bool | None = None) -> Encoder:
    if cfg is None:
        from cvmatch.core.config import get_config

        cfg = get_config()
    e = cfg.models.embed
    if fake is None:
        fake = os.environ.get("CVMATCH_FAKE_ENCODER", "0") == "1"
    if fake:
        return FakeEncoder(dim=e.dim, key=f"fake-{e.key}")
    from cvmatch.core.models.bge_m3 import load_bge_m3

    return load_bge_m3(e.model, e.revision, e.device, e.dtype, e.batch_size, e.max_len, e.key)

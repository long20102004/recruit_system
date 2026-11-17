import pytest
from pydantic import ValidationError

from cvmatch.core.config import load_config


def test_default_config_loads_with_design_values():
    cfg = load_config()
    # 11 muc 1.1
    assert cfg.prep.ev.in_description == 1.0
    assert cfg.prep.ev.in_technologies == 0.8
    assert cfg.prep.ev.listed_only == 0.6
    assert (cfg.prep.w_imp.core, cfg.prep.w_imp.medium, cfg.prep.w_imp.minor) == (1.0, 0.7, 0.4)
    assert cfg.prep.bullet.min_words == 4
    # 11 muc 1.2
    assert cfg.retrieve.K == 200
    assert cfg.retrieve.reverse.skill.min_imp_sum == 3.0
    # 11 muc 1.3
    assert cfg.rerank.b4.calib.lo == 0.65 and cfg.rerank.b4.calib.hi == 0.90
    assert cfg.rerank.gate.caps == (50, 70)
    assert cfg.rerank.features_enabled == ["A1", "B4", "B1", "B2"]


def test_rerank_weights_sum_to_one():
    cfg = load_config()
    assert abs(sum(cfg.rerank.weights.values()) - 1.0) < 1e-9
    assert cfg.rerank.weights["B4"] + cfg.rerank.weights["B5"] == pytest.approx(0.40)


def test_weights_not_summing_to_one_rejected():
    with pytest.raises(ValidationError, match="1.00"):
        load_config(overrides={"rerank": {"weights": {"A1": 0.5}}})


def test_bertscore_config_key():
    cfg = load_config()
    key = cfg.bertscore.key()
    # mau thiet ke 00 muc 3.4 + co doi alias, dau vao, kieu so
    assert key == "bge-m3@5617a9f61b/L24/noidf/norescale/2048/mask1/alias1/text_raw/fp32"
    assert key.startswith("bge-m3@5617a9f61b/L24/noidf/norescale/2048/mask1")


def test_versions_bundle():
    v = load_config().versions
    assert v.pipeline_version == "prep-1.0"
    assert v.embed_model == "bge-m3@5617a9f61b"
    assert v.rerank_config_version == "rr-1.0"
    assert v.ontology_version == load_config().ontology_version  # lay tu active.yaml


def test_config_hash_stable_and_sensitive():
    a = load_config().config_hash()
    assert a == load_config().config_hash()
    b = load_config(overrides={"rerank": {"b4": {"calib": {"lo": 0.6}}}}).config_hash()
    assert a != b


def test_device_env_override(monkeypatch):
    monkeypatch.setenv("CVMATCH_DEVICE", "cpu")
    assert load_config().models.embed.device == "cpu"


def test_pattern_files_exist():
    cfg = load_config()
    for name in ("negation", "coursework", "generic_resp", "injection", "locations"):
        assert cfg.pattern_path(name).is_file(), name

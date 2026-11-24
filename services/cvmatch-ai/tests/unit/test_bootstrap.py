"""I01: kiem khoa bi mat truoc khi chay trong container."""

import pytest

from cvmatch.api.bootstrap import BootstrapError, check_secrets


@pytest.mark.parametrize("key", ["", "change-me"])
def test_prod_rejects_weak_hmac(monkeypatch, key):
    monkeypatch.setenv("CVMATCH_HMAC_KEY", key)
    with pytest.raises(BootstrapError):
        check_secrets("prod")


def test_dev_allows_placeholder_but_not_empty(monkeypatch):
    monkeypatch.setenv("CVMATCH_HMAC_KEY", "change-me")
    check_secrets("dev")
    monkeypatch.setenv("CVMATCH_HMAC_KEY", "")
    with pytest.raises(BootstrapError):
        check_secrets("dev")


def test_ontology_env_override(monkeypatch):
    from cvmatch.core.config import load_config

    monkeypatch.setenv("CVMATCH_ONTOLOGY_VERSION", "kb-test-1")
    assert load_config().ontology_version == "kb-test-1"
    assert load_config(overrides={"ontology_version": "x"}).ontology_version == "x"

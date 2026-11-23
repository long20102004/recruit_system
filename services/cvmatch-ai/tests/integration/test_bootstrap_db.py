"""I01: bootstrap cua container (migrate + nap KB khi chua co), chay lai khong lam gi them."""

import shutil
from pathlib import Path

import pytest

from cvmatch.api.bootstrap import BootstrapError, bootstrap
from cvmatch.core.config import load_config
from cvmatch.core.db import connect
from cvmatch.core.kb.store import list_versions

pytestmark = pytest.mark.db
FIX = Path(__file__).resolve().parents[1] / "fixtures"


def test_bootstrap_idempotent(fresh_db_url, tmp_path, monkeypatch):
    monkeypatch.setenv("CVMATCH_HMAC_KEY", "k")
    shutil.copytree(FIX / "kb_mini", tmp_path / "kb-mini-test")
    cfg = load_config(overrides={"ontology_version": "kb-mini-test"})
    first = bootstrap(fresh_db_url, cfg, kb_dir=tmp_path, db_timeout_s=10)
    assert first["ontology_version"] == "kb-mini-test" and first["migrations"]
    again = bootstrap(fresh_db_url, cfg, kb_dir=tmp_path, db_timeout_s=10)
    assert again == {"migrations": [], "ontology_version": "kb-mini-test"}
    with connect(fresh_db_url) as conn:
        assert [r["ontology_version"] for r in list_versions(conn)] == ["kb-mini-test"]

    missing = load_config(overrides={"ontology_version": "kb-khong-co"})
    with pytest.raises(BootstrapError, match="khong thay snapshot"):
        bootstrap(fresh_db_url, missing, kb_dir=tmp_path, db_timeout_s=10)

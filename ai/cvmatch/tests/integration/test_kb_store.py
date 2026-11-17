import json
import shutil
from pathlib import Path

import pytest

from cvmatch.core.db import connect, migrate
from cvmatch.core.kb.snapshot import KBSnapshot
from cvmatch.core.kb.store import SnapshotError, import_snapshot, load_snapshot_db

pytestmark = pytest.mark.db
KB_MINI = Path(__file__).resolve().parents[1] / "fixtures" / "kb_mini"


def test_import_and_reload_equals_dir(fresh_db_url):
    migrate(fresh_db_url)
    with connect(fresh_db_url) as conn:
        assert import_snapshot(conn, KB_MINI) == "kb-mini-test"
        a = load_snapshot_db(conn)
    b = KBSnapshot.from_dir(KB_MINI)
    assert a.skills == b.skills
    assert (a.title_map, a.level_map, a.major_map, a.ambiguous, a.role_distance) == \
        (b.title_map, b.level_map, b.major_map, b.ambiguous, b.role_distance)


def test_reimport_rules(fresh_db_url, tmp_path):
    migrate(fresh_db_url)
    with connect(fresh_db_url) as conn:
        import_snapshot(conn, KB_MINI)
        with pytest.raises(SnapshotError, match="da duoc nap"):
            import_snapshot(conn, KB_MINI)
        dev = tmp_path / "dev"
        shutil.copytree(KB_MINI, dev)
        m = json.loads((dev / "manifest.json").read_text(encoding="utf-8"))
        m["ontology_version"] = "kb-x-dev"
        (dev / "manifest.json").write_text(json.dumps(m), encoding="utf-8")
        import_snapshot(conn, dev)
        assert import_snapshot(conn, dev, replace=True) == "kb-x-dev"   # ban -dev duoc ghi de


def test_sha256_mismatch_rejected(fresh_db_url, tmp_path):
    migrate(fresh_db_url)
    bad = tmp_path / "bad"
    shutil.copytree(KB_MINI, bad)
    m = json.loads((bad / "manifest.json").read_text(encoding="utf-8"))
    m["files"] = {"skill_ontology": {"sha256": "0" * 64}}
    (bad / "manifest.json").write_text(json.dumps(m), encoding="utf-8")
    with connect(fresh_db_url) as conn:
        with pytest.raises(SnapshotError, match="sha256"):
            import_snapshot(conn, bad)
        assert conn.execute("SELECT count(*) AS n FROM kb_version").fetchone()["n"] == 0

import pytest

from cvmatch.core.db import connect, list_tables, migrate

pytestmark = pytest.mark.db

KB_TABLES = {"kb_version", "skill_ontology", "role_title_map", "role_distance", "major_group",
             "ambiguous_aliases"}
# 17 bang cua tien xu ly (thiet ke 03 "Cac bang")
PREP_TABLES = {"cv", "cv_meta", "cv_experience", "cv_education", "cv_skill", "cv_bullet",
               "cv_vector", "cv_bullet_vector", "cv_bm25_doc",
               "jd", "jd_meta", "jd_skill", "jd_responsibility", "jd_requirement_item", "jd_vector",
               "unknown_skill", "ingest_log"}
RETRIEVE_TABLES = {"match_run", "match_result"}
RERANK_TABLES = {"rerank_run", "rerank_feature", "rerank_result", "bertscore_token_cache",
                 "bertscore_pair_cache"}


def test_migrate_creates_all_tables_and_is_idempotent(fresh_db_url):
    ran = migrate(fresh_db_url)
    assert ran[0].startswith("001") and len(ran) == 6
    assert migrate(fresh_db_url) == []  # chay lai khong lam gi

    with connect(fresh_db_url, autocommit=True) as conn:
        tables = set(list_tables(conn))
    assert len(PREP_TABLES) == 17
    expected = KB_TABLES | PREP_TABLES | RETRIEVE_TABLES | RERANK_TABLES | {"schema_migrations"}
    assert tables == expected


def test_halfvec_roundtrip(fresh_db_url):
    import numpy as np
    from pgvector import HalfVector

    migrate(fresh_db_url)
    with connect(fresh_db_url) as conn:
        with conn.transaction():
            conn.execute(
                "INSERT INTO cv(cv_id, content_hash, ontology_version, pipeline_version, embed_model)"
                " VALUES ('00000000-0000-0000-0000-000000000001', 'h', 'kb-test', 'prep-1.0', 'bge-m3@x')"
            )
            vec = np.linspace(-1, 1, 1024, dtype=np.float32)
            conn.execute(
                "INSERT INTO cv_vector(cv_id, dense, embed_model) VALUES (%s, %s, %s)",
                ("00000000-0000-0000-0000-000000000001", HalfVector(vec), "bge-m3@x"),
            )
        row = conn.execute("SELECT dense FROM cv_vector").fetchone()
        got = np.asarray(row["dense"].to_list(), dtype=np.float32)
    assert got.shape == (1024,)
    assert np.allclose(got, vec, atol=1e-3)


def test_transaction_rolls_back_everything(fresh_db_url):
    from cvmatch.core.db import transaction

    migrate(fresh_db_url)
    with connect(fresh_db_url) as conn:
        with pytest.raises(Exception):
            with transaction(conn) as cur:
                cur.execute(
                    "INSERT INTO cv(cv_id, content_hash, ontology_version, pipeline_version, embed_model)"
                    " VALUES ('00000000-0000-0000-0000-000000000002', 'h', 'kb', 'p', 'e')"
                )
                cur.execute("INSERT INTO cv_meta(cv_id, level_rank) VALUES "
                            "('00000000-0000-0000-0000-000000000002', 9)")  # vi pham CHECK
        n = conn.execute("SELECT count(*) AS n FROM cv").fetchone()["n"]
    assert n == 0

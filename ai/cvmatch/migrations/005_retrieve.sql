-- Nhat ky Retrieve (thiet ke 06 muc 3).

CREATE TABLE match_run (
    run_id           uuid PRIMARY KEY,
    direction        text NOT NULL CHECK (direction IN ('jd_to_cv', 'cv_to_jd')),
    query_id         text NOT NULL,                     -- jd_id hoac cv_id
    query_version    int,
    config_json      jsonb NOT NULL,
    config_hash      text NOT NULL,
    k                int NOT NULL,
    n_pool           int,                               -- so muc duoc cham sau C2/D2
    warnings         jsonb NOT NULL DEFAULT '[]'::jsonb,
    ontology_version text NOT NULL,
    pipeline_version text NOT NULL,
    embed_model      text NOT NULL,
    created_at       timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX match_run_query_idx ON match_run (direction, query_id, created_at);

CREATE TABLE match_result (
    run_id           uuid NOT NULL REFERENCES match_run ON DELETE CASCADE,
    item_id          text NOT NULL,                     -- cv_id hoac jd_id tuy direction
    rank             int NOT NULL,
    s_dense          real,                              -- diem GOC (Rerank doc cac cot nay)
    s_bm25           real,
    s_skill          real,
    s_resp           real,
    n_dense          real,                              -- diem da min-max
    n_bm25           real,
    n_skill          real,
    n_resp           real,
    fused            real NOT NULL,
    explanation_json jsonb,                             -- ky nang khop/thieu, gach khop nhat
    PRIMARY KEY (run_id, item_id),
    UNIQUE (run_id, rank)
);

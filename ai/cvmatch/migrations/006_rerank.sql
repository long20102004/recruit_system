-- Bang cua Rerank (thiet ke 07 muc 6).

CREATE TABLE rerank_run (
    run_id                uuid PRIMARY KEY,
    retrieve_run_id       uuid NOT NULL REFERENCES match_run ON DELETE CASCADE,
    direction             text NOT NULL CHECK (direction IN ('jd_to_cv', 'cv_to_jd')),
    n                     int NOT NULL,
    config_json           jsonb NOT NULL,
    config_hash           text NOT NULL,
    bertscore_config      text NOT NULL,
    rerank_config_version text NOT NULL,
    timings_json          jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at            timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE rerank_feature (
    run_id        uuid NOT NULL REFERENCES rerank_run ON DELETE CASCADE,
    item_id       text NOT NULL,
    features_json jsonb NOT NULL,                       -- {A1, A2, B4, ...: float | null}
    missing_json  jsonb NOT NULL DEFAULT '{}'::jsonb,   -- {feature: 'jd_side' | 'cv_side'}
    detail_json   jsonb NOT NULL DEFAULT '{}'::jsonb,   -- resp_detail, req_detail
    s_raw         real,
    gate_cap      smallint CHECK (gate_cap IN (50, 70, 100)),
    PRIMARY KEY (run_id, item_id)
);

CREATE TABLE rerank_result (
    run_id           uuid NOT NULL REFERENCES rerank_run ON DELETE CASCADE,
    item_id          text NOT NULL,
    rank             int NOT NULL,
    score            smallint NOT NULL CHECK (score BETWEEN 0 AND 100),
    score_raw        real NOT NULL,
    cap_applied      boolean NOT NULL DEFAULT false,
    facts_json       jsonb NOT NULL,                    -- FinalItem
    explanation_json jsonb,                             -- Explain (luoi)
    PRIMARY KEY (run_id, item_id),
    UNIQUE (run_id, rank)
);

-- Cache embedding token cua BERTScore. Khoa gom bertscore_config (doi cau hinh -> khong trung cache).
CREATE TABLE bertscore_token_cache (
    text_hash        text NOT NULL,                     -- sha256 van ban SAU buoc chuan bi (07 muc 2.1)
    bertscore_config text NOT NULL,
    n_tokens         int NOT NULL,
    tokens_json      jsonb NOT NULL,                    -- token + offset ky tu
    emb              bytea NOT NULL,                    -- float16, n_tokens x 1024
    created_at       timestamptz NOT NULL DEFAULT now(),
    last_used_at     timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (text_hash, bertscore_config)
);

CREATE TABLE bertscore_pair_cache (
    jd_text_hash     text NOT NULL,
    cv_text_hash     text NOT NULL,
    bertscore_config text NOT NULL,
    recall           real NOT NULL,
    precision        real,
    f1               real,
    align_json       jsonb,
    PRIMARY KEY (jd_text_hash, cv_text_hash, bertscore_config)
);
CREATE INDEX bertscore_pair_cv_idx ON bertscore_pair_cache (cv_text_hash);

-- Bang chung (thiet ke 03): unknown_skill (A5, B4) va ingest_log (moi buoc).

CREATE TABLE unknown_skill (
    text       text PRIMARY KEY,                        -- cum da chuan hoa
    count      int NOT NULL DEFAULT 1,
    first_seen timestamptz NOT NULL DEFAULT now(),
    last_seen  timestamptz NOT NULL DEFAULT now(),
    example    text,                                    -- vi du ngu canh (xoa theo CV khi xoa du lieu)
    sources    text[] NOT NULL DEFAULT '{}'             -- 'cv' / 'jd'
);

CREATE TABLE ingest_log (
    id          bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    entity      text NOT NULL CHECK (entity IN ('cv', 'jd')),
    entity_id   text,                                   -- cv_id hoac jd_id (NULL neu sai schema truoc khi cap)
    version     int,
    status      text NOT NULL CHECK (status IN ('ok', 'invalid', 'duplicate', 'failed', 'deleted')),
    errors      jsonb NOT NULL DEFAULT '[]'::jsonb,
    flags       text[] NOT NULL DEFAULT '{}',
    detail      jsonb NOT NULL DEFAULT '{}'::jsonb,     -- vd cv_id cua ban da co khi duplicate
    duration_ms int,
    created_at  timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ingest_log_entity_idx ON ingest_log (entity, entity_id);
CREATE INDEX ingest_log_status_idx ON ingest_log (status, created_at);

-- Nhom CV (thiet ke 03 "Cac bang", 04 muc "Ket qua va noi luu" cua A1-A11).

-- A1-A4, A8, A11: bang chinh, moi phien ban CV mot dong
CREATE TABLE cv (
    cv_id            uuid PRIMARY KEY,
    candidate_key    text,                              -- HMAC email/sdt; NULL + co no_identity
    version          int NOT NULL DEFAULT 1,
    is_latest        boolean NOT NULL DEFAULT true,
    status           text NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'failed', 'deleted')),
    content_hash     text NOT NULL,                     -- SHA-256 hex cua canonical JSON
    raw_json         jsonb,                             -- vung goc (co thong tin ca nhan); NULL sau khi xoa
    anon_json        jsonb,                             -- vung cham diem: da an danh + chuan hoa
    doc_text         text,                              -- A8
    flags            text[] NOT NULL DEFAULT '{}',
    ontology_version text NOT NULL,
    pipeline_version text NOT NULL,
    embed_model      text NOT NULL,
    created_at       timestamptz NOT NULL DEFAULT now(),
    updated_at       timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX cv_content_hash_idx  ON cv (content_hash);
CREATE INDEX cv_candidate_key_idx ON cv (candidate_key);
CREATE INDEX cv_status_latest_idx ON cv (status, is_latest);
CREATE UNIQUE INDEX cv_candidate_version_uq ON cv (candidate_key, version) WHERE candidate_key IS NOT NULL;

-- A6, A7: metadata, moi CV mot dong
CREATE TABLE cv_meta (
    cv_id            uuid PRIMARY KEY REFERENCES cv ON DELETE CASCADE,
    location         text,
    years_experience numeric(4,1),
    intern_months    smallint,
    level_rank       smallint CHECK (level_rank BETWEEN 0 AND 5),
    level_source     text CHECK (level_source IN ('title', 'inferred')),
    role_group       text,
    major_group      text CHECK (major_group IN ('it', 'related', 'other')),
    n_bullets        int NOT NULL DEFAULT 0
);

-- A6: tung muc kinh nghiem / du an (Rerank B1, B2, B3)
CREATE TABLE cv_experience (
    cv_id           uuid NOT NULL REFERENCES cv ON DELETE CASCADE,
    idx             int NOT NULL,                       -- 0 = moi nhat
    kind            text NOT NULL CHECK (kind IN ('job', 'intern', 'project_personal', 'project_team')),
    title_raw       text,
    role_group      text,
    role_group_conf real,
    role_group_src  text CHECK (role_group_src IN ('rule', 'keyword')),
    start_ym        text CHECK (start_ym ~ '^\d{4}-\d{2}$'),
    end_ym          text CHECK (end_ym ~ '^\d{4}-\d{2}$'),
    is_current      boolean NOT NULL DEFAULT false,
    months          int,
    dates_quality   text NOT NULL CHECK (dates_quality IN ('ok', 'partial', 'missing')),
    PRIMARY KEY (cv_id, idx)
);

-- A6: tung muc hoc van (Rerank C1). Khong luu ten truong.
CREATE TABLE cv_education (
    cv_id           uuid NOT NULL REFERENCES cv ON DELETE CASCADE,
    idx             int NOT NULL,
    level           text,
    major_raw       text,
    major_group     text CHECK (major_group IN ('it', 'related', 'other')),
    status          text NOT NULL CHECK (status IN ('graduated', 'studying', 'unknown')),
    end_year        smallint,
    expected_end_ym text CHECK (expected_end_ym ~ '^\d{4}-\d{2}$'),
    PRIMARY KEY (cv_id, idx)
);

-- A7: gach dau dong
CREATE TABLE cv_bullet (
    bullet_id     bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    cv_id         uuid NOT NULL REFERENCES cv ON DELETE CASCADE,
    section       text NOT NULL CHECK (section IN ('experience', 'project')),
    item_idx      int NOT NULL,                         -- muc thu may (0 = moi nhat)
    pos           int NOT NULL,                         -- gach thu may trong muc
    text          text NOT NULL,                        -- da chuan hoa (chu thuong)
    text_raw      text NOT NULL,                        -- NFC, giu dau + hoa/thuong: dau vao BERTScore, hien thi Explain
    context_text  text NOT NULL,                        -- "chuc danh: gach" -> vector A10
    has_negation  boolean NOT NULL DEFAULT false,
    is_coursework boolean NOT NULL DEFAULT false,
    UNIQUE (cv_id, section, item_idx, pos)
);
CREATE INDEX cv_bullet_cv_idx ON cv_bullet (cv_id);

-- A5: ky nang + muc bang chung ev
CREATE TABLE cv_skill (
    cv_id            uuid NOT NULL REFERENCES cv ON DELETE CASCADE,
    skill_id         text NOT NULL,
    ev               real NOT NULL CHECK (ev BETWEEN 0 AND 1),
    source_field     text NOT NULL,                     -- vd experiences[0].description[1]
    evidence_snippet text,
    bullet_id        bigint REFERENCES cv_bullet ON DELETE SET NULL,
    last_used        text CHECK (last_used ~ '^\d{4}-\d{2}$'),
    PRIMARY KEY (cv_id, skill_id)
);
CREATE INDEX cv_skill_skill_idx ON cv_skill (skill_id);

-- A10: vector ca CV
CREATE TABLE cv_vector (
    cv_id       uuid PRIMARY KEY REFERENCES cv ON DELETE CASCADE,
    dense       halfvec(1024) NOT NULL,
    sparse      jsonb,                                  -- tu -> trong so
    embed_model text NOT NULL
);

-- A10: vector tung gach
CREATE TABLE cv_bullet_vector (
    bullet_id bigint PRIMARY KEY REFERENCES cv_bullet ON DELETE CASCADE,
    dense     halfvec(1024) NOT NULL
);

-- A9: token BM25 (3 truong rieng)
CREATE TABLE cv_bm25_doc (
    cv_id        uuid PRIMARY KEY REFERENCES cv ON DELETE CASCADE,
    bm25_noacc   text[] NOT NULL DEFAULT '{}',
    bm25_acc     text[] NOT NULL DEFAULT '{}',
    skill_tokens text[] NOT NULL DEFAULT '{}'
);

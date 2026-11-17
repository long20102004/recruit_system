-- Nhom JD (thiet ke 03 "Cac bang", 05 muc "Ket qua va noi luu" cua B1-B8).
-- Moi phien ban JD xac dinh bang (jd_id, version); moi bang con mang cap nay.

CREATE TABLE jd (
    jd_id            text NOT NULL,                     -- lay tu Module 1
    version          int NOT NULL,
    is_latest        boolean NOT NULL DEFAULT true,
    status           text NOT NULL CHECK (status IN ('open', 'draft', 'closed', 'expired')),
    raw_json         jsonb NOT NULL,
    norm_json        jsonb,                             -- B2
    query_text       text,                              -- B3
    warnings         jsonb NOT NULL DEFAULT '[]'::jsonb, -- B8
    ontology_version text NOT NULL,
    pipeline_version text NOT NULL,
    embed_model      text NOT NULL,
    created_at       timestamptz NOT NULL DEFAULT now(),
    updated_at       timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (jd_id, version)
);
CREATE INDEX jd_status_latest_idx ON jd (status, is_latest);
CREATE UNIQUE INDEX jd_one_latest_uq ON jd (jd_id) WHERE is_latest;

-- B5: yeu cau dang metadata (cung ten, cung kieu voi cv_meta)
CREATE TABLE jd_meta (
    jd_id        text NOT NULL,
    version      int NOT NULL,
    location     text,
    work_mode    text,
    min_years    numeric(4,1),
    max_years    numeric(4,1),
    level_rank   smallint CHECK (level_rank BETWEEN 0 AND 5),
    role_group   text,
    edu_required text CHECK (edu_required IN ('none', 'it_related', 'any_degree')),
    PRIMARY KEY (jd_id, version),
    FOREIGN KEY (jd_id, version) REFERENCES jd ON DELETE CASCADE
);

-- B4: ky nang JD
CREATE TABLE jd_skill (
    jd_id    text NOT NULL,
    version  int NOT NULL,
    skill_id text NOT NULL,
    required boolean NOT NULL,
    w_imp    real NOT NULL CHECK (w_imp BETWEEN 0 AND 1),
    group_id int,                                       -- nhom "A hoac B"
    source   text NOT NULL CHECK (source IN ('module1', 'requirements')),
    raw_text text,
    PRIMARY KEY (jd_id, version, skill_id),
    FOREIGN KEY (jd_id, version) REFERENCES jd ON DELETE CASCADE
);
CREATE INDEX jd_skill_skill_idx ON jd_skill (skill_id);

-- B6, B7: trach nhiem
CREATE TABLE jd_responsibility (
    jd_id        text NOT NULL,
    version      int NOT NULL,
    idx          int NOT NULL,
    text         text NOT NULL,
    text_raw     text NOT NULL,
    context_text text NOT NULL,
    is_generic   boolean NOT NULL DEFAULT false,
    dense        halfvec(1024),                         -- dien o B7
    PRIMARY KEY (jd_id, version, idx),
    FOREIGN KEY (jd_id, version) REFERENCES jd ON DELETE CASCADE
);

-- B5: tung dong yeu cau da phan loai
CREATE TABLE jd_requirement_item (
    jd_id    text NOT NULL,
    version  int NOT NULL,
    idx      int NOT NULL,
    text     text NOT NULL,
    text_raw text NOT NULL,
    kind     text NOT NULL CHECK (kind IN ('years', 'degree', 'language', 'skill_only', 'text')),
    PRIMARY KEY (jd_id, version, idx),
    FOREIGN KEY (jd_id, version) REFERENCES jd ON DELETE CASCADE
);

-- B7: vector + token truy van
CREATE TABLE jd_vector (
    jd_id             text NOT NULL,
    version           int NOT NULL,
    dense             halfvec(1024) NOT NULL,
    sparse            jsonb,
    bm25_query_tokens text[] NOT NULL DEFAULT '{}',
    embed_model       text NOT NULL,
    PRIMARY KEY (jd_id, version),
    FOREIGN KEY (jd_id, version) REFERENCES jd ON DELETE CASCADE
);

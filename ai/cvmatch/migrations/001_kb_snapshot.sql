-- Ban chup KB (thiet ke 02 muc 8, 03 "Knowledge Base duoc dung o dau").
-- Chi doc doi voi tien xu ly; nap bang `cvmatch kb import` (T01).
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE kb_version (
    ontology_version  text PRIMARY KEY,              -- = KBVersion.id, vd kb-2026-11-06 / kb-2026-11-14-dev
    created_at        timestamptz,                   -- ngay xuat tu Neo4j (manifest)
    imported_at       timestamptz NOT NULL DEFAULT now(),
    include_candidate boolean NOT NULL DEFAULT false, -- Q-3: ban dev xuat ca candidate
    manifest          jsonb NOT NULL DEFAULT '{}'::jsonb
);

-- T1, T2: ky nang chuan, alias, cha, nhom sibling_ok
CREATE TABLE skill_ontology (
    ontology_version      text NOT NULL REFERENCES kb_version ON DELETE CASCADE,
    skill_id              text NOT NULL,                 -- S0002
    name                  text NOT NULL,
    aliases               text[] NOT NULL DEFAULT '{}',  -- da chuan hoa (NFC, chu thuong, gop khoang trang)
    type                  text NOT NULL CHECK (type IN ('technology', 'concept')),
    parents               text[] NOT NULL DEFAULT '{}',  -- skill_id cha (PARENT_OF)
    categories_sibling_ok text[] NOT NULL DEFAULT '{}',  -- Category co sibling_ok = true
    status                text NOT NULL DEFAULT 'accepted' CHECK (status IN ('accepted', 'candidate')),
    PRIMARY KEY (ontology_version, skill_id)
);

-- T4: alias chuc danh -> nhom vai tro; alias cap bac -> level_rank
CREATE TABLE role_title_map (
    ontology_version text NOT NULL REFERENCES kb_version ON DELETE CASCADE,
    kind             text NOT NULL CHECK (kind IN ('title', 'level')),
    alias            text NOT NULL,
    role_group       text,                               -- kind = title
    level_rank       smallint,                           -- kind = level: Intern 0 .. Lead 5
    PRIMARY KEY (ontology_version, kind, alias),
    CHECK ((kind = 'title' AND role_group IS NOT NULL) OR (kind = 'level' AND level_rank IS NOT NULL))
);

-- T5: khoang cach nhom vai tro M[g,g'] (doi xung, luu mot chieu)
CREATE TABLE role_distance (
    ontology_version text NOT NULL REFERENCES kb_version ON DELETE CASCADE,
    group_a          text NOT NULL,
    group_b          text NOT NULL,
    m                real NOT NULL CHECK (m BETWEEN 0 AND 1),
    method           text NOT NULL CHECK (method IN ('hypothesis', 'computed')),
    PRIMARY KEY (ontology_version, group_a, group_b, method)
);

-- T6: alias nganh hoc -> nhom
CREATE TABLE major_group (
    ontology_version text NOT NULL REFERENCES kb_version ON DELETE CASCADE,
    major_alias      text NOT NULL,
    "group"          text NOT NULL CHECK ("group" IN ('it', 'related', 'other')),
    PRIMARY KEY (ontology_version, major_alias)
);

-- Alias de nham: khong tu khop trong van ban tu do (A5, B4)
CREATE TABLE ambiguous_aliases (
    ontology_version text NOT NULL REFERENCES kb_version ON DELETE CASCADE,
    alias            text NOT NULL,
    candidates       text[] NOT NULL DEFAULT '{}',      -- skill_id co the
    PRIMARY KEY (ontology_version, alias)
);

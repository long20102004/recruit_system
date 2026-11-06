-- Schema for Knowledge Base (PostgreSQL, recruit_kb)
-- Contract: contracts/kb-schema.md

CREATE TABLE IF NOT EXISTS category (
    id SERIAL PRIMARY KEY,
    name TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS skill (
    id INT PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    category_id INT NOT NULL REFERENCES category(id) ON DELETE CASCADE,
    reviewed BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS skill_alias (
    alias_key TEXT PRIMARY KEY,
    skill_id INT NOT NULL REFERENCES skill(id) ON DELETE CASCADE,
    surface TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS skill_edge (
    src_id INT NOT NULL REFERENCES skill(id) ON DELETE CASCADE,
    rel TEXT NOT NULL,
    dst_id INT NOT NULL REFERENCES skill(id) ON DELETE CASCADE,
    PRIMARY KEY (src_id, rel, dst_id),
    CONSTRAINT chk_skill_edge_rel CHECK (rel IN ('PART_OF', 'REQUIRES')),
    CONSTRAINT chk_skill_edge_no_self_loop CHECK (src_id <> dst_id)
);

CREATE TABLE IF NOT EXISTS university (
    id INT PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    reviewed BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS university_alias (
    alias_key TEXT PRIMARY KEY,
    university_id INT NOT NULL REFERENCES university(id) ON DELETE CASCADE,
    surface TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS job_title (
    id INT PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    alias_key TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS job_title_skill (
    job_title_id INT NOT NULL REFERENCES job_title(id) ON DELETE CASCADE,
    skill_id INT NOT NULL REFERENCES skill(id) ON DELETE CASCADE,
    weight REAL DEFAULT 1.0,
    PRIMARY KEY (job_title_id, skill_id)
);

CREATE TABLE IF NOT EXISTS section_heading (
    heading TEXT PRIMARY KEY,
    section TEXT NOT NULL
);

-- T05 reprocess: ban song song cua cung CV o bo khoa phien ban khac (KB / pipeline / model moi).
-- Moi bo khoa (ontology_version, pipeline_version, embed_model) co day so version + is_latest rieng.
DROP INDEX IF EXISTS cv_candidate_version_uq;
CREATE UNIQUE INDEX cv_candidate_version_uq
    ON cv (candidate_key, version, ontology_version, pipeline_version, embed_model) WHERE candidate_key IS NOT NULL;
CREATE INDEX IF NOT EXISTS cv_keys_idx ON cv (ontology_version, pipeline_version, embed_model) WHERE status = 'active';
CREATE INDEX IF NOT EXISTS jd_keys_idx ON jd (jd_id, ontology_version, pipeline_version, embed_model, version);

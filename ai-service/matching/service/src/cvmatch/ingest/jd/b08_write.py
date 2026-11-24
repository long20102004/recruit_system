"""B8. Kiem tra (canh bao HR, khong chan) va ghi mot giao dich (thiet ke 05 B8)."""

from __future__ import annotations

import psycopg

from cvmatch.core.db import transaction
from cvmatch.ingest.common.writer import halfvec, insert_rows, jsonb, log_ingest, upsert_unknown_skills
from cvmatch.ingest.jd.record import JdRecord, PrepContext


def compute_warnings(rec: JdRecord, ctx: PrepContext) -> list[dict]:
    w = []
    if not any(s.required for s in rec.skills_found):
        w.append({"code": "no_required_skill",
                  "message": "JD không có kỹ năng bắt buộc nào gắn được mã: góc nhìn kỹ năng sẽ không dùng được"})
    if not any(not r.is_generic for r in rec.responsibilities):
        w.append({"code": "no_responsibility",
                  "message": "JD không có trách nhiệm cụ thể (hoặc toàn bộ là chung chung)"})
    n_words = len((rec.query_text or "").split())
    if n_words < ctx.cfg.prep.jd.min_query_words:
        w.append({"code": "short_query", "message": f"Văn bản truy vấn chỉ {n_words} từ: chất lượng match thấp"})
    if rec.n_skill_items:
        ratio = len(rec.unknown_skills) / rec.n_skill_items
        if ratio > ctx.cfg.prep.unknown_skill.warn_ratio:
            w.append({"code": "many_unmapped_skills",
                      "message": f"{ratio:.0%} kỹ năng không gắn được mã: KB có thể thiếu kỹ năng của mảng này"})
    return w


def write_jd(conn: psycopg.Connection, rec: JdRecord, *, duration_ms: int | None = None) -> None:
    v = rec.vectors
    if v is None:
        raise ValueError("JdRecord chua co vector (B7)")
    key = (rec.jd_id, rec.version)
    with transaction(conn) as cur:
        cur.execute("UPDATE jd SET is_latest = false, updated_at = now() WHERE jd_id = %s AND is_latest",
                    (rec.jd_id,))
        cur.execute(
            "INSERT INTO jd(jd_id, version, is_latest, status, raw_json, norm_json, query_text, warnings,"
            " ontology_version, pipeline_version, embed_model)"
            " VALUES (%s, %s, true, %s, %s, %s, %s, %s, %s, %s, %s)",
            (*key, rec.status, jsonb(rec.raw_json), jsonb(rec.norm_json), rec.query_text,
             jsonb(rec.warnings), rec.ontology_version, rec.pipeline_version, v["embed_model"]))
        m = rec.meta
        cur.execute(
            "INSERT INTO jd_meta(jd_id, version, location, work_mode, min_years, max_years, level_rank,"
            " role_group, edu_required) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (*key, m.location, m.work_mode, m.min_years, m.max_years, m.level_rank, m.role_group,
             m.edu_required))
        insert_rows(cur, "jd_requirement_item", ("jd_id", "version", "idx", "text", "text_raw", "kind"),
                    [(*key, r.idx, r.text, r.text_raw, r.kind) for r in rec.requirement_items])
        insert_rows(cur, "jd_skill",
                    ("jd_id", "version", "skill_id", "required", "w_imp", "group_id", "source", "raw_text"),
                    [(*key, s.skill_id, s.required, s.w_imp, s.group_id, s.source, s.raw_text)
                     for s in rec.skills_found])
        insert_rows(cur, "jd_responsibility",
                    ("jd_id", "version", "idx", "text", "text_raw", "context_text", "is_generic", "dense"),
                    [(*key, r.idx, r.text, r.text_raw, r.context_text, r.is_generic, halfvec(d))
                     for r, d in zip(rec.responsibilities, v["resp_dense"])], chunk=200)
        cur.execute("INSERT INTO jd_vector(jd_id, version, dense, sparse, bm25_query_tokens, embed_model)"
                    " VALUES (%s, %s, %s, %s, %s, %s)",
                    (*key, halfvec(v["dense"]), jsonb(v["sparse"]), rec.bm25_query_tokens, v["embed_model"]))
        upsert_unknown_skills(cur, rec.unknown_skills, "jd")
        log_ingest(cur, "jd", rec.jd_id, "ok", version=rec.version,
                   flags=[w["code"] for w in rec.warnings], duration_ms=duration_ms)

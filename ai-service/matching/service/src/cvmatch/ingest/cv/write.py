"""A11. Ghi va kich hoat (thiet ke 04 A11): hoac du het, hoac khong co gi.

`write_cvs` ghi MOT LO CV trong mot giao dich (moi bang mot lenh nhieu dong) - van dam bao khong
co CV "nua voi" (atomic theo lo con chat hon theo CV). Service goi lo truoc; lo loi -> rollback roi
ghi lai TUNG CV (`write_cv`) de mot CV loi khong chan ca lo.
Ly do gop lo: moi lenh mang du lieu lon (vector, JSON) bi tre co dinh ~40 ms qua mang Docker
Desktop tren Windows (do duoc), gop lai thi tre mot lan cho ca lo.

Thu tu trong giao dich (giong thiet ke):
 1. `cv` (ban cu cung candidate_key -> is_latest = false)
 2. `cv_meta`, `cv_experience`, `cv_education`
 3. `cv_bullet` (lay bullet_id) -> `cv_bullet_vector`
 4. `cv_skill` (bullet_id da co - tuong duong "dien sau" cua thiet ke, vi cung giao dich)
 5. `cv_vector`, 6. `cv_bm25_doc`, 7. `unknown_skill`, 8. `ingest_log` ok
Su kien `cv_committed` phat SAU khi commit (o service).
"""

from __future__ import annotations

from collections import Counter

import psycopg

from cvmatch.core.db import transaction
from cvmatch.ingest.common.writer import halfvec, insert_rows, jsonb, upsert_unknown_skills
from cvmatch.ingest.cv.record import CvRecord

_CV_COLS = ("cv_id", "candidate_key", "version", "is_latest", "status", "content_hash", "raw_json",
            "anon_json", "doc_text", "flags", "ontology_version", "pipeline_version", "embed_model")
_META_COLS = ("cv_id", "location", "years_experience", "intern_months", "level_rank", "level_source",
              "role_group", "major_group", "n_bullets")
_EXP_COLS = ("idx", "kind", "title_raw", "role_group", "role_group_conf", "role_group_src", "start_ym",
             "end_ym", "is_current", "months", "dates_quality")
_EDU_COLS = ("idx", "level", "major_raw", "major_group", "status", "end_year", "expected_end_ym")
_BULLET_COLS = ("section", "item_idx", "pos", "text", "text_raw", "context_text", "has_negation",
                "is_coursework")
_SKILL_COLS = ("cv_id", "skill_id", "ev", "source_field", "evidence_snippet", "bullet_id", "last_used")
_LOG_COLS = ("entity", "entity_id", "version", "status", "flags", "detail", "duration_ms")


def write_cv(conn: psycopg.Connection, rec: CvRecord, *, duration_ms: int | None = None) -> dict:
    return write_cvs(conn, [rec], durations=[duration_ms])[rec.cv_id]


def write_cvs(conn: psycopg.Connection, recs: list[CvRecord],
              durations: list[int | None] | None = None) -> dict[str, dict]:
    """Ghi mot lo CV trong MOT giao dich. Tra ve {cv_id: {(section, item_idx, pos): bullet_id}}.
    Loi bat ky -> rollback ca lo, raise."""
    if not recs:
        return {}
    for r in recs:
        if r.vectors is None:
            raise ValueError(f"CvRecord {r.cv_id} chua co vector (A10)")
    durations = durations or [None] * len(recs)

    # ban moi nhat cua tung nguoi trong lo (hai ban cung nguoi trong mot lo: chi ban cao nhat is_latest)
    top_version: dict[str, int] = {}
    for r in recs:
        if r.candidate_key:
            top_version[r.candidate_key] = max(r.version, top_version.get(r.candidate_key, 0))

    with transaction(conn) as cur:
        # 1) cv
        keys = sorted(top_version)
        if keys:   # is_latest theo TUNG bo khoa phien ban: ban song song (reprocess) cua cau hinh khac giu nguyen
            r0 = recs[0]
            cur.execute("UPDATE cv SET is_latest = false, updated_at = now()"
                        " WHERE candidate_key = ANY(%s) AND is_latest AND ontology_version = %s"
                        " AND pipeline_version = %s AND embed_model = %s",
                        (keys, r0.ontology_version, r0.pipeline_version, r0.vectors["embed_model"]))
        insert_rows(cur, "cv", _CV_COLS, [
            (r.cv_id, r.candidate_key, r.version,
             (r.candidate_key is None or r.version == top_version[r.candidate_key]), "active",
             r.content_hash, jsonb(r.raw_json), jsonb(r.anon_json), r.doc_text, r.flags,
             r.ontology_version, r.pipeline_version, r.vectors["embed_model"])
            for r in recs])
        # S07: ban moi (version moi / reprocess) ke thua co nhan goi y cua cung nguoi
        cur.execute("UPDATE cv n SET recommendable = true WHERE n.cv_id = ANY(%s::uuid[]) AND n.candidate_key IS NOT NULL"
                    " AND EXISTS (SELECT 1 FROM cv o WHERE o.candidate_key = n.candidate_key AND o.recommendable"
                    " AND o.cv_id <> n.cv_id)", ([r.cv_id for r in recs],))

        # 2) metadata, tung muc kinh nghiem / hoc van
        insert_rows(cur, "cv_meta", _META_COLS, [
            (r.cv_id, r.meta.location, r.meta.years_experience, r.meta.intern_months, r.meta.level_rank,
             r.meta.level_source, r.meta.role_group, r.meta.major_group, r.meta.n_bullets) for r in recs])
        exp_rows, edu_rows = [], []
        for r in recs:
            # idx duy nhat tren ca hai section: kinh nghiem truoc (moi -> cu), du an sau
            for i, e in enumerate(sorted(r.experiences, key=lambda e: (e.section != "experience", e.idx))):
                d = e.model_dump()
                d["idx"] = i
                exp_rows.append((r.cv_id, *(d[c] for c in _EXP_COLS)))
            edu_rows.extend((r.cv_id, *(e.model_dump()[c] for c in _EDU_COLS)) for e in r.education)
        insert_rows(cur, "cv_experience", ("cv_id", *_EXP_COLS), exp_rows)
        insert_rows(cur, "cv_education", ("cv_id", *_EDU_COLS), edu_rows)

        # 3) gach + vector gach. RETURNING kem khoa (cv_id, section, item_idx, pos) nen anh xa
        #    bullet_id khong phu thuoc thu tu dong tra ve.
        bullet_ids: dict[str, dict[tuple[str, int, int], int]] = {r.cv_id: {} for r in recs}
        b_rows = [(r.cv_id, *(getattr(b, c) for c in _BULLET_COLS)) for r in recs for b in r.bullets]
        if b_rows:
            for s in range(0, len(b_rows), 500):
                insert_rows(cur, "cv_bullet", ("cv_id", *_BULLET_COLS), b_rows[s:s + 500],
                            suffix="RETURNING bullet_id, cv_id, section, item_idx, pos")
                for row in cur.fetchall():
                    bullet_ids[str(row["cv_id"])][(row["section"], row["item_idx"], row["pos"])] = row["bullet_id"]
            insert_rows(cur, "cv_bullet_vector", ("bullet_id", "dense"), [
                (bullet_ids[r.cv_id][(b.section, b.item_idx, b.pos)], halfvec(vec))
                for r in recs for b, vec in zip(r.bullets, r.vectors["bullet_dense"])], chunk=300)

        insert_rows(cur, "cv_summary_sentence",
                    ("cv_id", "idx", "text", "text_raw", "has_negation", "is_coursework"),
                    [(r.cv_id, s.idx, s.text, s.text_raw, s.has_negation, s.is_coursework)
                     for r in recs for s in r.summary_sentences])

        # 4) ky nang
        insert_rows(cur, "cv_skill", _SKILL_COLS, [
            (r.cv_id, s.skill_id, s.ev, s.source_field, s.evidence_snippet,
             bullet_ids[r.cv_id].get(tuple(s.bullet_ref)) if s.bullet_ref else None, s.last_used)
            for r in recs for s in r.skills_found])

        # 5) vector CV, 6) token BM25
        insert_rows(cur, "cv_vector", ("cv_id", "dense", "sparse", "embed_model"), [
            (r.cv_id, halfvec(r.vectors["doc_dense"]), jsonb(r.vectors["doc_sparse"]), r.vectors["embed_model"])
            for r in recs], chunk=300)
        insert_rows(cur, "cv_bm25_doc", ("cv_id", "bm25_noacc", "bm25_acc", "skill_tokens"), [
            (r.cv_id, r.bm25.bm25_noacc, r.bm25.bm25_acc, r.bm25.skill_tokens) for r in recs])

        # 7) cum chua co trong KB (dem gop ca lo), 8) log
        cnt: Counter[str] = Counter()
        example: dict[str, str | None] = {}
        for r in recs:
            for u in r.unknown_skills:
                cnt[u.text] += 1
                example.setdefault(u.text, u.example)
        upsert_unknown_skills(cur, [(t, example[t], n) for t, n in sorted(cnt.items())], "cv")
        insert_rows(cur, "ingest_log", _LOG_COLS, [
            ("cv", r.cv_id, r.version, "ok", r.flags,
             jsonb({"replaces_cv_id": r.replaces_cv_id, "n_bullets": len(r.bullets),
                    "n_skills": len(r.skills_found)}), d)
            for r, d in zip(recs, durations)])
    return bullet_ids

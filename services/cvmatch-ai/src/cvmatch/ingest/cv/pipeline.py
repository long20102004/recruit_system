"""Luong A, buoc A1-A9: CV JSON -> CvRecord (chua co vector). Ham thuan: khong DB, khong GPU.

Tra cuu trung (A2) qua `ctx.dedup` (interface); T05 noi Postgres, A10 embedding va A11 ghi.
Dung som: `InvalidCV` (A1), `DuplicateCV` (A2).
"""

from __future__ import annotations

from typing import Any

from cvmatch.ingest.cv.a01_schema import step_a01
from cvmatch.ingest.cv.a02_dedup import step_a02
from cvmatch.ingest.cv.a03_anonymize import step_a03
from cvmatch.ingest.cv.a04_normalize import step_a04
from cvmatch.ingest.cv.a05_skills import step_a05
from cvmatch.ingest.cv.a06_meta import step_a06
from cvmatch.ingest.cv.a07_bullets import step_a07
from cvmatch.ingest.cv.a08_doc_text import step_a08
from cvmatch.ingest.cv.a09_bm25 import step_a09
from cvmatch.ingest.cv.record import CvContext, CvRecord

# A7 chay truoc A5/A6 ve mat du lieu khong can, nhung giu dung thu tu thiet ke cho de doc:
# A5 va A6 tu goi lai ham tach gach cua A7 (thuan, tat dinh) khi can vi tri gach.
STEPS_AFTER_A04 = (step_a05, step_a06, step_a07, step_a08, step_a09)


def build_cv_record(raw_input: Any, ctx: CvContext) -> CvRecord:
    rec = step_a01(raw_input, ctx)
    rec = step_a02(rec, raw_input, ctx)
    rec = step_a03(rec, ctx)
    rec = step_a04(rec, ctx)
    for step in STEPS_AFTER_A04:
        rec = step(rec, ctx)
    return rec

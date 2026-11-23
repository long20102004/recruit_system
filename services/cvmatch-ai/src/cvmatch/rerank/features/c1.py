"""C1 hoc van (thiet ke 07 muc 5.7).

    C1 = w_major x major_rel + w_degree x degree_status        (lay muc hoc van tot nhat)
    major_rel:     it 1,0 · related 0,7 · other 0,3            (cv_education.major_group)
    degree_status: da tot nghiep 1,0 · dang hoc con <= 12 thang 0,7 · dang hoc con > 12 thang 0,3

- Da tot nghiep LUON 1,0 bat ke tot nghiep bao lau (khong de feature thanh bien thay the tuoi).
- `status = unknown` (khong co ngay) coi nhu da tot nghiep: khong phat vi thieu ngay.
- `edu_required` in {none, NULL} -> null phia JD. Muc khong co `major_group` bo qua; khong con muc
  nao -> null phia CV. Khong dung ten truong / GPA.
"""

from __future__ import annotations

from dataclasses import dataclass

from cvmatch.core.config import C1Config
from cvmatch.core.timeutil import ym_to_index


@dataclass(frozen=True)
class Edu:
    major_group: str | None
    status: str                       # graduated | studying | unknown
    expected_end_ym: str | None = None


def degree_status(e: Edu, ref_ym: str, cfg: C1Config) -> float:
    if e.status != "studying":
        return cfg.degree_graduated
    if e.expected_end_ym is None:
        return cfg.degree_later
    remaining = ym_to_index(e.expected_end_ym) - ym_to_index(ref_ym)
    return cfg.degree_soon if remaining <= cfg.soon_months else cfg.degree_later


def c1_education(edus: list[Edu], edu_required: str | None, ref_ym: str, cfg: C1Config,
                 ) -> tuple[float | None, str | None]:
    if edu_required in (None, "none"):
        return None, "jd_side"
    vals = [cfg.w_major * cfg.major_rel[e.major_group] + cfg.w_degree * degree_status(e, ref_ym, cfg)
            for e in edus if e.major_group in cfg.major_rel]
    if not vals:
        return None, "cv_side"
    return max(vals), None

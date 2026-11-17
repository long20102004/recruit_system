"""B1 dung huong vai tro, B2 so nam lien quan (thiet ke 07 muc 5.6). B3 cap bac la P2 (T15).

Quy uoc dem thang dung chung `core.timeutil` (tinh ca hai dau; thang hien tai cua muc dang lam chua tinh).

B1 = sum_g share_g x M[g, g_JD]
    share_g = ty trong thang lam viec theo nhom; muc ket thuc trong `recent_months` gan `ref_ym` nhan
    `recent_boost`. Chi dung job/intern; khong co -> dung du an (trong so loai nhu B2). Muc khong co
    ngay bi bo qua; muc co ngay nhung khong ro nhom (vd "Designer") van vao mau so voi M = 0.
    Khong con muc nao co ngay -> None (thieu phia CV).

B2: m_g(muc) = 1 cung nhom · 0,5 neu M >= 0,5 · 0; trong_so_loai = 1 job/intern · project_personal_weight
    du an (ca du an nhom) · 0 neu thieu ngay; moi THANG lay max; y = tong / 12; fit(y) theo min/max.
    JD khong ro nhom -> m_g = 1 cho moi muc (so nam lam viec noi chung).
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass

from cvmatch.core.config import B1Config, B2Config
from cvmatch.core.timeutil import month_span, ym_to_index

RoleM = Callable[[str | None, str | None], float | None]
WORK_KINDS = ("job", "intern")
PROJECT_KINDS = ("project_personal", "project_team")


@dataclass(frozen=True)
class Exp:
    kind: str
    role_group: str | None
    start_ym: str | None
    end_ym: str | None
    is_current: bool = False

    def span(self) -> range | None:
        return month_span(self.start_ym, self.end_ym, is_current=self.is_current)


def _kind_weight(e: Exp, cfg: B2Config) -> float:
    if e.span() is None:
        return 0.0
    return 1.0 if e.kind in WORK_KINDS else cfg.project_personal_weight


# --------------------------------------------------------------------------- B1


def role_shares(exps: Iterable[Exp], b1: B1Config, b2: B2Config, ref_ym: str) -> dict[str | None, float]:
    """Ty trong theo nhom; muc co ngay nhung khong ro nhom -> khoa None (M = 0), khong phai thieu du lieu."""
    exps = list(exps)
    work = [e for e in exps if e.kind in WORK_KINDS and e.span() is not None]
    use = work or [e for e in exps if e.kind in PROJECT_KINDS and e.span() is not None]
    ref = ym_to_index(ref_ym)
    weights: dict[str | None, float] = {}
    for e in use:
        sp = e.span()
        w = len(sp) * _kind_weight(e, b2)
        if ref - sp[-1] < b1.recent_months:          # muc ket thuc trong 36 thang gan nhat
            w *= b1.recent_boost
        weights[e.role_group] = weights.get(e.role_group, 0.0) + w
    total = sum(weights.values())
    return {g: w / total for g, w in weights.items()} if total > 0 else {}


def b1_role(exps: Iterable[Exp], g_jd: str | None, M: RoleM, b1: B1Config, b2: B2Config,
            ref_ym: str) -> tuple[float | None, str | None, dict[str, float]]:
    """-> (B1, 'jd_side'|'cv_side'|None, share_g)."""
    if g_jd is None:
        return None, "jd_side", {}
    shares = role_shares(exps, b1, b2, ref_ym)
    if not shares:
        return None, "cv_side", {}
    return float(sum(s * (M(g, g_jd) or 0.0) for g, s in shares.items())), None, shares


# --------------------------------------------------------------------------- B2


def relevant_years(exps: Iterable[Exp], g_jd: str | None, M: RoleM, cfg: B2Config) -> float | None:
    """None khi CV co muc nhung khong muc nao co ngay (khong tinh duoc); khong co muc nao -> 0."""
    exps = list(exps)
    if not exps:
        return 0.0
    if all(e.span() is None for e in exps):
        return None
    per_month: dict[int, float] = {}
    for e in exps:
        kw = _kind_weight(e, cfg)
        if kw <= 0:
            continue
        if g_jd is None:
            mg = 1.0
        elif e.role_group == g_jd:
            mg = 1.0
        else:
            mg = 0.5 if (M(e.role_group, g_jd) or 0.0) >= 0.5 else 0.0
        w = mg * kw
        if w <= 0:
            continue
        for t in e.span():
            if w > per_month.get(t, 0.0):
                per_month[t] = w
    return sum(per_month.values()) / 12.0


def years_fit(y: float, min_years: float | None, max_years: float | None, *,
              overqual_penalty: bool = True) -> float | None:
    """fit(y): JD khong co min lan max -> None; chi co min -> khong phat thua."""
    if min_years is None and max_years is None:
        return None
    if min_years is not None and min_years > 0 and y < min_years:
        return y / min_years
    if max_years is not None and y > max_years:
        return max(0.6, 1.0 - 0.1 * (y - max_years)) if overqual_penalty else 1.0
    return 1.0


def b2_years(exps: Iterable[Exp], g_jd: str | None, M: RoleM, cfg: B2Config, min_years: float | None,
             max_years: float | None, *, overqual_penalty: bool | None = None,
             ) -> tuple[float | None, str | None, float | None]:
    """-> (B2, 'jd_side'|'cv_side'|None, y)."""
    pen = cfg.overqual_penalty if overqual_penalty is None else overqual_penalty
    y = relevant_years(exps, g_jd, M, cfg)
    if min_years is None and max_years is None:
        return None, "jd_side", y
    if y is None:
        return None, "cv_side", None
    return years_fit(y, min_years, max_years, overqual_penalty=pen), None, y

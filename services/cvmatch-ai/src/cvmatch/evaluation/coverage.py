"""T07: script do phu Module 1 (thiet ke 11 muc 2.1, 3.1).

Tra loi bang so: voi du lieu that, truong nao du de BAT feature nao. Feature chua dat nguong thi
tat trong config, khong doan bu. Bao cao chi DE XUAT sua `config/rr-*.yaml`, khong tu sua.

Doc JSON qua adapter + schema cua T04/T06 (khong viet parser rieng) va chi chay A1 (adapter,
kiem kieu, sua ngay) - khong chay pipeline day du, khong can DB / KB / GPU.
"""

from __future__ import annotations

import copy
import json
import re
import statistics
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from cvmatch.core.text.diacritics import no_diacritics
from cvmatch.core.text.normalize import _MONTHS_EN, normalize
from cvmatch.ingest.cv.a01_schema import _fix_dates
from cvmatch.ingest.cv.a04_normalize import free_texts
from cvmatch.ingest.cv.a07_bullets import n_words, split_description
from cvmatch.ingest.cv.adapter import adapt_cv
from cvmatch.ingest.cv.schema import InvalidCV, validate_cv
from cvmatch.ingest.jd.schema import InvalidJD, _as_list, adapt_jd, validate_jd

# Nhan hien thi cua tung dong (thu tu = thu tu trong bao cao)
CV_ROWS = {
    "cv_exp_dated": "CV có ≥ 1 kinh nghiệm đủ `title` + `start` + (`end` | `is_current`)",
    "cv_has_bullet": "CV có ≥ 1 gạch `description` (sau tách, ≥ `bullet.min_words` từ)",
    "cv_edu_major_end": "CV có `major` + `end` học vấn",
    "cv_item_kind": "CV phân biệt job / dự án (có trường `projects` riêng — kể cả rỗng — hoặc `kind`)",
    "cv_has_technologies": "CV có `technologies` ở kinh nghiệm/dự án",
    "cv_date_unparsed": "CV có ngày không đọc được (`date_unparsed`)",
    "cv_no_diacritics": "CV tiếng Việt gõ không dấu (`no_diacritics`)",
}
JD_ROWS = {
    "jd_responsibilities": "JD có `responsibilities`",
    "jd_skills": "JD có `skills`",
    "jd_skill_required": "JD: `skills` kèm `required`",
    "jd_skill_importance": "JD: `skills` kèm `importance`",
    "jd_min_years": "JD có `min_years`",
    "jd_level": "JD có `level`",
    "jd_role_group": "JD có `role_group`",
    "jd_edu_required": "JD có yêu cầu học vấn (`edu_required`)",
}
_UNDER = {"cv_date_unparsed", "cv_no_diacritics"}   # dong "cang thap cang tot", khong co nguong bat
DATED_SECTIONS = ("experiences", "projects", "education")


def load_coverage_config(config_dir: str | Path) -> dict:
    with (Path(config_dir) / "coverage.yaml").open(encoding="utf-8") as f:
        return yaml.safe_load(f)


# --------------------------------------------------------------------------- dinh dang ngay

_DIGIT_RE = re.compile(r"\d")
_WORD_RE = re.compile(r"[^\W\d_]+", re.UNICODE)


def date_shape(v: Any) -> str:
    """Mau dinh dang cua mot gia tri ngay: so -> 9, ten thang tieng Anh -> Mon. vd 'Tháng 3/2022' -> 'tháng 9/9999'."""
    if isinstance(v, bool) or v is None:
        return repr(v)
    if isinstance(v, int):
        return "int:" + _DIGIT_RE.sub("9", str(v))
    s = normalize(str(v)).strip()
    s = _DIGIT_RE.sub("9", s)
    return _WORD_RE.sub(lambda m: "Mon" if m.group(0)[:3] in _MONTHS_EN else m.group(0), s)


# --------------------------------------------------------------------------- dem tung tai lieu


@dataclass
class CvStats:
    valid: bool
    has: dict[str, bool] = field(default_factory=dict)
    date_shapes: list[str] = field(default_factory=list)
    desc_forms: Counter = field(default_factory=Counter)      # list | str (theo muc co description)
    n_bullets: int = 0
    bullet_lens: list[int] = field(default_factory=list)
    errors: list[dict] = field(default_factory=list)


def _filled(v: Any) -> bool:
    return v not in (None, "", [], {})


def cv_stats(raw: Any, *, min_words: int, no_diac_threshold: float, tokenizer=None) -> CvStats:
    """Mot CV JSON -> cac dong do phu. Sai schema (A1) -> valid=False, khong dem tiep."""
    adapted = adapt_cv(copy.deepcopy(raw)) if isinstance(raw, dict) else raw
    try:
        validate_cv(adapted)
    except InvalidCV as e:
        return CvStats(valid=False, errors=e.errors)
    cv = copy.deepcopy(adapted)
    st = CvStats(valid=True)
    for sec in DATED_SECTIONS:
        for it in cv.get(sec) or []:
            if isinstance(it, dict):
                st.date_shapes.extend(date_shape(it[k]) for k in ("start", "end") if _filled(it.get(k)))
    flags: list[str] = []
    _fix_dates(cv, flags, [])                                   # A1: sua ngay ve YYYY-MM

    exps = [e for e in cv.get("experiences") or [] if isinstance(e, dict)]
    projs = [p for p in cv.get("projects") or [] if isinstance(p, dict)]
    edus = [e for e in cv.get("education") or [] if isinstance(e, dict)]
    st.has["cv_exp_dated"] = any(_filled(e.get("title")) and e.get("start") and (e.get("end") or e.get("is_current"))
                                 for e in exps)
    for it in exps + projs:
        d = it.get("description")
        if isinstance(d, list) and d:
            st.desc_forms["list"] += 1
        elif isinstance(d, str) and d.strip():
            st.desc_forms["str"] += 1
        for part in split_description(d, min_words):
            if part.kept:
                st.n_bullets += 1
                st.bullet_lens.append(len(tokenizer(part.raw)) if tokenizer else n_words(part.raw))
    st.has["cv_has_bullet"] = st.n_bullets > 0
    st.has["cv_edu_major_end"] = any(_filled(e.get("major")) and e.get("end") for e in edus)
    # Module 1 tach du an khi JSON CO truong `projects` (ke ca rong); hoac moi muc co `kind`
    st.has["cv_item_kind"] = "projects" in adapted or any(_filled(it.get("kind")) for it in exps + projs)
    st.has["cv_has_technologies"] = any(_filled(it.get("technologies")) for it in exps + projs)
    st.has["cv_date_unparsed"] = "date_unparsed" in flags
    st.has["cv_no_diacritics"] = no_diacritics(free_texts(cv), no_diac_threshold)
    return st


@dataclass
class JdStats:
    valid: bool
    has: dict[str, bool] = field(default_factory=dict)
    errors: list[dict] = field(default_factory=list)


def jd_stats(raw: Any) -> JdStats:
    adapted = adapt_jd(copy.deepcopy(raw))
    try:
        validate_jd(adapted)
    except InvalidJD as e:
        return JdStats(valid=False, errors=e.errors)
    skills = [s for s in _as_list(adapted.get("skills")) if s]
    dict_sk = [s for s in skills if isinstance(s, dict)]
    st = JdStats(valid=True)
    st.has = {
        "jd_responsibilities": bool([r for r in _as_list(adapted.get("responsibilities")) if str(r).strip()]),
        "jd_skills": bool(skills),
        # "kem required/importance": MOI ky nang dang object co truong do (thieu -> w_imp = 1, bat buoc)
        "jd_skill_required": bool(skills) and len(dict_sk) == len(skills) and all("required" in s for s in dict_sk),
        "jd_skill_importance": bool(skills) and len(dict_sk) == len(skills)
        and all(_filled(s.get("importance")) for s in dict_sk),
        "jd_min_years": adapted.get("min_years") is not None,
        "jd_level": _filled(adapted.get("level")),
        "jd_role_group": _filled(adapted.get("role_group")),
        "jd_edu_required": _filled(adapted.get("edu_required")),
    }
    return st


# --------------------------------------------------------------------------- tong hop


def _percentile(xs: list[int], q: float) -> float | None:
    if not xs:
        return None
    s = sorted(xs)
    k = (len(s) - 1) * q
    lo, hi = int(k), min(int(k) + 1, len(s) - 1)
    return float(s[lo] + (s[hi] - s[lo]) * (k - lo))


@dataclass
class CoverageReport:
    n_cv_files: int
    n_cv: int                                   # hop le
    n_jd_files: int
    n_jd: int
    rates: dict[str, float | None]              # dong -> ti le tren so tai lieu HOP LE
    thresholds: dict[str, float]
    features: dict[str, list[str]]
    date_formats: list[tuple[str, int]]
    desc_forms: dict[str, int]
    bullets_per_cv: float | None
    bullet_len_p50: float | None
    bullet_len_p95: float | None
    len_unit: str
    invalid: list[tuple[str, str]]              # (nguon, loi dau tien)
    current_features: list[str]

    def passed(self, row: str) -> bool | None:
        r = self.rates.get(row)
        t = self.thresholds.get(row)
        if r is None or t is None:
            return None
        return r >= t

    def feature_on(self, feat: str) -> tuple[bool | None, list[str]]:
        """-> (bat?, cac dong khong dat). None khi chua co du lieu cho dong nao."""
        rows = self.features.get(feat, [])
        res = {r: self.passed(r) for r in rows}
        failed = [r for r, ok in res.items() if ok is False]
        if failed:
            return False, failed
        if rows and all(ok is None for ok in res.values()):
            return None, []
        return True, []

    def suggested_features(self) -> list[str]:
        """features_enabled de xuat: giu feature dang bat ma du lieu cho phep (chua co du lieu -> giu)."""
        return [f for f in self.current_features if self.feature_on(f)[0] is not False]

    def to_markdown(self) -> str:
        pct = lambda x: "–" if x is None else f"{100 * x:.1f}%"  # noqa: E731
        by_row: dict[str, list[str]] = {}
        for f, rows in self.features.items():
            for r in rows:
                by_row.setdefault(r, []).append(f)
        out = ["# Báo cáo độ phủ Module 1", "",
               f"- CV: {self.n_cv} hợp lệ / {self.n_cv_files} file · JD: {self.n_jd} hợp lệ / {self.n_jd_files} file",
               "- Tỉ lệ tính trên tài liệu **hợp lệ** (qua A1). Ngưỡng ở `config/coverage.yaml` (thiết kế 11 mục 2.1).",
               "", "## Trường · tỉ lệ · ngưỡng · feature", "",
               "| Trường | Tỉ lệ | Ngưỡng | Đạt | → Feature |", "| --- | --- | --- | --- | --- |"]
        for row, label in {**CV_ROWS, **JD_ROWS}.items():
            ok = self.passed(row)
            mark = "–" if ok is None else ("✅" if ok else "❌ tắt")
            feats = ", ".join(by_row.get(row, [])) or ("ghi nhận (thấp là tốt)" if row in _UNDER else "ghi nhận")
            thr = self.thresholds.get(row)
            out.append(f"| {label} | {pct(self.rates.get(row))} | {'≥ ' + pct(thr) if thr is not None else '–'}"
                       f" | {mark} | {feats} |")
        out += ["", "## Quyết định theo feature", "", "| Feature | Bật? | Lý do |", "| --- | --- | --- |"]
        for f in self.features:
            on, failed = self.feature_on(f)
            if failed:
                why = "không đạt: " + ", ".join(failed)
            elif on is None:
                why = "chưa có dữ liệu"
            else:
                why = "đủ ngưỡng" if self.features[f] else "không cần trường riêng"
            out.append(f"| {f} | {'–' if on is None else ('bật' if on else '**tắt**')} | {why} |")
        jd_req = self.rates.get("jd_skill_required")
        jd_imp = self.rates.get("jd_skill_importance")
        if jd_req is not None and (jd_req < 1 or (jd_imp or 0) < 1):
            out += ["", f"> A1/A2: {pct(jd_req)} JD có `required`, {pct(jd_imp)} có `importance` cho mọi kỹ năng. "
                        "Thiếu → mọi kỹ năng coi là bắt buộc, `w_imp = 1` (thiết kế 11 mục 3.1.2)."]
        out += ["", "## Chi tiết", "",
                f"- Số gạch trung bình / CV: {'–' if self.bullets_per_cv is None else f'{self.bullets_per_cv:.2f}'}",
                f"- Độ dài gạch ({self.len_unit}): p50 = {self.bullet_len_p50 if self.bullet_len_p50 is not None else '–'},"
                f" p95 = {self.bullet_len_p95 if self.bullet_len_p95 is not None else '–'}",
                f"- `description` theo mục: mảng {self.desc_forms.get('list', 0)} · đoạn văn {self.desc_forms.get('str', 0)}",
                "", f"### Định dạng ngày (top {len(self.date_formats)})", "",
                "| Mẫu | Số lần |", "| --- | --- |"]
        out += [f"| `{s}` | {n} |" for s, n in self.date_formats] or ["| – | 0 |"]
        if self.invalid:
            out += ["", f"### Tài liệu sai schema ({len(self.invalid)})", ""]
            out += [f"- `{src}`: {err}" for src, err in self.invalid[:30]]
        sug = self.suggested_features()
        out += ["", "## Đề xuất sửa config (không tự sửa)", "",
                f"Feature đang bật (`{', '.join(self.current_features)}`) → đề xuất:", "", "```yaml",
                f"features_enabled: [{', '.join(sug)}]", "```"]
        off = [f for f in self.features if self.feature_on(f)[0] is False]
        if off:
            out.append(f"\nKhông bật ở P2 khi dữ liệu chưa đổi: {', '.join(off)}.")
        if not self.n_cv or not self.n_jd:
            out.append("\n> Chưa đủ cả CV và JD: dòng không có dữ liệu để `–`, feature tương ứng giữ nguyên.")
        return "\n".join(out) + "\n"


def _iter_json(path: str | Path | None):
    if path is None:
        return
    p = Path(path)
    for f in sorted(p.rglob("*.json")) if p.is_dir() else [p]:
        try:
            yield str(f), json.loads(f.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            yield str(f), e


def _first_err(errors: list[dict]) -> str:
    if not errors:
        return "?"
    e = errors[0]
    return f"{'.'.join(map(str, e.get('loc', [])))}: {e.get('msg')}"


def run_coverage(cv_items: list[tuple[str, Any]], jd_items: list[tuple[str, Any]], *, cov_cfg: dict,
                 min_words: int, no_diac_threshold: float, current_features: list[str],
                 tokenizer=None, len_unit: str = "từ") -> CoverageReport:
    invalid: list[tuple[str, str]] = []
    cvs: list[CvStats] = []
    for src, raw in cv_items:
        if isinstance(raw, Exception):
            invalid.append((src, f"JSON lỗi: {raw}"))
            continue
        st = cv_stats(raw, min_words=min_words, no_diac_threshold=no_diac_threshold, tokenizer=tokenizer)
        (cvs.append(st) if st.valid else invalid.append((src, _first_err(st.errors))))
    jds: list[JdStats] = []
    for src, raw in jd_items:
        if isinstance(raw, Exception):
            invalid.append((src, f"JSON lỗi: {raw}"))
            continue
        st = jd_stats(raw)
        (jds.append(st) if st.valid else invalid.append((src, _first_err(st.errors))))

    rate = lambda docs, k: (sum(d.has[k] for d in docs) / len(docs)) if docs else None  # noqa: E731
    rates = {k: rate(cvs, k) for k in CV_ROWS} | {k: rate(jds, k) for k in JD_ROWS}
    shapes = Counter(s for c in cvs for s in c.date_shapes)
    forms = Counter()
    for c in cvs:
        forms.update(c.desc_forms)
    lens = [x for c in cvs for x in c.bullet_lens]
    return CoverageReport(
        n_cv_files=len(cv_items), n_cv=len(cvs), n_jd_files=len(jd_items), n_jd=len(jds), rates=rates,
        thresholds=dict(cov_cfg.get("thresholds") or {}), features=dict(cov_cfg.get("features") or {}),
        date_formats=shapes.most_common(int(cov_cfg.get("top_date_formats", 10))), desc_forms=dict(forms),
        bullets_per_cv=statistics.fmean(c.n_bullets for c in cvs) if cvs else None,
        bullet_len_p50=_percentile(lens, 0.5), bullet_len_p95=_percentile(lens, 0.95), len_unit=len_unit,
        invalid=invalid, current_features=list(current_features))


def coverage_from_dirs(cv_dir: str | Path | None, jd_dir: str | Path | None, cfg, *, tokenizer=None,
                       len_unit: str = "từ") -> CoverageReport:
    return run_coverage(list(_iter_json(cv_dir)), list(_iter_json(jd_dir)),
                        cov_cfg=load_coverage_config(cfg.config_dir), min_words=cfg.prep.bullet.min_words,
                        no_diac_threshold=cfg.prep.no_diacritics.threshold,
                        current_features=list(cfg.rerank.features_enabled), tokenizer=tokenizer, len_unit=len_unit)

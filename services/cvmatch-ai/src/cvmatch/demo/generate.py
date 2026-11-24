"""Sinh bo CV / JD tong hop "giong that" cho moi truong demo (DU LIEU GIA, tat dinh theo seed).

Co y lam du da dang de thu API nhieu kieu:
- ~23 vai tro (ti trong gan thi truong IT VN), 6 cap bac, 1-4 muc kinh nghiem, doi nghe, dan dat nhom;
- description dang mang / doan van / tieng Anh / bo trong; ngay thang nhieu dinh dang ("03/2021",
  "Tháng 3/2021", "Mar 2021", "2021", "Hiện tại", "present"); ten truong kieu khac (adapter);
- CV go khong dau, cau phu dinh, mo ta hoc tap, sinh vien dang hoc, CV it thong tin;
- mot so nguoi co 2 ban CV (cung email, ban moi hon) -> version 2;
- JD: ky nang co / khong `required` + `importance`, yeu cau dang chu, so nam, hoc van, ngoai ngu, dia diem,
  hinh thuc lam viec, trang thai open / closed / draft.
`manifest.json` ghi vai tro / nhom / cap bac / so nam that cua tung file de kich ban API kiem tra hop ly.
"""

from __future__ import annotations

import json
import random
from pathlib import Path

from cvmatch.core.text.normalize import strip_diacritics
from cvmatch.demo.pools import (COMPANIES, COURSEWORK, FIRST, LAST, LEVEL_WEIGHTS, LEVELS, LOCATION_WEIGHTS,
                                LOCATIONS, MAJORS_IT, MAJORS_OTHER, MAJORS_RELATED, MIDDLE, NEGATION, ROLE_WEIGHTS,
                                ROLES, SCHOOLS, SOFT)

REF_YEAR, REF_MONTH = 2026, 11
MONTHS_EN = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def _fmt_date(y: int, m: int, rng: random.Random) -> str | int:
    k = rng.random()
    if k < 0.45:
        return f"{y}-{m:02d}"
    if k < 0.70:
        return f"{m:02d}/{y}"
    if k < 0.82:
        return f"Tháng {m}/{y}"
    if k < 0.92:
        return f"{MONTHS_EN[m - 1]} {y}"
    return y if rng.random() < 0.5 else str(y)            # chi co nam


def _bullet(text: str, rng: random.Random) -> str:
    return text.replace("{n}", str(rng.choice([15, 20, 25, 30, 35, 40, 50, 60, 70, 80, 100])))


def _months_back(y: int, m: int, n: int) -> tuple[int, int]:
    t = y * 12 + (m - 1) - n
    return t // 12, t % 12 + 1


def _name(rng: random.Random) -> str:
    return f"{rng.choice(LAST)} {rng.choice(MIDDLE)} {rng.choice(FIRST)}"


def _pick_role(rng: random.Random) -> str:
    keys = list(ROLE_WEIGHTS)
    return rng.choices(keys, weights=[ROLE_WEIGHTS[k] for k in keys])[0]


def make_cv(i: int, rng: random.Random, *, role: str | None = None, level_idx: int | None = None) -> tuple[dict, dict]:
    role = role or _pick_role(rng)
    R = ROLES[role]
    li = level_idx if level_idx is not None else rng.choices(range(len(LEVELS)), weights=LEVEL_WEIGHTS)[0]
    if role == "non_it":
        li = rng.choice([1, 2, 3])
    lvl_name, lvl_rank, years = LEVELS[li]
    years = max(0.0, years + rng.uniform(-0.8, 1.5))
    english = rng.random() < 0.10
    student = li <= 1 and rng.random() < 0.6
    switch = rng.random() < 0.10 and li >= 3
    flags: list[str] = []

    # kinh nghiem: lui dan tu thang hien tai
    exps = []
    remaining = int(round(years * 12))
    cy, cm = REF_YEAR, REF_MONTH
    n_items = 1 if remaining < 18 else rng.randint(2, 4)
    for k in range(n_items):
        if remaining <= 0 and k > 0:
            break
        dur = remaining if k == n_items - 1 else max(6, int(remaining * rng.uniform(0.3, 0.6)))
        dur = max(3, dur)
        sy, sm = _months_back(cy, cm, dur)
        r_role = role
        if switch and k == n_items - 1:
            r_role = rng.choice([r for r in ROLES if ROLES[r]["group"] and r != role])
            flags.append(f"switch_from:{r_role}")
        RR = ROLES[r_role]
        title = rng.choice(RR["titles"])
        if k == 0 and lvl_name and lvl_name not in ("Intern",) and r_role != "non_it":
            title = f"{lvl_name} {title}"
        if lvl_name == "Intern" and k == 0:
            title = f"Thực tập sinh {title}"
        pool = RR["en"] if english else RR["vi"]
        n_b = rng.randint(min(2, len(pool)), min(5, len(pool))) if pool else 0
        bullets = [_bullet(b, rng) for b in rng.sample(pool, n_b)]
        if k == 0 and lvl_rank >= 5 and not english:
            bullets.append("Dẫn dắt nhóm 6 kỹ sư, thiết kế kiến trúc hệ thống và review code")
        if rng.random() < 0.08 and not english:
            bullets.append(rng.choice(NEGATION))
            flags.append("negation")
        if rng.random() < 0.15 and not english:
            bullets.append(rng.choice(SOFT))
        form = rng.random()
        if form < 0.03:
            desc = []
            flags.append("no_bullets")
        elif form < 0.28:
            desc = ". ".join(b.rstrip(".") for b in bullets) + "."
            flags.append("paragraph")
        else:
            desc = bullets
        current = k == 0 and not student and rng.random() < 0.8
        e = {"title": title, "company": rng.choice(COMPANIES), "start": _fmt_date(sy, sm, rng),
             "end": (rng.choice(["Hiện tại", "present", "nay"]) if current and rng.random() < 0.5 else
                     None if current else _fmt_date(cy, cm, rng)),
             "description": desc,
             "technologies": rng.sample(RR["core"] + RR["extra"], min(len(RR["core"] + RR["extra"]),
                                                                       rng.randint(2, 5)))}
        if current and e["end"] is None:
            e["is_current"] = True
        if lvl_name == "Intern" and k == 0:
            e["type"] = "intern"
        exps.append(e)
        remaining -= dur
        cy, cm = _months_back(sy, sm, rng.randint(0, 3))
    if student and rng.random() < 0.3:
        exps = []                                           # sinh vien chua di lam

    projects = []
    if (student or li <= 2) and R["projects"]:
        for _ in range(rng.randint(1, 2)):
            tech = rng.choice(R["core"])
            pd = [_bullet(rng.choice(R["vi"]), rng)]
            if rng.random() < 0.4:
                pd.append(rng.choice(COURSEWORK).replace("{tech}", tech))
                flags.append("coursework")
            projects.append({"name": rng.choice(R["projects"]), "role": "Thành viên",
                             "description": pd, "technologies": rng.sample(R["core"], 2),
                             "kind": rng.choice(["personal", "team"])})

    if role in ("designer", "non_it", "ba", "pm"):
        major = rng.choice(MAJORS_OTHER + MAJORS_IT)
    else:
        major = rng.choices([rng.choice(MAJORS_IT), rng.choice(MAJORS_RELATED), rng.choice(MAJORS_OTHER)],
                            weights=[80, 15, 5])[0]
    grad_year = REF_YEAR + (1 if student else -int(years) - rng.randint(0, 1))
    edu = {"school": rng.choice(SCHOOLS), "major": major,
           "degree": rng.choice(["Kỹ sư", "Cử nhân"]),
           "start": str(grad_year - 4),
           "end": ("Đang học" if student and rng.random() < 0.5 else f"{rng.randint(5, 8):02d}/{grad_year}")}
    if student:
        flags.append("student")

    skills = list(dict.fromkeys(R["core"] + rng.sample(R["extra"], min(len(R["extra"]), rng.randint(1, 5)))))
    if rng.random() < 0.12:
        skills = skills + rng.sample(["Git", "Jira", "Agile", "Docker", "Linux", "SQL", "Excel"], 3)
    name = _name(rng)
    gender = rng.choice(["Nam", "Nữ"])
    t0 = exps[0]["title"] if exps else f"Sinh viên {major}"
    summary = (f"{t0} with {years:.0f} years of experience." if english else
               rng.choice([f"{t0} với {years:.0f} năm kinh nghiệm, mong muốn phát triển trong môi trường chuyên nghiệp.",
                           f"Có kinh nghiệm {', '.join(skills[:3])}. Mong muốn tham gia dự án sản phẩm lớn.",
                           f"Định hướng trở thành {rng.choice(R['titles'])} giỏi.", ""]))
    cv: dict = {"full_name": name, "gender": gender, "birth_year": REF_YEAR - 22 - int(years) - rng.randint(0, 3),
                "email": f"demo.cv{i:04d}@example.com", "phone": f"09{i:08d}",
                "location": rng.choices(LOCATIONS, weights=LOCATION_WEIGHTS)[0], "summary": summary,
                "skills": skills, "experiences": exps, "projects": projects, "education": [edu],
                "certificates": rng.sample(["AWS Certified Developer", "TOEIC 750", "IELTS 6.5", "Scrum Master",
                                            "JLPT N3"], rng.randint(0, 2)),
                "languages": ["Tiếng Anh"] + (["Tiếng Nhật"] if rng.random() < 0.1 else [])}
    if rng.random() < 0.04:                                 # CV go khong dau
        keep = {k: cv[k] for k in ("email", "phone")}
        cv = json.loads(strip_diacritics(json.dumps(cv, ensure_ascii=False)).lower())
        cv.update(keep)
        flags.append("no_diacritics")
    if rng.random() < 0.15:                                 # ten truong kieu khac -> adapter
        cv["work_experience"] = cv.pop("experiences")
        for e in cv["work_experience"]:
            e["position"] = e.pop("title")
            e["start_date"] = e.pop("start")
            e["end_date"] = e.pop("end")
        cv["name"] = cv.pop("full_name")
        flags.append("alt_fields")
    meta = {"role": role, "group": R["group"], "level": lvl_rank, "years": round(years, 1),
            "location": cv["location"], "english": english, "flags": flags}
    return cv, meta


def make_jd(j: int, rng: random.Random, role: str, level_idx: int) -> tuple[dict, dict]:
    R = ROLES[role]
    lvl_name, lvl_rank, years = LEVELS[level_idx]
    title = f"{lvl_name} {R['titles'][0]}".strip()
    k = rng.random()
    if k < 0.15:                                            # chi ten ky nang, khong required / importance
        skills = R["core"] + rng.sample(R["extra"], min(2, len(R["extra"])))
    else:
        skills = [{"name": s, "required": True, "importance": "core" if n == 0 else rng.choice(["core", "medium"])}
                  for n, s in enumerate(R["core"])]
        skills += [{"name": s, "required": rng.random() < 0.3, "importance": rng.choice(["medium", "minor"])}
                   for s in rng.sample(R["extra"], min(len(R["extra"]), rng.randint(1, 4)))]
    min_years = {0: None, 1: 0, 2: 1, 3: 2, 4: 4, 5: 6}[lvl_rank]
    reqs = []
    if min_years:
        reqs.append(f"Tối thiểu {min_years} năm kinh nghiệm ở vị trí tương đương")
    if rng.random() < 0.5:
        reqs.append("Tốt nghiệp Đại học chuyên ngành Công nghệ thông tin hoặc liên quan")
    if rng.random() < 0.3:
        reqs.append("Tiếng Anh đọc hiểu tài liệu kỹ thuật, ưu tiên TOEIC 650 trở lên")
    reqs.append(rng.choice(["Có kinh nghiệm thiết kế hệ thống chịu tải cao",
                            "Hiểu biết về quy trình phát triển phần mềm Agile/Scrum",
                            "Có khả năng làm việc độc lập và làm việc nhóm tốt",
                            "Có kinh nghiệm dẫn dắt nhóm là một lợi thế"]))
    resp = [_bullet(b, rng).split(",")[0] for b in rng.sample(R["vi"], min(len(R["vi"]), rng.randint(3, 5)))]
    resp.append("Tham gia các buổi họp của team")
    jd = {"jd_id": f"DEMO-{j:03d}", "title": title,
          "company_intro": "Công ty công nghệ đang phát triển nhanh, môi trường trẻ trung.",
          "location": rng.choices(LOCATIONS[:4], weights=[45, 40, 10, 5])[0],
          "work_mode": rng.choice(["onsite", "hybrid", "hybrid", "remote"]),
          "skills": skills, "requirements": reqs, "benefits": ["Lương tháng 13", "Bảo hiểm sức khoẻ"],
          "status": "open"}
    if rng.random() > 0.08:
        jd["responsibilities"] = resp                       # vai JD thieu trach nhiem (B4 null phia JD)
    if min_years is not None:
        jd["min_years"] = min_years
    if lvl_rank in (2, 3) and rng.random() < 0.3:
        jd["max_years"] = min_years + 3
    if lvl_name:
        jd["level"] = lvl_name
    if rng.random() < 0.4:
        jd["edu_required"] = rng.choice(["it_related", "any_degree", "none"])
    return jd, {"role": role, "group": R["group"], "level": lvl_rank}


# 30 JD: phu cac vai tro chinh x cap bac; 2 closed, 1 draft
JD_PLAN = [("java", 4), ("java", 2), ("java", 5), ("python", 3), ("python", 2), ("node", 3), ("dotnet", 3),
           ("golang", 4), ("php", 2), ("frontend", 4), ("frontend", 2), ("vue", 3), ("angular", 3), ("fullstack", 3),
           ("fullstack", 4), ("android", 3), ("ios", 3), ("flutter", 2), ("data_eng", 4), ("data_eng", 2),
           ("data_analyst", 2), ("ml", 4), ("ml", 1), ("devops", 4), ("devops", 3), ("qa", 2), ("qa", 4),
           ("security", 3), ("ba", 3), ("designer", 2)]


def generate(out_dir: str | Path, *, n_cv: int = 300, seed: int = 2026, n_updates: int = 10) -> dict:
    out = Path(out_dir)
    for sub in ("cv", "cv_updates", "jd"):
        (out / sub).mkdir(parents=True, exist_ok=True)
        for f in (out / sub).glob("*.json"):
            f.unlink()
    rng = random.Random(seed)
    manifest: dict = {"seed": seed, "cv": {}, "cv_updates": {}, "jd": {}}
    cvs = []
    for i in range(n_cv):
        cv, meta = make_cv(i, rng)
        name = f"cv_{i:04d}_{meta['role']}.json"
        (out / "cv" / name).write_text(json.dumps(cv, ensure_ascii=False, indent=1), encoding="utf-8")
        manifest["cv"][name] = meta
        cvs.append((name, cv, meta))
    # ban CV moi cua cung nguoi (cung email): them kinh nghiem moi nhat -> version 2 khi nap sau
    for name, cv, meta in rng.sample([c for c in cvs if "alt_fields" not in c[2]["flags"]
                                      and c[1].get("experiences")], n_updates):
        upd = json.loads(json.dumps(cv))
        upd["summary"] = (upd.get("summary") or "") + " Vừa hoàn thành dự án mới."
        d0 = upd["experiences"][0]["description"]
        extra = "Hoàn thành dự án chuyển đổi hệ thống sang nền tảng cloud"
        upd["experiences"][0]["description"] = (d0 + [extra]) if isinstance(d0, list) else f"{d0} {extra}."
        un = name.replace(".json", "_v2.json")
        (out / "cv_updates" / un).write_text(json.dumps(upd, ensure_ascii=False, indent=1), encoding="utf-8")
        manifest["cv_updates"][un] = {**meta, "updates": name}
    for j, (role, li) in enumerate(JD_PLAN):
        jd, meta = make_jd(j, rng, role, li)
        if j in (8, 27):
            jd["status"] = "closed"
        if j == 22:
            jd["status"] = "draft"
        meta["status"] = jd["status"]
        name = f"{jd['jd_id'].lower()}_{role}.json"
        (out / "jd" / name).write_text(json.dumps(jd, ensure_ascii=False, indent=1), encoding="utf-8")
        manifest["jd"][jd["jd_id"]] = {**meta, "file": name, "title": jd["title"]}
    (out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    return {"n_cv": n_cv, "n_updates": n_updates, "n_jd": len(JD_PLAN), "dir": str(out)}

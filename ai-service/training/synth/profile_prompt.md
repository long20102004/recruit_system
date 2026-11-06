# Instructions: generate fictional CV profiles (feature 007)

Write ONE JSON object per line (JSONL). Every object describes a **fictional** IT candidate in Vietnam. Do not copy real people. Output only valid JSONL to the file you are told to write.

## Object format

```json
{
  "id": "b03-007",
  "level": "middle",
  "lang": "en",
  "role": "Backend Developer (Java)",
  "profile": {
    "personal_info": {"full_name": "...", "email": "...", "phone": "...", "github_url": "..." },
    "objective": "...",
    "education": [{"school": "...", "major": "...", "start_year": 2014, "end_year": 2018, "gpa": "3.2/4.0"}],
    "experience": [{"company": "...", "job_title": "...", "start_date": "03/2021", "end_date": null, "description": ["...", "..."]}],
    "personal_projects": [{"name": "...", "role": "...", "team_size": 4, "start_date": "...", "end_date": "...", "github_url": null, "description": ["...", "..."], "tech_stack": ["...", "..."]}],
    "skills": ["Java", "Spring Boot", "..."],
    "certificates": ["AWS Certified Solutions Architect – Associate (2023)"],
    "honours": ["Best Employee of the Year 2022 – FPT Software"],
    "languages": [{"language": "English", "note": "IELTS 7.0"}]
  },
  "extras": {
    "headline": "Backend Developer",
    "address": "Cau Giay, Ha Noi",
    "dob": "14/02/1996",
    "linkedin": "linkedin.com/in/...",
    "skill_groups": [{"group": "Languages", "items": ["Java", "Go"]}, {"group": "Frameworks", "items": ["Spring Boot"]}],
    "interests": ["Reading", "Football"]
  }
}
```

## Rules (all mandatory)
1. `profile` keys exactly as above, all present. Missing scalar → `null`, missing list → `[]`.
2. `extras.skill_groups` items, concatenated in order, must equal `profile.skills` exactly (same strings, same order). Use realistic group names: Languages, Programming Languages, Frameworks, Backend, Frontend, Database(s), DevOps, Cloud, Tools, Testing, ORM, Message Broker, Others, Soft Skills.
3. `languages` contains only spoken languages (English, Japanese, Vietnamese, Korean, Chinese, French…). Programming languages go to `skills` only.
4. `experience.company` is only the organisation name (e.g. "FPT Software", "Công ty Cổ phần MISA", "Viettel Digital"), never with city or dates.
5. Dates: pick ONE format per profile and use it everywhere: "03/2021", "Mar 2021", "March 2021" or "2021". Current job → `end_date: null`. Dates must be chronologically valid and consistent with the level.
6. Phone: valid Vietnamese mobile, 10 digits starting with 03/05/07/08/09, written plainly or with spaces/dots ("0912 345 678", "091.234.5678") or "+84 912 345 678". Email: realistic personal address (gmail.com, outlook.com, yahoo.com) derived from the name. `github_url`: "https://github.com/<handle>" or "github.com/<handle>" or null (≈ 30 % null).
7. Text values must be single-line strings: no "\n", no markdown, no emoji. Each bullet one sentence or two, 8–35 words, concrete (technologies, numbers, outcomes). Vary verbs and sentence shapes; never reuse the same sentence across profiles.
8. `start_year` / `end_year` / `team_size` integers; `gpa` string ("3.45/4.0", "8.1/10") or null.
9. Level targets:
   - junior: 1–2.5 years, 1–2 jobs, 2–3 personal projects, often 1 recent graduation.
   - middle: 3–5 years, 2–3 jobs, 0–2 projects.
   - senior: 5–9 years, 3–4 jobs, 0–2 projects, titles like Senior / Tech Lead in the latest job.
   - lead: 8–15 years, 3–6 jobs, titles like Engineering Manager, Solution Architect, Head of Engineering, Principal Engineer; bullets about teams, architecture, budgets, hiring.
10. Bullets per job: junior 2–4, middle 3–5, senior/lead 3–6. Certificates 0–4, honours 0–3, languages 1–3 (Vietnamese native in ~50 % of profiles, English with a note like "IELTS 6.5", "TOEIC 850", "Fluent", "Professional working proficiency").
11. `lang = "vi"`: write objective, bullets, titles, majors in Vietnamese with diacritics (company / technology names stay as they are). `lang = "en"`: everything in English except Vietnamese proper names (people, schools may stay in Vietnamese or English form).
12. Schools: Vietnamese universities (HUST, PTIT, UET-VNU, HCMUT, UIT, FPT University, UTE, Da Nang University of Science and Technology, …) written in varied official forms (full Vietnamese name, English name, with or without abbreviation); a few abroad.
13. Diversity across the batch: different roles, domains (fintech, banking, e-commerce, telecom, logistics, healthcare, edtech, gaming, government, outsourcing for Japan/US/EU clients), company sizes, cities (Ha Noi, Ho Chi Minh City, Da Nang, Can Tho, Hai Phong), and tech stacks.

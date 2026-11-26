import type { CandidateProfileDto } from "../../api/client";

/** Tiện ích cho hồ sơ theo cấu trúc CandidateProfile (response của POST /api/cvs, giống /analyze-pdf). */

type Profile = CandidateProfileDto;

export function emptyProfile(): Profile {
  return {
    personal_info: { full_name: null, email: null, phone: null, github_url: null },
    objective: null,
    education: [],
    experience: [],
    personal_projects: [],
    skills: [],
    certificates: [],
    honours: [],
    languages: [],
  };
}

/** Đưa mọi list null về [] và personal_info null về object rỗng để form luôn có chỗ điền. */
export function normalizeProfile(p: Profile | null | undefined): Profile {
  const base = emptyProfile();
  if (!p) return base;
  return {
    personal_info: { ...base.personal_info!, ...(p.personal_info ?? {}) },
    objective: p.objective ?? null,
    education: p.education ?? [],
    experience: (p.experience ?? []).map((e) => ({ ...e, description: e.description ?? [] })),
    personal_projects: (p.personal_projects ?? []).map((x) => ({
      ...x,
      description: x.description ?? [],
      tech_stack: x.tech_stack ?? [],
    })),
    skills: p.skills ?? [],
    certificates: p.certificates ?? [],
    honours: p.honours ?? [],
    languages: p.languages ?? [],
  };
}

/** Bỏ dòng trống, chuỗi rỗng thành null trước khi gửi lưu. */
export function cleanProfile(p: Profile): Profile {
  const s = (v: string | null | undefined) => (v == null || v.trim() === "" ? null : v.trim());
  const lines = (xs: string[] | null | undefined) => (xs ?? []).map((x) => x.trim()).filter(Boolean);
  const info = p.personal_info ?? emptyProfile().personal_info!;
  return {
    personal_info: {
      full_name: s(info.full_name),
      email: s(info.email),
      phone: s(info.phone),
      github_url: s(info.github_url),
    },
    objective: s(p.objective),
    education: (p.education ?? [])
      .map((e) => ({ ...e, school: s(e.school), major: s(e.major), gpa: s(e.gpa) }))
      .filter((e) => e.school || e.major || e.gpa || e.start_year != null || e.end_year != null),
    experience: (p.experience ?? [])
      .map((e) => ({
        company: s(e.company),
        job_title: s(e.job_title),
        start_date: s(e.start_date),
        end_date: s(e.end_date),
        description: lines(e.description),
      }))
      .filter((e) => e.company || e.job_title || e.description.length),
    personal_projects: (p.personal_projects ?? [])
      .map((x) => ({
        name: s(x.name),
        role: s(x.role),
        team_size: x.team_size,
        start_date: s(x.start_date),
        end_date: s(x.end_date),
        github_url: s(x.github_url),
        description: lines(x.description),
        tech_stack: lines(x.tech_stack),
      }))
      .filter((x) => x.name || x.description.length || x.tech_stack.length),
    skills: lines(p.skills),
    certificates: lines(p.certificates),
    honours: lines(p.honours),
    languages: (p.languages ?? [])
      .map((l) => ({ language: s(l.language), note: s(l.note) }))
      .filter((l) => l.language),
  };
}

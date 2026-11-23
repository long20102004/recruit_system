import type { JobDto, MatchDto } from "../api/client";
import type { Job, MatchResult } from "../types";

const LOGO_COLORS = ["#0d9488", "#2563eb", "#7c3aed", "#c2410c", "#0f766e"];

function initials(name: string): string {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0]?.toUpperCase() ?? "")
    .join("");
}

const APPLICATION_STATUS: Record<string, string> = {
  SUBMITTED: "Đã nộp",
  REVIEWING: "Đang xem xét",
  INTERVIEW: "Mời phỏng vấn",
  REJECTED: "Từ chối",
  HIRED: "Đã tuyển",
};

export function applicationStatusLabel(status: string): string {
  return APPLICATION_STATUS[status] ?? status;
}

function colorFor(id: number): string {
  return LOGO_COLORS[id % LOGO_COLORS.length];
}

export function mapJob(dto: JobDto): Job {
  const location = dto.location ?? dto.city ?? "";
  return {
    id: String(dto.id),
    title: dto.title,
    company: dto.company,
    location,
    city: dto.city ?? location,
    workType: dto.workType ?? "Hybrid",
    level: dto.level ?? "Junior",
    salary: dto.salaryText ?? "Thỏa thuận",
    postedAgo: dto.postedAt ? relativeTime(dto.postedAt) : "Mới",
    distanceKm: null,
    hot: dto.hot,
    nearYou: false,
    logo: initials(dto.company || dto.title),
    logoColor: colorFor(dto.id),
    requiredSkills: dto.requiredSkills ?? [],
    preferredSkills: dto.preferredSkills ?? [],
    minYears: Number(dto.minYears ?? 0),
    description: dto.description ?? "",
    requirements: dto.requirements ?? "",
    responsibilities: dto.responsibilities ?? "",
  };
}

export function mapMatch(dto: MatchDto): MatchResult {
  return {
    jobId: String(dto.jobId),
    rank: dto.rankPosition ?? 0,
    score: Number(dto.overallScore ?? 0),
    semanticSimilarity: Number(dto.semanticSimilarity ?? 0),
    tfidfSimilarity: Number(dto.tfidfSimilarity ?? 0),
    skillOverlap: Number(dto.skillOverlap ?? 0),
    matchedSkills: dto.matchedSkills ?? [],
    missingSkills: dto.missingSkills ?? [],
    reasons: dto.reasons ?? [],
    modelVersion: dto.modelVersion ?? "",
    id: dto.id,
    band: dto.band ?? null,
    capApplied: dto.capApplied ?? null,
    partialSkills: dto.partialSkills ?? [],
    hasExplanation: dto.hasExplanation ?? false,
  };
}

function relativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const hours = Math.floor(diff / 3600000);
  if (hours < 1) return "Vừa xong";
  if (hours < 24) return `${hours} giờ trước`;
  const days = Math.floor(hours / 24);
  return `${days} ngày trước`;
}

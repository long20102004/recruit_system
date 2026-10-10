import type { Job, MatchResult } from "../types";

export interface JobFilters {
  keyword?: string;
  city?: string;
  nearOnly?: boolean;
}

export function jobById(jobs: Job[], id: string): Job | undefined {
  return jobs.find((j) => j.id === id);
}

export function matchForJob(
  results: MatchResult[],
  jobId: string
): MatchResult | undefined {
  return results.find((m) => m.jobId === jobId);
}

export function filterJobs(jobs: Job[], filters: JobFilters = {}): Job[] {
  const { keyword, city, nearOnly } = filters;
  const kw = (keyword || "").trim().toLowerCase();

  return jobs.filter((j) => {
    if (nearOnly && !j.nearYou) return false;
    if (
      city &&
      city !== "all" &&
      j.city !== city &&
      !(city === "Remote" && j.city === "Remote")
    ) {
      return false;
    }
    if (!kw) return true;
    const hay = [j.title, j.company, j.location, ...(j.requiredSkills || [])]
      .join(" ")
      .toLowerCase();
    return hay.includes(kw);
  });
}

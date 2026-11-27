import { apiData, type JobDto, type PageDto } from "../client";

export interface AdminKpi {
  id: string;
  label: string;
  value: string;
  note: string;
}

export interface RoleBreakdown {
  role: "CANDIDATE" | "RECRUITER" | "ADMIN";
  label: string;
  count: number;
}

export interface AdminActivityLog {
  id: number;
  time: string;
  event: string;
  badgeClass: string;
  target: string;
  actor: string;
}

export interface AdminDashboardData {
  kpis: AdminKpi[];
  roles: RoleBreakdown[];
  lockedUsersCount: number;
  activityLog: AdminActivityLog[];
}

export interface JobLockState {
  jobId: number;
  locked: boolean;
  reason: string;
  note: string;
  lockedAt: string;
}

export const JOB_LOCK_REASONS: string[] = [
  "Nội dung sai sự thật / lừa đảo",
  "Không phải việc làm IT",
  "Trùng lặp",
  "Khác",
];

export async function getAdminDashboard(): Promise<AdminDashboardData> {
  return apiData<AdminDashboardData>("/admin/dashboard");
}

export async function recordAdminActivity(
  entry: Omit<AdminActivityLog, "id" | "time">
): Promise<AdminActivityLog> {
  return apiData<AdminActivityLog>("/admin/audit-logs", {
    method: "POST",
    body: JSON.stringify({
      eventType: "ADMIN_ACTION",
      eventLabel: entry.event,
      badgeClass: entry.badgeClass,
      target: entry.target,
      actorEmail: entry.actor,
    }),
  });
}

export async function listAdminJobs(params?: { status?: string; companyId?: number; keyword?: string; size?: number }): Promise<PageDto<JobDto>> {
  const qs = new URLSearchParams();
  if (params?.status && params.status !== "ALL") qs.set("status", params.status);
  if (params?.companyId != null) qs.set("companyId", String(params.companyId));
  if (params?.keyword?.trim()) qs.set("keyword", params.keyword.trim());
  qs.set("size", String(params?.size ?? 100));
  return apiData<PageDto<JobDto>>(`/admin/jobs?${qs.toString()}`);
}

export async function getJobLockStates(): Promise<Record<number, JobLockState>> {
  return (await apiData<Record<number, JobLockState>>("/admin/jobs/locks")) ?? {};
}

export async function lockAdminJob(
  jobId: number,
  reason: string,
  note: string,
  _jobTitle?: string,
  _actorEmail?: string
): Promise<JobLockState> {
  return apiData<JobLockState>(`/admin/jobs/${jobId}/lock`, {
    method: "POST",
    body: JSON.stringify({ reason: reason.trim(), note: note.trim() }),
  });
}

export async function unlockAdminJob(
  jobId: number,
  _jobTitle?: string,
  _actorEmail?: string
): Promise<void> {
  await apiData<void>(`/admin/jobs/${jobId}/unlock`, { method: "POST" });
}

import { apiData, type JobDto, type PageDto } from "../client";
import { mockReject, mockResolve, nextId } from "./core";

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

export type CvTemplateStatus = "ACTIVE" | "HIDDEN";
export type CvTemplateLayout = "TWO_COLUMN" | "ONE_COLUMN";
export type CvPreviewTone = "sky" | "brand" | "paper" | "ok";

export interface CvTemplateDto {
  id: number;
  name: string;
  status: CvTemplateStatus;
  accentToken: string;
  layout: CvTemplateLayout;
  sections: string[];
  usedCount: number;
  updatedAt: string;
  previewTone: CvPreviewTone;
}

export interface CvTemplatePayload {
  name: string;
  status: CvTemplateStatus;
  accentToken: string;
  layout: CvTemplateLayout;
  sections: string[];
  previewTone: CvPreviewTone;
}

export const JOB_LOCK_REASONS: string[] = [
  "Nội dung sai sự thật / lừa đảo",
  "Không phải việc làm IT",
  "Trùng lặp",
  "Khác",
];

export const CV_TEMPLATE_SECTIONS: string[] = [
  "Cá nhân",
  "Kinh nghiệm",
  "Học vấn",
  "Kỹ năng",
  "Dự án",
  "Giải thưởng",
  "Người tham chiếu",
];

export const CV_ACCENT_OPTIONS: { token: string; label: string }[] = [
  { token: "var(--brand)", label: "Xanh HireLens" },
  { token: "var(--ink)", label: "Than cổ điển" },
  { token: "var(--ok)", label: "Xanh lá" },
  { token: "var(--gold)", label: "Vàng đồng" },
];

export const CV_TONE_OPTIONS: { tone: CvPreviewTone; label: string }[] = [
  { tone: "sky", label: "Giấy ấm" },
  { tone: "brand", label: "Xanh nhạt" },
  { tone: "paper", label: "Trắng sáng" },
  { tone: "ok", label: "Xanh lá nhạt" },
];

const CV_TEMPLATES: CvTemplateDto[] = [
  {
    id: 1,
    name: "Cổ điển",
    status: "ACTIVE",
    accentToken: "var(--ink)",
    layout: "ONE_COLUMN",
    sections: ["Cá nhân", "Kinh nghiệm", "Học vấn", "Kỹ năng"],
    usedCount: 1820,
    updatedAt: "01/11/2026",
    previewTone: "sky",
  },
  {
    id: 2,
    name: "Hiện đại",
    status: "ACTIVE",
    accentToken: "var(--brand)",
    layout: "TWO_COLUMN",
    sections: ["Cá nhân", "Kinh nghiệm", "Học vấn", "Kỹ năng", "Dự án"],
    usedCount: 2210,
    updatedAt: "15/11/2026",
    previewTone: "brand",
  },
  {
    id: 3,
    name: "Tối giản",
    status: "ACTIVE",
    accentToken: "var(--gold)",
    layout: "ONE_COLUMN",
    sections: ["Cá nhân", "Kinh nghiệm", "Kỹ năng", "Dự án"],
    usedCount: 640,
    updatedAt: "20/10/2026",
    previewTone: "paper",
  },
  {
    id: 4,
    name: "Kỹ sư",
    status: "HIDDEN",
    accentToken: "var(--ok)",
    layout: "TWO_COLUMN",
    sections: ["Cá nhân", "Kinh nghiệm", "Học vấn", "Kỹ năng", "Dự án", "Giải thưởng"],
    usedCount: 0,
    updatedAt: "22/11/2026",
    previewTone: "ok",
  },
];

function todayFormatted(): string {
  return new Date().toLocaleDateString("vi-VN");
}

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

export async function listCvTemplates(): Promise<CvTemplateDto[]> {
  return mockResolve(CV_TEMPLATES);
}

export async function createCvTemplate(payload: CvTemplatePayload): Promise<CvTemplateDto> {
  const name = payload.name.trim();
  if (!name) return mockReject("Vui lòng nhập tên mẫu CV.");
  if (payload.sections.length === 0) return mockReject("Chọn ít nhất một mục hiển thị.");

  const created: CvTemplateDto = {
    id: nextId(CV_TEMPLATES),
    name,
    status: payload.status,
    accentToken: payload.accentToken,
    layout: payload.layout,
    sections: [...payload.sections],
    usedCount: 0,
    updatedAt: todayFormatted(),
    previewTone: payload.previewTone,
  };
  CV_TEMPLATES.push(created);
  return mockResolve(created);
}

export async function updateCvTemplate(
  id: number,
  payload: CvTemplatePayload
): Promise<CvTemplateDto> {
  const name = payload.name.trim();
  if (!name) return mockReject("Vui lòng nhập tên mẫu CV.");
  if (payload.sections.length === 0) return mockReject("Chọn ít nhất một mục hiển thị.");

  const target = CV_TEMPLATES.find((t) => t.id === id);
  if (!target) return mockReject("Không tìm thấy mẫu CV.");

  target.name = name;
  target.status = payload.status;
  target.accentToken = payload.accentToken;
  target.layout = payload.layout;
  target.sections = [...payload.sections];
  target.previewTone = payload.previewTone;
  target.updatedAt = todayFormatted();
  return mockResolve(target);
}

export async function deleteCvTemplate(id: number): Promise<void> {
  const idx = CV_TEMPLATES.findIndex((t) => t.id === id);
  if (idx === -1) return mockReject("Không tìm thấy mẫu CV để xoá.");
  CV_TEMPLATES.splice(idx, 1);
  return mockResolve(undefined);
}

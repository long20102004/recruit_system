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

const DASHBOARD_KPIS: AdminKpi[] = [
  { id: "users", label: "Người dùng", value: "5.214", note: "+312 trong 30 ngày" },
  { id: "companies", label: "Công ty hoạt động", value: "186", note: "5 chờ duyệt" },
  { id: "jobs", label: "Tin đang đăng", value: "1.240", note: "3 tin bị khoá" },
  { id: "applications", label: "Đơn ứng tuyển (30 ngày)", value: "9.870", note: "+14% so với tháng trước" },
  { id: "questions", label: "Câu hỏi phỏng vấn", value: "30", note: "30 cần chuyên gia duyệt" },
];

const ROLE_BREAKDOWN: RoleBreakdown[] = [
  { role: "CANDIDATE", label: "Ứng viên", count: 4870 },
  { role: "RECRUITER", label: "Nhà tuyển dụng", count: 341 },
  { role: "ADMIN", label: "Admin", count: 3 },
];

const ACTIVITY_LOG: AdminActivityLog[] = [
  { id: 1, time: "24/11 10:12", event: "Duyệt công ty", badgeClass: "badge b-ok", target: "Lumen Fintech", actor: "admin@hirelens.local" },
  { id: 2, time: "24/11 09:40", event: "Khoá tin", badgeClass: "badge b-danger", target: "Tuyển CTV nhập liệu, lương 50tr", actor: "admin@hirelens.local" },
  { id: 3, time: "23/11 17:05", event: "Từ chối công ty", badgeClass: "badge b-warn", target: "ABC Tech", actor: "admin@hirelens.local" },
  { id: 4, time: "23/11 15:22", event: "Khoá tài khoản", badgeClass: "badge b-danger", target: "spam.user@mail.com", actor: "admin@hirelens.local" },
  { id: 5, time: "23/11 11:00", event: "Thêm câu hỏi", badgeClass: "badge b-brand", target: "Kafka – consumer group", actor: "admin@hirelens.local" },
];

const JOB_LOCKS: JobLockState[] = [];

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

function nowShortStamp(): string {
  const d = new Date();
  const dd = String(d.getDate()).padStart(2, "0");
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  const hh = String(d.getHours()).padStart(2, "0");
  const min = String(d.getMinutes()).padStart(2, "0");
  return `${dd}/${mm} ${hh}:${min}`;
}

function todayFormatted(): string {
  return new Date().toLocaleDateString("vi-VN");
}

export async function getAdminDashboard(): Promise<AdminDashboardData> {
  return mockResolve({
    kpis: DASHBOARD_KPIS,
    roles: ROLE_BREAKDOWN,
    lockedUsersCount: 8,
    activityLog: ACTIVITY_LOG.slice(0, 10),
  });
}

export async function recordAdminActivity(
  entry: Omit<AdminActivityLog, "id" | "time">
): Promise<AdminActivityLog> {
  const item: AdminActivityLog = {
    id: nextId(ACTIVITY_LOG),
    time: nowShortStamp(),
    ...entry,
  };
  ACTIVITY_LOG.unshift(item);
  return mockResolve(item);
}

export async function getJobLockStates(): Promise<Record<number, JobLockState>> {
  const out: Record<number, JobLockState> = {};
  for (const item of JOB_LOCKS) {
    if (item.locked) out[item.jobId] = item;
  }
  return mockResolve(out);
}

export async function lockAdminJob(
  jobId: number,
  reason: string,
  note: string,
  jobTitle?: string,
  actorEmail = "admin@hirelens.local"
): Promise<JobLockState> {
  const cleanReason = reason.trim();
  if (!cleanReason) {
    return mockReject("Vui lòng chọn lý do khoá tin.");
  }
  const existing = JOB_LOCKS.find((x) => x.jobId === jobId);
  const next: JobLockState = {
    jobId,
    locked: true,
    reason: cleanReason,
    note: note.trim(),
    lockedAt: new Date().toISOString(),
  };
  if (existing) {
    Object.assign(existing, next);
  } else {
    JOB_LOCKS.push(next);
  }
  ACTIVITY_LOG.unshift({
    id: nextId(ACTIVITY_LOG),
    time: nowShortStamp(),
    event: "Khoá tin",
    badgeClass: "badge b-danger",
    target: jobTitle || `Tin #${jobId}`,
    actor: actorEmail,
  });
  return mockResolve(next);
}

export async function unlockAdminJob(
  jobId: number,
  jobTitle?: string,
  actorEmail = "admin@hirelens.local"
): Promise<void> {
  const existing = JOB_LOCKS.find((x) => x.jobId === jobId);
  if (existing) {
    existing.locked = false;
  }
  ACTIVITY_LOG.unshift({
    id: nextId(ACTIVITY_LOG),
    time: nowShortStamp(),
    event: "Mở khoá tin",
    badgeClass: "badge b-ok",
    target: jobTitle || `Tin #${jobId}`,
    actor: actorEmail,
  });
  return mockResolve(undefined);
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

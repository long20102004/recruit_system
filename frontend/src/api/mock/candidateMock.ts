import { savedJobsApi, type SavedJobDto } from "../client";
import { shortDate } from "../../utils/format";
import { mockReject, mockResolve, nextId } from "./core";

/* ── C02 · Danh sách CV của ứng viên ─────────────────────────────── */

export const MAX_CANDIDATE_CVS = 5;

export interface CandidateCvItem {
  id: number;
  title: string;
  isMain: boolean;
  source: string;
  updatedAt: string;
  skills: string[];
  fileName: string;
  /** CV đang gắn với đơn ứng tuyển chưa kết thúc thì không cho xoá. */
  inActiveApplication?: boolean;
}

const cvs: CandidateCvItem[] = [
  {
    id: 1,
    title: "Backend Java – 2026",
    isMain: true,
    source: "Tải lên PDF, AI trích xuất",
    updatedAt: "22/11/2026",
    skills: ["Java", "Spring Boot", "MySQL", "Docker"],
    fileName: "NguyenAn_Backend_2026.pdf",
    inActiveApplication: true,
  },
  {
    id: 2,
    title: "Fullstack (Java + React)",
    isMain: false,
    source: "Tạo từ form",
    updatedAt: "10/10/2026",
    skills: ["Java", "ReactJS", "TypeScript"],
    fileName: "NguyenAn_Fullstack_2026.pdf",
    inActiveApplication: false,
  },
  {
    id: 3,
    title: "CV tiếng Anh",
    isMain: false,
    source: "Tải lên PDF, AI trích xuất",
    updatedAt: "01/09/2026",
    skills: ["Java", "English", "AWS"],
    fileName: "NguyenAn_CV_EN.pdf",
    inActiveApplication: false,
  },
];

export const cvsMock = {
  list(): Promise<CandidateCvItem[]> {
    return mockResolve(cvs);
  },

  setMain(id: number): Promise<CandidateCvItem[]> {
    const target = cvs.find((c) => c.id === id);
    if (!target) return mockReject("Không tìm thấy CV cần đặt làm CV chính.");
    for (const item of cvs) {
      item.isMain = item.id === id;
    }
    return mockResolve(cvs);
  },

  remove(id: number): Promise<void> {
    const idx = cvs.findIndex((c) => c.id === id);
    if (idx === -1) return mockReject("Không tìm thấy CV cần xoá.");
    if (cvs[idx].inActiveApplication) {
      return mockReject("Không thể xóa CV đang đính kèm trong đơn ứng tuyển chưa kết thúc.");
    }
    const wasMain = cvs[idx].isMain;
    cvs.splice(idx, 1);
    if (wasMain && cvs.length > 0) {
      cvs[0].isMain = true;
    }
    return mockResolve(undefined);
  },
};

/* ── C07 · Việc làm đã lưu ───────────────────────────────────────── */

export type SavedJobStatus = "OPEN" | "CLOSED" | "EXPIRED";

export interface SavedJobItem {
  id: number;
  /** ID tin tuyển dụng thật để mở /candidate/jobs/<id>; bỏ trống nếu tin chỉ có trong dữ liệu mẫu. */
  jobId?: number;
  title: string;
  company: string;
  logo: string;
  city: string;
  mode: string;
  level: string;
  salary: string;
  skills: string[];
  savedAt: string;
  deadline: string;
  status: SavedJobStatus;
  hot?: boolean;
  match?: number;
}

function mapSavedJobDto(dto: SavedJobDto): SavedJobItem {
  return {
    id: dto.id,
    jobId: dto.jobId,
    title: dto.title,
    company: dto.company,
    logo: dto.logo,
    city: dto.city,
    mode: dto.mode,
    level: dto.level,
    salary: dto.salary,
    skills: dto.skills ?? [],
    savedAt: shortDate(dto.savedAt),
    deadline: dto.deadline ? shortDate(dto.deadline) : "Không giới hạn",
    status: dto.status,
    hot: dto.hot,
    match: dto.match ?? undefined,
  };
}

export const savedJobsMock = {
  async list(): Promise<SavedJobItem[]> {
    const rows = await savedJobsApi.list();
    return (rows ?? []).map(mapSavedJobDto);
  },

  async save(jobId: number): Promise<SavedJobItem> {
    const dto = await savedJobsApi.save(jobId);
    return mapSavedJobDto(dto);
  },

  async unsave(id: number): Promise<void> {
    await savedJobsApi.unsave(id);
  },
};

/* ── C09 · Job alert ─────────────────────────────────────────────── */

export const MAX_JOB_ALERTS = 5;

export type JobAlertFrequency = "instant" | "daily";

export interface JobAlertChannels {
  inApp: boolean;
  email: boolean;
}

export interface JobAlertItem {
  id: number;
  name: string;
  keywords: string[];
  city: string;
  level: string;
  minSalary: number | null;
  channels: JobAlertChannels;
  frequency: JobAlertFrequency;
  enabled: boolean;
  matchedCount: number;
}

export interface JobAlertInput {
  name: string;
  keywords: string[];
  city: string;
  level: string;
  minSalary: number | null;
  channels: JobAlertChannels;
  frequency: JobAlertFrequency;
}

const jobAlerts: JobAlertItem[] = [
  {
    id: 1,
    name: "Java Backend TP.HCM",
    keywords: ["Java", "Spring Boot"],
    city: "TP. Hồ Chí Minh",
    level: "Middle",
    minSalary: 30,
    channels: { inApp: true, email: true },
    frequency: "instant",
    enabled: true,
    matchedCount: 12,
  },
  {
    id: 2,
    name: "Remote Backend",
    keywords: ["Backend"],
    city: "Remote",
    level: "Middle",
    minSalary: null,
    channels: { inApp: false, email: true },
    frequency: "daily",
    enabled: true,
    matchedCount: 3,
  },
  {
    id: 3,
    name: "Thực tập Java 2027",
    keywords: ["Java"],
    city: "Hà Nội",
    level: "Intern",
    minSalary: null,
    channels: { inApp: true, email: false },
    frequency: "instant",
    enabled: false,
    matchedCount: 0,
  },
];

function validateAlertInput(input: JobAlertInput): string | null {
  if (!input.name.trim()) return "Vui lòng nhập tên job alert.";
  if (!input.channels.inApp && !input.channels.email) {
    return "Vui lòng chọn ít nhất một kênh nhận thông báo.";
  }
  if (input.minSalary != null && (Number.isNaN(input.minSalary) || input.minSalary < 0)) {
    return "Lương tối thiểu không hợp lệ.";
  }
  return null;
}

export const jobAlertsMock = {
  list(): Promise<JobAlertItem[]> {
    return mockResolve(jobAlerts);
  },

  create(input: JobAlertInput): Promise<JobAlertItem> {
    if (jobAlerts.length >= MAX_JOB_ALERTS) {
      return mockReject("Bạn đã đạt tối đa 5 job alert. Hãy xoá bớt trước khi tạo mới.");
    }
    const err = validateAlertInput(input);
    if (err) return mockReject(err);

    const created: JobAlertItem = {
      id: nextId(jobAlerts),
      name: input.name.trim(),
      keywords: input.keywords,
      city: input.city,
      level: input.level,
      minSalary: input.minSalary,
      channels: { ...input.channels },
      frequency: input.frequency,
      enabled: true,
      matchedCount: 0,
    };
    jobAlerts.unshift(created);
    return mockResolve(created);
  },

  update(id: number, input: JobAlertInput): Promise<JobAlertItem> {
    const existing = jobAlerts.find((a) => a.id === id);
    if (!existing) return mockReject("Không tìm thấy job alert cần sửa.");
    const err = validateAlertInput(input);
    if (err) return mockReject(err);

    existing.name = input.name.trim();
    existing.keywords = input.keywords;
    existing.city = input.city;
    existing.level = input.level;
    existing.minSalary = input.minSalary;
    existing.channels = { ...input.channels };
    existing.frequency = input.frequency;
    return mockResolve(existing);
  },

  toggle(id: number, enabled: boolean): Promise<JobAlertItem> {
    const existing = jobAlerts.find((a) => a.id === id);
    if (!existing) return mockReject("Không tìm thấy job alert.");
    existing.enabled = enabled;
    return mockResolve(existing);
  },

  remove(id: number): Promise<void> {
    const idx = jobAlerts.findIndex((a) => a.id === id);
    if (idx === -1) return mockReject("Không tìm thấy job alert cần xoá.");
    jobAlerts.splice(idx, 1);
    return mockResolve(undefined);
  },
};

/* ── C13 · Trung tâm thông báo ───────────────────────────────────── */

export type NotificationCategory = "application" | "interview" | "alert" | "company" | "cv";
export type NotificationTone = "b-gold" | "b-brand" | "b-ok" | "b-danger" | "b-plain";
export type InviteStatus = "pending" | "accepted" | "declined";

export interface NotificationItem {
  id: number;
  category: NotificationCategory;
  icon: string;
  iconCls: NotificationTone;
  title: string;
  body: string;
  time: string;
  unread: boolean;
  isInvite?: boolean;
  inviteStatus?: InviteStatus;
  inviteExpiry?: string;
}

const notifications: NotificationItem[] = [
  {
    id: 1,
    category: "interview",
    icon: "PV",
    iconCls: "b-gold",
    title: "Lumen Fintech mời bạn làm phiên phỏng vấn",
    body: "Senior Java Backend Engineer · 6 câu · hạn 28/11/2026.",
    time: "2 giờ trước",
    unread: true,
  },
  {
    id: 2,
    category: "company",
    icon: "CT",
    iconCls: "b-brand",
    title: "Lời mời tham gia công ty Orbit Analytics",
    body: "Lê Thu Hà mời bạn với vai trò Recruiter.",
    time: "5 giờ trước",
    unread: true,
    isInvite: true,
    inviteStatus: "pending",
    inviteExpiry: "Hết hạn sau 7 ngày",
  },
  {
    id: 3,
    category: "alert",
    icon: "JA",
    iconCls: "b-ok",
    title: "3 việc mới khớp job alert “Java Backend TP.HCM”",
    body: "Java Developer (Microservices) – Sao Mai Software và 2 việc khác.",
    time: "Hôm nay 08:00",
    unread: true,
  },
  {
    id: 4,
    category: "application",
    icon: "ĐƠN",
    iconCls: "b-brand",
    title: "Đơn ứng tuyển được chuyển sang Đang xem xét",
    body: "Java Developer (Microservices) – Sao Mai Software.",
    time: "19/11",
    unread: false,
  },
  {
    id: 5,
    category: "cv",
    icon: "CV",
    iconCls: "b-ok",
    title: "AI đã đọc xong CV của bạn",
    body: "NguyenAn_Backend_2026.pdf · kiểm tra lại 2 trường trước khi lưu.",
    time: "18/11",
    unread: false,
  },
  {
    id: 6,
    category: "application",
    icon: "ĐƠN",
    iconCls: "b-danger",
    title: "Đơn ứng tuyển không được chọn",
    body: "Java Spring Developer – Tidewave Games.",
    time: "09/11",
    unread: false,
  },
  {
    id: 7,
    category: "interview",
    icon: "PV",
    iconCls: "b-brand",
    title: "Kết quả phỏng vấn AI đã sẵn sàng",
    body: "Backend Java Developer – Cobalt Cloud · Điểm tổng hợp 8.1/10.",
    time: "05/11",
    unread: false,
  },
  {
    id: 8,
    category: "alert",
    icon: "JA",
    iconCls: "b-ok",
    title: "2 việc mới khớp job alert “Remote Backend”",
    body: "Node.js / TypeScript Backend – Nova Studio và 1 việc khác.",
    time: "02/11",
    unread: false,
  },
  {
    id: 9,
    category: "application",
    icon: "ĐƠN",
    iconCls: "b-ok",
    title: "Bạn đã nộp đơn thành công",
    body: "Senior Java Backend Engineer – Lumen Fintech.",
    time: "29/10",
    unread: false,
  },
];

export const notificationsMock = {
  list(): Promise<NotificationItem[]> {
    return mockResolve(notifications);
  },

  unreadCount(): Promise<number> {
    return mockResolve(notifications.filter((n) => n.unread).length);
  },

  markRead(id: number): Promise<NotificationItem> {
    const item = notifications.find((n) => n.id === id);
    if (!item) return mockReject("Không tìm thấy thông báo.");
    item.unread = false;
    return mockResolve(item);
  },

  markAllRead(): Promise<void> {
    for (const item of notifications) {
      item.unread = false;
    }
    return mockResolve(undefined);
  },

  respondInvite(id: number, decision: "accepted" | "declined"): Promise<NotificationItem> {
    const item = notifications.find((n) => n.id === id && n.isInvite);
    if (!item) return mockReject("Không tìm thấy lời mời tham gia công ty.");
    item.inviteStatus = decision;
    item.unread = false;
    return mockResolve(item);
  },
};

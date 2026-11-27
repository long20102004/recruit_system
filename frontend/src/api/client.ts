const API_BASE = import.meta.env.VITE_API_URL ?? "/api";

const TOKEN_KEY = "hirelens_token";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string | null) {
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
}

export class ApiError extends Error {
  status: number;
  /** Mã lỗi nghiệp vụ từ backend (ví dụ 2003 chưa xác thực email), nếu có. */
  code?: number;
  data?: Record<string, unknown> | null;

  constructor(
    status: number,
    message: string,
    code?: number,
    data?: Record<string, unknown> | null
  ) {
    super(message);
    this.status = status;
    this.code = code;
    this.data = data;
  }
}

/** Mã lỗi auth (specs/003-auth-flow, contracts/auth-api.md). */
export const AuthErrorCode = {
  INVALID_CREDENTIALS: 2001,
  EMAIL_NOT_VERIFIED: 2003,
  LOGIN_TEMPORARILY_LOCKED: 2004,
  ACCOUNT_LOCKED: 2005,
  INVALID_LINK_TOKEN: 2006,
} as const;

async function parseError(res: Response): Promise<ApiError> {
  try {
    const data = (await res.json()) as {
      message?: string;
      code?: number;
      data?: Record<string, unknown> | null;
    };
    return new ApiError(
      res.status,
      data.message ?? res.statusText,
      data.code,
      data.data
    );
  } catch {
    return new ApiError(res.status, res.statusText || "Request failed");
  }
}

export async function api<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const headers = new Headers(options.headers);
  if (!headers.has("Content-Type") && !(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }
  const token = getToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });
  if (!res.ok) {
    throw await parseError(res);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

/** API trả khung BaseResponse {code, message, data}: lấy data ra. */
export async function apiData<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await api<BaseResponse<T>>(path, options);
  return res?.data as T;
}

/** Link ký tạm tới file private trên R2 (specs/008-r2-storage). */
export interface FileLinkDto {
  url: string;
  expiresAt: string;
}

/**
 * Lấy link ký tạm từ backend rồi mở file. Link do R2 cấp đã kèm Content-Disposition
 * (attachment để tải, inline để xem) nên không cần đọc nội dung qua fetch.
 */
export async function openFileLink(path: string, mode: "download" | "view" = "download"): Promise<void> {
  const link = await apiData<FileLinkDto>(path);
  if (mode === "view") {
    window.open(link.url, "_blank", "noopener,noreferrer");
    return;
  }
  const a = document.createElement("a");
  a.href = link.url;
  a.rel = "noopener";
  document.body.appendChild(a);
  a.click();
  a.remove();
}

/** Tham số phân trang (page từ 0). Backend giới hạn size tối đa {@link MAX_PAGE_SIZE}. */
export interface PageParams {
  page?: number;
  size?: number;
}

export const MAX_PAGE_SIZE = 100;

function pageQuery(params?: PageParams, extra?: Record<string, string | undefined>): string {
  const q = new URLSearchParams();
  for (const [k, v] of Object.entries(extra ?? {})) if (v) q.set(k, v);
  q.set("page", String(params?.page ?? 0));
  q.set("size", String(params?.size ?? 20));
  return `?${q.toString()}`;
}

export const authApi = {
  login: (email: string, password: string) =>
    apiData<AuthResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
  register: (body: RegisterBody) =>
    apiData<RegisterResponse>("/auth/register", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  /** Đăng nhập bằng ID token của Google Identity Services (specs/005-google-login). */
  google: (credential: string) =>
    apiData<AuthResponse>("/auth/google", {
      method: "POST",
      body: JSON.stringify({ credential }),
    }),
  verifyEmail: (token: string) =>
    apiData<AuthResponse>("/auth/verify-email", {
      method: "POST",
      body: JSON.stringify({ token }),
    }),
  resendVerification: (email: string) =>
    apiData<MessageResponse>("/auth/resend-verification", {
      method: "POST",
      body: JSON.stringify({ email }),
    }),
  forgotPassword: (email: string) =>
    apiData<MessageResponse>("/auth/forgot-password", {
      method: "POST",
      body: JSON.stringify({ email }),
    }),
  resetPassword: (token: string, newPassword: string) =>
    apiData<MessageResponse>("/auth/reset-password", {
      method: "POST",
      body: JSON.stringify({ token, newPassword }),
    }),
  me: () => apiData<UserDto>("/auth/me"),
  chooseRole: (role: "CANDIDATE" | "RECRUITER") =>
    apiData<AuthResponse>("/auth/role", {
      method: "POST",
      body: JSON.stringify({ role }),
    }),
};

/** Tài khoản của chính người dùng (specs/006-account-settings, màn C14). */
export type Gender = "MALE" | "FEMALE" | "OTHER";
export type NotificationType =
  | "APPLICATION_STATUS"
  | "INTERVIEW_INVITE"
  | "JOB_ALERT"
  | "COMPANY_INVITE"
  | "CV_PROCESSED"
  | "COMPANY_STATUS"
  | "JOB_MODERATION";

export type NotificationCategory = "application" | "interview" | "alert" | "company" | "cv";

export interface NotificationDto {
  id: number;
  type: NotificationType;
  category: NotificationCategory;
  title: string;
  body: string | null;
  link: string | null;
  read: boolean;
  createdAt: string;
}

export interface UnreadCountDto {
  count: number;
}

export interface ProfileDto {
  id: number;
  fullName: string;
  email: string;
  phone: string | null;
  /** yyyy-MM-dd */
  dateOfBirth: string | null;
  gender: Gender | null;
  role: UserDto["role"];
  /** false: tài khoản tạo bằng Google, chưa đặt mật khẩu. */
  passwordSet: boolean;
  googleLinked: boolean;
}

export interface UpdateProfileBody {
  fullName: string;
  phone: string | null;
  dateOfBirth: string | null;
  gender: Gender | null;
}

export interface NotificationPrefDto {
  type: NotificationType;
  inApp: boolean;
  email: boolean;
}

export const accountApi = {
  profile: () => apiData<ProfileDto>("/account/profile"),
  updateProfile: (body: UpdateProfileBody) =>
    apiData<ProfileDto>("/account/profile", { method: "PUT", body: JSON.stringify(body) }),
  /** Trả token mới; các phiên khác bị đăng xuất. */
  changePassword: (currentPassword: string | null, newPassword: string) =>
    apiData<AuthResponse>("/account/password", {
      method: "POST",
      body: JSON.stringify({ currentPassword, newPassword }),
    }),
  notifications: () => apiData<{ items: NotificationPrefDto[] }>("/account/notifications"),
  updateNotifications: (items: NotificationPrefDto[]) =>
    apiData<{ items: NotificationPrefDto[] }>("/account/notifications", {
      method: "PUT",
      body: JSON.stringify({ items }),
    }),
};

/** Thông báo & SSE stream (specs/009-notification-service). */
export const notificationsApi = {
  list: (params?: { category?: NotificationCategory; unread?: boolean; page?: number; size?: number }) =>
    apiData<PageDto<NotificationDto>>(
      `/notifications${pageQuery(params, {
        category: params?.category,
        unread: params?.unread != null ? String(params.unread) : undefined,
      })}`
    ),
  unreadCount: () => apiData<UnreadCountDto>("/notifications/unread-count"),
  markRead: (id: number) =>
    apiData<NotificationDto>(`/notifications/${id}/read`, { method: "POST" }),
  markAllRead: () =>
    apiData<UnreadCountDto>("/notifications/read-all", { method: "POST" }),
  streamUrl: () => `${API_BASE}/notifications/stream`,
};

export const jobsApi = {
  list: (params?: { keyword?: string; city?: string; minSalary?: number } & PageParams) =>
    apiData<PageDto<JobDto>>(`/jobs${pageQuery(params, {
      keyword: params?.keyword?.trim() || undefined,
      city: params?.city && params.city !== "all" ? params.city : undefined,
      minSalary: params?.minSalary != null && params.minSalary > 0 ? String(params.minSalary) : undefined,
    })}`),
  mine: (params?: PageParams) => apiData<PageDto<JobDto>>(`/jobs/mine${pageQuery(params)}`),
  get: (id: number) => api<JobDto>(`/jobs/${id}`),
  create: (body: CreateJobBody) =>
    api<JobDto>("/jobs", { method: "POST", body: JSON.stringify(body) }),
  update: (id: number, body: CreateJobBody) =>
    api<JobDto>(`/jobs/${id}`, { method: "PUT", body: JSON.stringify(body) }),
  remove: (id: number) =>
    api<void>(`/jobs/${id}`, { method: "DELETE" }),
  renew: (id: number, deadline?: string) =>
    api<JobDto>(`/jobs/${id}/renew`, {
      method: "POST",
      body: JSON.stringify(deadline ? { deadline } : {}),
    }),
  updateStatus: (id: number, status: string) =>
    api<JobDto>(`/jobs/${id}/status`, {
      method: "PATCH",
      body: JSON.stringify({ status }),
    }),
};

export const applicationsApi = {
  apply: (jobId: number, body?: { cvDocumentId?: number; coverLetter?: string }) =>
    api<ApplicationDto>(`/applications/jobs/${jobId}`, {
      method: "POST",
      body: JSON.stringify(body ?? {}),
    }),
  mine: (params?: PageParams) => apiData<PageDto<ApplicationDto>>(`/applications/mine${pageQuery(params)}`),
  recruiter: (params?: PageParams & { status?: string; jobId?: number; minMatchScore?: number }) =>
    apiData<PageDto<ApplicationDto>>(`/applications/recruiter${pageQuery(params, {
      status: params?.status && params.status !== "ALL" ? params.status : undefined,
      jobId: params?.jobId != null ? String(params.jobId) : undefined,
      minMatchScore: params?.minMatchScore != null ? String(params.minMatchScore) : undefined,
    })}`),
  detail: (id: number) => apiData<ApplicationDetailDto>(`/applications/${id}`),
  updateStatus: (id: number, status: string, note?: string) =>
    apiData<ApplicationDetailDto>(`/applications/${id}/status`, {
      method: "PATCH",
      body: JSON.stringify({ status, note: note ?? "" }),
    }),
  bulkUpdateStatus: (applicationIds: number[], status: string, note?: string) =>
    apiData<ApplicationDto[]>("/applications/bulk-status", {
      method: "PATCH",
      body: JSON.stringify({ applicationIds, status, note: note ?? "" }),
    }),
  withdraw: (id: number) =>
    apiData<ApplicationDetailDto>(`/applications/${id}/withdraw`, { method: "POST" }),
  saveNote: (id: number, rating: number, internalNote: string) =>
    apiData<ApplicationDetailDto>(`/applications/${id}/note`, {
      method: "PUT",
      body: JSON.stringify({ rating, internalNote }),
    }),
  history: (id: number) => apiData<ApplicationHistoryDto[]>(`/applications/${id}/history`),
  /** Tải PDF CV đính kèm đơn qua link ký tạm trên R2. */
  downloadCvFile: (id: number) => openFileLink(`/applications/${id}/cv-file`),
};

export const savedJobsApi = {
  list: () => apiData<SavedJobDto[]>("/saved-jobs"),
  save: (jobId: number) => apiData<SavedJobDto>(`/saved-jobs/${jobId}`, { method: "POST" }),
  unsave: (jobIdOrSavedId: number) => api<void>(`/saved-jobs/${jobIdOrSavedId}`, { method: "DELETE" }),
};

function cvQuery(cvId?: number | null): string {
  return cvId != null ? `?cvId=${cvId}` : "";
}

function cvForm(file: File): FormData {
  const fd = new FormData();
  fd.append("file", file);
  return fd;
}

/** Ứng viên có tối đa 5 CV; không truyền cvId thì làm trên CV chính. */
export const MAX_CANDIDATE_CVS = 5;

export const cvsApi = {
  mine: (cvId?: number | null) => api<CvFormDto>(`/cvs${cvQuery(cvId)}`),
  /** API cũ: ghi vào CV chính (chưa có CV thì tạo CV đầu tiên). */
  upload: (file: File) =>
    api<BaseResponse<CandidateProfileDto>>("/cvs", { method: "POST", body: cvForm(file) }),
  /** profile: hồ sơ đã sửa theo CandidateProfile; fields: ghi đè thêm từng field (vd "Kỹ năng suy ra"). */
  confirm: (body: { profile?: CandidateProfileDto; fields?: CvFieldDto[] }, cvId?: number | null) =>
    api<CvFormDto>(`/cvs${cvQuery(cvId)}`, {
      method: "PUT",
      body: JSON.stringify(body),
    }),
  documents: () => apiData<CvDocumentDto[]>("/cvs/documents"),
  /** Thêm CV mới; lỗi 400 khi đã đủ {@link MAX_CANDIDATE_CVS} CV. */
  uploadNew: (file: File) =>
    api<BaseResponse<CvUploadDto>>("/cvs/documents", { method: "POST", body: cvForm(file) }),
  reupload: (cvId: number, file: File) =>
    api<BaseResponse<CvUploadDto>>(`/cvs/documents/${cvId}/file`, { method: "POST", body: cvForm(file) }),
  rename: (cvId: number, title: string) =>
    apiData<CvDocumentDto>(`/cvs/documents/${cvId}`, {
      method: "PATCH",
      body: JSON.stringify({ title }),
    }),
  setMain: (cvId: number) => apiData<CvDocumentDto[]>(`/cvs/documents/${cvId}/main`, { method: "POST" }),
  remove: (cvId: number) => api<void>(`/cvs/documents/${cvId}`, { method: "DELETE" }),
  /** Tải file CV gốc qua link ký tạm trên R2 (tên file do backend đặt trong link). */
  download: (cvId: number) => openFileLink(`/cvs/documents/${cvId}/file`),
};

export const matchingApi = {
  mine: (params?: PageParams) => apiData<PageDto<MatchDto>>(`/matching/mine${pageQuery(params)}`),
  refreshMine: () =>
    api<MatchDto[]>("/matching/mine/refresh", { method: "POST" }),
  forJob: (jobId: number, params?: PageParams) =>
    apiData<PageDto<MatchDto>>(`/matching/jobs/${jobId}${pageQuery(params)}`),
  run: (jobId: number, candidateId?: number) =>
    api<MatchDto>("/matching/run", {
      method: "POST",
      body: JSON.stringify({ jobId, candidateId }),
    }),
  /** cvmatch: xếp hạng lại ứng viên của một job (mặc định: ứng viên đã nộp đơn). */
  refreshJob: (jobId: number, scope?: "applicants" | "pool") =>
    api<MatchDto[]>(`/matching/jobs/${jobId}/refresh`, {
      method: "POST",
      body: JSON.stringify({ scope }),
    }),
  /** cvmatch: giải thích của một kết quả (lấy lười, lưu lại phía server). */
  explanation: (matchId: number) =>
    api<ExplanationDto>(`/matching/${matchId}/explanation`),
};

export const interviewsApi = {
  questions: (params?: PageParams) => apiData<PageDto<QuestionDto>>(`/interviews/questions${pageQuery(params)}`),
  mine: (params?: PageParams) => apiData<PageDto<SessionDto>>(`/interviews/sessions/mine${pageQuery(params)}`),
  summary: (id: number) => api<SessionSummaryDto>(`/interviews/sessions/${id}/summary`),
  createSession: (body?: {
    jobId?: number;
    applicationId?: number;
    questionIds?: number[];
    questionCount?: number;
  }) =>
    api<SessionDto>("/interviews/sessions", {
      method: "POST",
      body: JSON.stringify(body ?? {}),
    }),
  getSession: (id: number) => api<SessionDto>(`/interviews/sessions/${id}`),
  submit: (sessionId: number, questionId: number, answerText: string) =>
    api<EvaluationDto>(`/interviews/sessions/${sessionId}/responses`, {
      method: "POST",
      body: JSON.stringify({ questionId, answerText }),
    }),
};

export const dashboardApi = {
  recruiter: (days = 30) => api<RecruiterStatsDto>(`/dashboard/recruiter?days=${days}`),
};

export type RoleDto = "CANDIDATE" | "RECRUITER" | "ADMIN";

export interface UserDto {
  id: number;
  fullName: string;
  email: string;
  role: RoleDto;
  roleChosen?: boolean;
  /** Quyền theo ma trận RBAC (specs/004-rbac), vd "job:create". */
  permissions?: string[];
}

export interface AuthResponse {
  token: string;
  user: UserDto;
}

export interface RegisterBody {
  email: string;
  password: string;
}

export interface RegisterResponse {
  email: string;
  message: string;
}

export interface MessageResponse {
  message: string;
}

/** Quy tắc mật khẩu giống backend: 8–100 ký tự, có chữ và số. */
export const PASSWORD_RULE = /^(?=.*[A-Za-z])(?=.*\d).{8,100}$/;
export const PASSWORD_HINT = "Ít nhất 8 ký tự, gồm cả chữ và số.";

export interface JobDto {
  id: number;
  title: string;
  company: string;
  companyId: number;
  location: string | null;
  city: string | null;
  workType: string | null;
  level: string | null;
  salaryText: string | null;
  minYears: number | null;
  status: string;
  hot: boolean;
  description: string | null;
  requirements: string | null;
  responsibilities: string | null;
  postedAt: string | null;
  requiredSkills: string[];
  preferredSkills: string[];
  salaryMin?: number | null;
  salaryMax?: number | null;
  currency?: string | null;
  headcount?: number | null;
  benefits?: string | null;
  deadline?: string | null;
  defaultInterviewQuestions?: number | null;
  lockReason?: string | null;
  lockNote?: string | null;
  lockedAt?: string | null;
  applicantsCount?: number;
  createdById?: number | null;
}

export interface CreateJobBody {
  title: string;
  description: string;
  location?: string;
  city?: string;
  workType?: string;
  level?: string;
  salaryText?: string;
  minYears?: number;
  hot?: boolean;
  status?: string;
  requiredSkills?: string[];
  preferredSkills?: string[];
  /** Mỗi dòng một yêu cầu. */
  requirements?: string;
  /** Mỗi dòng một trách nhiệm (giúp ghép hồ sơ chính xác hơn). */
  responsibilities?: string;
  salaryMin?: number | null;
  salaryMax?: number | null;
  currency?: string;
  headcount?: number | null;
  benefits?: string;
  deadline?: string | null;
  defaultInterviewQuestions?: number | null;
}

export interface ApplicationDto {
  id: number;
  jobId: number;
  jobTitle: string;
  companyName: string;
  candidateId: number;
  candidateName: string;
  cvDocumentId: number | null;
  status: string;
  coverLetter: string | null;
  appliedAt: string;
  matchScore?: number | null;
}

export interface ApplicationCvDetailDto {
  roleTitle: string;
  yearsExpLabel: string;
  email: string;
  phone: string;
  summary: string;
  experiences: { title: string; company: string | null; period: string; description: string }[];
  education: string;
  matchedSkills: string[];
  otherSkills: string[];
}

export interface ApplicationMatchDetailDto {
  overallPercent: number;
  breakdown: { label: string; percent: number }[];
  missingSkills: string[];
}

export interface ApplicationHistoryDto {
  id: number;
  fromStatus: string | null;
  toStatus: string;
  statusLabel: string;
  timestamp: string;
  actor: string;
  note: string | null;
}

export interface ApplicationDetailDto {
  id: number;
  jobId: number;
  jobTitle: string;
  companyName: string;
  candidateId: number;
  candidateName: string;
  cvDocumentId: number | null;
  cvFileName: string | null;
  hasCvFile: boolean;
  status: string;
  coverLetter: string | null;
  appliedAt: string;
  rating: number;
  internalNote: string | null;
  cv: ApplicationCvDetailDto;
  match: ApplicationMatchDetailDto | null;
  history: ApplicationHistoryDto[];
}

export interface SavedJobDto {
  id: number;
  jobId: number;
  title: string;
  company: string;
  logo: string;
  city: string;
  mode: string;
  level: string;
  salary: string;
  skills: string[];
  savedAt: string;
  deadline: string | null;
  status: "OPEN" | "CLOSED" | "EXPIRED";
  hot: boolean;
  match: number | null;
}

export interface CvFieldDto {
  field: string;
  values: string[];
}

/** Khung response chung của backend: {code, message, data}. */
export interface BaseResponse<T> {
  code: number;
  message: string;
  data?: T;
}

/**
 * Profile AI trích xuất từ CV (response của POST /api/cvs), cùng cấu trúc với
 * CandidateProfile của /api/v1/cv/analyze-pdf (nhánh hocnv/DO-06). Trường nào AI không đọc được thì null.
 */
export interface CandidateProfileDto {
  personal_info: {
    full_name: string | null;
    email: string | null;
    phone: string | null;
    github_url: string | null;
  } | null;
  objective: string | null;
  education: {
    school: string | null;
    major: string | null;
    start_year: number | null;
    end_year: number | null;
    gpa: string | null;
  }[] | null;
  experience: {
    company: string | null;
    job_title: string | null;
    start_date: string | null;
    end_date: string | null;
    description: string[] | null;
  }[] | null;
  personal_projects: {
    name: string | null;
    role: string | null;
    team_size: number | null;
    start_date: string | null;
    end_date: string | null;
    github_url: string | null;
    description: string[] | null;
    tech_stack: string[] | null;
  }[] | null;
  skills: string[] | null;
  certificates: string[] | null;
  honours: string[] | null;
  languages: { language: string | null; note: string | null }[] | null;
}

export interface CvDocumentDto {
  id: number;
  title: string;
  fileName: string | null;
  /** CV chính: dùng cho matching và gợi ý việc. */
  main: boolean;
  parsingStatus: string | null;
  analyzed: boolean;
  skills: string[];
  updatedAt: string;
  /** Đang gắn với đơn ứng tuyển chưa kết thúc: không xoá được. */
  inActiveApplication: boolean;
}

export interface CvUploadDto {
  cvId: number;
  profile: CandidateProfileDto | null;
}

export interface CvFormDto {
  /** CV đang xem; null khi chưa có CV nào. */
  cvId: number | null;
  title: string | null;
  main: boolean;
  fileName: string | null;
  parsingStatus: string | null;
  analyzed: boolean;
  fields: CvFieldDto[];
  /** Hồ sơ theo cấu trúc CandidateProfile đã lưu; null khi chưa tải CV. */
  profile: CandidateProfileDto | null;
}

export interface MatchDto {
  id: number;
  jobId: number;
  jobTitle: string;
  companyName: string;
  candidateId: number;
  candidateName: string;
  overallScore: number;
  semanticSimilarity: number | null;
  tfidfSimilarity: number | null;
  skillOverlap: number | null;
  matchedSkills: string[];
  missingSkills: string[];
  reasons: string[];
  modelVersion: string | null;
  rankPosition: number | null;
  createdAt: string;
  /** cvmatch: high | mid | low; null với engine cũ. */
  band?: MatchBand | null;
  capApplied?: boolean | null;
  engine?: string;
  hasExplanation?: boolean;
  partialSkills?: string[];
}

export type MatchBand = "high" | "mid" | "low";

export interface ExplanationDto {
  matchId: number;
  audience: "hr" | "candidate";
  band: MatchBand | null;
  bandLabel: string | null;
  /** null với ứng viên (giải thích hướng ứng viên không hiện điểm). */
  score: number | null;
  capApplied: boolean | null;
  text: string;
  sections: Record<string, unknown> | null;
}

export interface QuestionDto {
  id: number;
  topic: string | null;
  difficulty: string | null;
  skill: string | null;
  questionText: string;
  referenceAnswer: string | null;
  rubricLabels: string[];
}

export interface SessionDto {
  id: number;
  status: string;
  currentIndex: number;
  jobId: number | null;
  jobTitle: string | null;
  questions: {
    questionId: number;
    sortOrder: number;
    topic: string | null;
    difficulty: string | null;
    questionText: string;
  }[];
  createdAt: string;
}

export interface CriterionResultDto {
  key: string; label: string; status: string; credit: number;
  points: number; max_points: number; semantic_f1: number | null; feedback: string;
}
export interface SessionSummaryDto {
  sessionId: number; status: string; totalQuestions: number;
  answeredQuestions: number; averageScore: number | null; evaluations: EvaluationDto[];
}
export interface EvaluationDto {
  responseId: number;
  questionId: number;
  predictedScore: number;
  scoreScale: string;
  coveredPoints: string[];
  missingPoints: string[];
  comment: string | null;
  evaluationMethod: string;
  modelVersion: string | null;
  scoringMode: string | null;
  bertscorePrecision: number | null;
  bertscoreRecall: number | null;
  bertscoreF1: number | null;
  coverageScore: number | null;
  criterionResults: CriterionResultDto[];
}

export interface ExpiringJobDto {
  id: number;
  title: string;
  deadline: string;
  applicantsCount: number;
}

export interface RecruiterStatsDto {
  openJobsCount: number;
  applicationsCount: number;
  questionsCount: number;
  draftJobsCount?: number;
  newApplicationsCount?: number;
  previousPeriodApplicationsCount?: number;
  pendingApplicationsCount?: number;
  completedInterviewsCount?: number;
  averageInterviewScore?: number | null;
  funnel?: Record<string, number>;
  expiringJobs?: ExpiringJobDto[];
}

// ── Quản trị (specs/004-rbac) ───────────────────────────

export interface PageDto<T> {
  content: T[];
  pageNumber: number;
  pageSize: number;
  totalElements: number;
  totalPages: number;
  last: boolean;
}

export interface AdminUserDto {
  id: number;
  fullName: string;
  email: string;
  role: RoleDto;
  status: "ACTIVE" | "INACTIVE" | "BANNED";
  emailVerified: boolean;
  lockedReason: string | null;
  lockedAt: string | null;
  createdAt: string;
}

export interface RbacPermissionDto {
  code: string;
  resource: string;
  description: string;
}

export interface RbacRoleDto {
  code: string;
  name: string;
  description: string | null;
  permissions: string[];
}

export interface RbacMatrixDto {
  roles: RbacRoleDto[];
  permissions: RbacPermissionDto[];
}

export const adminApi = {
  users: (params: { q?: string; status?: string; page?: number; size?: number }) => {
    const qs = new URLSearchParams();
    if (params.q) qs.set("q", params.q);
    if (params.status) qs.set("status", params.status);
    qs.set("page", String(params.page ?? 0));
    qs.set("size", String(params.size ?? 20));
    return apiData<PageDto<AdminUserDto>>(`/admin/users?${qs.toString()}`);
  },
  lock: (id: number, reason: string) =>
    apiData<AdminUserDto>(`/admin/users/${id}/lock`, { method: "PATCH", body: JSON.stringify({ reason }) }),
  unlock: (id: number) => apiData<AdminUserDto>(`/admin/users/${id}/unlock`, { method: "PATCH" }),
  roles: () => apiData<RbacMatrixDto>("/admin/roles"),
  updateRole: (code: string, permissions: string[]) =>
    apiData<RbacRoleDto>(`/admin/roles/${code}/permissions`, { method: "PUT", body: JSON.stringify({ permissions }) }),
};


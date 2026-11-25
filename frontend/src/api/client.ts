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

export const authApi = {
  login: (email: string, password: string) =>
    api<AuthResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
  register: (body: RegisterBody) =>
    api<RegisterResponse>("/auth/register", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  verifyEmail: (token: string) =>
    api<AuthResponse>("/auth/verify-email", {
      method: "POST",
      body: JSON.stringify({ token }),
    }),
  resendVerification: (email: string) =>
    api<MessageResponse>("/auth/resend-verification", {
      method: "POST",
      body: JSON.stringify({ email }),
    }),
  forgotPassword: (email: string) =>
    api<MessageResponse>("/auth/forgot-password", {
      method: "POST",
      body: JSON.stringify({ email }),
    }),
  resetPassword: (token: string, newPassword: string) =>
    api<MessageResponse>("/auth/reset-password", {
      method: "POST",
      body: JSON.stringify({ token, newPassword }),
    }),
  me: () => api<UserDto>("/auth/me"),
  chooseRole: (role: "CANDIDATE" | "RECRUITER") =>
    api<AuthResponse>("/auth/role", {
      method: "POST",
      body: JSON.stringify({ role }),
    }),
};

export const jobsApi = {
  list: (params?: { keyword?: string; city?: string }) => {
    const q = new URLSearchParams();
    if (params?.keyword) q.set("keyword", params.keyword);
    if (params?.city && params.city !== "all") q.set("city", params.city);
    const qs = q.toString();
    return api<JobDto[]>(`/jobs${qs ? `?${qs}` : ""}`);
  },
  mine: () => api<JobDto[]>("/jobs/mine"),
  get: (id: number) => api<JobDto>(`/jobs/${id}`),
  create: (body: CreateJobBody) =>
    api<JobDto>("/jobs", { method: "POST", body: JSON.stringify(body) }),
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
  mine: () => api<ApplicationDto[]>("/applications/mine"),
  recruiter: () => api<ApplicationDto[]>("/applications/recruiter"),
};

export const cvsApi = {
  mine: () => api<CvFormDto>("/cvs"),
  upload: (file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return api<CvFormDto>("/cvs", { method: "POST", body: fd });
  },
  confirm: (fields: CvFieldDto[]) =>
    api<CvFormDto>("/cvs", {
      method: "PUT",
      body: JSON.stringify({ fields }),
    }),
};

export const matchingApi = {
  mine: () => api<MatchDto[]>("/matching/mine"),
  refreshMine: () =>
    api<MatchDto[]>("/matching/mine/refresh", { method: "POST" }),
  forJob: (jobId: number) => api<MatchDto[]>(`/matching/jobs/${jobId}`),
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
  questions: () => api<QuestionDto[]>("/interviews/questions"),
  mine: () => api<SessionDto[]>("/interviews/sessions/mine"),
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
  recruiter: () => api<RecruiterStatsDto>("/dashboard/recruiter"),
};

export type RoleDto = "CANDIDATE" | "RECRUITER" | "ADMIN";

export interface UserDto {
  id: number;
  fullName: string;
  email: string;
  role: RoleDto;
  roleChosen?: boolean;
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
}

export interface CvFieldDto {
  field: string;
  values: string[];
}

export interface CvFormDto {
  fileName: string | null;
  parsingStatus: string | null;
  analyzed: boolean;
  fields: CvFieldDto[];
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

export interface RecruiterStatsDto {
  openJobsCount: number;
  applicationsCount: number;
  questionsCount: number;
}

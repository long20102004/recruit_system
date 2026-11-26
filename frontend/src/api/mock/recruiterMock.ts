import { mockReject, mockResolve, nextId } from "./core";

// ── R02 & R09: Đăng ký & Hồ sơ công ty ──────────────────────────────

export type CompanyVerificationStatus = "PENDING" | "REJECTED" | "ACTIVE";

export interface CompanyProfile {
  id: number;
  name: string;
  displayName: string;
  taxCode: string;
  industry: string;
  size: string;
  companyType: string;
  website: string;
  foundedYear: string;
  headquarters: string;
  officeAddress: string;
  contactEmail: string;
  contactPhone: string;
  shortBio: string;
  description: string;
  whyWorkHere: string;
  workingDays: string;
  overtimePolicy: string;
  techStack: string[];
  logoFileName: string;
  coverFileName: string;
  licenseFileName: string;
  licenseFileMeta: string;
  confirmed: boolean;
  status: CompanyVerificationStatus;
  submittedAt: string;
  approvedAt: string | null;
  createdBy: string;
  rejectionReason: string | null;
}

export interface CompanyRegistrationInput {
  name: string;
  taxCode: string;
  industry: string;
  size: string;
  companyType: string;
  website: string;
  foundedYear: string;
  headquarters: string;
  contactEmail: string;
  contactPhone: string;
  shortBio: string;
  logoFileName: string;
  licenseFileName: string;
  licenseFileMeta: string;
  confirmed: boolean;
}

export interface CompanyProfileUpdateInput {
  displayName: string;
  industry: string;
  size: string;
  companyType: string;
  website: string;
  workingDays: string;
  overtimePolicy: string;
  officeAddress: string;
  description: string;
  whyWorkHere: string;
  techStack: string[];
  logoFileName: string;
  coverFileName: string;
}

let companyState: CompanyProfile = {
  id: 1,
  name: "Công ty TNHH Lumen Fintech",
  displayName: "Lumen Fintech",
  taxCode: "0312345678",
  industry: "Fintech",
  size: "300 – 500 nhân viên",
  companyType: "Product",
  website: "https://lumenfintech.vn",
  foundedYear: "2016",
  headquarters: "2A Nguyễn Lương Bằng, Quận 7, TP. Hồ Chí Minh",
  officeAddress: "Tầng 12, toà Riverside, 2A Nguyễn Lương Bằng, Quận 7, TP. Hồ Chí Minh",
  contactEmail: "hr@lumenfintech.vn",
  contactPhone: "028 3812 3456",
  shortBio: "Nền tảng thanh toán cho doanh nghiệp vừa và nhỏ.",
  description:
    "Lumen Fintech xây dựng hạ tầng thanh toán, đối soát và quản lý dòng tiền cho doanh nghiệp vừa và nhỏ tại Việt Nam.",
  whyWorkHere: "- Hybrid 3/2\n- Bảo hiểm sức khoẻ cho gia đình",
  workingDays: "Thứ 2 – Thứ 6",
  overtimePolicy: "Không OT",
  techStack: ["Java", "Spring Boot", "Kafka", "AWS"],
  logoFileName: "logo-lumen.png",
  coverFileName: "cover-lumen.jpg",
  licenseFileName: "GPKD_Lumen.pdf",
  licenseFileMeta: "1,2 MB",
  confirmed: true,
  status: "PENDING",
  submittedAt: "24/11/2026",
  approvedAt: "25/11/2026",
  createdBy: "Trần Minh Khoa",
  rejectionReason: "Giấy phép kinh doanh không rõ nét. Vui lòng tải lại bản scan.",
};

function todayVi(): string {
  return new Date().toLocaleDateString("vi-VN");
}

export async function getCompanyProfile(): Promise<CompanyProfile> {
  return mockResolve(companyState);
}

export async function saveCompanyDraft(
  input: CompanyRegistrationInput
): Promise<CompanyProfile> {
  if (!input.name.trim()) {
    return mockReject("Vui lòng nhập tên công ty trước khi lưu nháp.");
  }
  companyState = {
    ...companyState,
    ...input,
    displayName: companyState.displayName || input.name.trim(),
  };
  return mockResolve(companyState);
}

export async function submitCompanyRegistration(
  input: CompanyRegistrationInput
): Promise<CompanyProfile> {
  if (
    !input.name.trim() ||
    !input.taxCode.trim() ||
    !input.headquarters.trim() ||
    !input.contactEmail.trim() ||
    !input.contactPhone.trim()
  ) {
    return mockReject("Vui lòng điền đầy đủ các trường bắt buộc (*).");
  }
  if (!input.licenseFileName.trim()) {
    return mockReject("Vui lòng chọn tệp Giấy phép kinh doanh.");
  }
  if (!input.confirmed) {
    return mockReject("Vui lòng xác nhận thông tin và quyền đại diện công ty.");
  }
  companyState = {
    ...companyState,
    ...input,
    status: "PENDING",
    submittedAt: todayVi(),
    rejectionReason: null,
  };
  return mockResolve(companyState);
}

export async function setMockCompanyStatus(
  status: CompanyVerificationStatus
): Promise<CompanyProfile> {
  companyState = {
    ...companyState,
    status,
    approvedAt: status === "ACTIVE" ? companyState.approvedAt ?? todayVi() : companyState.approvedAt,
    rejectionReason:
      status === "REJECTED"
        ? companyState.rejectionReason ??
          "Giấy phép kinh doanh không rõ nét. Vui lòng tải lại bản scan."
        : null,
  };
  return mockResolve(companyState);
}

export async function updateCompanyProfile(
  input: CompanyProfileUpdateInput
): Promise<CompanyProfile> {
  if (!input.displayName.trim()) {
    return mockReject("Tên hiển thị công ty không được để trống.");
  }
  companyState = {
    ...companyState,
    ...input,
  };
  return mockResolve(companyState);
}

// ── R10: Thành viên công ty ───────────────────────────────────────────

export type CompanyRole = "Owner" | "Manager" | "Recruiter" | "Viewer";
export type EditableCompanyRole = Exclude<CompanyRole, "Owner">;

export interface TeamMember {
  id: number;
  name: string;
  email: string;
  role: CompanyRole;
  joinedAt: string;
}

export interface TeamInvite {
  id: number;
  email: string;
  role: EditableCompanyRole;
  invitedBy: string;
  expiresAt: string;
}

export interface TeamData {
  members: TeamMember[];
  invites: TeamInvite[];
}

let teamMembers: TeamMember[] = [
  { id: 1, name: "Trần Minh Khoa", email: "khoa@lumenfintech.vn", role: "Owner", joinedAt: "25/11/2026" },
  { id: 2, name: "Lê Thu Hà", email: "ha.le@lumenfintech.vn", role: "Manager", joinedAt: "26/11/2026" },
  { id: 3, name: "Phan Bảo", email: "bao.phan@lumenfintech.vn", role: "Recruiter", joinedAt: "27/11/2026" },
  { id: 4, name: "Ngô Tâm", email: "tam.ngo@lumenfintech.vn", role: "Recruiter", joinedAt: "01/12/2026" },
  { id: 5, name: "Vũ Linh", email: "linh.vu@lumenfintech.vn", role: "Viewer", joinedAt: "02/12/2026" },
];

let teamInvites: TeamInvite[] = [
  { id: 1, email: "thu.ha@gmail.com", role: "Recruiter", invitedBy: "Trần Minh Khoa", expiresAt: "01/12/2026" },
  { id: 2, email: "quang.vo@gmail.com", role: "Viewer", invitedBy: "Lê Thu Hà", expiresAt: "29/11/2026" },
];

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

function futureDateVi(days: number): string {
  const d = new Date();
  d.setDate(d.getDate() + days);
  return d.toLocaleDateString("vi-VN");
}

export async function getTeamData(): Promise<TeamData> {
  return mockResolve({ members: teamMembers, invites: teamInvites });
}

export async function updateMemberRole(
  memberId: number,
  role: EditableCompanyRole
): Promise<TeamMember> {
  const target = teamMembers.find((m) => m.id === memberId);
  if (!target) {
    return mockReject("Không tìm thấy thành viên.");
  }
  if (target.role === "Owner") {
    return mockReject("Không thể thay đổi vai trò của Owner.");
  }
  target.role = role;
  return mockResolve(target);
}

export async function removeTeamMember(memberId: number): Promise<void> {
  const target = teamMembers.find((m) => m.id === memberId);
  if (!target) {
    return mockReject("Không tìm thấy thành viên.");
  }
  if (target.role === "Owner") {
    return mockReject("Không thể xoá Owner khỏi công ty.");
  }
  teamMembers = teamMembers.filter((m) => m.id !== memberId);
  return mockResolve(undefined);
}

export async function inviteTeamMember(
  emailRaw: string,
  role: EditableCompanyRole,
  invitedBy = "Trần Minh Khoa"
): Promise<TeamInvite> {
  const email = emailRaw.trim();
  if (!email || !EMAIL_RE.test(email)) {
    return mockReject("Email không hợp lệ.");
  }
  const normalized = email.toLowerCase();
  if (teamMembers.some((m) => m.email.toLowerCase() === normalized)) {
    return mockReject("Người này đã là thành viên.");
  }
  if (teamInvites.some((inv) => inv.email.toLowerCase() === normalized)) {
    return mockReject("Đã có lời mời đang chờ.");
  }
  const created: TeamInvite = {
    id: nextId(teamInvites),
    email,
    role,
    invitedBy,
    expiresAt: futureDateVi(7),
  };
  teamInvites = [created, ...teamInvites];
  return mockResolve(created);
}

export async function resendTeamInvite(inviteId: number): Promise<TeamInvite> {
  const target = teamInvites.find((i) => i.id === inviteId);
  if (!target) {
    return mockReject("Không tìm thấy lời mời.");
  }
  target.expiresAt = futureDateVi(7);
  return mockResolve(target);
}

export async function revokeTeamInvite(inviteId: number): Promise<void> {
  teamInvites = teamInvites.filter((i) => i.id !== inviteId);
  return mockResolve(undefined);
}

// ── R11: Tìm & lưu CV ─────────────────────────────────────────────────

export interface CvCandidateExperience {
  role: string;
  company: string;
  period: string;
  summary: string;
}

export interface CvCandidateSummary {
  id: number;
  code: string;
  title: string;
  yearsExp: number;
  expLabel: string;
  city: string;
  matchByJob: Record<string, number>;
  skills: string[];
  summary: string;
  education: string;
  experiences: CvCandidateExperience[];
  saved: boolean;
  note: string;
}

export const CV_COMPARE_JOBS: readonly string[] = [
  "Senior Java Backend Engineer",
  "Frontend React Engineer",
  "QA Automation Engineer",
  "Không so sánh",
];

let cvPool: CvCandidateSummary[] = [
  {
    id: 1042,
    code: "Ứng viên #1042",
    title: "Backend Developer",
    yearsExp: 4,
    expLabel: "4 năm",
    city: "TP. Hồ Chí Minh",
    matchByJob: {
      "Senior Java Backend Engineer": 83,
      "Frontend React Engineer": 42,
      "QA Automation Engineer": 55,
      "Không so sánh": 83,
    },
    skills: ["Java", "Spring Boot", "Kafka"],
    summary: "4 năm xây dựng hệ thống thanh toán và đối soát giao dịch thời gian thực bằng Java Spring Boot & Kafka.",
    education: "ĐH Bách Khoa TP.HCM · Kỹ thuật phần mềm · 2018 – 2022",
    experiences: [
      {
        role: "Backend Developer",
        company: "PayFlow Vietnam",
        period: "05/2023 – nay",
        summary: "Thiết kế luồng xử lý giao dịch Kafka xử lý 1.200 msg/giây; tối ưu truy vấn PostgreSQL giảm 35% độ trễ.",
      },
      {
        role: "Java Developer",
        company: "KMS Technology",
        period: "06/2022 – 04/2023",
        summary: "Phát triển REST API Spring Boot và viết integration test với Testcontainers.",
      },
    ],
    saved: true,
    note: "Phù hợp team Payment, liên hệ khi mở tin Q1.",
  },
  {
    id: 981,
    code: "Ứng viên #0981",
    title: "Java Developer",
    yearsExp: 3,
    expLabel: "3 năm",
    city: "TP. Hồ Chí Minh",
    matchByJob: {
      "Senior Java Backend Engineer": 80,
      "Frontend React Engineer": 38,
      "QA Automation Engineer": 51,
      "Không so sánh": 80,
    },
    skills: ["Java", "Spring Boot", "MySQL"],
    summary: "3 năm kinh nghiệm phát triển microservices Java, Spring Data JPA, tối ưu chỉ mục MySQL cho hệ thống ERP.",
    education: "ĐH Khoa học Tự nhiên TP.HCM · CNTT · 2019 – 2023",
    experiences: [
      {
        role: "Java Developer",
        company: "Misa JSC",
        period: "07/2023 – nay",
        summary: "Phát triển phân hệ kế toán doanh nghiệp với Spring Boot và MySQL.",
      },
    ],
    saved: false,
    note: "",
  },
  {
    id: 1107,
    code: "Ứng viên #1107",
    title: "Software Engineer",
    yearsExp: 5,
    expLabel: "5 năm",
    city: "TP. Hồ Chí Minh",
    matchByJob: {
      "Senior Java Backend Engineer": 76,
      "Frontend React Engineer": 46,
      "QA Automation Engineer": 58,
      "Không so sánh": 76,
    },
    skills: ["Java", "AWS", "Docker"],
    summary: "Kỹ sư phần mềm tập trung kiến trúc cloud-native trên AWS ECS, Docker và Java 21.",
    education: "ĐH Công nghệ Thông tin ĐHQG-HCM · 2017 – 2021",
    experiences: [
      {
        role: "Software Engineer",
        company: "VNG Cloud",
        period: "01/2022 – nay",
        summary: "Vận hành và phát triển dịch vụ IAM trên AWS và Kubernetes.",
      },
    ],
    saved: false,
    note: "",
  },
  {
    id: 876,
    code: "Ứng viên #0876",
    title: "Backend Engineer",
    yearsExp: 2,
    expLabel: "2 năm",
    city: "TP. Hồ Chí Minh",
    matchByJob: {
      "Senior Java Backend Engineer": 72,
      "Frontend React Engineer": 39,
      "QA Automation Engineer": 48,
      "Không so sánh": 72,
    },
    skills: ["Java", "Redis", "Git"],
    summary: "Backend Engineer có nền tảng vững về caching với Redis, Spring Security và CI/CD.",
    education: "ĐH Sư phạm Kỹ thuật TP.HCM · 2020 – 2024",
    experiences: [
      {
        role: "Backend Engineer",
        company: "Tiki Corp",
        period: "03/2024 – nay",
        summary: "Tối ưu API giỏ hàng và bộ nhớ đệm Redis cho chiến dịch flash sale.",
      },
    ],
    saved: false,
    note: "",
  },
  {
    id: 1220,
    code: "Ứng viên #1220",
    title: "Fullstack Developer",
    yearsExp: 3,
    expLabel: "3 năm",
    city: "TP. Hồ Chí Minh",
    matchByJob: {
      "Senior Java Backend Engineer": 66,
      "Frontend React Engineer": 84,
      "QA Automation Engineer": 49,
      "Không so sánh": 66,
    },
    skills: ["Java", "ReactJS", "PostgreSQL"],
    summary: "Fullstack developer kết hợp Java Spring Boot ở backend và ReactJS TypeScript ở frontend.",
    education: "Học viện Công nghệ BCVT · 2019 – 2023",
    experiences: [
      {
        role: "Fullstack Developer",
        company: "Haravan",
        period: "06/2023 – nay",
        summary: "Xây dựng dashboard phân tích bán hàng cho chủ shop bằng ReactJS & PostgreSQL.",
      },
    ],
    saved: true,
    note: "Có thể chuyển sang team Frontend.",
  },
  {
    id: 755,
    code: "Ứng viên #0755",
    title: "Java Developer",
    yearsExp: 2,
    expLabel: "2 năm",
    city: "TP. Hồ Chí Minh",
    matchByJob: {
      "Senior Java Backend Engineer": 61,
      "Frontend React Engineer": 30,
      "QA Automation Engineer": 52,
      "Không so sánh": 61,
    },
    skills: ["Java", "Spring MVC", "Oracle"],
    summary: "2 năm bảo trì và nâng cấp hệ thống core banking nội bộ trên Java Spring MVC và Oracle DB.",
    education: "ĐH Tôn Đức Thắng · 2020 – 2024",
    experiences: [
      {
        role: "Java Developer",
        company: "FPT Software",
        period: "04/2024 – nay",
        summary: "Phát triển module báo cáo tài chính cho khách hàng ngân hàng Nhật Bản.",
      },
    ],
    saved: false,
    note: "",
  },
  {
    id: 1304,
    code: "Ứng viên #1304",
    title: "Senior Java Architect",
    yearsExp: 7,
    expLabel: "7 năm",
    city: "Hà Nội",
    matchByJob: {
      "Senior Java Backend Engineer": 91,
      "Frontend React Engineer": 35,
      "QA Automation Engineer": 60,
      "Không so sánh": 91,
    },
    skills: ["Java", "Spring Boot", "Kafka", "Kubernetes"],
    summary: "7 năm thiết kế hệ thống phân tán chịu tải cao trong lĩnh vực tài chính số.",
    education: "ĐH Bách Khoa Hà Nội · 2015 – 2019",
    experiences: [
      {
        role: "Tech Lead",
        company: "VNPay",
        period: "02/2021 – nay",
        summary: "Dẫn dắt nhóm 10 kỹ sư phát triển cổng thanh toán QR & đối soát tự động.",
      },
    ],
    saved: false,
    note: "",
  },
  {
    id: 1412,
    code: "Ứng viên #1412",
    title: "Frontend React Engineer",
    yearsExp: 1,
    expLabel: "1 năm",
    city: "Hà Nội",
    matchByJob: {
      "Senior Java Backend Engineer": 36,
      "Frontend React Engineer": 85,
      "QA Automation Engineer": 44,
      "Không so sánh": 68,
    },
    skills: ["ReactJS", "TypeScript", "Vite"],
    summary: "Kỹ sư Frontend chuyên React 19, TypeScript strict và thiết kế hệ thống UI chuẩn WCAG.",
    education: "ĐH Công nghệ ĐHQG Hà Nội · 2021 – 2025",
    experiences: [
      {
        role: "Frontend Developer",
        company: "Base.vn",
        period: "07/2025 – nay",
        summary: "Phát triển giao diện quản lý quy trình tuyển dụng và tối ưu hiệu năng bảng dữ liệu.",
      },
    ],
    saved: false,
    note: "",
  },
];

export async function listCandidateCvs(): Promise<CvCandidateSummary[]> {
  return mockResolve(cvPool);
}

export async function toggleSaveCv(
  candidateId: number,
  saved: boolean,
  note?: string
): Promise<CvCandidateSummary> {
  const target = cvPool.find((c) => c.id === candidateId);
  if (!target) {
    return mockReject("Không tìm thấy hồ sơ ứng viên.");
  }
  target.saved = saved;
  if (note !== undefined) {
    target.note = note.trim();
  }
  return mockResolve(target);
}

export async function updateCvNote(
  candidateId: number,
  note: string
): Promise<CvCandidateSummary> {
  const target = cvPool.find((c) => c.id === candidateId);
  if (!target) {
    return mockReject("Không tìm thấy hồ sơ ứng viên.");
  }
  target.note = note.trim();
  return mockResolve(target);
}

// ── R08: Kết quả phỏng vấn ────────────────────────────────────────────

export type InterviewResultStatus = "COMPLETED" | "PENDING" | "IN_PROGRESS" | "CANCELLED";

export interface InterviewTopicScore {
  topic: string;
  score: number;
}

export interface RecruiterInterviewResult {
  id: number;
  applicationId: number;
  candidateName: string;
  jobTitle: string;
  invitedAt: string;
  invitedIso: string;
  status: InterviewResultStatus;
  score: number | null;
  weakestTopic: string | null;
  questionCount: number;
  durationMinutes: number | null;
  topicScores: InterviewTopicScore[];
  summaryComment: string;
}

const interviewResults: RecruiterInterviewResult[] = [
  {
    id: 1,
    applicationId: 101,
    candidateName: "Trịnh Quang Huy",
    jobTitle: "Senior Java Backend Engineer",
    invitedAt: "20/11",
    invitedIso: "2026-11-20",
    status: "COMPLETED",
    score: 8.1,
    weakestTopic: "Docker (6,5)",
    questionCount: 6,
    durationMinutes: 25,
    topicScores: [
      { topic: "Java", score: 8.6 },
      { topic: "Spring Boot", score: 8.4 },
      { topic: "SQL", score: 8.0 },
      { topic: "REST API", score: 7.9 },
      { topic: "Docker", score: 6.5 },
    ],
    summaryComment: "Trả lời mạch lạc phần concurrency và transaction isolation; cần bổ sung kinh nghiệm multi-stage Docker build.",
  },
  {
    id: 2,
    applicationId: 102,
    candidateName: "Nguyễn Văn An",
    jobTitle: "Senior Java Backend Engineer",
    invitedAt: "21/11",
    invitedIso: "2026-11-21",
    status: "COMPLETED",
    score: 7.4,
    weakestTopic: "Docker (6,0)",
    questionCount: 6,
    durationMinutes: 28,
    topicScores: [
      { topic: "Java", score: 8.2 },
      { topic: "Spring Boot", score: 7.8 },
      { topic: "SQL", score: 7.5 },
      { topic: "REST API", score: 7.0 },
      { topic: "Docker", score: 6.0 },
    ],
    summaryComment: "Nền tảng Java/Spring Boot vững, diễn đạt rõ ràng; phần Docker chỉ dừng ở mức sử dụng cơ bản.",
  },
  {
    id: 3,
    applicationId: 103,
    candidateName: "Đỗ Thu Hằng",
    jobTitle: "QA Engineer",
    invitedAt: "19/11",
    invitedIso: "2026-11-19",
    status: "COMPLETED",
    score: 6.2,
    weakestTopic: "SQL (5,1)",
    questionCount: 5,
    durationMinutes: 22,
    topicScores: [
      { topic: "Test Design", score: 7.4 },
      { topic: "API Testing", score: 6.8 },
      { topic: "Automation", score: 6.1 },
      { topic: "SQL", score: 5.1 },
    ],
    summaryComment: "Nắm tốt quy trình viết test case và kiểm thử API; cần cải thiện truy vấn SQL phức tạp.",
  },
  {
    id: 4,
    applicationId: 104,
    candidateName: "Bùi Khánh",
    jobTitle: "Senior Java Backend Engineer",
    invitedAt: "24/11",
    invitedIso: "2026-11-24",
    status: "PENDING",
    score: null,
    weakestTopic: null,
    questionCount: 6,
    durationMinutes: null,
    topicScores: [],
    summaryComment: "Đã gửi lời mời phỏng vấn qua email, đang chờ ứng viên bắt đầu phiên.",
  },
  {
    id: 5,
    applicationId: 105,
    candidateName: "Hoàng Đức Tùng",
    jobTitle: "Frontend Engineer",
    invitedAt: "23/11",
    invitedIso: "2026-11-23",
    status: "IN_PROGRESS",
    score: null,
    weakestTopic: null,
    questionCount: 5,
    durationMinutes: null,
    topicScores: [],
    summaryComment: "Ứng viên đã hoàn thành 3/5 câu hỏi.",
  },
  {
    id: 6,
    applicationId: 106,
    candidateName: "Đặng Vũ",
    jobTitle: "Senior Java Backend Engineer",
    invitedAt: "14/11",
    invitedIso: "2026-11-14",
    status: "CANCELLED",
    score: null,
    weakestTopic: "Đơn đã rút",
    questionCount: 6,
    durationMinutes: null,
    topicScores: [],
    summaryComment: "Phiên phỏng vấn bị huỷ do ứng viên đã rút đơn ứng tuyển.",
  },
];

export async function getRecruiterInterviewResults(): Promise<RecruiterInterviewResult[]> {
  return mockResolve(interviewResults);
}

export async function remindInterviewCandidate(resultId: number): Promise<void> {
  const target = interviewResults.find((r) => r.id === resultId);
  if (!target) {
    return mockReject("Không tìm thấy lời mời phỏng vấn.");
  }
  return mockResolve(undefined);
}

// ── R06: Chi tiết đơn ứng tuyển (phần mở rộng mock) ──────────────────

export interface ApplicationCvMock {
  roleTitle: string;
  yearsExpLabel: string;
  email: string;
  phone: string;
  summary: string;
  experiences: {
    title: string;
    company: string;
    period: string;
    description: string;
  }[];
  education: string;
  matchedSkills: string[];
  otherSkills: string[];
}

export interface ApplicationMatchMock {
  overallPercent: number;
  breakdown: { label: string; percent: number }[];
  missingSkills: string[];
}

export interface ApplicationInterviewMock {
  completedAt: string;
  questionCount: number;
  durationMinutes: number;
  overallScore: number;
  topics: { name: string; score: number }[];
}

export interface ApplicationHistoryItem {
  statusLabel: string;
  timestamp: string;
  actor: string;
  note?: string;
}

export interface ApplicationDetailMock {
  applicationId: number;
  overrideStatus: string | null;
  rating: number;
  internalNote: string;
  cv: ApplicationCvMock;
  match: ApplicationMatchMock;
  interview: ApplicationInterviewMock | null;
  history: ApplicationHistoryItem[];
}

const applicationDetailStore = new Map<number, ApplicationDetailMock>();

function slugEmailFromName(name: string): string {
  const ascii = name
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/đ/g, "d")
    .replace(/Đ/g, "D")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, ".")
    .replace(/^\.+|\.+$/g, "");
  return `${ascii || "ung.vien"}@gmail.com`;
}

function formatShortTimestamp(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  const day = String(d.getDate()).padStart(2, "0");
  const month = String(d.getMonth() + 1).padStart(2, "0");
  const hour = String(d.getHours()).padStart(2, "0");
  const min = String(d.getMinutes()).padStart(2, "0");
  return `${day}/${month} ${hour}:${min}`;
}

function nowShortTimestamp(): string {
  return formatShortTimestamp(new Date().toISOString());
}

const STATUS_LABELS: Record<string, string> = {
  SUBMITTED: "Đã nộp",
  REVIEWING: "Đang xem xét",
  INTERVIEW: "Mời phỏng vấn",
  HIRED: "Trúng tuyển",
  REJECTED: "Từ chối",
  WITHDRAWN: "Đã rút",
};

function buildInitialDetailMock(seed: {
  id: number;
  candidateName: string;
  jobTitle: string;
  status: string;
  appliedAt: string;
}): ApplicationDetailMock {
  const variant = Math.abs(seed.id) % 3;
  const isFrontend = seed.jobTitle.toLowerCase().includes("front") || seed.jobTitle.toLowerCase().includes("react");
  const isQa = seed.jobTitle.toLowerCase().includes("qa") || seed.jobTitle.toLowerCase().includes("test");

  const cv: ApplicationCvMock = isFrontend
    ? {
        roleTitle: "Frontend Engineer",
        yearsExpLabel: `${2 + variant} năm kinh nghiệm`,
        email: slugEmailFromName(seed.candidateName),
        phone: `09${10 + variant}2 345 6${70 + variant}`,
        summary:
          "Kinh nghiệm phát triển ứng dụng web React, TypeScript strict, tối ưu Core Web Vitals và xây dựng design system.",
        experiences: [
          {
            title: "Frontend Developer · Sendo Tech",
            company: "Sendo Tech",
            period: "04/2024 – nay",
            description: "Phát triển luồng giỏ hàng và trang quản trị nhà bán hàng bằng React 19 & Vite.",
          },
          {
            title: "Web Intern · TMA Solutions",
            company: "TMA Solutions",
            period: "05/2023 – 03/2024",
            description: "Xây dựng component UI chuẩn accessibility và viết unit test Vitest.",
          },
        ],
        education: "ĐH Công nghệ Thông tin ĐHQG-HCM · Kỹ thuật phần mềm · 2019 – 2023",
        matchedSkills: ["React", "TypeScript", "HTML/CSS", "REST API"],
        otherSkills: ["Vite", "Git"],
      }
    : isQa
      ? {
          roleTitle: "QA Automation Engineer",
          yearsExpLabel: `${2 + variant} năm kinh nghiệm`,
          email: slugEmailFromName(seed.candidateName),
          phone: `09${30 + variant}4 512 8${10 + variant}`,
          summary:
            "Kinh nghiệm kiểm thử tự động API & E2E, thiết kế bộ test regression và theo dõi chất lượng release.",
          experiences: [
            {
              title: "QA Engineer · NashTech",
              company: "NashTech",
              period: "03/2024 – nay",
              description: "Viết script Playwright & Postman CI kiểm thử hệ thống thanh toán.",
            },
          ],
          education: "ĐH Khoa học Tự nhiên · Hệ thống thông tin · 2019 – 2023",
          matchedSkills: ["Playwright", "Postman", "SQL", "CI/CD"],
          otherSkills: ["Java", "Git"],
        }
      : {
          roleTitle: "Backend Developer",
          yearsExpLabel: `${3 + variant} năm kinh nghiệm`,
          email: slugEmailFromName(seed.candidateName),
          phone: `0912 345 6${78 - variant}`,
          summary:
            "3 năm kinh nghiệm phát triển backend Java, Spring Boot cho hệ thống thương mại điện tử và thanh toán.",
          experiences: [
            {
              title: "Backend Developer · Nami Commerce",
              company: "Nami Commerce",
              period: "06/2024 – nay",
              description: "Dịch vụ đơn hàng Spring Boot; giảm 40% thời gian truy vấn báo cáo.",
            },
            {
              title: "Java Intern · Sao Mai Software",
              company: "Sao Mai Software",
              period: "01/2023 – 05/2024",
              description: "API quản lý kho, unit test JUnit.",
            },
          ],
          education: "Học viện Công nghệ Bưu chính Viễn thông · Công nghệ thông tin · 2019 – 2024",
          matchedSkills: ["Java", "Spring Boot", "MySQL", "Docker"],
          otherSkills: ["Redis", "Git"],
        };

  const overallPercent = 86 - variant * 4;
  const match: ApplicationMatchMock = {
    overallPercent,
    breakdown: [
      { label: "Chức danh", percent: 90 - variant * 3 },
      { label: "Kinh nghiệm", percent: 82 - variant * 4 },
      { label: "Kỹ năng", percent: 88 - variant * 5 },
    ],
    missingSkills: isFrontend ? ["GraphQL"] : isQa ? ["Performance Testing"] : ["Kafka"],
  };

  const upperStatus = seed.status.toUpperCase();
  const hasInterview = upperStatus === "INTERVIEW" || upperStatus === "HIRED" || variant === 0;
  const interview: ApplicationInterviewMock | null = hasInterview
    ? {
        completedAt: "22/11/2026",
        questionCount: 6,
        durationMinutes: 28,
        overallScore: Number((7.4 + variant * 0.3).toFixed(1)),
        topics: isFrontend
          ? [
              { name: "React", score: 8.3 },
              { name: "TypeScript", score: 7.9 },
              { name: "CSS Layout", score: 7.4 },
              { name: "Performance", score: 6.8 },
              { name: "Testing", score: 6.4 },
            ]
          : [
              { name: "Java", score: 8.2 },
              { name: "SQL", score: 7.5 },
              { name: "Spring Boot", score: 7.8 },
              { name: "REST API", score: 7.0 },
              { name: "Docker", score: 6.0 },
            ],
      }
    : null;

  const appliedTime = formatShortTimestamp(seed.appliedAt);
  const history: ApplicationHistoryItem[] = [];
  if (interview) {
    history.push({
      statusLabel: `Hoàn thành phỏng vấn (${String(interview.overallScore).replace(".", ",")}/10)`,
      timestamp: "22/11 16:40",
      actor: "Hệ thống",
    });
  }
  if (upperStatus === "INTERVIEW" || upperStatus === "HIRED") {
    history.push({
      statusLabel: "Mời phỏng vấn",
      timestamp: "21/11 15:02",
      actor: "Trần Minh Khoa",
    });
  }
  if (upperStatus !== "SUBMITTED") {
    history.push({
      statusLabel: STATUS_LABELS[upperStatus] ?? upperStatus,
      timestamp: "21/11 14:30",
      actor: "Trần Minh Khoa",
    });
  }
  history.push({
    statusLabel: "Đã nộp",
    timestamp: appliedTime || "20/11 09:12",
    actor: "Ứng viên",
  });

  return {
    applicationId: seed.id,
    overrideStatus: null,
    rating: 4,
    internalNote: "Giao tiếp tốt, cần hỏi thêm về Kafka ở vòng trực tiếp.",
    cv,
    match,
    interview,
    history,
  };
}

export async function getApplicationDetailMock(seed: {
  id: number;
  candidateName: string;
  jobTitle: string;
  status: string;
  appliedAt: string;
}): Promise<ApplicationDetailMock> {
  let entry = applicationDetailStore.get(seed.id);
  if (!entry) {
    entry = buildInitialDetailMock(seed);
    applicationDetailStore.set(seed.id, entry);
  }
  return mockResolve(entry);
}

export async function updateMockApplicationStatus(
  applicationId: number,
  nextStatus: string,
  note: string,
  actor = "Trần Minh Khoa"
): Promise<ApplicationDetailMock> {
  const entry = applicationDetailStore.get(applicationId);
  if (!entry) {
    return mockReject("Không tìm thấy dữ liệu đơn ứng tuyển.");
  }
  entry.overrideStatus = nextStatus;
  entry.history = [
    {
      statusLabel: STATUS_LABELS[nextStatus.toUpperCase()] ?? nextStatus,
      timestamp: nowShortTimestamp(),
      actor,
      note: note.trim() || undefined,
    },
    ...entry.history,
  ];
  return mockResolve(entry);
}

export async function saveMockApplicationNote(
  applicationId: number,
  rating: number,
  internalNote: string
): Promise<ApplicationDetailMock> {
  const entry = applicationDetailStore.get(applicationId);
  if (!entry) {
    return mockReject("Không tìm thấy dữ liệu đơn ứng tuyển.");
  }
  entry.rating = rating;
  entry.internalNote = internalNote;
  return mockResolve(entry);
}

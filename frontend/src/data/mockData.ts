import type {
  Candidate,
  ExtractedCv,
  InterviewQuestion,
  InterviewSession,
  Job,
  MatchResult,
} from "../types";

/** Dữ liệu minh họa — đồng bộ với ui-prototype/assets/js/mock-data.js */
export const mockMeta = {
  notice: "Dữ liệu minh họa cho demo UI",
  userLocation: "Quận 1, TP. Hồ Chí Minh",
  modelVersions: {
    ner: "rule+ner-baseline-v0 (chưa deploy service)",
    embedding: "sentence-transformer-planned-v0",
    matching: "hybrid-baseline-v0 (TF-IDF + semantic stub)",
    interview: "bertscore-mbert + linear-calibration-demo",
  },
};

export const mockCandidate: Candidate = {
  id: "cand-001",
  name: "Nguyễn Minh An",
  email: "minhan.demo@email.com",
  title: "Backend Developer",
  yearsExp: 2.5,
  city: "TP. Hồ Chí Minh",
};

export const mockExtractedCv: ExtractedCv = {
  status: "pending_review",
  confidence: 0.82,
  sourceFile: "CV_Nguyen_Minh_An.pdf",
  contact: {
    fullName: "Nguyễn Minh An",
    email: "minhan.demo@email.com",
    phone: "0901 234 567",
    location: "TP. Hồ Chí Minh",
  },
  summary:
    "Sinh viên năm cuối CNTT, có kinh nghiệm thực tập backend với Java/Spring Boot và PostgreSQL.",
  education: [
    {
      school: "Đại học Công nghệ Thông tin",
      degree: "Cử nhân CNTT",
      period: "2022 – 2026",
    },
  ],
  experience: [
    {
      title: "Thực tập sinh Backend",
      organization: "Công ty Demo Soft",
      period: "06/2025 – 12/2025",
      bullets: [
        "Phát triển REST API bằng Spring Boot",
        "Thiết kế schema PostgreSQL cho module tuyển dụng",
      ],
    },
  ],
  projects: [
    {
      name: "Hệ thống tuyển dụng thông minh",
      description: "Áp dụng NER, Embedding, Learning-to-Rank và BERTScore.",
      skills: ["Java", "Spring Boot", "Python", "NLP"],
    },
  ],
  skills: ["Java", "Spring Boot", "PostgreSQL", "Python", "REST API", "Git"],
  languages: ["Tiếng Việt (bản ngữ)", "English (B1)"],
  certificates: ["AWS Cloud Practitioner (minh họa)"],
  missingFields: ["linkedin", "expected_salary"],
};

export const mockJobs: Job[] = [
  {
    id: "job-101",
    title: "Junior Backend Developer (Java)",
    company: "NovaTech",
    location: "Quận 1, TP.HCM",
    city: "TP. Hồ Chí Minh",
    workType: "Hybrid",
    level: "Junior",
    salary: "15 – 22 triệu",
    postedAgo: "2 giờ trước",
    distanceKm: 1.8,
    hot: true,
    nearYou: true,
    logo: "NT",
    logoColor: "#0d9488",
    requiredSkills: ["Java", "Spring Boot", "PostgreSQL", "REST API"],
    preferredSkills: ["Docker", "Kafka"],
    minYears: 1,
    description:
      "Tham gia xây dựng microservice Java/Spring Boot, viết API và tối ưu truy vấn PostgreSQL.",
  },
  {
    id: "job-102",
    title: "NLP Engineer Intern",
    company: "AI Hub Vietnam",
    location: "Cầu Giấy, Hà Nội",
    city: "Hà Nội",
    workType: "Tại văn phòng",
    level: "Intern",
    salary: "5 – 8 triệu",
    postedAgo: "Hôm nay",
    distanceKm: null,
    hot: false,
    nearYou: false,
    logo: "AI",
    logoColor: "#2563eb",
    requiredSkills: ["Python", "NLP", "PyTorch"],
    preferredSkills: ["BERT", "FastAPI"],
    minYears: 0,
    description:
      "Hỗ trợ pipeline trích xuất thông tin CV và đánh giá câu trả lời phỏng vấn bằng Transformer.",
  },
  {
    id: "job-103",
    title: "Full-stack Developer",
    company: "PixelWorks",
    location: "Remote toàn quốc",
    city: "Remote",
    workType: "Remote",
    level: "Mid",
    salary: "25 – 35 triệu",
    postedAgo: "1 ngày trước",
    distanceKm: null,
    hot: true,
    nearYou: false,
    logo: "PW",
    logoColor: "#ea580c",
    requiredSkills: ["React", "Node.js", "TypeScript", "PostgreSQL"],
    preferredSkills: ["AWS"],
    minYears: 2,
    description: "Phát triển sản phẩm web end-to-end cho nền tảng HR.",
  },
  {
    id: "job-104",
    title: "Java Intern",
    company: "FPT Software",
    location: "Quận 9, TP.HCM",
    city: "TP. Hồ Chí Minh",
    workType: "Tại văn phòng",
    level: "Intern",
    salary: "Thỏa thuận",
    postedAgo: "3 giờ trước",
    distanceKm: 8.5,
    hot: false,
    nearYou: true,
    logo: "FS",
    logoColor: "#059669",
    requiredSkills: ["Java", "SQL", "Git"],
    preferredSkills: ["Spring Boot"],
    minYears: 0,
    description: "Thực tập Java, tham gia dự án outsourcing và mentorship.",
  },
  {
    id: "job-105",
    title: "Backend Developer (Spring)",
    company: "VNG Games",
    location: "Bình Thạnh, TP.HCM",
    city: "TP. Hồ Chí Minh",
    workType: "Hybrid",
    level: "Junior",
    salary: "18 – 28 triệu",
    postedAgo: "5 giờ trước",
    distanceKm: 4.2,
    hot: true,
    nearYou: true,
    logo: "VG",
    logoColor: "#dc2626",
    requiredSkills: ["Java", "Spring Boot", "MySQL", "Redis"],
    preferredSkills: ["Kafka", "Kubernetes"],
    minYears: 1,
    description: "Xây dựng dịch vụ backend cho sản phẩm game / social.",
  },
  {
    id: "job-106",
    title: "Data / ML Intern",
    company: "Tiki",
    location: "Quận 7, TP.HCM",
    city: "TP. Hồ Chí Minh",
    workType: "Hybrid",
    level: "Intern",
    salary: "6 – 10 triệu",
    postedAgo: "Hôm qua",
    distanceKm: 6.1,
    hot: false,
    nearYou: true,
    logo: "TK",
    logoColor: "#1d4ed8",
    requiredSkills: ["Python", "Machine Learning", "SQL"],
    preferredSkills: ["NLP"],
    minYears: 0,
    description: "Hỗ trợ các bài toán ranking, NLP và phân tích hành vi người dùng.",
  },
];

export const mockMatchingResults: MatchResult[] = [
  {
    jobId: "job-101",
    rank: 1,
    score: 0.86,
    semanticSimilarity: 0.81,
    tfidfSimilarity: 0.74,
    skillOverlap: 0.92,
    matchedSkills: ["Java", "Spring Boot", "PostgreSQL", "REST API"],
    missingSkills: ["Docker"],
    reasons: [
      "Kỹ năng bắt buộc trùng 4/4",
      "Kinh nghiệm backend Java phù hợp JD",
      "Điểm semantic (stub) cao với mô tả công việc",
    ],
    modelVersion: "hybrid-baseline-v0",
  },
  {
    jobId: "job-105",
    rank: 2,
    score: 0.79,
    semanticSimilarity: 0.77,
    tfidfSimilarity: 0.69,
    skillOverlap: 0.75,
    matchedSkills: ["Java", "Spring Boot"],
    missingSkills: ["MySQL", "Redis"],
    reasons: ["Gần vị trí của bạn (~4 km)", "Stack Java/Spring trùng mạnh"],
    modelVersion: "hybrid-baseline-v0",
  },
  {
    jobId: "job-102",
    rank: 3,
    score: 0.71,
    semanticSimilarity: 0.76,
    tfidfSimilarity: 0.58,
    skillOverlap: 0.67,
    matchedSkills: ["Python", "NLP"],
    missingSkills: ["PyTorch"],
    reasons: [
      "Có dự án NLP/đồ án liên quan",
      "Thiếu PyTorch trong CV đã trích xuất",
    ],
    modelVersion: "hybrid-baseline-v0",
  },
  {
    jobId: "job-103",
    rank: 4,
    score: 0.39,
    semanticSimilarity: 0.48,
    tfidfSimilarity: 0.33,
    skillOverlap: 0.25,
    matchedSkills: ["PostgreSQL"],
    missingSkills: ["React", "Node.js", "TypeScript"],
    reasons: [
      "Thiếu nhiều kỹ năng frontend bắt buộc",
      "Hồ sơ thiên về backend hơn full-stack",
    ],
    modelVersion: "hybrid-baseline-v0",
  },
];

export const mockInterviewQuestions: InterviewQuestion[] = [
  {
    id: "q-01",
    topic: "Java",
    difficulty: "Dễ",
    skill: "Java",
    question: "Java là gì?",
    referenceAnswer:
      "Java là ngôn ngữ lập trình hướng đối tượng, đa nền tảng, thường được sử dụng để xây dựng ứng dụng backend, web và nhiều loại phần mềm.",
    rubric: ["Hướng đối tượng", "Đa nền tảng", "Ứng dụng backend/web"],
  },
  {
    id: "q-02",
    topic: "Spring",
    difficulty: "Trung bình",
    skill: "Spring Boot",
    question: "Spring Boot là gì?",
    referenceAnswer:
      "Spring Boot là framework dựa trên Spring, giúp đơn giản hóa việc tạo và cấu hình ứng dụng Java, đặc biệt là các ứng dụng web và REST API.",
    rubric: ["Dựa trên Spring", "Giảm cấu hình", "Web/REST API"],
  },
  {
    id: "q-03",
    topic: "Database",
    difficulty: "Trung bình",
    skill: "SQL",
    question: "SQL JOIN dùng để làm gì?",
    referenceAnswer:
      "JOIN trong SQL dùng để kết hợp dữ liệu từ hai hoặc nhiều bảng dựa trên điều kiện liên kết giữa các cột.",
    rubric: ["Kết hợp nhiều bảng", "Điều kiện liên kết"],
  },
];

export const mockInterviewSession: InterviewSession = {
  id: "sess-778",
  status: "in_progress",
  jobTitle: "Junior Backend Developer (Java)",
  currentIndex: 0,
  responses: [
    {
      questionId: "q-01",
      answer:
        "Java là ngôn ngữ lập trình hướng đối tượng được sử dụng để phát triển các ứng dụng backend.",
      evaluation: {
        bertPrecision: 0.91,
        bertRecall: 0.84,
        bertF1: 0.87,
        predictedScore: 8.2,
        scoreScale:
          "0–10 (đã hiệu chỉnh từ BERTScore, không quy đổi trực tiếp)",
        coveredPoints: ["Hướng đối tượng", "Ứng dụng backend"],
        missingPoints: ["Đa nền tảng"],
        comment:
          "Câu trả lời đúng trọng tâm nhưng chưa đề cập đặc tính đa nền tảng.",
        modelVersion: "bertscore-mbert + linear-calibration-demo",
      },
    },
  ],
};

export const scoreDefinitions = {
  matchScore:
    "Điểm phù hợp tổng hợp (0–1) = trọng số semantic + skill overlap + kinh nghiệm. Bản demo dùng stub có thể giải thích được, chưa phải Learning-to-Rank đã huấn luyện.",
  bertscore:
    "BERTScore đo tương đồng ngữ nghĩa với đáp án tham chiếu. Điểm phỏng vấn hiển thị đã qua bước hiệu chỉnh tuyến tính trên dữ liệu demo — không phải điểm tuyệt đối.",
  cvConfidence:
    "Độ tin cậy trích xuất ước lượng từ rule-based + NER baseline (minh họa).",
};

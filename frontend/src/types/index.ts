export type UserRole = "candidate" | "recruiter";

export type HeaderMode = "public" | "candidate" | "recruiter";

export type NavKey =
  | "jobs"
  | "login"
  | "home"
  | "candidates"
  | "matching"
  | "interview"
  | "interviews"
  | "cv";

export interface NavLink {
  href: string;
  key: NavKey;
  label: string;
}

export interface Job {
  id: string;
  title: string;
  company: string;
  location: string;
  city: string;
  workType: string;
  level: string;
  salary: string;
  postedAgo: string;
  distanceKm: number | null;
  hot: boolean;
  nearYou: boolean;
  logo: string;
  logoColor: string;
  requiredSkills: string[];
  preferredSkills: string[];
  minYears: number;
  description: string;
}

export interface MatchResult {
  jobId: string;
  rank: number;
  score: number;
  semanticSimilarity: number;
  tfidfSimilarity: number;
  skillOverlap: number;
  matchedSkills: string[];
  missingSkills: string[];
  reasons: string[];
  modelVersion: string;
}

export interface Candidate {
  id: string;
  name: string;
  email: string;
  title: string;
  yearsExp: number;
  city: string;
}

export interface ExtractedCv {
  status: string;
  confidence: number;
  sourceFile: string;
  contact: {
    fullName: string;
    email: string;
    phone: string;
    location: string;
  };
  summary: string;
  education: { school: string; degree: string; period: string }[];
  experience: {
    title: string;
    organization: string;
    period: string;
    bullets: string[];
  }[];
  projects: { name: string; description: string; skills: string[] }[];
  skills: string[];
  languages: string[];
  certificates: string[];
  missingFields: string[];
}

export interface InterviewQuestion {
  id: string;
  topic: string;
  difficulty: string;
  skill: string;
  question: string;
  referenceAnswer: string;
  rubric: string[];
}

export interface InterviewEvaluation {
  bertPrecision: number;
  bertRecall: number;
  bertF1: number;
  predictedScore: number;
  scoreScale: string;
  coveredPoints: string[];
  missingPoints: string[];
  comment: string;
  modelVersion: string;
}

export interface InterviewSession {
  id: string;
  status: string;
  jobTitle: string;
  currentIndex: number;
  responses: {
    questionId: string;
    answer: string;
    evaluation: InterviewEvaluation;
  }[];
}

export interface ButtonVariant {
  variant?: "primary" | "accent" | "ghost" | "soft";
  size?: "sm" | "md";
  block?: boolean;
}

export type ChipTone = "default" | "ok" | "warn" | "hot" | "near" | "accent" | "brand";

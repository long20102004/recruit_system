import { api, type PageDto } from "./client";

export type QuestionType = "Kiến thức" | "Áp dụng" | "Tình huống";
export const QUESTION_TYPES: QuestionType[] = ["Kiến thức", "Áp dụng", "Tình huống"];
export const QUESTION_LEVELS = ["Intern", "Junior", "Middle", "Senior"];

export interface RubricCriterion {
  name: string;
  /** Trọng số phần trăm; tổng các tiêu chí nên bằng 100. */
  weight: number;
  points: string;
  keywords: string;
  misconceptions: string;
}

export interface BankQuestion {
  id: number;
  questionText: string;
  topic: string;
  level: string;
  type: QuestionType;
  referenceAnswer: string;
  rubric: RubricCriterion[];
  approved: boolean;
  enabled: boolean;
}

export type BankQuestionInput = Omit<BankQuestion, "id" | "approved" | "enabled">;

const base = "/interviews/admin/questions";

export const questionBankApi = {
  async list() {
    const first = await api<PageDto<BankQuestion>>(`${base}?page=0&size=100`);
    const pages = [];
    for (let page = 1; page < first.totalPages; page++) {
      pages.push(await api<PageDto<BankQuestion>>(`${base}?page=${page}&size=100`));
    }
    return [first, ...pages].flatMap((page) => page.content);
  },
  create: (input: BankQuestionInput) =>
    api<BankQuestion>(base, { method: "POST", body: JSON.stringify(input) }),
  update: (id: number, input: BankQuestionInput) =>
    api<BankQuestion>(`${base}/${id}`, { method: "PUT", body: JSON.stringify(input) }),
  setEnabled: (id: number, enabled: boolean) =>
    api<BankQuestion>(`${base}/${id}`, { method: "PATCH", body: JSON.stringify({ enabled }) }),
  setApproved: (id: number, approved: boolean) =>
    api<BankQuestion>(`${base}/${id}`, { method: "PATCH", body: JSON.stringify({ approved }) }),
  archive: (id: number) => api<void>(`${base}/${id}`, { method: "DELETE" }),
};

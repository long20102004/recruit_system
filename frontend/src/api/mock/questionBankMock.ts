import { MAX_PAGE_SIZE, interviewsApi, type QuestionDto } from "../client";
import { mockReject, mockResolve } from "./core";

/**
 * Ngân hàng câu hỏi cho admin (màn AD05). Danh sách câu hỏi lấy từ API thật
 * (GET /api/interviews/questions); backend chưa có API thêm/sửa/duyệt/bật-tắt và chưa lưu
 * dạng câu hỏi, trạng thái duyệt, rubric chi tiết, nên các phần đó là dữ liệu mẫu trong bộ nhớ.
 * Khi có API: thay thân các hàm dưới, giữ nguyên chữ ký.
 */

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

/** Độ khó từ API (Easy/Medium/Hard) đổi sang cấp độ như canvas. */
const LEVEL_FROM_DIFFICULTY: Record<string, string> = { Easy: "Intern", Medium: "Junior", Hard: "Middle" };

let store: BankQuestion[] | null = null;
let localId = 100000;

function fromApi(q: QuestionDto): BankQuestion {
  const labels = q.rubricLabels.length ? q.rubricLabels : ["Nêu đúng khái niệm", "So sánh, khi nào dùng", "Ví dụ minh hoạ"];
  const base = Math.floor(100 / labels.length);
  return {
    id: q.id,
    questionText: q.questionText,
    topic: q.topic ?? q.skill ?? "Khác",
    level: LEVEL_FROM_DIFFICULTY[q.difficulty ?? ""] ?? q.difficulty ?? "Junior",
    type: "Kiến thức",
    referenceAnswer: q.referenceAnswer ?? "",
    rubric: labels.map((name, i) => ({
      name,
      weight: i === labels.length - 1 ? 100 - base * (labels.length - 1) : base,
      points: "",
      keywords: "",
      misconceptions: "",
    })),
    approved: false,
    enabled: true,
  };
}

async function load(): Promise<BankQuestion[]> {
  if (!store) {
    const page = await interviewsApi.questions({ size: MAX_PAGE_SIZE });
    store = page.content.map(fromApi);
  }
  return store;
}

function validate(input: BankQuestionInput): string | null {
  if (!input.questionText.trim()) return "Vui lòng nhập nội dung câu hỏi.";
  if (!input.topic.trim()) return "Vui lòng chọn chủ đề.";
  if (input.rubric.length === 0) return "Cần ít nhất một tiêu chí rubric.";
  if (input.rubric.some((r) => !r.name.trim())) return "Tiêu chí rubric cần có tên.";
  const total = input.rubric.reduce((s, r) => s + (Number(r.weight) || 0), 0);
  if (total !== 100) return `Tổng trọng số rubric phải bằng 100% (hiện ${total}%).`;
  return null;
}

export const questionBankMock = {
  async list(): Promise<BankQuestion[]> {
    return mockResolve(await load());
  },

  async create(input: BankQuestionInput): Promise<BankQuestion> {
    const err = validate(input);
    if (err) return mockReject(err);
    const list = await load();
    const q: BankQuestion = { ...input, id: ++localId, approved: false, enabled: true };
    list.unshift(q);
    return mockResolve(q);
  },

  async update(id: number, input: BankQuestionInput): Promise<BankQuestion> {
    const err = validate(input);
    if (err) return mockReject(err);
    const list = await load();
    const i = list.findIndex((q) => q.id === id);
    if (i === -1) return mockReject("Không tìm thấy câu hỏi.");
    // Sửa nội dung thì cần duyệt lại.
    list[i] = { ...list[i], ...input, approved: false };
    return mockResolve(list[i]);
  },

  async setApproved(id: number, approved: boolean): Promise<BankQuestion> {
    const list = await load();
    const q = list.find((x) => x.id === id);
    if (!q) return mockReject("Không tìm thấy câu hỏi.");
    q.approved = approved;
    return mockResolve(q);
  },

  async setEnabled(id: number, enabled: boolean): Promise<BankQuestion> {
    const list = await load();
    const q = list.find((x) => x.id === id);
    if (!q) return mockReject("Không tìm thấy câu hỏi.");
    q.enabled = enabled;
    return mockResolve(q);
  },
};

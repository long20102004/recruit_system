// Build the Module 1 pipeline document (Vietnamese) as .docx
const fs = require("fs");
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType, Table, TableRow, TableCell,
  WidthType, ShadingType, BorderStyle, LevelFormat, TableOfContents, PageBreak, Footer, PageNumber, ImageRun,
} = require("docx");

const FONT = "Times New Roman";
const MONO = "Consolas";
const W = 9026; // A4 content width (DXA) with 1" margins
const KB = JSON.parse(fs.readFileSync(__dirname + "/kb_numbers.json", "utf8"));
const CMP = JSON.parse(fs.readFileSync(__dirname + "/fig/compare.json", "utf8"));
const NEO = JSON.parse(fs.readFileSync(__dirname + "/neo4j_counts.json", "utf8"));
const KB1 = JSON.parse(fs.readFileSync(__dirname + "/../../ai-service/kb/sources/kb1_books.json", "utf8"));
const COLAB = fs.existsSync(__dirname + "/colab_output.json") ? JSON.parse(fs.readFileSync(__dirname + "/colab_output.json", "utf8")) : null;
function img(file, widthPx) {
  const data = fs.readFileSync(__dirname + "/fig/" + file);
  const w = data.readUInt32BE(16), h = data.readUInt32BE(20);
  return new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 120, after: 60 },
    children: [new ImageRun({ type: "png", data, transformation: { width: widthPx, height: Math.round(widthPx * h / w) },
      altText: { title: file, description: file, name: file } })] });
}
const fmt = (v) => (v === null || v === undefined) ? "chờ chạy" : v.toFixed(3).replace(".", ",");

// ---------- helpers ----------
function runs(text, base = {}) {
  // **bold**, `code`
  const out = [];
  const re = /(\*\*[^*]+\*\*|`[^`]+`)/g;
  let last = 0, m;
  while ((m = re.exec(text))) {
    if (m.index > last) out.push(new TextRun({ text: text.slice(last, m.index), ...base }));
    const t = m[0];
    if (t.startsWith("**")) out.push(new TextRun({ text: t.slice(2, -2), bold: true, ...base }));
    else out.push(new TextRun({ text: t.slice(1, -1), font: MONO, size: 22, ...base }));
    last = m.index + t.length;
  }
  if (last < text.length) out.push(new TextRun({ text: text.slice(last), ...base }));
  return out;
}
const P = (t, o = {}) => new Paragraph({ children: runs(t), spacing: { after: 120, line: 300 }, alignment: AlignmentType.JUSTIFIED, ...o });
const H1 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun(t)], pageBreakBefore: true });
const H2 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun(t)] });
const H3 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_3, children: [new TextRun(t)] });
const B = (t, level = 0) => new Paragraph({ numbering: { reference: "bullets", level }, children: runs(t), spacing: { after: 60, line: 288 } });
const N = (t, ref = "num1") => new Paragraph({ numbering: { reference: ref, level: 0 }, children: runs(t), spacing: { after: 60, line: 288 } });
const caption = (t) => new Paragraph({ children: [new TextRun({ text: t, italics: true, size: 22 })], alignment: AlignmentType.CENTER, spacing: { before: 60, after: 200 } });

function code(lines, title) {
  const out = [];
  if (title) out.push(new Paragraph({ children: [new TextRun({ text: title, bold: true, size: 20, font: MONO, color: "1F4E79" })], spacing: { before: 120, after: 0 }, keepNext: true }));
  const arr = lines.replace(/\t/g, "    ").split("\n");
  arr.forEach((l, i) => out.push(new Paragraph({
    children: [new TextRun({ text: l.length ? l : " ", font: MONO, size: 18 })],
    shading: { type: ShadingType.CLEAR, fill: "F2F2F2", color: "auto" },
    spacing: { before: 0, after: i === arr.length - 1 ? 160 : 0, line: 240 },
    keepLines: true, keepNext: i < arr.length - 1 && arr.length < 25,
    border: {
      left: { style: BorderStyle.SINGLE, size: 12, color: "2E75B6", space: 6 },
    },
  })));
  return out;
}

const border = { style: BorderStyle.SINGLE, size: 4, color: "A6A6A6" };
const borders = { top: border, bottom: border, left: border, right: border };
function table(headers, rows, widths, opts = {}) {
  const total = widths.reduce((a, b) => a + b, 0);
  const mk = (txt, w, head, fill) => new TableCell({
    borders, width: { size: w, type: WidthType.DXA },
    shading: head ? { fill: "1F4E79", type: ShadingType.CLEAR, color: "auto" } : (fill ? { fill, type: ShadingType.CLEAR, color: "auto" } : undefined),
    margins: { top: 60, bottom: 60, left: 100, right: 100 },
    children: String(txt).split("\n").map((line) => new Paragraph({
      children: runs(line, head ? { bold: true, color: "FFFFFF", size: 22 } : { size: 22 }),
      spacing: { after: 0, line: 264 },
    })),
  });
  return new Table({
    width: { size: total, type: WidthType.DXA }, columnWidths: widths,
    rows: [
      new TableRow({ tableHeader: true, children: headers.map((h, i) => mk(h, widths[i], true)) }),
      ...rows.map((r, ri) => new TableRow({ children: r.map((c, i) => mk(c, widths[i], false, opts.zebra && ri % 2 ? "EEF3F8" : undefined)) })),
    ],
  });
}
function box(title, lines, fill = "FFF4E5", edge = "C55A11") {
  const b = { style: BorderStyle.SINGLE, size: 8, color: edge };
  return new Table({
    width: { size: W, type: WidthType.DXA }, columnWidths: [W],
    rows: [new TableRow({ children: [new TableCell({
      width: { size: W, type: WidthType.DXA }, borders: { top: b, bottom: b, left: b, right: b },
      shading: { fill, type: ShadingType.CLEAR, color: "auto" }, margins: { top: 100, bottom: 100, left: 160, right: 160 },
      children: [new Paragraph({ children: [new TextRun({ text: title, bold: true })], spacing: { after: 60 } }),
        ...lines.map((l) => new Paragraph({ children: runs(l), spacing: { after: 40, line: 276 } }))],
    })] })],
  });
}
const gap = () => new Paragraph({ children: [], spacing: { after: 80 } });

// Pipeline diagram as a one-column table of steps with arrows
function flow(steps) {
  const out = [];
  steps.forEach(([title, detail, fill], i) => {
    const b = { style: BorderStyle.SINGLE, size: 6, color: "2E75B6" };
    out.push(new Table({
      width: { size: W, type: WidthType.DXA }, columnWidths: [2600, W - 2600],
      rows: [new TableRow({ cantSplit: true, children: [
        new TableCell({ width: { size: 2600, type: WidthType.DXA }, borders: { top: b, bottom: b, left: b, right: b },
          shading: { fill: fill || "DEEAF6", type: ShadingType.CLEAR, color: "auto" }, margins: { top: 80, bottom: 80, left: 120, right: 120 },
          children: [new Paragraph({ children: [new TextRun({ text: title, bold: true, size: 22 })] })] }),
        new TableCell({ width: { size: W - 2600, type: WidthType.DXA }, borders: { top: b, bottom: b, left: b, right: b },
          margins: { top: 80, bottom: 80, left: 120, right: 120 },
          children: detail.split("\n").map((d) => new Paragraph({ children: runs(d, { size: 21 }), spacing: { after: 0, line: 264 } })) }),
      ] })],
    }));
    if (i < steps.length - 1) out.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 0, after: 0 }, children: [new TextRun({ text: "▼", color: "2E75B6", size: 22 })] }));
  });
  return out;
}

// ---------- content ----------
const C = [];

// Title page
C.push(
  new Paragraph({ spacing: { before: 2400, after: 200 }, alignment: AlignmentType.CENTER, children: [new TextRun({ text: "HỆ THỐNG HỖ TRỢ TUYỂN DỤNG", size: 28, bold: true, color: "595959" })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 200 }, children: [new TextRun({ text: "MODULE 1 — TRÍCH XUẤT THÔNG TIN CV", size: 40, bold: true, color: "1F4E79" })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 600 }, children: [new TextRun({ text: "Pipeline triển khai · Fine-tune mô hình · Knowledge Base & Knowledge Graph", size: 28, italics: true })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 120 }, children: [new TextRun({ text: "Tài liệu demo nội bộ (bản nháp để nắm luồng trước khi viết báo cáo)", size: 24 })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 120 }, children: [new TextRun({ text: "Mã nguồn: github.com/long20102004/recruit_system — nhánh hocnv/DO-06", size: 22 })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 120 }, children: [new TextRun({ text: "Cập nhật: 05/11/2026", size: 22 })] }),
);

// Reading guide + TOC
C.push(
  new Paragraph({ children: [new PageBreak()] }),
  new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("Cách đọc tài liệu này")] }),
  P("Tài liệu đi theo đúng khung 6 chương mà giảng viên yêu cầu, nhưng nhấn mạnh ba phần cần nắm trước: **(1) luồng xử lý một CV từ file PDF tới JSON**, **(2) cách fine-tune mô hình ngôn ngữ nhỏ cho việc trích xuất**, **(3) Knowledge Base (KB) và Knowledge Graph (KG) được xây dựng ra sao và dùng vào việc gì**. Mỗi phần quan trọng đều kèm đoạn code thật trong repo (đường dẫn ghi ở tiêu đề đoạn code) để có thể mở ra đối chiếu."),
  table(["Yêu cầu của giảng viên", "Ở đâu trong tài liệu"], [
    ["Đặt tên hệ thống; tổng quan cái gì", "Chương 1"],
    ["Kiến trúc hệ thống", "Chương 2"],
    ["Thử nghiệm, so sánh nhiều mô hình trên nhiều tập dữ liệu", "Chương 3 (+ khoảng trống ở Phụ lục A)"],
    ["Knowledge Base xây từ nhiều nguồn + sách PDF; Neo4j KB1/KB2/gộp; show KB; cập nhật KB", "Chương 4"],
    ["KB + RAG hoạt động thế nào", "Mục 4.8"],
    ["Cấu trúc + luồng hoạt động; code + output cụ thể", "Chương 5"],
    ["Cài đặt", "Chương 6"],
  ], [5600, 3426]),
  gap(),
  box("Lưu ý trạng thái", [
    "KB đã được xây lại hoàn toàn từ nguồn bên ngoài (feature 009, Chương 4); số liệu KB là của bản build ngày " + KB.date + ".",
    "Neo4j (KB1 + KB2), nguồn sách PDF và so sánh 5 mô hình × 4 tập dữ liệu đã được bổ sung (feature 010). Phụ lục A ghi trạng thái từng yêu cầu; các ô cần GPU chưa chạy được ghi \"chờ chạy\".",
  ]),
  new Paragraph({ children: [new PageBreak()] }),
  new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("Mục lục")] }),
  new TableOfContents("Mục lục", { hyperlink: true, headingStyleRange: "1-3" }),
  P("(Trong Word: chuột phải vào mục lục → Update Field để cập nhật số trang.)", { alignment: AlignmentType.LEFT }),
);

// ===== Chapter 1 =====
C.push(H1("Chương 1. Tổng quan"));
C.push(H2("1.1. Bài toán"));
C.push(P("Nhà tuyển dụng nhận CV ở dạng PDF với bố cục rất khác nhau: một cột, hai cột, có bảng, tiếng Việt hoặc tiếng Anh. Module 1 đọc một CV và trả về **một hồ sơ ứng viên có cấu trúc (JSON)** gồm thông tin liên hệ, học vấn, kinh nghiệm, dự án, kỹ năng, chứng chỉ, giải thưởng, ngoại ngữ. Module 2 dùng hồ sơ này để so khớp với mô tả công việc (JD)."));
C.push(table(["", "Mô tả"], [
  ["Đầu vào", "File PDF CV (text-based; CV dạng ảnh scan cần OCR — ngoài phạm vi hiện tại)"],
  ["Đầu ra", "CandidateProfile: personal_info, objective, education[], experience[], personal_projects[], skills[], certificates[], honours[], languages[]"],
  ["Ràng buộc", "Chạy được trên máy cá nhân (CPU) hoặc GPU miễn phí (Colab T4); dữ liệu CV không rời hệ thống; không bịa thông tin"],
], [1800, 7226]));
C.push(H2("1.2. Tên hệ thống (đề xuất)"));
C.push(P("Giảng viên yêu cầu đặt tên cho hệ thống. Đề xuất: **CVLens** — \"thấu kính\" đọc CV thành dữ liệu có cấu trúc. Module 1 có thể gọi là **CVLens Extractor**. (Tên chỉ là đề xuất, cần nhóm thống nhất.)"));
C.push(H2("1.3. Vì sao dùng mô hình ngôn ngữ nhỏ được fine-tune"));
C.push(P("Nhóm đã thử ba hướng:"));
C.push(B("**Luật (rule-based, regex + từ điển tiêu đề mục)**: rất nhanh (~9 ms/CV) và không bịa, nhưng không hiểu cấu trúc dòng — cùng một dòng kinh nghiệm có thể viết \"Chức danh, Công ty, Ngày\" hoặc \"Công ty | Chức danh | Ngày\". F1 trích xuất tên công ty chỉ 0,10 (Chương 3)."));
C.push(B("**LLM lớn trả phí (GPT, Gemini…)**: chính xác nhưng phải gửi CV (dữ liệu cá nhân) ra ngoài và tốn chi phí mỗi lượt — không phù hợp ràng buộc bảo mật."));
C.push(B("**LLM nhỏ mã nguồn mở + fine-tune (Qwen3-1.7B + LoRA)**: chạy cục bộ, hiểu được cấu trúc, học đúng quy ước nhãn của nhóm. Đây là hướng được chọn."));
C.push(P("Để bù điểm yếu của mô hình nhỏ (đôi khi bịa, lặp, sai tên gọi), pipeline thêm ba lớp **tất định** (deterministic) phía sau: hậu kiểm grounding (bỏ giá trị không có trong CV), Knowledge Base (chuẩn hoá tên kỹ năng, tên trường) và Knowledge Graph (quan hệ giữa các kỹ năng)."));
C.push(H2("1.4. Các phiên bản đã phát triển"));
C.push(table(["Feature", "Nội dung", "Kết quả chính"], [
  ["001", "Làm cứng AI service: hàng đợi, giới hạn token, không log dữ liệu CV", "Ổn định khi nhiều request"],
  ["002", "Hậu kiểm grounding", "Loại giá trị bịa (ví dụ kỹ năng không có trong CV)"],
  ["003", "Bộ đánh giá (eval harness) + tập val/val_swap", "Đo F1 từng trường, tỷ lệ bịa"],
  ["004–005", "Knowledge Base (PostgreSQL) + KG enrichment", "Chuẩn hoá kỹ năng/trường, suy ra kỹ năng ngầm"],
  ["006", "Fine-tune lại: mô hình v2", "Prompt chung train/serve, loss chỉ trên JSON"],
  ["007", "Dataset v3: CV thật + 200 CV sinh theo bố cục thật, đủ cấp độ", "Mô hình v3 (đang dùng)"],
  ["008", "Độ bền khi serve: chặn lặp, ghép JSON hỏng, lỗi 502", "20/20 CV thật trả kết quả"],
  ["009", "KB xây lại từ nguồn bên ngoài + chuẩn hoá output + ẩn KG", "813 kỹ năng, 387 trường, mọi dòng có nguồn"],
], [1100, 4700, 3226], { zebra: true }));

// ===== Chapter 2 =====
C.push(H1("Chương 2. Kiến trúc hệ thống"));
C.push(H2("2.1. Các thành phần"));
C.push(table(["Thành phần", "Công nghệ", "Vai trò"], [
  ["Frontend", "React 19 + TypeScript + Vite", "Tải CV lên, hiển thị hồ sơ"],
  ["Backend", "Java 21, Spring Boot 4, PDFBox, OpenFeign", "Nhận PDF, trích text, gọi AI service, trả CandidateProfile"],
  ["AI service", "Python, FastAPI, llama.cpp", "Chạy mô hình, hậu kiểm, KB/KG, trả JSON"],
  ["Mô hình", "Qwen3-1.7B + LoRA, lượng tử hoá GGUF Q4_K_M (~1,1 GB)", "Đọc text CV, sinh JSON"],
  ["Knowledge Base / KG", "Neo4j 5.26 (docker, cổng 7687) — kho chính; fallback CSV (PostgreSQL 16 còn hỗ trợ)", "KB1 (sách PDF) + KB2 (nguồn liên kết): kỹ năng, alias, quan hệ, trường học, nghề, mục sách"],
  ["Huấn luyện", "Google Colab T4, Unsloth, TRL", "Fine-tune LoRA, đánh giá, xuất GGUF"],
], [1700, 3300, 4026]));
C.push(H2("2.2. Sơ đồ kiến trúc"));
C.push(...flow([
  ["Người dùng / Frontend", "Upload file PDF CV", "E2EFDA"],
  ["Backend (Spring Boot)", "`POST /api/v1/cv/analyze-pdf` → PDFBox trích text (sắp theo vị trí)\nFeign client gọi AI service: `POST /api/v1/extract-cv {cv_text}`"],
  ["AI service (FastAPI)", "Dựng prompt v3 → llama.cpp sinh JSON (stream, có chặn lặp)\n→ parse/ghép JSON → hậu kiểm grounding"],
  ["Knowledge Base + KG (Neo4j)", "Link kỹ năng/trường về tên chuẩn (KB), suy quan hệ (KG: REQUIRES, PART_OF, RELATED_TO từ sách)\nChuẩn hoá output; phần KG chỉ trả khi `?include=kg`", "FFF2CC"],
  ["Backend → Frontend / Module 2", "CandidateProfile (JSON) — chỉ các trường trích từ CV", "E2EFDA"],
]));
C.push(caption("Hình 2.1. Luồng tổng thể của Module 1"));
C.push(H2("2.3. Hợp đồng API giữa Backend và AI service"));
C.push(...code(`@FeignClient(name = "ai-service", url = "\${ai.service.url:http://localhost:8000}")
public interface AiServiceClient {
    @PostMapping(value = "/api/v1/extract-cv", produces = "application/json")
    AiCvResponse extractCv(@RequestBody AiCvRequest request);
}`, "backend/src/main/java/recruit/demo/client/AiServiceClient.java"));
C.push(table(["Mã HTTP", "Ý nghĩa"], [
  ["200", "Thành công: {\"data\": CandidateProfile}"],
  ["400", "cv_text rỗng hoặc tham số include sai"],
  ["413", "CV quá dài so với context của mô hình"],
  ["502", "Mô hình trả kết quả rỗng / không phải JSON object"],
  ["503", "Mô hình chưa nạp hoặc đang bận quá thời gian chờ"],
  ["500", "Lỗi nội bộ (trả request_id, không lộ dữ liệu CV)"],
], [1500, 7526]));

// ===== Chapter 3 =====
C.push(H1("Chương 3. Dữ liệu, fine-tune và thử nghiệm mô hình"));
C.push(H2("3.1. Ý tưởng fine-tune"));
C.push(P("Mô hình gốc Qwen3-1.7B đã biết đọc tiếng Việt/tiếng Anh nhưng không biết **quy ước nhãn** của hệ thống (trường nào lấy gì, chép nguyên văn, không dịch, ngày tháng giữ như CV…). Fine-tune dạy mô hình đúng một việc: nhận text CV, viết ra đúng một object JSON theo schema."));
C.push(P("Dùng **LoRA** (Low-Rank Adaptation): đóng băng trọng số gốc, chỉ học các ma trận nhỏ gắn vào các lớp attention/MLP (r = 16, ~70 MB). Nhờ vậy train được trên GPU T4 miễn phí trong ~40 phút. Sau khi train, adapter được **gộp** vào mô hình gốc và **lượng tử hoá 4-bit (GGUF Q4_K_M)** để chạy bằng llama.cpp trên CPU hoặc GPU."));
C.push(H2("3.2. Dữ liệu huấn luyện (dataset v3)"));
C.push(table(["Nguồn", "Số mẫu train", "Cách tạo nhãn"], [
  ["CV sinh theo bố cục thật (generated)", "368", "Hồ sơ hư cấu (Gemini/ChatGPT viết theo đặc tả) → 10 template HTML mô phỏng CV thật → PDF (LibreOffice) → text bằng chính PDFBox của backend. Nhãn = hồ sơ gốc (chính xác tuyệt đối)."],
  ["CV thật", "31 + 62 bản hoán đổi", "Nhãn cũ được \"căn\" về đúng text PDFBox (fuzzy ≥ 85), bỏ giá trị không tìm thấy; mỗi CV thêm 2 bản đổi tên công ty/trường (augment)."],
  ["CV tổng hợp cũ (silver)", "250", "Nhãn do LLM tạo, áp lại quy ước v3."],
  ["Dev (chọn checkpoint)", "45", "Tách riêng, không train"],
  ["Test CV thật", "20", "Khoá riêng, chưa từng dùng để train; gold do Claude gán nháp, người dùng duyệt"],
], [2400, 1500, 5126]));
C.push(P("Phân bố cấp độ của 200 CV sinh: junior 50, middle 60, senior 60, lead/architect 30 (CV thật ban đầu chủ yếu là intern/fresher). Mẫu dài nhất 3.869 token, không mẫu nào bị cắt (giới hạn 4.096)."));
C.push(box("Bảo mật dữ liệu CV", [
  "CV thật chỉ nằm trong thư mục bị git-ignore (`ai-service/data/`, `dataset/`), không commit, không gửi cho LLM bên ngoài; chỉ hồ sơ hư cấu được sinh bởi subagent.",
  "Log của service chỉ ghi số đếm, không ghi nội dung CV.",
], "E8F1FB", "2E75B6"));
C.push(H2("3.3. Định dạng một mẫu train"));
C.push(P("Mỗi mẫu = **prompt** (system + text CV) + **completion** (JSON đích). Prompt dùng ở lúc train và lúc serve là **cùng một hàm** — lỗi train/serve lệch prompt ở v1 là nguyên nhân chính khiến v1 bỏ sót các mục cuối CV."));
C.push(...code(`SYSTEM_PROMPT = """Trích xuất CV thành MỘT object JSON đúng schema bên dưới.
- Chỉ dùng thông tin có trong CV. Chép nguyên văn: không dịch, không tóm tắt...
- CV có thể là PDF hai cột nên các dòng bị xen kẽ: ghép đúng nội dung của từng mục...
- skills: mọi kỹ năng trong mục Kỹ năng, gồm TẤT CẢ các nhóm con...
- languages: CHỈ ngoại ngữ / ngôn ngữ tự nhiên ...
Schema: {"personal_info":{...},"education":[...],"experience":[...], ...}"""

def render_prompt(cv_text: str) -> str:
    return (f"<|im_start|>system\\n{SYSTEM_PROMPT}<|im_end|>\\n"
            f"<|im_start|>user\\n{cv_text.strip()}<|im_end|>\\n"
            f"<|im_start|>assistant\\n<think>\\n\\n</think>\\n\\n")   # model viết JSON từ đây`, "ai-service/app/services/prompt_v3.py (rút gọn)"));
C.push(H2("3.4. Quy trình huấn luyện (notebook Colab)"));
C.push(P("Notebook `ai-service/training/retrain_qwen3_v2.ipynb` chạy trên Colab T4. Các bước:"));
C.push(N("Build dataset trên máy: `python -m training.build_dataset_v3` → upload `data/retrain_v3/` lên Google Drive.", "numtrain"));
C.push(N("Cell [1]–[3]: cấu hình (`RUN_NAME=\"v3\"`, `EVAL=\"real\"`, `SERVE=True`), clone đúng nhánh code, kiểm tra prompt trong dataset trùng prompt serving.", "numtrain"));
C.push(N("Cell [4]: nạp Qwen3-1.7B 4-bit + gắn LoRA (r=16, alpha=32, 7 lớp chiếu).", "numtrain"));
C.push(N("Cell [5]–[6]: train 2 epoch (batch hiệu dụng 8, lr 2e-4, cosine), **loss chỉ tính trên phần JSON trả lời**; giữ checkpoint có dev loss thấp nhất.", "numtrain"));
C.push(N("Cell [7]–[8]: sinh dự đoán cho 20 CV thật và chấm điểm bằng eval harness.", "numtrain"));
C.push(N("Cell [9]: gộp adapter + xuất GGUF Q4_K_M lên Drive.", "numtrain"));
C.push(N("Cell [10]–[11]: chạy luôn API + Cloudflare tunnel để test qua HTTP.", "numtrain"));
C.push(...code(`model = FastLanguageModel.get_peft_model(
    model, r=16, lora_alpha=32, lora_dropout=0, bias="none",
    target_modules=["q_proj","k_proj","v_proj","o_proj","gate_proj","up_proj","down_proj"],
    use_gradient_checkpointing="unsloth", random_state=42)

trainer = SFTTrainer(model=model, train_dataset=train_ds, eval_dataset=dev_ds, args=SFTConfig(
    per_device_train_batch_size=2, gradient_accumulation_steps=4, num_train_epochs=2,
    learning_rate=2e-4, lr_scheduler_type="cosine", eval_steps=25, save_steps=25,
    load_best_model_at_end=True, metric_for_best_model="eval_loss", max_length=4096, ...))

# Chỉ tính loss trên JSON: phần system + CV bị che (label = -100)
trainer = train_on_responses_only(trainer,
    instruction_part="<|im_start|>user\\n",
    response_part="<|im_start|>assistant\\n<think>\\n\\n</think>\\n\\n")
trainer.train()
model.save_pretrained_gguf(f"{OUT_DIR}/gguf", tokenizer, quantization_method="q4_k_m")`, "ai-service/training/retrain_qwen3_v2.ipynb — cell [4]–[9] (rút gọn)"));
C.push(P("Kết quả lần train v3: dev loss giảm đều 0,0129 → 0,0026 (bước 25 → 175), checkpoint tốt nhất ở bước 175."));
C.push(H2("3.5. Cách đánh giá"));
C.push(B("**Tập dữ liệu**: `val` (99 CV tổng hợp), `val_swap` (99 CV cùng nội dung nhưng đổi tên công ty/trường — kiểm tra mô hình có học vẹt tên không), `test_real` (20 CV thật)."));
C.push(B("**Chỉ số**: F1 theo từng trường danh sách (company, school, skills, project, certificates, honours, languages), độ chính xác trường liên hệ, **tỷ lệ bịa** (giá trị không có trong CV), độ trễ."));
C.push(B("**Biến thể**: A = output thô của mô hình; B = + hậu kiểm grounding (cách hệ thống chạy thật); C = + KG."));
C.push(H2("3.6. So sánh các mô hình"));
C.push(P("5 mô hình × 4 tập dữ liệu, chấm cùng một bộ đánh giá (biến thể B = output + hậu kiểm). **Rule-based**: luật + regex của backend, không dùng mô hình. **Qwen3-1.7B gốc**: mô hình chưa fine-tune, cùng prompt v3 (zero-shot) — cho thấy fine-tune mang lại bao nhiêu. **v1, v2, v3**: ba lần fine-tune (Chương 3.2–3.4). Các LLM chạy bằng file GGUF qua đúng code serving (`eval/run_models.py`, notebook `eval_models_colab.ipynb`)."));
{
  const splits = CMP.splits, models = CMP.models;
  const mean = (cell) => { if (!cell) return null; const v = CMP.fields.filter(([f]) => f !== "experience.job_title").map(([f]) => cell[f]).filter((x) => x !== null && x !== undefined); return v.length ? v.reduce((a, b) => a + b, 0) / v.length : null; };
  C.push(table(["Mô hình", "val (99 CV tổng hợp)", "val_swap (99, đổi tên)", "dev (45, bố cục thật)", "test_real (20 CV thật)"],
    models.map((m) => [CMP.label[m], ...splits.map((sp) => fmt(mean(CMP.table[m + "|" + sp])))]),
    [2226, 1700, 1700, 1700, 1700], { zebra: true }));
  C.push(caption("Bảng 3.1. F1 trung bình 7 trường (company, school, skills, project, certificates, honours, languages)"));
  C.push(img("chart_mean_f1.png", 600));
  C.push(caption("Hình 3.1. F1 trung bình theo mô hình và tập dữ liệu"));
  C.push(P("Bảng 3.2 — từng trường trên **20 CV thật** (thước đo quan trọng nhất):"));
  C.push(table(["Trường (F1)", ...models.map((m) => CMP.label[m])],
    CMP.fields.map(([f, name]) => [name, ...models.map((m) => fmt((CMP.table[m + "|test_real"] || {})[f]))]),
    [1926, 1420, 1420, 1420, 1420, 1420], { zebra: true }));
  C.push(caption("Bảng 3.2. 20 CV thật chưa từng dùng để train"));
  C.push(img("chart_test_real_fields.png", 600));
  C.push(caption("Hình 3.2. F1 từng trường trên 20 CV thật"));
  const pending = Object.entries(CMP.origin).filter(([, o]) => !o).map(([k]) => k.replace("|", " / "));
  C.push(P("Nguồn số liệu: ô chạy lại trên GPU bằng notebook so sánh được ưu tiên; các ô còn lại lấy từ lần đo trước (val/val_swap của v1, v2 và rule-based theo spec 003/006; v3 theo notebook train; test_real theo spec 007/008). Thời gian xử lý: rule-based ~9 ms/CV (CPU); LLM ~8–10 s/CV trên GPU T4, ~40–70 s/CV trên CPU." + (pending.length ? " Ô \"chờ chạy\" (" + pending.join(", ") + ") cần chạy notebook `eval_models_colab.ipynb` trên Colab." : "")));
}
C.push(H3("Nhận xét"));
C.push(B("Luật không thay được mô hình: trên CV thật rule-based chỉ đạt F1 trung bình ~0,32 (skills 0,34, project 0,26), kém LLM v3 hơn 30 điểm; trên CV tổng hợp kém 10–80 điểm ở mọi trường cấu trúc."));
C.push(B("Từ v1 → v3, điểm trên CV tổng hợp đã gần tuyệt đối, nhưng trên CV thật vẫn thấp hơn rõ (company 0,72, skills 0,73): khoảng cách giữa dữ liệu train và bố cục CV thật vẫn còn. v3 tốt nhất ở các trường Module 2 dùng nhiều (school, skills, languages, phone); kém v2 ở job_title."));
C.push(B("Lỗi còn lại tập trung ở CV dài, hai cột, nhiều dự án: 4/20 CV sinh output thoái hoá (lặp hoặc đóng ngoặc sớm). Feature 008 xử lý ở khâu serve (Chương 5); lần train sau cần thêm CV hai cột nhiều dự án."));

// ===== Chapter 4 =====
C.push(H1("Chương 4. Knowledge Base và Knowledge Graph"));
C.push(H2("4.1. KB và KG là gì trong hệ thống này"));
C.push(P("**Knowledge Base (KB)** là \"từ điển\" có cấu trúc: danh sách kỹ năng chuẩn (mỗi kỹ năng có ID, tên chuẩn, nhóm) kèm các cách viết khác (alias), danh sách trường đại học/cao đẳng kèm tên viết tắt, danh sách nghề nghiệp. **Knowledge Graph (KG)** là phần quan hệ giữa các thực thể trong KB, ví dụ `Spring Boot —REQUIRES→ Java`, `ASP.NET Core —PART_OF→ .NET`."));
C.push(P("Mô hình chỉ chép đúng chữ trong CV, nên cùng một kỹ năng có thể ra \"ReactJS\", \"React.js\", \"react\". KB đưa tất cả về **một tên chuẩn** (\"React\"); KG cho biết kỹ năng nào kéo theo kỹ năng nào. Đây là lớp tất định, nhanh (~5 ms/CV) và giải thích được (mỗi kết luận chỉ ra nguồn)."));
C.push(H2("4.2. Nguồn dữ liệu (feature 009)"));
C.push(P("KB được xây **chỉ từ nguồn công khai có giấy phép mở**; mỗi dòng dữ liệu mang cột `source` trỏ về nguồn gốc để trích dẫn được. Bản KB cũ (feature 004) dựng từ nhãn dữ liệu train + đề xuất của LLM nên không trích dẫn được — đã được thay thế."));
C.push(table(["Nguồn", "Giấy phép", "Lấy gì", "Dùng cho"], [
  ["Stack Overflow Developer Survey 2024–2026 (Stack Exchange, Inc.)", "ODbL 1.0 / DbCL 1.0", "Danh sách công nghệ theo câu hỏi khảo sát (ngôn ngữ, CSDL, cloud, framework web, IDE, công cụ test, bảo mật…)", "Tên chuẩn kỹ năng + nhóm"],
  ["Stack Overflow tags (Stack Exchange, Inc. và cộng đồng)", "CC BY-SA 4.0", "Tag đã phổ biến (≥ 500 câu hỏi) + tag đồng nghĩa, cho thư viện/công cụ khảo sát không hỏi (Spring MVC, Lombok, AutoMapper…)", "Bổ sung kỹ năng, alias"],
  ["Wikidata (Wikimedia)", "CC0 1.0", "Q-id, nhãn/alias tiếng Anh + tiếng Việt, quan hệ P277 (programmed in), P361 (part of), P527 (has part); trường đại học/cao đẳng Việt Nam + tên viết tắt (P1813)", "Alias, bổ sung thư viện/khái niệm, quan hệ KG, alias trường"],
  ["GitHub Linguist", "MIT", "Ngôn ngữ lập trình + alias chính thức (C# ↔ csharp…)", "Alias ngôn ngữ"],
  ["ESCO v1.2.1 (Ủy ban châu Âu)", "CC BY 4.0", "Kỹ năng chung (transversal) + nghề ICT (ISCO 25, 35) kèm nhãn thay thế", "Kỹ năng mềm, chức danh"],
  ["Wikipedia tiếng Việt, \"Danh sách trường đại học, học viện và cao đẳng tại Việt Nam\" (rev. 75654510)", "CC BY-SA 4.0", "244 trường/học viện + 38 trường thành viên", "Tên chính thức trường"],
], [2500, 1300, 3326, 1900], { zebra: true }));
C.push(caption("Bảng 4.1. Nguồn của KB — trích dẫn đầy đủ trong ai-service/kb/seed/SOURCES.md"));
C.push(H2("4.3. Quy trình xây KB"));
C.push(...flow([
  ["1. Tải nguồn (fetch)", "`python -m kb.fetch_sources` tải từng nguồn qua HTTP/API (User-Agent ghi tên dự án)\n→ lưu nguyên văn vào `kb/sources/` + `MANIFEST.json` (URL, ngày tải, phiên bản, SHA-256, giấy phép)"],
  ["2. Dựng seed (build, offline)", "`python -m kb.build_external` chỉ đọc snapshot (tái lập được, không cần mạng)\n→ chọn kỹ năng, gộp alias, sinh quan hệ, loại alias mơ hồ / trùng / chu trình"],
  ["3. File seed CSV", "`kb/seed/skills.csv`, `skill_aliases.csv`, `skill_edges.csv`, `universities.csv`, `university_aliases.csv`, `job_titles.csv` — mỗi dòng có `source`; kèm `SOURCES.md`"],
  ["4. Nạp vào PostgreSQL", "`python -m kb.load` (kiểm tra ràng buộc: không alias trùng, không quan hệ tự trỏ/chu trình) → bảng skill, skill_alias, skill_edge, university…"],
  ["5. AI service đọc KB khi khởi động", "PostgreSQL (`KB_DSN`) hoặc fallback CSV; dựng bộ link kỹ năng + trường trong RAM", "FFF2CC"],
]));
C.push(caption("Hình 4.1. Pipeline xây dựng KB từ nguồn bên ngoài"));
C.push(P("Các bước chính khi dựng:"));
C.push(B("**Chọn kỹ năng**: mọi lựa chọn công nghệ của Stack Overflow (bỏ \"Other\", câu trả lời không phải công nghệ); nhóm kỹ năng suy từ câu hỏi khảo sát (câu \"Databases\" → nhóm Database…)."));
C.push(B("**Bổ sung từ Wikidata** (thư viện, khái niệm khảo sát không hỏi như Hibernate, OOP, MVC): tìm Q-id cho các từ vựng kỹ năng xuất hiện trong **CV tổng hợp/hư cấu** (không bao giờ dùng CV thật) và chỉ nhận item thuộc lớp phần mềm/lập trình/khái niệm tin học (kiểm tra bằng SPARQL)."));
C.push(B("**Bổ sung từ Stack Overflow tags**: với từ vựng mà khảo sát và Wikidata đều không có (Wikidata không có item cho Spring MVC, Lombok…), thử các cách viết tag (spring-mvc, springmvc…), chỉ nhận tag có ≥ 500 câu hỏi; tag đồng nghĩa (nodejs → node.js) thành alias."));
C.push(B("**Alias**: nhãn và alias tiếng Anh/tiếng Việt của Wikidata, alias Linguist, nhãn thay thế ESCO; khoá so khớp chuẩn hoá (bỏ dấu câu, chữ thường). Alias trỏ tới hai kỹ năng khác nhau bị loại (mơ hồ)."));
C.push(B("**Quan hệ (KG)**: chỉ lấy từ thuộc tính Wikidata — P277 programmed in → `REQUIRES` (chỉ với framework/thư viện: Spring Boot → Java; công cụ như Docker không suy ra ngôn ngữ cài đặt của nó), P361 part of → `PART_OF`, P527 has part → `PART_OF` đảo chiều; chỉ giữ khi hai đầu đều là kỹ năng trong KB, loại chu trình."));
C.push(B("**Trường học**: tên chính thức theo Wikipedia; Wikidata bổ sung trường cao đẳng, tên tiếng Anh, tên viết tắt (P1813); sinh biến thể chính tả của tên đã công bố (Ho Chi Minh City ↔ HCMC, \"Cao đẳng X\" ↔ \"X College\")."));
C.push(...code(`id,name,category,source,source_id                    # skills.csv
568,PostgreSQL,Database,stackoverflow-2026:Databases,Q192490
608,React,Framework/Library,stackoverflow-2026:WebFramework,Q19399674
695,Spring Boot,Framework/Library,stackoverflow-2026:WebFramework,Q98731994

src_id,rel,dst_id,source                             # skill_edges.csv — quan hệ KG
695,REQUIRES,361,wikidata:Q98731994:P277   # Spring Boot -> Java

university_id,alias_key,source                       # university_aliases.csv
11,ptit,wikidata:Q10771881`, "ai-service/kb/seed/*.csv — ví dụ dữ liệu có nguồn"));
C.push(H3("Quy mô KB (bản build " + KB.date + ")"));
C.push(table(["Bảng", "Số dòng", "Theo nguồn"], KB.table, [2200, 1300, 5526], { zebra: true }));
C.push(P(KB.coverage_note));
C.push(H2("4.4. KB1 — tri thức trích từ sách PDF"));
C.push(P("Giảng viên yêu cầu KB có nguồn từ **file sách PDF** (KB1). Hai sách CNTT có giấy phép mở được chọn: **Pro Git** (S. Chacon, B. Straub, 2nd ed., CC BY-NC-SA 3.0) và **Think Python** (A. B. Downey, 2nd ed., CC BY-NC 3.0). Lệnh `python -m kb.books`:"));
C.push(N("Tải PDF chính thức vào cache cục bộ (không commit); ghi URL, SHA-256 và giấy phép vào MANIFEST.", "numbook"));
C.push(N("Đọc trang mục lục bằng `pdftotext` (Poppler), dựng cây **sách → chương → mục** kèm số trang; tự dò độ lệch giữa số trang in và số trang PDF.", "numbook"));
C.push(N("Đọc text từng mục, đếm số lần nhắc tới mỗi **kỹ năng của KB2** (tên chuẩn một từ như \"Python\" so khớp phân biệt hoa/thường; alias nhiều từ so khớp không phân biệt) → quan hệ `MENTIONS`.", "numbook"));
C.push(N("Hai kỹ năng cùng được nhắc trong ≥ 2 mục của một cuốn sách → quan hệ `RELATED_TO` (trọng số = số mục).", "numbook"));
C.push(N("Ghi `kb/sources/kb1_books.json`: chỉ tiêu đề mục, số trang và số đếm — **không chép văn bản sách**.", "numbook"));
{
  const rows = KB1.books.map((b) => { const ms = new Set(); b.sections.forEach((x) => Object.keys(x.mentions || {}).forEach((k) => ms.add(k)));
    return [b.title.split(":")[0], (b.authors || []).join(", "), b.licence, String(b.sections.length), String(ms.size)]; });
  C.push(table(["Sách", "Tác giả", "Giấy phép", "Chương + mục", "Kỹ năng được nhắc"], rows, [2000, 2100, 1900, 1400, 1626]));
  C.push(caption("Bảng 4.3. KB1 — " + KB1.related.length + " quan hệ RELATED_TO (ví dụ Git–GitHub cùng xuất hiện trong 48 mục, Git–Linux 28 mục)"));
}
C.push(...code(`def count_mentions(text, finder):
    """Đếm (tên chuẩn, vị trí) phân biệt; tên một từ phân biệt hoa/thường."""
    positions = defaultdict(set)
    for pattern, name in finder._case_words:          # "Python", "Git" (không bắt "word", "lists")
        for m in pattern.finditer(text):
            positions[name].add(m.start())
    for pattern in finder._batched_long_patterns:     # alias nhiều từ / có ký tự đặc biệt
        for m in pattern.finditer(normalized):
            positions[finder._norm_to_canonical[m.group(1)]].add(char_map[m.start()])
    return {name: len(p) for name, p in positions.items()}`, "ai-service/kb/books.py (rút gọn)"));
C.push(H2("4.5. Neo4j — gộp KB1 và KB2 thành KB"));
C.push(P("Neo4j là kho KG chính (docker `infra/kg`, Neo4j 5.26 Community). Lệnh `python -m kb.neo4j_load` nạp ba bước, mọi node/quan hệ mang thuộc tính `source` trỏ về nguồn:"));
C.push(...flow([
  ["KB2 — nguồn liên kết", "seed CSV (Chương 4.2–4.3) → node `Skill`, `Alias`, `Category`, `University`, `UniversityAlias`, `JobTitle` (nhãn phụ `:KB2`)\nquan hệ `ALIAS_OF`, `IN_CATEGORY`, `REQUIRES`, `PART_OF`"],
  ["KB1 — sách PDF", "`kb1_books.json` → node `Book`, `Section` (nhãn phụ `:KB1`), quan hệ `HAS_SECTION` (cây mục lục), `(Section)-[:MENTIONS {count}]->(Skill)`", "FBE5D6"],
  ["Gộp KB1 + KB2", "`(Skill)-[:RELATED_TO {weight, source}]->(Skill)` từ đồng xuất hiện trong sách\n`(Section)-[:ABOUT]->(Skill)` khi tiêu đề mục chính là tên/alias kỹ năng", "FFF2CC"],
  ["AI service", "`KnowledgeBase.from_neo4j()` đọc lại kỹ năng, alias, quan hệ, trường → bộ link trong RAM\nThứ tự: Neo4j (`NEO4J_URI`) → PostgreSQL → CSV", "E2EFDA"],
]));
C.push(caption("Hình 4.2. Luồng nạp và gộp KB1 + KB2 vào Neo4j"));
C.push(...code(`// KB2: kỹ năng + nhóm (UNWIND theo lô; MERGE nên chạy lại không sinh trùng)
UNWIND $batch AS row
MERGE (s:Skill {id: row.id})
SET s:KB2, s.name = row.name, s.category = row.category, s.source = row.source, s.source_id = row.source_id
WITH s, row WHERE row.category <> ''
MERGE (c:Category {name: row.category}) SET c:KB2
MERGE (s)-[:IN_CATEGORY]->(c)

// KB2: alias → kỹ năng
UNWIND $batch AS row
MERGE (a:Alias {key: row.key}) SET a:KB2, a.surface = row.surface, a.source = row.source
WITH a, row MATCH (s:Skill {id: row.skill_id})
MERGE (a)-[:ALIAS_OF]->(s)

// KB1: mục sách nhắc tới kỹ năng của KB2
UNWIND $batch AS row
MATCH (s:Section {id: row.section_id}) MATCH (sk:Skill {name: row.skill_name})
MERGE (s)-[m:MENTIONS]->(sk) SET m.count = row.count, m.source = row.source

// Gộp KB1 + KB2: quan hệ giữa kỹ năng KB2, bằng chứng từ sách
UNWIND $batch AS row
MATCH (sa:Skill {name: row.a}) MATCH (sb:Skill {name: row.b})
MERGE (sa)-[r:RELATED_TO {source: row.source}]->(sb) SET r.weight = row.weight`, "ai-service/kb/neo4j_load.py — các câu Cypher chính"));
C.push(table(["Node", "Số lượng", "Quan hệ", "Số lượng"],
  (() => { const n = Object.entries(NEO.nodes), r = Object.entries(NEO.rels); const out = [];
    for (let k = 0; k < Math.max(n.length, r.length); k++) out.push([n[k] ? n[k][0] : "", n[k] ? String(n[k][1]) : "", r[k] ? r[k][0] : "", r[k] ? String(r[k][1]) : ""]);
    return out; })(), [2400, 2113, 2400, 2113], { zebra: true }));
C.push(caption("Bảng 4.4. Nội dung Neo4j sau khi nạp và gộp (đếm thực tế)"));
C.push(img("kg_subgraph.png", 600));
C.push(caption("Hình 4.3. Đồ thị con thật lấy từ Neo4j: KB2 (xanh) — REQUIRES từ Wikidata; KB1 (cam) — sách Pro Git, mục sách MENTIONS kỹ năng; RELATED_TO là phần gộp"));
C.push(...code(`// Kỹ năng liên quan tới Git theo sách (KB1), kèm nguồn
MATCH (g:Skill {name: 'Git'})-[r:RELATED_TO]-(k:Skill)
RETURN k.name, r.weight, r.source ORDER BY r.weight DESC LIMIT 5;
// → GitHub 48 book:progit · Linux 28 · Windows 22 · C 22 · Ruby 15

// Mục sách nói nhiều nhất về Python
MATCH (b:Book)-[:HAS_SECTION*]->(s:Section)-[m:MENTIONS]->(:Skill {name: 'Python'})
RETURN b.title, s.title, s.page, m.count ORDER BY m.count DESC LIMIT 3;`, "Truy vấn mẫu trong Neo4j Browser (http://localhost:7474)"));
C.push(P("Kiểm chứng: KB đọc từ Neo4j cho kết quả **giống hệt** KB đọc từ CSV (813 kỹ năng, 132 quan hệ REQUIRES/PART_OF, 387 trường, cùng kết quả link trên bộ từ thử và tên trường, cùng 49 kỹ năng có RELATED_TO)."));
C.push(H2("4.6. Lược đồ dữ liệu"));
C.push(img("kg_schema.png", 600));
C.push(caption("Hình 4.4. Lược đồ KG trong Neo4j (số lượng thực tế)"));
C.push(P("Bảng tương ứng khi dùng CSV / PostgreSQL (dự phòng):"));
C.push(...code(`CREATE TABLE skill        (id INT PRIMARY KEY, name TEXT UNIQUE, category_id INT, source TEXT);
CREATE TABLE skill_alias  (alias_key TEXT PRIMARY KEY, skill_id INT REFERENCES skill, surface TEXT, source TEXT);
CREATE TABLE skill_edge   (src_id INT, rel TEXT CHECK (rel IN ('PART_OF','REQUIRES')), dst_id INT, source TEXT,
                           PRIMARY KEY (src_id, rel, dst_id), CHECK (src_id <> dst_id));
CREATE TABLE university        (id INT PRIMARY KEY, name TEXT UNIQUE, source TEXT);
CREATE TABLE university_alias  (alias_key TEXT PRIMARY KEY, university_id INT, surface TEXT, source TEXT);
CREATE TABLE job_title    (id INT PRIMARY KEY, name TEXT UNIQUE, alias_key TEXT UNIQUE, source TEXT);`, "ai-service/kb/sql/001_schema.sql + 002_source.sql (rút gọn)"));
C.push(H2("4.7. Vai trò của KB và KG khi xử lý một CV"));
C.push(H3("KB: chuẩn hoá output của mô hình"));
C.push(P("Sau hậu kiểm, mỗi kỹ năng (và từng mục `tech_stack` của dự án) được link vào KB theo thứ tự: khớp chính xác → khớp alias đã chuẩn hoá → biến thể chính tả (bỏ số phiên bản, phần trong ngoặc, đuôi chung như \"Core\": \"JavaScript(ES6+)\" → JavaScript) → nối bằng \"-\"/\"+\" (\"Nodejs-Expressjs\") → tách cụm (\"Java/Spring\") → khớp mờ (fuzzy ≥ 90, không áp dụng cho kỹ năng mềm). Kỹ năng kỹ thuật link được thay bằng **tên chuẩn**; kỹ năng mềm và kỹ năng không có trong KB **giữ nguyên như CV**. Tên trường link được thay bằng **tên chính thức**."));
C.push(...code(`def _normalize_skill_list(items, linker):
    expanded = []
    for item in items:
        links = linker.link_many([item])          # exact → alias → biến thể → tách → fuzzy
        if links and all(l.skill_id is not None for l in links) and not all_soft_skills(links):
            expanded.extend(l.name for l in links) # "ReactJS" → "React"
        else:
            expanded.append(item)                  # không có trong KB / kỹ năng mềm: giữ như CV
    return dedupe_casefold(expanded)

# education[].school: "PTIT" → "Học viện Công nghệ Bưu chính Viễn thông"
res = kb.link_school(edu["school"])
if res: edu["school"] = res[1]`, "ai-service/app/kb/normalize.py (rút gọn)"));
C.push(H3("KG: suy luận, chạy ngầm và ẩn khỏi output mặc định"));
C.push(P("KG chạy trên mọi request (`KG_ENABLED=true`) nhưng kết quả **không trả ra mặc định**, vì Module 2 tự làm việc so khớp. Khi cần demo hoặc phân tích, gọi `POST /api/v1/extract-cv?include=kg` để nhận thêm:"));
C.push(table(["Trường", "Ý nghĩa"], [
  ["skills_normalized", "Từng kỹ năng thô → ID/tên/nhóm trong KB và cách khớp (exact/normalized/split/fuzzy/unlinked)"],
  ["implied_skills", "Kỹ năng suy ra qua quan hệ, kèm đường suy luận (via). Ví dụ CV có Spring Boot → suy ra Java (REQUIRES)"],
  ["related_skills", "Kỹ năng liên quan theo sách (KB1, RELATED_TO), kèm trọng số. Ví dụ CV có Git → GitHub (48), Linux (28)"],
  ["skills_detected", "Kỹ năng của mô hình ∪ kỹ năng KB tìm thấy khi quét toàn bộ text CV (recall 0,97 trên 20 CV thật)"],
  ["education[].school_normalized", "ID + tên chính thức của trường"],
  ["flags", "Cảnh báo: kỹ năng chưa có trong KB, thiếu liên hệ, đã loại giá trị không có trong CV…"],
], [2700, 6326]));
C.push(...code(`queue = deque((sid, 0) for sid in linked_ids)        # kỹ năng đã link trong CV
while queue:
    curr, depth = queue.popleft()
    for rel, dst in kb.edges.get(curr, []):
        if rel in ("REQUIRES", "PART_OF") and dst not in visited:
            visited.add(dst)
            implied.append({"name": kb.skills[dst][0],
                            "via": [{"from": kb.skills[curr][0], "rel": rel}]})
            queue.append((dst, depth + 1))`, "ai-service/app/kg/enrich.py — duyệt đồ thị theo chiều rộng (rút gọn)"));
C.push(H3("Cập nhật KB"));
C.push(P("Giảng viên hỏi \"muốn cập nhật KB thì làm sao\". Quy trình:"));
C.push(N("Chạy lại `python -m kb.fetch_sources --refresh` để tải phiên bản mới của các nguồn (ví dụ khảo sát Stack Overflow năm sau, Wikidata mới). Thêm nguồn mới = thêm một hàm tải + một dòng trong MANIFEST.", "numupd"));
C.push(N("`python -m kb.build_external` dựng lại seed; xem diff CSV trong git để duyệt thay đổi (kỹ năng mới, alias bị loại do trùng).", "numupd"));
C.push(N("`python -m kb.books` khi có sách mới hoặc KB2 đổi (đếm lại MENTIONS/RELATED_TO).", "numupd"));
C.push(N("`python -m kb.neo4j_load --reset` nạp lại KB1 + KB2 và gộp trong Neo4j (MERGE, có ràng buộc unique); khởi động lại AI service. Mô hình không cần train lại.", "numupd"));
C.push(N("Đo lại tỷ lệ link trên tập CV kiểm thử (script đo trong spec 009) trước khi đưa vào dùng.", "numupd"));
C.push(H2("4.8. KB và RAG"));
C.push(P("**RAG (Retrieval-Augmented Generation)** là kỹ thuật: trước khi mô hình sinh câu trả lời, hệ thống **truy xuất** (retrieve) tri thức liên quan từ kho và **đưa vào prompt** để mô hình dựa vào đó mà sinh."));
C.push(P("Trong hệ thống hiện tại, KB được dùng **sau** khi mô hình sinh (chuẩn hoá + suy luận), **không** đưa vào prompt — tức là chưa phải RAG. Lý do: nhiệm vụ trích xuất yêu cầu chép nguyên văn từ CV; đưa tên chuẩn vào prompt dễ khiến mô hình chép tên từ KB thay vì từ CV (bịa). Nhóm đã thử một biến thể gần RAG ở feature 006 (biến thể D, `build_dataset --hints`): quét text CV tìm ứng viên kỹ năng trong KB rồi đưa danh sách gợi ý vào prompt; biến thể này chưa được train/đánh giá đầy đủ."));
C.push(box("Nếu bắt buộc có KB + RAG (đề xuất)", [
  "Retrieve: quét text CV bằng KB (CandidateSkillFinder đã có) → top-k kỹ năng/trường ứng viên.",
  "Augment: thêm vào prompt dòng \"Gợi ý từ KB: …\" (đã có sẵn tham số `candidate_skills` trong `render_prompt`).",
  "Generate: mô hình vẫn chỉ được chép giá trị có trong CV; hậu kiểm grounding loại bỏ giá trị lấy từ gợi ý mà không có trong CV.",
  "Cần train lại với dataset có gợi ý (biến thể D) và so sánh với v3 trên 20 CV thật.",
]));

// ===== Chapter 5 =====
C.push(H1("Chương 5. Cấu trúc và luồng hoạt động chi tiết"));
C.push(P("Chương này đi theo một request thật, từng bước một, kèm code ở mỗi bước."));
C.push(H2("5.1. Bước 1 — Backend trích text từ PDF"));
C.push(...code(`public String extractTextFromPdf(MultipartFile file) {
    try (PDDocument document = Loader.loadPDF(file.getBytes())) {
        PDFTextStripper stripper = new PDFTextStripper();
        stripper.setSortByPosition(true);       // đọc theo vị trí: giữ thứ tự dòng của PDF hai cột
        return stripper.getText(document);
    }
}`, "backend/.../service/CvAnalysisService.java"));
C.push(H2("5.2. Bước 2 — Sinh JSON có chặn vòng lặp"));
C.push(P("Mô hình sinh theo kiểu stream (từng token). Bộ chặn lặp (`LoopGuard`) theo dõi JSON đang được viết và dừng ngay khi output thoái hoá: một chuỗi dài quá 2.000 ký tự, hoặc cùng một giá trị lặp 3 lần trong cùng một danh sách (trong 974 nhãn thật không có trường hợp hợp lệ nào như vậy). Phần JSON đã sinh được sửa lại và trả về, thay vì chờ tới trần 2.048 token."));
C.push(...code(`resp = state.llm(prompt=prompt, max_tokens=config.MAX_NEW_TOKENS, temperature=0.0,
                 stop=["<|im_end|>", "<|endoftext|>"], stream=True)
guard = LoopGuard(config.LOOP_MAX_STRING_CHARS, config.LOOP_MAX_REPEATS)
for chunk in resp:
    text = chunk["choices"][0]["text"]
    parts.append(text)
    if guard.feed(text):            # "long_string" | "repeated_value"
        reason = guard.reason
        break
...
if reason:
    raw_output = json.dumps(salvage(raw_output))   # cắt chuỗi dở, json_repair, bỏ phần tử trùng`, "ai-service/app/services/generator.py (rút gọn)"));
C.push(H2("5.3. Bước 3 — Parse JSON và ghép mảnh"));
C.push(P("Đôi khi mô hình đóng ngoặc `}` quá sớm, JSON bị tách thành nhiều mảnh. `merge_fragments` ghép lại: khoá cấp cao của mảnh sau bổ sung vào object chính; mảnh có dạng dự án/kinh nghiệm/học vấn được trả về đúng danh sách. Nhờ vậy 2/20 CV thật trước đây lỗi 502 nay trả đủ dữ liệu. Nếu vẫn không có nội dung → HTTP 502."));
C.push(H2("5.4. Bước 4 — Hậu kiểm grounding"));
C.push(...code(`def postprocess(data, cv_text):
    profile = normalize_profile(data, stats)              # đúng schema, đúng kiểu
    profile["skills"] = clean_skill_list(profile["skills"], stats)
    profile = ground_profile(profile, cv_text, stats)     # mọi giá trị phải tìm thấy trong CV
    return profile, stats`, "ai-service/app/postprocess/pipeline.py"));
C.push(B("Mọi chuỗi phải xuất hiện trong text CV (so khớp đã chuẩn hoá, fuzzy ≥ 85); không có → loại."));
C.push(B("Chức danh phải nằm gần tên công ty (200 ký tự trước / 300 ký tự sau); xa quá → đặt null."));
C.push(B("Số điện thoại, email phải có trong CV; kinh nghiệm ghi \"sinh viên\" bị loại khỏi experience."));
C.push(H2("5.5. Bước 5 — KB/KG và lắp response"));
C.push(...code(`raw_profile = deepcopy(data)                                   # sau hậu kiểm
enriched = enrich(data, kb, pp_stats, cv_text=cv_text)         # KG luôn chạy
base = {k: v for k, v in raw_profile.items() if k not in KG_FIELDS}
base = normalize_profile_with_kb(base, kb)                     # KB: tên chuẩn
if "kg" in include:  base |= {k: enriched[k] for k in KG_FIELDS}
if "raw" in include: base["raw_profile"] = raw_profile         # để đánh giá / đối chiếu
return {"data": base}`, "ai-service/app/api/routes.py (rút gọn)"));
C.push(H2("5.6. Ví dụ output cụ thể"));
C.push(P("CV tổng hợp (không phải dữ liệu thật) dùng trong notebook kiểm thử:"));
C.push(...code(`NGUYEN VAN SYNTHETIC
syn.dev@example.test | 0900000099 | https://github.com/synthetic-dev
EXPERIENCE
Công ty TNHH Synthetic Software      October 2025 - May 2026
Backend Developer
• Developed RESTful APIs using Spring Boot and PostgreSQL
EDUCATION
Học viện Công nghệ Bưu chính Viễn thông      2022 - 2026
TECHNICAL SKILL
● Backend: Spring Boot, ReactJS, Postgress, Docker
LANGUAGES
● English: TOEIC 750`, "Đầu vào: text CV"));
C.push(...code(`{"data": {
  "personal_info": {"full_name": "NGUYEN VAN SYNTHETIC", "email": "syn.dev@example.test",
                    "phone": "0900000099", "github_url": "https://github.com/synthetic-dev"},
  "objective": null,
  "education": [{"school": "Học viện Công nghệ Bưu chính Viễn thông", "major": null,
                 "start_year": 2022, "end_year": 2026, "gpa": null}],
  "experience": [{"company": "Công ty TNHH Synthetic Software", "job_title": "Backend Developer",
                  "start_date": "October 2025", "end_date": "May 2026",
                  "description": ["Developed RESTful APIs using Spring Boot and PostgreSQL"]}],
  "personal_projects": [],
  "skills": ["Spring Boot", "React", "PostgreSQL", "Docker"],     <- "ReactJS", "Postgress" đã chuẩn hoá
  "certificates": [], "honours": [],
  "languages": [{"language": "English", "note": "TOEIC 750"}]
}}`, "Đầu ra mặc định: POST /api/v1/extract-cv"));
C.push(...code(`"skills_normalized": [{"raw": "Spring Boot", "name": "Spring Boot", "category": "Framework/Library", "method": "exact"},
                      {"raw": "ReactJS", "name": "React", "category": "Framework/Library", "method": "normalized"},
                      {"raw": "Postgress", "name": "PostgreSQL", "category": "Database", "method": "fuzzy"},
                      {"raw": "Docker", "name": "Docker", "category": "Cloud", "method": "exact"}],
"implied_skills": [{"name": "Java", "category": "Programming Language", "via": [{"from": "Spring Boot", "rel": "REQUIRES"}]},
                   {"name": "JavaScript", "category": "Programming Language", "via": [{"from": "React", "rel": "REQUIRES"}]}],
"skills_detected": [GitHub (text), Spring Boot (both), Spring Framework (text), PostgreSQL (both), Docker (both), React (model), ...],
"flags": []`, "Thêm khi gọi ?include=kg"));
C.push(P("Kết quả trên chạy bằng code chuẩn hoá và KG thật với KB bản " + KB.date + ". Lưu ý: `implied_skills` là gợi ý suy từ quan hệ \"programmed in\" của Wikidata, không phải bằng chứng ứng viên biết kỹ năng đó; với thư viện viết bằng nhiều ngôn ngữ, quan hệ có thể thừa (ví dụ PyTorch → C)."));

if (COLAB) {
  C.push(H2("5.7. Output thật qua service trên Colab (GPU) sau khi bổ sung KB/KG"));
  C.push(P("Service chạy bằng notebook `run_on_colab.ipynb` (commit " + COLAB.commit + ", GPU T4, KB đọc từ CSV kèm quan hệ KB1). Gọi `POST /api/v1/extract-cv?include=kg,raw` với 20 CV thật (chỉ báo cáo số đếm, không đưa nội dung CV thật vào tài liệu) và với CV tổng hợp ở mục 5.6."));
  C.push(table(["Chỉ số (20 CV thật)", "Giá trị"], COLAB.stats, [5000, 4026], { zebra: true }));
  C.push(caption("Bảng 5.1. Kết quả chạy service trên Colab"));
  C.push(...code(COLAB.synthetic_output, "Output thật cho CV tổng hợp (mục 5.6), ?include=kg — rút gọn các trường dài"));
}

// ===== Chapter 6 =====
C.push(H1("Chương 6. Cài đặt và triển khai"));
C.push(H2("6.1. Chạy trên máy cá nhân"));
C.push(...code(`# 1. Knowledge Graph (Neo4j trong docker, cổng 7687; mật khẩu trong infra/kg/.env)
docker compose -f infra/kg/docker-compose.yml --env-file infra/kg/.env up -d
cd ai-service && set -a && . ../infra/kg/.env && set +a
python -m kb.neo4j_load --uri bolt://localhost:7687 --user neo4j --password-env NEO4J_PASSWORD --reset

# 2. AI service (model v3, ~1,1 GB)
gdown 1mqmolAF-4nJXg1db89oHAYZKYlZ3CUcq -O merged_model/model-v3-q4_k_m.gguf
NEO4J_URI=bolt://localhost:7687 uvicorn main:app --port 8000

# 3. Backend
cd ../backend && ./mvnw spring-boot:run              # gọi AI service tại http://localhost:8000`, "Lệnh cài đặt"));
C.push(P("Trên CPU mỗi CV mất ~40–70 giây; trên GPU T4 ~8 giây."));
C.push(H2("6.2. Chạy AI service trên Colab GPU"));
C.push(P("Mở `ai-service/run_on_colab.ipynb` trên Colab (runtime T4) → Run all. Notebook clone code, tải GGUF v3, chạy service và mở Cloudflare tunnel; in ra URL dạng `https://….trycloudflare.com`. Backend local trỏ vào URL đó: `./mvnw spring-boot:run -Dspring-boot.run.arguments=--ai.service.url=<URL>`."));
C.push(H2("6.3. Biến môi trường chính"));
C.push(table(["Biến", "Mặc định", "Ý nghĩa"], [
  ["PROMPT_VERSION", "v3", "Phiên bản prompt + mô hình (v1, v2, v3)"],
  ["GGUF_MODEL_PATH", "merged_model/model-v3-q4_k_m.gguf", "File mô hình"],
  ["MAX_NEW_TOKENS", "2048", "Số token tối đa mô hình được sinh"],
  ["LOOP_MAX_STRING_CHARS / LOOP_MAX_REPEATS", "2000 / 3", "Ngưỡng chặn lặp"],
  ["POSTPROCESS_ENABLED", "true", "Hậu kiểm grounding"],
  ["KG_ENABLED", "true", "Nạp KB, chuẩn hoá, chạy KG (output KG ẩn trừ khi include=kg)"],
  ["NEO4J_URI / NEO4J_USER / NEO4J_PASSWORD", "— / neo4j / —", "Kho KG chính (Neo4j); không đặt thì dùng CSV"],
  ["KB_DSN / KB_SEED_DIR", "— / kb/seed", "PostgreSQL (dự phòng) hoặc thư mục CSV"],
], [3100, 2800, 3126]));
C.push(H2("6.4. Huấn luyện lại"));
C.push(N("`python -m training.build_dataset_v3` → upload `data/retrain_v3/` lên Drive `MyDrive/cv-analysis-service/retrain_v3/`.", "num6"));
C.push(N("Mở `training/retrain_qwen3_v2.ipynb` trên Colab T4, `RUN_NAME=\"v3\"`, chạy thử `SMOKE=True` (~10 phút) rồi Run all (~1 giờ).", "num6"));
C.push(N("Gửi URL API ở cell [10] để đánh giá trên 20 CV thật; nếu tốt hơn, tải GGUF về `merged_model/` và đổi `PROMPT_VERSION`.", "num6"));

// ===== Appendix =====
C.push(H1("Phụ lục A. Đối chiếu yêu cầu của giảng viên"));
{
  const pending = Object.entries(CMP.origin).filter(([, o]) => !o).length;
  C.push(table(["Yêu cầu", "Trạng thái", "Ở đâu / còn thiếu"], [
    ["Neo4j: PDF → KB1, nguồn liên kết → KB2, gộp KB1 + KB2 thành KB", "Đã làm", "Mục 4.4–4.5: kb.books, kb.neo4j_load (KB2, KB1, gộp RELATED_TO/ABOUT); service đọc KB từ Neo4j"],
    ["KB từ nhiều nguồn + sách PDF", "Đã làm", "6 nguồn liên kết (Stack Overflow survey + tags, Wikidata, Linguist, ESCO, Wikipedia) + 2 sách PDF; SOURCES.md"],
    ["Cập nhật KB", "Đã làm", "Mục 4.7 — quy trình 5 bước, không cần train lại mô hình"],
    ["So sánh 4–5 mô hình trên 4–5 tập dữ liệu", pending ? "Một phần" : "Đã làm", "5 mô hình × 4 tập (Bảng 3.1)" + (pending ? "; " + pending + " ô chờ chạy notebook eval_models_colab.ipynb trên GPU" : "")],
    ["KB + RAG", "Chưa làm (ngoài phạm vi đã chọn)", "Mục 4.8 giải thích vì sao và cách làm (biến thể D: gợi ý kỹ năng từ KB vào prompt, cần train lại)"],
    ["Visual phong phú", "Đã làm", "Sơ đồ luồng, biểu đồ F1 (Hình 3.1–3.2), lược đồ và đồ thị KG thật từ Neo4j (Hình 4.3–4.4)"],
    ["Show output cụ thể", COLAB ? "Đã làm" : "Một phần", COLAB ? "Mục 5.7 — output thật từ service trên Colab với include=kg" : "Mục 5.6 (chạy bằng code thật trên máy); output qua service Colab chờ chạy"],
  ], [3000, 1700, 4326], { zebra: true }));
}
C.push(H1("Phụ lục B. Thuật ngữ"));
C.push(table(["Thuật ngữ", "Giải thích ngắn"], [
  ["LLM", "Mô hình ngôn ngữ lớn; ở đây dùng bản nhỏ 1,7 tỷ tham số"],
  ["Fine-tune / LoRA", "Huấn luyện thêm trên dữ liệu riêng; LoRA chỉ học vài ma trận nhỏ thay vì toàn bộ mô hình"],
  ["GGUF, Q4_K_M", "Định dạng file mô hình cho llama.cpp; Q4_K_M = lượng tử hoá ~4 bit/trọng số"],
  ["Token", "Đơn vị văn bản mô hình xử lý (~ ¾ từ tiếng Anh)"],
  ["Grounding", "Kiểm tra giá trị mô hình sinh có thật sự nằm trong CV"],
  ["F1", "Trung bình điều hoà của precision (đúng trong số đã trả) và recall (bắt được trong số cần bắt)"],
  ["Entity linking", "Gắn một chuỗi (\"ReactJS\") với thực thể chuẩn trong KB (React, Q19399674)"],
  ["RAG", "Truy xuất tri thức liên quan rồi đưa vào prompt trước khi mô hình sinh"],
], [2300, 6726]));

// ---------- document ----------
const doc = new Document({
  features: { updateFields: true },
  creator: "recruit_system", title: "Module 1 — Pipeline, Fine-tune, KB & KG",
  styles: {
    default: { document: { run: { font: FONT, size: 26 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { font: FONT, size: 34, bold: true, color: "1F4E79" }, paragraph: { spacing: { before: 240, after: 200 }, keepNext: true, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { font: FONT, size: 29, bold: true, color: "2E75B6" }, paragraph: { spacing: { before: 280, after: 120 }, keepNext: true, outlineLevel: 1 } },
      { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { font: FONT, size: 26, bold: true, italics: true }, paragraph: { spacing: { before: 200, after: 80 }, keepNext: true, outlineLevel: 2 } },
    ],
  },
  numbering: { config: [
    { reference: "bullets", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 720, hanging: 360 } } } },
      { level: 1, format: LevelFormat.BULLET, text: "–", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 1440, hanging: 360 } } } }] },
    ...["num1", "numtrain", "numupd", "num6", "numbook"].map((r) => ({ reference: r, levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] })),
  ] },
  sections: [{
    properties: { page: { size: { width: 11906, height: 16838 }, margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 } } },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ children: [PageNumber.CURRENT], size: 20 })] })] }) },
    children: C,
  }],
});
Packer.toBuffer(doc).then((buf) => { fs.writeFileSync(process.argv[2], buf); console.log("written", process.argv[2]); });

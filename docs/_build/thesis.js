// Build the thesis-format report (Vietnamese) for Module 1 as .docx
// Run from docs/_build:  node thesis.js demo/render/raw.docx && python3 update_toc.py demo/render/raw.docx ../DoAn_Module1_TrichXuatCV.docx
//   (the second step fills the TOC / list of figures / list of tables with page numbers via LibreOffice)
// Real CVs appear only as counts; every CV shown in full is fictional (synthetic).
const fs = require("fs");
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType, Table, TableRow, TableCell,
  WidthType, ShadingType, BorderStyle, LevelFormat, TableOfContents, StyleLevel, Footer, PageNumber,
  ImageRun, NumberFormat, PageBreak, VerticalAlign,
} = require("docx");

const FONT = "Times New Roman";
const MONO = "Consolas";
const W = 9071; // A4 width 11906 - left 3 cm (1701) - right 2 cm (1134)
const B_ = __dirname;
const KB = JSON.parse(fs.readFileSync(B_ + "/kb_numbers.json", "utf8"));
const CMP = JSON.parse(fs.readFileSync(B_ + "/fig/compare.json", "utf8"));
const NEO = JSON.parse(fs.readFileSync(B_ + "/neo4j_counts.json", "utf8"));
const KB1 = JSON.parse(fs.readFileSync(B_ + "/../../ai-service/kb/sources/kb1_books.json", "utf8"));
const demo = (f) => JSON.parse(fs.readFileSync(B_ + "/demo/" + f, "utf8"));
const OUT1 = demo("out_one_default.json").data;
const OUT1KG = demo("out_one_kg.json").data;
const OUT2 = demo("out_two_default.json").data;
const TXT_LEG = demo("two_legacy/b03-015.json").text;
const TXT_LAY = demo("two_layout/b03-015.json").text;
const TXT_ONE = demo("one_layout/b03-015.json").text;

// ---------- numbering of figures / tables per chapter ----------
let chap = 0, nFig = 0, nTab = 0;
const figLabel = () => `Hình ${chap}.${++nFig}`;
const tabLabel = () => `Bảng ${chap}.${++nTab}`;

// ---------- text helpers ----------
function runs(text, base = {}) {
  const out = [];
  const re = /(\*\*[^*]+\*\*|`[^`]+`)/g;
  let last = 0, m;
  while ((m = re.exec(text))) {
    if (m.index > last) out.push(new TextRun({ text: text.slice(last, m.index), ...base }));
    const t = m[0];
    if (t.startsWith("**")) out.push(new TextRun({ text: t.slice(2, -2), bold: true, ...base }));
    else if (t.startsWith("`")) out.push(new TextRun({ text: t.slice(1, -1), font: MONO, size: 22, ...base }));
    else out.push(new TextRun({ text: t.slice(1, -1), italics: true, ...base }));
    last = m.index + t.length;
  }
  if (last < text.length) out.push(new TextRun({ text: text.slice(last), ...base }));
  return out;
}
const P = (t, o = {}) => new Paragraph({ children: runs(t), spacing: { before: 0, after: 120, line: 360 },
  indent: { firstLine: 567 }, alignment: AlignmentType.JUSTIFIED, ...o });
const PN = (t, o = {}) => P(t, { indent: { firstLine: 0 }, ...o });
const H1 = (t) => { chap += 1; nFig = 0; nTab = 0; return new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun(`CHƯƠNG ${chap}. ${t.toUpperCase()}`)], pageBreakBefore: true }); };
const H1U = (t) => new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun(t)], pageBreakBefore: true });
let h2 = 0, h3 = 0;
const H2 = (t) => { h2 += 1; h3 = 0; return new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun(`${chap}.${h2}. ${t}`)] }); };
const H3 = (t) => { h3 += 1; return new Paragraph({ heading: HeadingLevel.HEADING_3, children: [new TextRun(`${chap}.${h2}.${h3}. ${t}`)] }); };
const resetH = () => { h2 = 0; h3 = 0; };
const B = (t, level = 0) => new Paragraph({ numbering: { reference: "bullets", level }, children: runs(t), spacing: { after: 60, line: 340 }, alignment: AlignmentType.JUSTIFIED });
let numRef = 0;
const newList = () => `n${++numRef}`;
const N = (t, ref) => new Paragraph({ numbering: { reference: ref, level: 0 }, children: runs(t), spacing: { after: 60, line: 340 }, alignment: AlignmentType.JUSTIFIED });

const figCap = (t) => new Paragraph({ style: "HinhCaption", children: [new TextRun({ text: figLabel() + ". ", bold: true }), ...runs(t)] });
const tabCap = (t) => new Paragraph({ style: "BangCaption", keepNext: true, children: [new TextRun({ text: tabLabel() + ". ", bold: true }), ...runs(t)] });

function img(file, widthPx, dir = "/fig/") {
  const data = fs.readFileSync(B_ + dir + file);
  const w = data.readUInt32BE(16), h = data.readUInt32BE(20);
  return new ImageRun({ type: "png", data, transformation: { width: widthPx, height: Math.round(widthPx * h / w) },
    altText: { title: file, description: file, name: file } });
}
const figure = (file, widthPx, caption, dir) => [
  new Paragraph({ alignment: AlignmentType.CENTER, keepNext: true, spacing: { before: 120, after: 60 }, children: [img(file, widthPx, dir)] }),
  figCap(caption),
];

function code(lines, title) {
  const out = [];
  if (title) out.push(new Paragraph({ children: [new TextRun({ text: title, bold: true, size: 20, font: MONO, color: "1F4E79" })], spacing: { before: 120, after: 0 }, keepNext: true }));
  const arr = lines.replace(/\t/g, "    ").split("\n");
  arr.forEach((l, i) => out.push(new Paragraph({
    children: [new TextRun({ text: l.length ? l : " ", font: MONO, size: 17 })],
    shading: { type: ShadingType.CLEAR, fill: "F3F3F3", color: "auto" },
    spacing: { before: 0, after: i === arr.length - 1 ? 160 : 0, line: 230 },
    keepLines: true, keepNext: i < arr.length - 1 && arr.length < 30,
    border: { left: { style: BorderStyle.SINGLE, size: 12, color: "2E75B6", space: 6 } },
  })));
  return out;
}

const border = { style: BorderStyle.SINGLE, size: 4, color: "8C8C8C" };
const borders = { top: border, bottom: border, left: border, right: border };
function table(headers, rows, widths, opts = {}) {
  const total = widths.reduce((a, b) => a + b, 0);
  const mk = (txt, w, head, fill) => new TableCell({
    borders, width: { size: w, type: WidthType.DXA }, verticalAlign: VerticalAlign.CENTER,
    shading: head ? { fill: "D9E2F3", type: ShadingType.CLEAR, color: "auto" } : (fill ? { fill, type: ShadingType.CLEAR, color: "auto" } : undefined),
    margins: { top: 50, bottom: 50, left: 90, right: 90 },
    children: String(txt).split("\n").map((line) => new Paragraph({
      children: runs(line, head ? { bold: true, size: 22 } : { size: 22 }),
      alignment: head ? AlignmentType.CENTER : AlignmentType.LEFT,
      spacing: { after: 0, line: 260 },
    })),
  });
  return new Table({
    width: { size: total, type: WidthType.DXA }, columnWidths: widths,
    rows: [
      new TableRow({ tableHeader: true, cantSplit: true, children: headers.map((h, i) => mk(h, widths[i], true)) }),
      ...rows.map((r, ri) => new TableRow({ cantSplit: true, children: r.map((c, i) => mk(c, widths[i], false, opts.zebra && ri % 2 ? "F2F6FB" : undefined)) })),
    ],
  });
}
const gap = () => new Paragraph({ children: [], spacing: { after: 60 } });
const fmt = (v) => (v === null || v === undefined) ? "–" : v.toFixed(3).replace(".", ",");
const num = (v) => String(v).replace(/\B(?=(\d{3})+(?!\d))/g, ".");
const C = [];

// =====================================================================================
// COVER (own section)
const cover = [];
const ctr = (text, size, opt = {}) => new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: opt.after ?? 80, before: opt.before ?? 0 },
  children: [new TextRun({ text, size, bold: opt.bold ?? true, italics: opt.italics, font: FONT })] });
cover.push(
  ctr("HỌC VIỆN CÔNG NGHỆ BƯU CHÍNH VIỄN THÔNG", 26),
  ctr("KHOA CÔNG NGHỆ THÔNG TIN 1", 26, { after: 40 }),
  ctr("───────────────", 26, { bold: false, after: 1400 }),
  ctr("ĐỒ ÁN TỐT NGHIỆP ĐẠI HỌC", 36, { after: 700 }),
  ctr("Đề tài:", 28, { bold: false, italics: true, after: 160 }),
  ctr("XÂY DỰNG MODULE TRÍCH XUẤT THÔNG TIN CV ỨNG VIÊN", 28, { after: 60 }),
  ctr("SỬ DỤNG MÔ HÌNH NGÔN NGỮ NHỎ ĐƯỢC TINH CHỈNH", 28, { after: 60 }),
  ctr("KẾT HỢP KNOWLEDGE BASE VÀ KNOWLEDGE GRAPH", 28, { after: 1400 }),
);
const infoRow = (k, v) => new TableRow({ children: [
  new TableCell({ width: { size: 3600, type: WidthType.DXA }, borders: { top: { style: BorderStyle.NONE }, bottom: { style: BorderStyle.NONE }, left: { style: BorderStyle.NONE }, right: { style: BorderStyle.NONE } },
    children: [new Paragraph({ children: [new TextRun({ text: k, size: 26, bold: true })], spacing: { after: 100 } })] }),
  new TableCell({ width: { size: 4400, type: WidthType.DXA }, borders: { top: { style: BorderStyle.NONE }, bottom: { style: BorderStyle.NONE }, left: { style: BorderStyle.NONE }, right: { style: BorderStyle.NONE } },
    children: [new Paragraph({ children: [new TextRun({ text: v, size: 26 })], spacing: { after: 100 } })] }),
] });
cover.push(new Table({ width: { size: 8000, type: WidthType.DXA }, columnWidths: [3600, 4400], alignment: AlignmentType.CENTER,
  rows: [infoRow("Giảng viên hướng dẫn:", "[Họ và tên GVHD]"), infoRow("Sinh viên thực hiện:", "[Họ và tên sinh viên]"),
    infoRow("Mã sinh viên:", "[Mã SV]"), infoRow("Lớp:", "[Lớp]"), infoRow("Hệ:", "Chính quy")] }));
cover.push(ctr("HÀ NỘI – 2026", 26, { before: 1500 }));

// =====================================================================================
// FRONT MATTER (roman page numbers)
const front = [];
const frontH = (t) => new Paragraph({ style: "FrontTitle", children: [new TextRun(t)], pageBreakBefore: front.length > 0 });
front.push(frontH("LỜI CẢM ƠN"));
front.push(P("[Phần này sinh viên tự viết: lời cảm ơn giảng viên hướng dẫn, khoa, gia đình và bạn bè.]", { alignment: AlignmentType.LEFT }));
front.push(frontH("LỜI CAM ĐOAN"));
front.push(P("[Phần này sinh viên tự viết theo mẫu của khoa: cam đoan đồ án là kết quả nghiên cứu của bản thân, số liệu trung thực, các nguồn tham khảo được trích dẫn đầy đủ.]", { alignment: AlignmentType.LEFT }));
front.push(frontH("MỤC LỤC"));
front.push(new TableOfContents("Mục lục", { hyperlink: true, headingStyleRange: "1-3" }));
front.push(frontH("DANH MỤC HÌNH VẼ"));
front.push(new TableOfContents("Danh mục hình vẽ", { hyperlink: true, stylesWithLevels: [new StyleLevel("HinhCaption", 1)] }));
front.push(frontH("DANH MỤC BẢNG BIỂU"));
front.push(new TableOfContents("Danh mục bảng biểu", { hyperlink: true, stylesWithLevels: [new StyleLevel("BangCaption", 1)] }));
front.push(frontH("DANH MỤC TỪ VIẾT TẮT VÀ THUẬT NGỮ"));
front.push(table(["Viết tắt / thuật ngữ", "Tiếng Anh", "Giải thích"], [
  ["API", "Application Programming Interface", "Giao diện lập trình; ở đây là các endpoint HTTP"],
  ["CV", "Curriculum Vitae", "Hồ sơ xin việc của ứng viên"],
  ["JD", "Job Description", "Mô tả công việc của nhà tuyển dụng"],
  ["LLM", "Large Language Model", "Mô hình ngôn ngữ lớn; đồ án dùng bản nhỏ 1,7 tỷ tham số"],
  ["SFT", "Supervised Fine-Tuning", "Tinh chỉnh có giám sát trên cặp (đầu vào, đầu ra mong muốn)"],
  ["LoRA", "Low-Rank Adaptation", "Tinh chỉnh bằng cách học thêm ma trận hạng thấp, đóng băng trọng số gốc"],
  ["QLoRA", "Quantized LoRA", "LoRA trên mô hình gốc được nạp ở dạng 4-bit"],
  ["GGUF", "GPT-Generated Unified Format", "Định dạng file mô hình của llama.cpp"],
  ["Q4_K_M", "–", "Kiểu lượng tử hoá khoảng 4 bit/trọng số của llama.cpp"],
  ["KB", "Knowledge Base", "Cơ sở tri thức: kỹ năng, alias, trường học, nghề nghiệp"],
  ["KG", "Knowledge Graph", "Đồ thị tri thức: các thực thể và quan hệ giữa chúng"],
  ["RAG", "Retrieval-Augmented Generation", "Sinh văn bản có bổ sung tri thức truy xuất được vào prompt"],
  ["Grounding", "–", "Kiểm tra mỗi giá trị mô hình sinh ra có thật sự xuất hiện trong CV"],
  ["Entity linking", "–", "Gắn một chuỗi (\"ReactJS\") với thực thể chuẩn trong KB (React)"],
  ["XY-cut", "Recursive XY-cut", "Thuật toán chia trang theo khoảng trắng ngang/dọc để tìm thứ tự đọc"],
  ["F1", "F1-score", "Trung bình điều hoà của precision và recall"],
  ["OCR", "Optical Character Recognition", "Nhận dạng ký tự từ ảnh (ngoài phạm vi đồ án)"],
  ["Token", "–", "Đơn vị văn bản mô hình xử lý (khoảng ¾ từ tiếng Anh)"],
], [2000, 2900, 4171], { zebra: true }));

// =====================================================================================
// MỞ ĐẦU
C.push(H1U("MỞ ĐẦU"));
C.push(new Paragraph({ children: [new TextRun({ text: "1. Tính cấp thiết của đề tài", bold: true })], spacing: { before: 120, after: 80 } }));
C.push(P("Mỗi đợt tuyển dụng, bộ phận nhân sự nhận hàng trăm CV ở dạng PDF với bố cục rất khác nhau: một cột, hai cột, có bảng, có dòng thời gian, viết bằng tiếng Việt hoặc tiếng Anh. Việc đọc thủ công từng CV để lấy ra học vấn, kinh nghiệm, dự án và kỹ năng tốn thời gian và dễ sai sót, đồng thời là bước bắt buộc trước khi có thể so khớp ứng viên với mô tả công việc (JD) một cách tự động."));
C.push(P("Các bộ lọc dựa trên luật (regex, từ điển tiêu đề mục) hoạt động kém khi bố cục thay đổi. Các mô hình ngôn ngữ lớn thương mại xử lý tốt hơn nhưng đòi hỏi gửi CV – vốn chứa dữ liệu cá nhân – ra dịch vụ bên ngoài và tốn chi phí cho mỗi lượt gọi. Vì vậy cần một giải pháp trích xuất chạy cục bộ, đủ chính xác trên CV thật, không bịa thông tin và có thể giải thích được."));
C.push(new Paragraph({ children: [new TextRun({ text: "2. Mục tiêu của đồ án", bold: true })], spacing: { before: 120, after: 80 } }));
C.push(B("Xây dựng **Module 1 – trích xuất thông tin CV** của hệ thống hỗ trợ tuyển dụng: nhận file PDF, trả về hồ sơ ứng viên có cấu trúc (JSON) cho Module 2 (so khớp CV – JD)."));
C.push(B("Tinh chỉnh (fine-tune) mô hình ngôn ngữ nhỏ mã nguồn mở Qwen3-1.7B bằng LoRA trên dữ liệu được xây dựng riêng, chạy được trên GPU miễn phí (Google Colab T4) và trên CPU."));
C.push(B("Xây dựng Knowledge Base (KB) từ các nguồn công khai có trích dẫn và Knowledge Graph (KG) trên Neo4j để chuẩn hoá output của mô hình và suy luận quan hệ giữa các kỹ năng."));
C.push(B("Đánh giá định lượng trên CV thật chưa từng dùng để huấn luyện, so sánh với phương pháp dựa trên luật và mô hình gốc chưa tinh chỉnh."));
C.push(new Paragraph({ children: [new TextRun({ text: "3. Đối tượng và phạm vi", bold: true })], spacing: { before: 120, after: 80 } }));
C.push(P("Đối tượng là CV ngành Công nghệ thông tin dạng PDF có lớp văn bản (text-based), tiếng Việt hoặc tiếng Anh. CV dạng ảnh scan (cần OCR) và việc so khớp CV – JD (Module 2) nằm ngoài phạm vi đồ án. Hệ thống gồm backend Java Spring Boot, AI service Python FastAPI, mô hình chạy bằng llama.cpp và kho tri thức Neo4j."));
C.push(new Paragraph({ children: [new TextRun({ text: "4. Phương pháp thực hiện", bold: true })], spacing: { before: 120, after: 80 } }));
C.push(P("Đồ án kết hợp ba lớp: (1) tiền xử lý PDF theo bố cục (thuật toán XY-cut) để mô hình nhận văn bản đúng thứ tự đọc; (2) mô hình ngôn ngữ nhỏ được tinh chỉnh để chuyển văn bản CV thành JSON; (3) các lớp hậu xử lý tất định – kiểm tra grounding, chuẩn hoá bằng KB, suy luận bằng KG – để loại bỏ thông tin bịa và thống nhất tên gọi. Mọi thay đổi được đo lại trên cùng một bộ CV thật bằng bộ đánh giá tự động."));
C.push(new Paragraph({ children: [new TextRun({ text: "5. Bố cục đồ án", bold: true })], spacing: { before: 120, after: 80 } }));
C.push(table(["Chương", "Nội dung"], [
  ["Chương 1", "Tổng quan bài toán và cơ sở lý thuyết: LLM, LoRA, lượng tử hoá, trích xuất văn bản PDF, KB/KG, chỉ số đánh giá"],
  ["Chương 2", "Phân tích yêu cầu và thiết kế hệ thống: kiến trúc, luồng xử lý, API, mô hình dữ liệu, bảo mật"],
  ["Chương 3", "Xử lý dữ liệu và tinh chỉnh mô hình: quy ước nhãn, sinh dữ liệu theo bố cục, các phiên bản dataset, huấn luyện"],
  ["Chương 4", "Xây dựng và sử dụng Knowledge Base, Knowledge Graph (Neo4j)"],
  ["Chương 5", "Luồng xử lý chi tiết từ backend đến AI service, kèm code và output thật của mô hình v4"],
  ["Chương 6", "Thử nghiệm, đánh giá và triển khai"],
], [1500, 7571]));

// =====================================================================================
// CHƯƠNG 1
C.push(H1("Tổng quan và cơ sở lý thuyết")); resetH();
C.push(H2("Bài toán trích xuất thông tin CV"));
C.push(P("Bài toán nhận vào một file CV dạng PDF và trả về **hồ sơ ứng viên có cấu trúc** (CandidateProfile). Đây là bài toán trích xuất thông tin (information extraction) trên văn bản bán cấu trúc: CV có các mục quen thuộc (học vấn, kinh nghiệm, kỹ năng…) nhưng tên mục, thứ tự mục và cách trình bày từng dòng thay đổi theo từng ứng viên và từng mẫu CV."));
C.push(tabCap("Đầu vào, đầu ra và ràng buộc của bài toán"));
C.push(table(["", "Mô tả"], [
  ["Đầu vào", "File PDF CV có lớp văn bản, tối đa 10 trang, tiếng Việt hoặc tiếng Anh"],
  ["Đầu ra", "JSON gồm personal_info, objective, education[], experience[], personal_projects[], skills[], certificates[], honours[], languages[]"],
  ["Ràng buộc", "Chạy cục bộ (CPU) hoặc trên GPU miễn phí; dữ liệu CV không gửi ra dịch vụ bên ngoài; không bịa thông tin; thời gian xử lý chấp nhận được (dưới 1 phút/CV trên CPU)"],
], [1600, 7471]));
C.push(P("Các khó khăn chính gồm:"));
C.push(B("**Bố cục đa dạng**: CV hai cột, cột thanh bên (sidebar), bảng, dòng thời gian dọc. Thư viện đọc PDF mặc định ghép chữ theo từng dòng ngang nên trộn nội dung của hai cột (mục 1.6)."));
C.push(B("**Cách viết không thống nhất**: cùng một kỹ năng có thể ghi \"ReactJS\", \"React.js\", \"react\"; cùng một trường có thể ghi \"PTIT\" hay tên đầy đủ."));
C.push(B("**Song ngữ** và tiêu đề mục không cố định (\"Kinh nghiệm làm việc\", \"Work Experience\", \"Career\", \"Quá trình làm việc\")."));
C.push(B("**Dữ liệu cá nhân**: CV chứa họ tên, số điện thoại, email; không được ghi log hay gửi ra ngoài."));
C.push(H2("Các hướng tiếp cận"));
C.push(tabCap("So sánh ba hướng tiếp cận"));
C.push(table(["Hướng", "Ưu điểm", "Nhược điểm"], [
  ["Dựa trên luật (regex + từ điển tiêu đề mục)", "Rất nhanh (~9 ms/CV), không bịa, dễ giải thích", "Không hiểu cấu trúc dòng; F1 tên công ty chỉ 0,10 trên dữ liệu kiểm thử (Chương 6)"],
  ["LLM thương mại qua API (GPT, Gemini…)", "Chính xác, không cần huấn luyện", "Gửi dữ liệu cá nhân ra ngoài; chi phí theo lượt; phụ thuộc nhà cung cấp"],
  ["LLM nhỏ mã nguồn mở + tinh chỉnh (Qwen3-1.7B + LoRA)", "Chạy cục bộ, học đúng quy ước nhãn, chi phí huấn luyện thấp", "Cần xây dựng dữ liệu; mô hình nhỏ có thể bịa, lặp → cần lớp hậu kiểm"],
], [2700, 3000, 3371]));
C.push(P("Đồ án chọn hướng thứ ba và bổ sung ba lớp tất định phía sau mô hình – hậu kiểm grounding, chuẩn hoá bằng KB, suy luận bằng KG – để bù cho điểm yếu của mô hình nhỏ."));
C.push(H2("Mô hình ngôn ngữ lớn và Qwen3"));
C.push(P("Mô hình ngôn ngữ lớn hiện đại dựa trên kiến trúc Transformer [4] dạng chỉ-decoder: mô hình nhận một chuỗi token và dự đoán token tiếp theo; lặp lại phép dự đoán này (sinh tự hồi quy) cho ra văn bản. Khi giải mã tham lam (greedy, temperature = 0), mô hình luôn chọn token có xác suất cao nhất nên cùng một đầu vào cho cùng một đầu ra – tính chất cần thiết cho bài toán trích xuất."));
C.push(P("**Qwen3-1.7B** [1] là mô hình mã nguồn mở 1,7 tỷ tham số (28 lớp, ngữ cảnh tối đa 32.768 token), hỗ trợ tốt tiếng Việt và tiếng Anh. Mô hình dùng định dạng hội thoại ChatML (`<|im_start|>system … <|im_end|>`) và có chế độ \"suy nghĩ\" (`<think>…</think>`); đồ án tắt chế độ này bằng cách mồi sẵn một khối `<think>` rỗng để mô hình viết JSON ngay."));
C.push(H2("Tinh chỉnh mô hình bằng LoRA"));
C.push(P("**Tinh chỉnh có giám sát (SFT)** huấn luyện tiếp mô hình trên các cặp (prompt, câu trả lời mong muốn). Với bài toán này, prompt là hướng dẫn + văn bản CV, câu trả lời là JSON nhãn. Hàm mất mát chỉ tính trên phần câu trả lời (phần prompt bị che bằng nhãn −100), để mô hình học cách viết JSON chứ không học lại văn bản CV."));
C.push(P("Cập nhật toàn bộ 1,7 tỷ tham số đòi hỏi bộ nhớ GPU lớn. **LoRA** [2] giữ nguyên ma trận trọng số gốc W₀ và học thêm hai ma trận nhỏ A (r × d) và B (d × r) sao cho đầu ra của lớp là h = W₀x + (α/r)·BAx, với hạng r rất nhỏ so với d. **QLoRA** [3] nạp W₀ ở dạng 4-bit để giảm bộ nhớ thêm nữa. Với r = 16 gắn vào 7 phép chiếu của mỗi lớp, số tham số được học khoảng 17,4 triệu (~1 % mô hình, adapter ~70 MB), đủ để huấn luyện trên GPU T4 16 GB của Google Colab."));
C.push(...figure("d_lora.png", 520, "Nguyên lý LoRA: trọng số gốc đóng băng, chỉ học hai ma trận hạng thấp A, B"));
C.push(H2("Lượng tử hoá và suy luận cục bộ"));
C.push(P("Sau khi huấn luyện, adapter LoRA được gộp vào mô hình gốc rồi **lượng tử hoá** sang định dạng GGUF kiểu Q4_K_M (khoảng 4–5 bit/trọng số theo từng khối), giảm kích thước file từ ~3,4 GB (bf16) xuống ~1,1 GB. File GGUF được chạy bằng **llama.cpp** [7] – thư viện suy luận C/C++ chạy được trên CPU thường và tận dụng GPU khi có. Nhờ đó cùng một file mô hình dùng được cho máy cá nhân, máy chủ và Colab."));
C.push(H2("Trích xuất văn bản từ PDF và thứ tự đọc"));
C.push(P("PDF không lưu \"đoạn văn\" mà lưu danh sách ký tự (glyph) kèm toạ độ trên trang. Thư viện **Apache PDFBox** [6] ghép glyph thành từ và dòng; ở chế độ `sortByPosition`, các glyph được sắp theo toạ độ y rồi x. Với CV hai cột, một dòng ngang cắt qua cả hai cột nên text thu được trộn nội dung hai cột vào cùng một dòng (Hình 1.2, bên trái) – mô hình phải \"đoán\" đâu là học vấn, đâu là kinh nghiệm."));
C.push(P("Thuật toán **XY-cut đệ quy** [5] khôi phục thứ tự đọc: tìm khe trắng dọc hoặc ngang lớn nhất mà không đoạn chữ nào cắt qua, chia vùng thành hai nửa, rồi lặp lại trên từng nửa cho tới khi không chia được; mỗi vùng lá là một khối văn bản, đọc theo thứ tự trên-xuống, trái-sang-phải. Đồ án cài đặt XY-cut trong backend (mục 5.2) với các luật riêng cho CV: một bên của khe dọc chỉ được coi là cột thật khi có ít nhất 3 đoạn và trải rộng tối thiểu 25 % vùng, để dải ngày tháng hẹp bên lề không bị tách thành cột."));
C.push(...figure("d_xycut.png", 560, "Thứ tự đọc của PDFBox mặc định và của thuật toán XY-cut trên CV hai cột"));
C.push(H2("Knowledge Base, Knowledge Graph và entity linking"));
C.push(P("**Knowledge Base (KB)** là tập tri thức có cấu trúc về các thực thể của miền bài toán – ở đây là kỹ năng (mỗi kỹ năng có mã, tên chuẩn, nhóm và các cách viết khác – alias), trường học và chức danh nghề nghiệp. **Knowledge Graph (KG)** [17] biểu diễn tri thức dưới dạng đồ thị: nút là thực thể, cạnh là quan hệ có nhãn, ví dụ `Spring Boot –REQUIRES→ Java`. Đồ án lưu KG trên **Neo4j** [16], cơ sở dữ liệu đồ thị dùng ngôn ngữ truy vấn Cypher."));
C.push(P("**Entity linking** [20] là bước gắn một chuỗi trong văn bản (\"ReactJS\") với thực thể chuẩn trong KB (React). **RAG** [18] (Retrieval-Augmented Generation) là kỹ thuật truy xuất tri thức liên quan rồi đưa vào prompt trước khi mô hình sinh; mục 4.8 thảo luận vì sao đồ án dùng KB sau bước sinh thay vì RAG."));
C.push(H2("Chỉ số đánh giá"));
C.push(P("Với các trường dạng danh sách (công ty, trường, dự án, kỹ năng, chứng chỉ, giải thưởng, ngoại ngữ), mỗi giá trị dự đoán được so khớp với giá trị nhãn (gold) sau khi chuẩn hoá chữ hoa/thường, dấu và khoảng trắng. Gọi TP là số giá trị khớp, FP là số giá trị dự đoán thừa, FN là số giá trị nhãn bị bỏ sót:"));
C.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 120 }, children: [new TextRun({ text: "Precision = TP / (TP + FP);   Recall = TP / (TP + FN);   F1 = 2 · P · R / (P + R)", italics: true })] }));
C.push(P("Các trường đơn (họ tên, email, điện thoại, GitHub) dùng độ chính xác (accuracy). **Tỷ lệ bịa** (hallucination rate) là tỷ lệ giá trị dự đoán không tìm thấy trong văn bản CV. Mỗi lần chạy được chấm ở ba biến thể: **A** – output thô của mô hình; **B** – sau hậu kiểm (cách hệ thống chạy thật, dùng để báo cáo); **C** – B cộng thêm làm giàu bằng KG."));
C.push(H2("Kết luận chương"));
C.push(P("Chương 1 trình bày bài toán, lý do chọn mô hình ngôn ngữ nhỏ được tinh chỉnh bằng LoRA kết hợp các lớp tất định, cùng các kiến thức nền: LLM, LoRA/QLoRA, lượng tử hoá GGUF, thứ tự đọc PDF và XY-cut, KB/KG và các chỉ số đánh giá. Chương 2 sử dụng các khái niệm này để thiết kế hệ thống."));

// =====================================================================================
// CHƯƠNG 2
C.push(H1("Phân tích và thiết kế hệ thống")); resetH();
C.push(H2("Yêu cầu hệ thống"));
C.push(tabCap("Yêu cầu chức năng và phi chức năng của Module 1"));
C.push(table(["Mã", "Yêu cầu", "Cách đáp ứng"], [
  ["F1", "Nhận file PDF CV và trả về CandidateProfile (JSON)", "Backend `POST /api/v1/cv/analyze-pdf`"],
  ["F2", "Đọc đúng CV một cột, hai cột, có bảng, có dòng thời gian", "Trích xuất text theo bố cục (XY-cut), mô hình huấn luyện trên 15 bố cục"],
  ["F3", "Chuẩn hoá tên kỹ năng, tên trường", "KB: link về tên chuẩn / tên chính thức"],
  ["F4", "Cung cấp quan hệ kỹ năng khi cần phân tích", "KG: `?include=kg` trả implied_skills, related_skills"],
  ["N1", "Không bịa thông tin", "Hậu kiểm grounding: mọi giá trị phải có trong CV"],
  ["N2", "Không lộ dữ liệu CV", "Mô hình chạy cục bộ; log chỉ ghi số đếm; dữ liệu thật không commit"],
  ["N3", "Ổn định khi mô hình sinh lỗi", "Chặn lặp, sinh nối tiếp, ghép JSON; mã lỗi HTTP rõ ràng"],
  ["N4", "Chạy được trên CPU và GPU miễn phí", "GGUF Q4_K_M ~1,1 GB, llama.cpp"],
], [800, 4000, 4271], { zebra: true }));
C.push(H2("Kiến trúc tổng thể"));
C.push(P("Hệ thống gồm các thành phần độc lập giao tiếp qua HTTP (Hình 2.1). Backend Java chịu trách nhiệm nghiệp vụ và xử lý file PDF; AI service Python chỉ nhận văn bản và trả JSON, nên có thể thay mô hình hoặc chạy AI service trên máy có GPU mà không ảnh hưởng backend."));
C.push(...figure("d_architecture.png", 600, "Kiến trúc tổng thể của Module 1"));
C.push(tabCap("Các thành phần và công nghệ"));
C.push(table(["Thành phần", "Công nghệ", "Vai trò"], [
  ["Frontend", "React 19, TypeScript, Vite", "Tải CV lên, hiển thị hồ sơ"],
  ["Backend", "Java 21, Spring Boot 4, Apache PDFBox 3, OpenFeign", "Nhận PDF, trích văn bản theo bố cục, gọi AI service, trả CandidateProfile"],
  ["AI service", "Python 3, FastAPI, llama-cpp-python", "Dựng prompt, chạy mô hình, hậu kiểm, chuẩn hoá KB, làm giàu KG"],
  ["Mô hình", "Qwen3-1.7B + LoRA (v4), GGUF Q4_K_M", "Đọc văn bản CV, sinh JSON"],
  ["KB / KG", "Neo4j 5.26 (kho chính), PostgreSQL 16 / CSV (dự phòng)", "Kỹ năng, alias, quan hệ, trường học, nghề, mục sách"],
  ["Huấn luyện", "Google Colab T4, Unsloth [8], TRL [9], Google Drive", "Tinh chỉnh LoRA, đánh giá, xuất GGUF, chạy thử API"],
], [1700, 3300, 4071]));
C.push(H2("Luồng xử lý tổng quát"));
C.push(P("Hình 2.2 mô tả trình tự xử lý một CV: frontend gửi file tới backend; backend trích văn bản theo bố cục rồi gọi AI service qua Feign client; AI service dựng prompt, cho mô hình sinh JSON có kiểm soát, hậu kiểm, chuẩn hoá bằng KB, làm giàu bằng KG và trả kết quả. Chương 5 trình bày chi tiết từng bước kèm mã nguồn."));
C.push(...figure("d_sequence.png", 600, "Biểu đồ tuần tự xử lý một CV từ backend đến AI service"));
C.push(H2("Thiết kế API"));
C.push(tabCap("Các endpoint của backend (`CvAnalysisController`, tiền tố `/api/v1/cv`)"));
C.push(table(["Phương thức + đường dẫn", "Đầu vào", "Đầu ra / mục đích"], [
  ["POST /analyze-pdf", "multipart `file` (PDF)", "CandidateProfile – luồng chính"],
  ["POST /analyze", "văn bản CV thô", "CandidateProfile – khi đã có text"],
  ["POST /extract-text", "multipart `file`", "Chỉ trả văn bản trích xuất (kiểm tra bố cục, sinh dữ liệu)"],
  ["POST /extract-rule-based", "multipart `file`", "CandidateProfile bằng luật – dùng để so sánh"],
], [2700, 2400, 3971]));
C.push(tabCap("Endpoint của AI service và mã lỗi"));
C.push(table(["Endpoint / mã", "Ý nghĩa"], [
  ["GET /health", "Trạng thái, engine, phiên bản prompt, đường dẫn mô hình, nguồn và quy mô KB"],
  ["POST /api/v1/extract-cv", "Body `{\"cv_text\": \"…\"}` → `{\"data\": CandidateProfile}`"],
  ["?include=kg", "Thêm skills_normalized, implied_skills, related_skills, skills_detected, flags"],
  ["?include=raw", "Thêm raw_profile (output sau hậu kiểm, trước chuẩn hoá KB) để đánh giá"],
  ["400", "cv_text rỗng hoặc tham số include không hợp lệ"],
  ["413", "CV quá dài so với ngữ cảnh 8.192 token của mô hình"],
  ["502", "Mô hình không sinh được object JSON có nội dung"],
  ["503", "Mô hình chưa nạp xong hoặc hàng đợi quá thời gian chờ"],
  ["500", "Lỗi nội bộ: trả request_id, không chứa dữ liệu CV"],
], [2500, 6571]));
C.push(...code(`@FeignClient(name = "ai-service", url = "\${ai.service.url:http://localhost:8000}")
public interface AiServiceClient {
    @PostMapping(value = "/api/v1/extract-cv", produces = "application/json")
    AiCvResponse extractCv(@RequestBody AiCvRequest request);   // AiCvRequest { String cv_text; }
}`, "backend/.../client/AiServiceClient.java"));
C.push(H2("Mô hình dữ liệu CandidateProfile"));
C.push(tabCap("Cấu trúc CandidateProfile"));
C.push(table(["Trường", "Kiểu", "Mô tả"], [
  ["personal_info", "object", "full_name, email, phone, github_url"],
  ["objective", "string | null", "Mục tiêu / tóm tắt nghề nghiệp"],
  ["education[]", "object", "school, major, start_year, end_year (số nguyên), gpa"],
  ["experience[]", "object", "company (chỉ tên tổ chức), job_title, start_date, end_date (null nếu đang làm), description[]"],
  ["personal_projects[]", "object", "name, role, team_size, start_date, end_date, github_url, description[], tech_stack[]"],
  ["skills[]", "string", "Mỗi kỹ năng một phần tử, đã chuẩn hoá tên bằng KB"],
  ["certificates[], honours[]", "string", "Chứng chỉ; giải thưởng / thành tích / học bổng"],
  ["languages[]", "object", "Chỉ ngôn ngữ tự nhiên: language, note (trình độ / điểm)"],
], [2300, 1600, 5171], { zebra: true }));
C.push(H2("Bảo mật dữ liệu CV"));
C.push(B("Mô hình chạy cục bộ hoặc trên phiên Colab của chính nhóm; không gọi API LLM bên ngoài với CV thật."));
C.push(B("Log của backend và AI service chỉ ghi số đếm (số ký tự, số token, số giá trị bị loại), không ghi nội dung CV; lỗi trả `request_id`."));
C.push(B("CV thật và dataset chỉ nằm trong thư mục bị git-ignore (`ai-service/data/`, `dataset/`); các LLM hỗ trợ phát triển chỉ được dùng để sinh hồ sơ **hư cấu**."));
C.push(B("Báo cáo chỉ trình bày số đếm trên CV thật; mọi ví dụ đầy đủ trong đồ án là CV hư cấu."));
C.push(H2("Kết luận chương"));
C.push(P("Chương 2 xác định yêu cầu, kiến trúc gồm frontend – backend – AI service – KB/KG, luồng xử lý, API và mô hình dữ liệu. Thiết kế tách xử lý PDF (backend) khỏi suy luận mô hình (AI service) để mỗi phần được thay đổi và đánh giá độc lập."));

// =====================================================================================
// CHƯƠNG 3
C.push(H1("Xử lý dữ liệu và tinh chỉnh mô hình")); resetH();
C.push(P("Chất lượng của mô hình nhỏ phụ thuộc chủ yếu vào dữ liệu huấn luyện: dữ liệu phải giống văn bản mà mô hình gặp khi chạy thật và nhãn phải nhất quán. Chương này trình bày quy ước nhãn, cách tạo dữ liệu, các phiên bản dataset và quy trình huấn luyện."));
C.push(H2("Quy ước nhãn"));
C.push(B("**Chép nguyên văn**: không dịch, không tóm tắt, không sửa chính tả; thiếu thì trường đơn là null, danh sách là []."));
C.push(B("**experience.company** chỉ chứa tên tổ chức (không kèm địa điểm, ngày, chức danh); **end_date = null** khi CV ghi Present / Now / Hiện tại; ngày giữ đúng định dạng trong CV."));
C.push(B("**skills**: mọi kỹ năng trong mục Kỹ năng, gồm tất cả nhóm con, mỗi kỹ năng một phần tử, bỏ tên nhóm; ngôn ngữ lập trình luôn thuộc skills."));
C.push(B("**languages** chỉ chứa ngôn ngữ tự nhiên; **certificates** lấy từ mục Chứng chỉ; **honours** gồm giải thưởng, thành tích, học bổng."));
C.push(B("start_year, end_year, team_size là số nguyên."));
C.push(H2("Nguồn dữ liệu"));
C.push(tabCap("Các nguồn dữ liệu huấn luyện và đánh giá"));
C.push(table(["Nguồn", "Số lượng", "Cách tạo nhãn", "Vai trò"], [
  ["CV sinh theo bố cục (hư cấu)", "200 hồ sơ × nhiều bố cục; +200 biến thể ở v5", "Nhãn = hồ sơ gốc, chỉ bỏ giá trị không in ra trong văn bản", "Phần lớn tập train"],
  ["CV thật – tập train", "31", "Nhãn được gán và duyệt thủ công, căn lại theo văn bản layout", "Train (kèm bản hoán đổi)"],
  ["CV tổng hợp cũ (silver)", "250", "Nhãn do LLM tạo, áp lại quy ước v3", "Train"],
  ["val / val_swap", "99 / 99", "CV tổng hợp; val_swap đổi tên công ty, trường", "Hồi quy, phát hiện học vẹt"],
  ["test_real", "20 CV thật", "Gold gán nháp, người dùng duyệt", "Thước đo chính, không dùng để train"],
], [2400, 1900, 3000, 1771], { zebra: true }));
C.push(H2("Sinh CV theo bố cục"));
C.push(P("CV thật có số lượng ít và không được phép chia sẻ, vì vậy phần lớn dữ liệu được **sinh**: hồ sơ ứng viên hư cấu (JSONL) được viết theo đặc tả `profile_prompt.md` với đủ cấp độ junior, middle, senior, lead; mỗi hồ sơ được render thành HTML theo một trong 15 bố cục mô phỏng CV thật, chuyển sang PDF bằng LibreOffice, rồi trích văn bản bằng **chính bộ trích xuất của backend** (`PdfTextDumpRunner`). Nhờ vậy văn bản lúc huấn luyện giống hệt văn bản lúc chạy thật, còn nhãn là hồ sơ gốc nên chính xác tuyệt đối. Bước `ground_label` bỏ khỏi nhãn những giá trị bố cục không in ra (ví dụ địa chỉ trong bố cục không có mục liên hệ)."));
C.push(...figure("d_data_pipeline.png", 600, "Pipeline sinh dữ liệu huấn luyện"));
C.push(tabCap("15 bố cục CV mẫu (`training/synth/render.py`)"));
C.push(table(["Bố cục", "Đặc điểm"], [
  ["L1–L3", "Một cột cổ điển; tiêu đề mục tiếng Anh / tiếng Việt; \"Công ty | Chức danh\" rồi dòng ngày"],
  ["L4, L5", "Công ty – địa điểm | chức danh | ngày trên một dòng; bảng hai ô với ngày căn phải"],
  ["L6, L7", "Kỹ năng dạng bảng nhóm; tech stack dạng Backend(…), Frontend(…)"],
  ["L8, L9", "Mục Objective; kỹ năng và ngoại ngữ trên một dòng; gộp Chứng chỉ & Giải thưởng"],
  ["L10", "Cột dòng thời gian bên trái, nội dung bên phải"],
  ["L11", "Hai cột có thanh bên; mỗi công việc: ngày kết thúc → công ty → chức danh → mô tả → ngày bắt đầu; ngắt trang giữa các công việc"],
  ["L12", "Kỹ năng dạng \"Nhóm: A (B, C, D), E\""],
  ["L13", "Hai cột cân bằng 47 % / 47 % từ đầu đến cuối trang"],
  ["L14", "Dự án đặt trước kinh nghiệm, tiêu đề \"Career\" / \"Quá trình làm việc\""],
  ["L15 (v5)", "Như L11 nhưng mỗi công việc: công ty → \"ngày kết thúc + chức danh\" trên một dòng → mô tả → ngày bắt đầu ở cuối"],
], [1300, 7771], { zebra: true }));
C.push(H2("Căn nhãn CV thật và tăng cường dữ liệu"));
C.push(P("Nhãn của CV thật được gán trên văn bản trích xuất cũ. Khi đổi sang văn bản theo bố cục (Chương 5), mỗi giá trị nhãn được tìm lại trong văn bản mới (so khớp mờ, ngưỡng 85); giá trị không còn tìm thấy bị loại – 1.440/1.443 giá trị được giữ. Mỗi CV thật được nhân thêm bằng **hoán đổi thực thể**: thay tên công ty, trường học bằng tên khác trong toàn bộ văn bản và nhãn, giúp mô hình học vị trí và cấu trúc thay vì nhớ tên. Tập val_swap được tạo theo cùng cách để kiểm tra mô hình có học vẹt hay không."));
C.push(H2("Các phiên bản dataset"));
C.push(tabCap("Quá trình phát triển dataset và mô hình"));
C.push(table(["Phiên bản", "Dữ liệu train", "Thay đổi chính", "Lý do"], [
  ["v1", "CV tổng hợp do LLM sinh", "Prompt huấn luyện khác prompt khi chạy", "Mốc ban đầu; bỏ sót mục cuối CV do lệch prompt"],
  ["v2", "824 mẫu", "Prompt chung cho train và serve; loss chỉ trên JSON", "Sửa lệch prompt"],
  ["v3", "711 mẫu", "Thêm CV thật + CV sinh theo 10 bố cục thật, đủ cấp độ", "Thu hẹp khoảng cách với CV thật"],
  ["v4", "895 mẫu", "Toàn bộ văn bản đổi sang text theo bố cục; thêm bố cục L11–L14", "Đồng bộ với bộ trích xuất XY-cut"],
  ["v5 (đã chuẩn bị)", "1.112 mẫu", "Thêm CV 4–6 công ty ngắn, CV sinh viên, bố cục L15; CV thật ×4", "Sửa các lỗi còn lại của v4 (mục 6.4)"],
], [1500, 1700, 3300, 2571], { zebra: true }));
C.push(...figure("c_dataset.png", 560, "Thành phần tập train của các dataset v3, v4, v5"));
C.push(P("Mỗi dataset có thêm tập dev (45–74 mẫu, tách theo hồ sơ để mọi bố cục của một hồ sơ cùng nằm ở dev) dùng chọn checkpoint. Builder kiểm tra không có mẫu nào trùng (độ tương đồng > 70 %) với các tập kiểm thử và loại mẫu dài hơn 4.096 token; mẫu dài nhất của v4 và v5 là 3.882 token."));
C.push(H2("Định dạng mẫu huấn luyện"));
C.push(P("Mỗi mẫu gồm **prompt** (system prompt + văn bản CV) và **completion** (JSON nhãn). Prompt khi huấn luyện và khi chạy thật được tạo bởi **cùng một hàm** `render_prompt` – lệch prompt giữa hai giai đoạn là nguyên nhân chính khiến v1 bỏ sót các mục cuối CV. Toàn văn system prompt ở Phụ lục A."));
C.push(...code(`SYSTEM_PROMPT = """Trích xuất CV thành MỘT object JSON đúng schema bên dưới.
- Chỉ dùng thông tin có trong CV. Chép nguyên văn: không dịch, không tóm tắt...
- CV có thể là PDF hai cột nên các dòng bị xen kẽ: ghép đúng nội dung của từng mục...
- experience: ... company: CHỈ tên tổ chức ... end_date = null nếu đang làm ...
Schema: {"personal_info":{...},"education":[...],"experience":[...], ...}"""

def render_prompt(cv_text: str) -> str:
    return (f"<|im_start|>system\\n{SYSTEM_PROMPT}<|im_end|>\\n"
            f"<|im_start|>user\\n{cv_text.strip()}<|im_end|>\\n"
            f"<|im_start|>assistant\\n<think>\\n\\n</think>\\n\\n")   # mô hình viết JSON từ đây`, "ai-service/app/services/prompt_v3.py (rút gọn)"));
C.push(H2("Cấu hình và quy trình huấn luyện"));
C.push(tabCap("Siêu tham số huấn luyện"));
C.push(table(["Tham số", "Giá trị", "Ghi chú"], [
  ["Mô hình gốc", "unsloth/Qwen3-1.7B, nạp 4-bit", "QLoRA"],
  ["LoRA", "r = 16, α = 32, dropout 0", "q, k, v, o, gate, up, down"],
  ["Batch", "2 × tích luỹ 4 = 8", "GPU T4 16 GB"],
  ["Tốc độ học", "2·10⁻⁴, cosine, warmup 5 %", "AdamW 8-bit, weight decay 0,01"],
  ["Số epoch", "2", "v4: 224 bước; v5: ~278 bước"],
  ["Độ dài tối đa", "4.096 token", "Không mẫu nào bị cắt"],
  ["Chọn checkpoint", "dev loss thấp nhất, đánh giá mỗi 25 bước", "load_best_model_at_end"],
], [2300, 3300, 3471], { zebra: true }));
C.push(...code(`model = FastLanguageModel.get_peft_model(
    model, r=16, lora_alpha=32, lora_dropout=0, bias="none",
    target_modules=["q_proj","k_proj","v_proj","o_proj","gate_proj","up_proj","down_proj"],
    use_gradient_checkpointing="unsloth", random_state=42)
trainer = SFTTrainer(model=model, train_dataset=train_ds, eval_dataset=dev_ds, args=SFTConfig(
    per_device_train_batch_size=2, gradient_accumulation_steps=4, num_train_epochs=2,
    learning_rate=2e-4, lr_scheduler_type="cosine", warmup_ratio=0.05, optim="adamw_8bit",
    eval_steps=25, save_steps=25, load_best_model_at_end=True, max_length=4096))
# Chỉ tính loss trên phần JSON: system + CV bị che (label = -100)
trainer = train_on_responses_only(trainer, instruction_part="<|im_start|>user\\n",
    response_part="<|im_start|>assistant\\n<think>\\n\\n</think>\\n\\n")
trainer.train()
model.save_pretrained_gguf(f"{OUT_DIR}/gguf", tokenizer, quantization_method="q4_k_m")`, "ai-service/training/retrain_qwen3_v2.ipynb – cell [4]–[9] (rút gọn)"));
C.push(P("Notebook huấn luyện chạy trên Google Colab theo các bước ở Hình 3.3. Dataset được build trên máy cá nhân (nơi có CV thật) rồi tải lên Google Drive; notebook clone đúng nhánh mã nguồn, kiểm tra prompt trong dataset trùng với prompt serving, huấn luyện, chấm 20 CV thật, xuất GGUF và cuối cùng chạy luôn AI service kèm Cloudflare tunnel để kiểm thử qua HTTP."));
C.push(...figure("d_train_flow.png", 600, "Các bước của notebook huấn luyện trên Google Colab"));
C.push(H2("Kết quả huấn luyện"));
C.push(P("Hình 3.4 là đường loss của hai lần huấn luyện gần nhất. Cả hai đều hội tụ đều, dev loss giảm liên tục và không có dấu hiệu quá khớp; checkpoint tốt nhất của v3 ở bước 175 (dev loss 0,0026), của v4 ở bước 224 (0,0051). Dev loss của v4 cao hơn không có nghĩa v4 kém hơn, vì tập dev của v4 có thêm CV hai cột khó hơn; chất lượng được so sánh trên cùng 20 CV thật ở Chương 6."));
C.push(...figure("c_loss.png", 600, "Train loss và dev loss của mô hình v3 và v4 (thang log)"));
C.push(H2("Kết luận chương"));
C.push(P("Dữ liệu được xây dựng theo nguyên tắc \"văn bản huấn luyện giống văn bản chạy thật\": CV hư cấu được render thành PDF và trích xuất bằng chính bộ trích xuất của backend, kết hợp CV thật có hoán đổi thực thể. Mô hình được tinh chỉnh bằng QLoRA trên GPU miễn phí và xuất thành file GGUF 1,1 GB."));

// =====================================================================================
// CHƯƠNG 4 – KB & KG
C.push(H1("Knowledge Base và Knowledge Graph")); resetH();
C.push(H2("Vai trò trong hệ thống"));
C.push(P("Mô hình chỉ chép đúng chữ trong CV nên cùng một kỹ năng có thể ra \"ReactJS\", \"React.js\", \"react\". KB đưa tất cả về **một tên chuẩn** (React); KG cho biết kỹ năng nào kéo theo kỹ năng nào (Spring Boot cần Java) và kỹ năng nào thường đi cùng nhau. Đây là lớp tất định, nhanh (~5–7 ms/CV) và giải thích được: mỗi kết luận chỉ ra quan hệ và nguồn gốc của nó."));
C.push(H2("Nguồn dữ liệu"));
C.push(P("KB được xây **chỉ từ nguồn công khai có giấy phép mở**; mỗi dòng dữ liệu mang cột `source` trỏ về nguồn gốc để trích dẫn được (Bảng 4.1). Ảnh chụp (snapshot) nguyên văn của từng nguồn được lưu kèm MANIFEST (URL, ngày tải, phiên bản, SHA-256, giấy phép) để việc build có thể lặp lại không cần mạng."));
C.push(tabCap("Nguồn của KB (trích dẫn đầy đủ trong `ai-service/kb/seed/SOURCES.md`)"));
C.push(table(["Nguồn", "Giấy phép", "Lấy gì", "Dùng cho"], [
  ["Stack Overflow Developer Survey 2024–2026 [10]", "ODbL 1.0", "Danh sách công nghệ theo câu hỏi khảo sát (ngôn ngữ, CSDL, cloud, framework, công cụ…)", "Tên chuẩn kỹ năng + nhóm"],
  ["Stack Overflow tags", "CC BY-SA 4.0", "Tag ≥ 500 câu hỏi + tag đồng nghĩa (Spring MVC, Lombok…)", "Bổ sung kỹ năng, alias"],
  ["Wikidata [11]", "CC0 1.0", "Nhãn/alias Anh – Việt; quan hệ P277, P361, P527; trường đại học Việt Nam + tên viết tắt", "Alias, quan hệ KG, alias trường"],
  ["GitHub Linguist [13]", "MIT", "Ngôn ngữ lập trình + alias (C# ↔ csharp)", "Alias ngôn ngữ"],
  ["ESCO v1.2.1 [12]", "CC BY 4.0", "Kỹ năng chung + nghề ICT kèm nhãn thay thế", "Kỹ năng mềm, chức danh"],
  ["Wikipedia tiếng Việt", "CC BY-SA 4.0", "Danh sách trường đại học, học viện, cao đẳng", "Tên chính thức trường"],
  ["Sách Pro Git [14], Think Python [15]", "CC BY-NC(-SA) 3.0", "Mục lục, mục sách, số lần nhắc kỹ năng (không chép văn bản)", "KB1, quan hệ RELATED_TO"],
], [2500, 1300, 3271, 2000], { zebra: true }));
C.push(H2("Quy trình xây dựng KB"));
C.push(...figure("d_kb_build.png", 600, "Pipeline xây dựng KB2 (nguồn liên kết) và KB1 (sách PDF) rồi nạp vào Neo4j"));
C.push(B("**Chọn kỹ năng**: mọi lựa chọn công nghệ của khảo sát Stack Overflow; nhóm kỹ năng suy từ câu hỏi khảo sát (câu \"Databases\" → nhóm Database)."));
C.push(B("**Bổ sung từ Wikidata và Stack Overflow tags** cho thư viện, khái niệm mà khảo sát không hỏi (Hibernate, OOP, Spring MVC); chỉ nhận item thuộc lớp phần mềm/khái niệm tin học (kiểm tra bằng SPARQL) và tag có ≥ 500 câu hỏi. Từ vựng ứng viên chỉ lấy từ CV **hư cấu**, không bao giờ từ CV thật."));
C.push(B("**Alias**: nhãn và alias Anh – Việt của Wikidata, alias Linguist, nhãn thay thế ESCO; alias trỏ tới hai kỹ năng khác nhau bị loại vì mơ hồ."));
C.push(B("**Quan hệ**: P277 (programmed in) → REQUIRES, chỉ áp dụng cho framework/thư viện; P361/P527 → PART_OF; chỉ giữ khi hai đầu đều có trong KB, loại chu trình."));
C.push(B("**Trường học**: tên chính thức theo Wikipedia, bổ sung tên tiếng Anh, tên viết tắt (P1813) và biến thể chính tả (Ho Chi Minh City ↔ HCMC)."));
C.push(...code(`id,name,category,source,source_id                    # skills.csv
568,PostgreSQL,Database,stackoverflow-2026:Databases,Q192490
695,Spring Boot,Framework/Library,stackoverflow-2026:WebFramework,Q98731994
src_id,rel,dst_id,source                             # skill_edges.csv
695,REQUIRES,361,wikidata:Q98731994:P277             # Spring Boot -> Java
university_id,alias_key,source                       # university_aliases.csv
11,ptit,wikidata:Q10771881`, "ai-service/kb/seed/*.csv – ví dụ dữ liệu kèm nguồn"));
C.push(tabCap("Quy mô KB2 (bản build " + KB.date + ")"));
C.push(table(["Bảng", "Số dòng", "Theo nguồn"], KB.table, [2200, 1100, 5771], { zebra: true }));
C.push(H2("KB1 – tri thức trích từ sách PDF"));
C.push(P("Hai sách CNTT có giấy phép mở được dùng làm nguồn tri thức dạng tài liệu. Lệnh `python -m kb.books` đọc trang mục lục bằng `pdftotext`, dựng cây sách → chương → mục kèm số trang, đếm số lần mỗi mục nhắc tới một kỹ năng của KB2 (quan hệ MENTIONS), và tạo quan hệ RELATED_TO giữa hai kỹ năng cùng được nhắc trong ít nhất 2 mục. Chỉ tiêu đề mục, số trang và số đếm được lưu – không chép văn bản sách."));
{
  const rows = KB1.books.map((b) => { const ms = new Set(); b.sections.forEach((x) => Object.keys(x.mentions || {}).forEach((k) => ms.add(k)));
    return [b.title.split(":")[0], (b.authors || []).join(", "), b.licence, String(b.sections.length), String(ms.size)]; });
  C.push(tabCap("KB1 – " + KB1.related.length + " quan hệ RELATED_TO (ví dụ Git – GitHub cùng xuất hiện trong 48 mục)"));
  C.push(table(["Sách", "Tác giả", "Giấy phép", "Chương + mục", "Kỹ năng được nhắc"], rows, [2000, 2200, 1900, 1400, 1571]));
}
C.push(H2("Neo4j – gộp KB1 và KB2"));
C.push(P("Lệnh `python -m kb.neo4j_load` nạp KB2 (Skill, Alias, Category, University, UniversityAlias, JobTitle), KB1 (Book, Section, HAS_SECTION, MENTIONS) rồi gộp bằng quan hệ RELATED_TO và ABOUT. Mọi câu lệnh dùng MERGE theo lô nên chạy lại không sinh trùng; mọi nút và cạnh mang thuộc tính `source`."));
C.push(...code(`UNWIND $batch AS row                                  // KB2: kỹ năng + nhóm
MERGE (s:Skill {id: row.id})
SET s:KB2, s.name = row.name, s.category = row.category, s.source = row.source
MERGE (c:Category {name: row.category}) MERGE (s)-[:IN_CATEGORY]->(c)

UNWIND $batch AS row                                  // KB1: mục sách nhắc tới kỹ năng
MATCH (s:Section {id: row.section_id}) MATCH (sk:Skill {name: row.skill_name})
MERGE (s)-[m:MENTIONS]->(sk) SET m.count = row.count

UNWIND $batch AS row                                  // gộp: quan hệ có bằng chứng từ sách
MATCH (a:Skill {name: row.a}) MATCH (b:Skill {name: row.b})
MERGE (a)-[r:RELATED_TO {source: row.source}]->(b) SET r.weight = row.weight`, "ai-service/kb/neo4j_load.py – các câu Cypher chính (rút gọn)"));
C.push(tabCap("Nội dung Neo4j sau khi nạp và gộp (đếm thực tế)"));
C.push(table(["Nút", "Số lượng", "Quan hệ", "Số lượng"],
  (() => { const n = Object.entries(NEO.nodes), r = Object.entries(NEO.rels); const out = [];
    for (let k = 0; k < Math.max(n.length, r.length); k++) out.push([n[k] ? n[k][0] : "", n[k] ? num(n[k][1]) : "", r[k] ? r[k][0] : "", r[k] ? num(r[k][1]) : ""]);
    return out; })(), [2400, 2135, 2400, 2136], { zebra: true }));
C.push(...figure("kg_schema.png", 560, "Lược đồ KG trong Neo4j"));
C.push(...figure("kg_subgraph.png", 560, "Đồ thị con lấy từ Neo4j: KB2 (REQUIRES từ Wikidata) và KB1 (mục sách Pro Git MENTIONS kỹ năng); RELATED_TO là phần gộp"));
C.push(H2("Sử dụng KB và KG khi xử lý một CV"));
C.push(H3("Chuẩn hoá output bằng KB"));
C.push(P("Sau hậu kiểm, mỗi kỹ năng và mỗi mục tech_stack được link vào KB theo thứ tự: khớp chính xác → khớp alias đã chuẩn hoá → biến thể chính tả (bỏ số phiên bản, phần trong ngoặc: \"JavaScript(ES6+)\" → JavaScript) → nối bằng \"-\"/\"+\" → tách cụm (\"Java/Spring\") → khớp mờ (≥ 90, không áp dụng cho kỹ năng mềm). Kỹ năng kỹ thuật link được thay bằng **tên chuẩn**; kỹ năng mềm và kỹ năng không có trong KB **giữ nguyên như CV**; tên trường link được thay bằng tên chính thức."));
C.push(...code(`def _normalize_skill_list(items, linker):
    expanded = []
    for item in items:
        links = linker.link_many([item])          # exact → alias → biến thể → tách → fuzzy
        if links and all(l.skill_id is not None for l in links) and not all_soft_skills(links):
            expanded.extend(l.name for l in links) # "ReactJS" → "React"
        else:
            expanded.append(item)                  # không có trong KB / kỹ năng mềm: giữ như CV
    return dedupe_casefold(expanded)`, "ai-service/app/kb/normalize.py (rút gọn)"));
C.push(H3("Suy luận bằng KG"));
C.push(P("KG chạy trên mọi request nhưng kết quả chỉ trả ra khi gọi `?include=kg`, vì Module 2 tự thực hiện việc so khớp. Bảng 4.5 liệt kê các trường KG; ví dụ thật ở mục 5.10."));
C.push(tabCap("Các trường do KG bổ sung"));
C.push(table(["Trường", "Ý nghĩa"], [
  ["skills_normalized", "Từng kỹ năng thô → mã, tên, nhóm trong KB và cách khớp (exact / normalized / split / fuzzy / unlinked)"],
  ["implied_skills", "Kỹ năng suy ra qua REQUIRES / PART_OF, kèm đường suy luận (via)"],
  ["related_skills", "Kỹ năng liên quan theo sách (KB1, RELATED_TO), kèm trọng số"],
  ["skills_detected", "Kỹ năng của mô hình ∪ kỹ năng KB tìm thấy khi quét toàn văn bản CV"],
  ["flags", "Cảnh báo: kỹ năng chưa có trong KB, thiếu liên hệ, đã loại giá trị không có trong CV…"],
], [2400, 6671]));
C.push(...code(`queue = deque((sid, 0) for sid in linked_ids)        # kỹ năng đã link trong CV
while queue:                                          # duyệt đồ thị theo chiều rộng
    curr, depth = queue.popleft()
    for rel, dst in kb.edges.get(curr, []):
        if rel in ("REQUIRES", "PART_OF") and dst not in visited:
            visited.add(dst)
            implied.append({"name": kb.skills[dst][0], "via": [{"from": kb.skills[curr][0], "rel": rel}]})
            queue.append((dst, depth + 1))`, "ai-service/app/kg/enrich.py (rút gọn)"));
C.push(H2("Cập nhật KB"));
const updList = newList();
C.push(N("`python -m kb.fetch_sources --refresh`: tải phiên bản mới của các nguồn (khảo sát năm sau, Wikidata mới); thêm nguồn mới = thêm một hàm tải + một dòng MANIFEST.", updList));
C.push(N("`python -m kb.build_external`: dựng lại seed; duyệt thay đổi qua diff CSV trong git.", updList));
C.push(N("`python -m kb.books`: khi có sách mới hoặc KB2 thay đổi.", updList));
C.push(N("`python -m kb.neo4j_load --reset`: nạp lại và gộp trong Neo4j; khởi động lại AI service. **Mô hình không cần huấn luyện lại.**", updList));
C.push(N("Đo lại tỷ lệ link trên tập CV kiểm thử trước khi đưa vào sử dụng.", updList));
C.push(H2("KB và RAG"));
C.push(P("Trong hệ thống hiện tại KB được dùng **sau** khi mô hình sinh, không đưa vào prompt, tức chưa phải RAG. Lý do: nhiệm vụ trích xuất yêu cầu chép nguyên văn từ CV; đưa tên chuẩn vào prompt dễ khiến mô hình chép tên từ KB thay vì từ CV. Hướng RAG khả thi là quét văn bản CV bằng KB để lấy danh sách kỹ năng ứng viên, đưa vào prompt dưới dạng gợi ý (tham số `candidate_skills` đã có sẵn trong `render_prompt`) và vẫn giữ hậu kiểm grounding để loại giá trị không có trong CV; hướng này cần huấn luyện lại với dataset có gợi ý."));
C.push(H2("Kết luận chương"));
C.push(P("KB được xây dựng từ 6 nguồn liên kết công khai và 2 sách PDF, mọi dòng đều trích dẫn được nguồn; KG lưu trên Neo4j gộp hai nguồn tri thức. Trong pipeline, KB chuẩn hoá output của mô hình và KG cung cấp suy luận quan hệ kỹ năng theo yêu cầu."));

// =====================================================================================
// CHƯƠNG 5 – detailed flow with v4 outputs
C.push(H1("Luồng xử lý chi tiết từ backend đến AI service")); resetH();
C.push(P("Chương này đi theo một CV từ lúc backend nhận file đến lúc trả JSON, kèm mã nguồn ở mỗi bước. Ví dụ minh hoạ là một CV **hư cấu** (ứng viên \"Trinh Thanh Phong\" – hồ sơ b03-015 thuộc tập dev, mô hình chưa từng thấy khi huấn luyện) được render ở hai bố cục: một cột (L5) và hai cột kiểu dòng thời gian (L11). Toàn bộ output trong chương là output thật của **mô hình v4** chạy bằng llama.cpp trên CPU máy cá nhân."));
C.push(...figure("d_ai_pipeline.png", 600, "Các bước xử lý trong AI service"));
C.push(H2("Backend tiếp nhận file"));
C.push(P("Controller nhận file multipart, service kiểm tra file không rỗng và có đuôi .pdf, trích văn bản rồi gọi AI service. PDF quá 10 trang hoặc không có lớp văn bản (ảnh scan) bị từ chối với thông báo rõ ràng."));
C.push(...code(`@PostMapping(value = "/analyze-pdf", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
public ResponseEntity<CandidateProfile> analyzeCvPdf(@RequestParam("file") MultipartFile file) {
    return ResponseEntity.ok(cvAnalysisService.analyzeCvPdf(file));
}

public CandidateProfile analyzeCvPdf(MultipartFile file) {
    validatePdfFile(file);                                   // không rỗng, đuôi .pdf
    String extractedText = extractTextFromPdf(file);         // mục 5.2
    if (extractedText == null || extractedText.trim().isEmpty())
        throw new RuntimeException("Không thể trích xuất nội dung ... (có thể là file ảnh scan)");
    log.info("Trích xuất thành công {} ký tự từ file PDF, mode={}", extractedText.length(), pdfTextMode);
    return analyzeCv(extractedText);                         // mục 5.3: gọi AI service
}`, "backend/.../controller/CvAnalysisController.java + service/CvAnalysisService.java"));
C.push(H2("Backend trích xuất văn bản theo bố cục"));
C.push(P("Chế độ trích xuất được chọn bằng cấu hình `cv.pdf.text-mode` (mặc định `layout`; `legacy` giữ cách cũ của PDFBox để so sánh). Ở chế độ layout, `PdfTextExtractor` xử lý từng trang qua bốn bước:"));
const exList = newList();
C.push(N("**Lấy từ và toạ độ**: lớp `PositionStripper` kế thừa `PDFTextStripper`, nhận từng \"run\" chữ kèm toạ độ glyph. Một run bị tách đôi nếu hai glyph liền nhau cách xa nhau (> max(1,2 × chiều cao chữ, 3 × khoảng trắng)) – trường hợp PDFBox gộp chữ của hai cột có cùng đường cơ sở thành một từ.", exList));
C.push(N("**Gom dòng**: gom run theo toạ độ y, rồi tách mỗi nhóm tại khe x vượt trội (khe giữa hai cột, không phải khoảng trắng giữa từ).", exList));
C.push(N("**XY-cut đệ quy**: tìm khe dọc rộng nhất (≥ max(6pt, 0,8 × chiều cao chữ)) mà hai bên đều là cột thật; nếu không có, tìm khe ngang ≥ 1,5 lần chiều cao dòng; chia và đệ quy.", exList));
C.push(N("**Ghép khối**: mỗi vùng lá là một khối; dải ngày hẹp bên cạnh đoạn văn rộng được đặt sau đoạn văn đó; `TextNormalizer` chuẩn hoá khoảng trắng, nối từ bị ngắt dòng bằng gạch nối, đưa bullet về \"- \".", exList));
C.push(...code(`private void xyCut(int page, List<RawLine> region, List<TextBlock> blocks, int orderBase) {
    // 1) khe dọc: sắp theo x, tìm khe rộng nhất mà hai bên đều là cột thật
    for (int i = 1; i < byX.size(); i++) {
        float gap = byX.get(i).x0 - end;
        if (gap >= Math.max(6f, 0.8f * glyphHeight) && gap > widest
                && realColumn(byX.subList(0, i), regionWidth)
                && realColumn(byX.subList(i, byX.size()), regionWidth)) { widest = gap; split = i; }
        end = Math.max(end, byX.get(i).x1);
    }
    if (split >= 0) { xyCut(page, left, blocks, orderBase); xyCut(page, right, blocks, orderBase); return; }
    // 2) khe ngang: sắp theo y, khe >= 1.5 lần chiều cao dòng
    ...
    // 3) lá: một khối văn bản (đoạn rộng trước, dải ngày hẹp bên cạnh sau)
}

/** Cột thật: >= 3 đoạn và trải rộng >= 25 % vùng (dải ngày hẹp không phải cột). */
private boolean realColumn(List<RawLine> segments, float regionWidth) {
    if (segments.size() < 3) return false;
    return maxX1(segments) - minX0(segments) >= regionWidth * 0.25f;
}`, "backend/.../extraction/pdf/PdfTextExtractor.java (rút gọn)"));
C.push(P("Hình 5.2 là trang đầu của CV minh hoạ ở bố cục hai cột. Hai đoạn text bên dưới là kết quả trích xuất thật của cùng file PDF ở hai chế độ: ở chế độ legacy, mỗi dòng trộn cột trái và cột phải (\"Education Summary\", \"(HCMUT) high-throughput financial…\"); ở chế độ layout, cột trái (học vấn, chứng chỉ, ngoại ngữ) được đọc hết rồi mới tới cột phải (tóm tắt, kinh nghiệm)."));
C.push(new Paragraph({ alignment: AlignmentType.CENTER, keepNext: true, spacing: { before: 120, after: 60 },
  children: [img("one_page-1.png", 285, "/demo/"), new TextRun("    "), img("two_page-1.png", 285, "/demo/")] }));
C.push(figCap("Trang 1 của CV hư cấu minh hoạ: bố cục một cột L5 (trái) và hai cột dòng thời gian L11 (phải)"));
const nonEmpty = (t, from, n) => { const ls = t.split("\n").filter((l) => l.trim()); const i = from ? ls.findIndex((l) => l.startsWith(from)) : 0; return ls.slice(Math.max(0, i), Math.max(0, i) + n).join("\n"); };
C.push(...code(nonEmpty(TXT_LEG, "Education", 16), "Văn bản trích xuất – chế độ legacy (PDFBox sortByPosition), CV hai cột"));
C.push(...code(nonEmpty(TXT_LAY, "Education", 24), "Văn bản trích xuất – chế độ layout (XY-cut), cùng CV"));
C.push(H2("Backend gọi AI service"));
C.push(P("Văn bản được đóng gói thành `AiCvRequest { cv_text }` và gửi qua Feign client tới `POST /api/v1/extract-cv`. Địa chỉ AI service cấu hình bằng `ai.service.url` (mặc định `http://localhost:8000`; khi chạy mô hình trên Colab là URL Cloudflare tunnel). Backend trả về phần `data` của response, tức CandidateProfile."));
C.push(H2("AI service: làm sạch và dựng prompt"));
C.push(P("AI service kiểm tra `cv_text` và tham số `include`, làm sạch văn bản (`clean_cv_text`: chuẩn hoá xuống dòng, bỏ ký tự điều khiển), đếm token và từ chối (413) nếu prompt cộng phần sinh vượt ngữ cảnh 8.192 token. Prompt được dựng bằng `render_prompt` của prompt v3 – cùng hàm đã dùng khi tạo dataset. Phiên bản mô hình được chọn bằng biến môi trường `PROMPT_VERSION` (v3 mặc định; v4 dùng prompt v3 với file `model-v4-q4_k_m.gguf`)."));
C.push(H2("Sinh JSON có kiểm soát"));
C.push(P("Mô hình sinh theo kiểu stream với temperature 0 và tối đa 2.048 token. Bộ chặn lặp `LoopGuard` đọc JSON đang được viết và dừng ngay khi output thoái hoá: một chuỗi dài quá 2.000 ký tự, hoặc cùng một giá trị lặp 3 lần trong một danh sách. Phần JSON đã sinh được sửa (`salvage`: cắt chuỗi dở, json_repair, bỏ phần tử trùng) thay vì chờ tới trần token."));
C.push(...code(`resp = state.llm(prompt=prompt, max_tokens=config.MAX_NEW_TOKENS, temperature=0.0,
                 stop=["<|im_end|>", "<|endoftext|>"], stream=True)
guard = LoopGuard(config.LOOP_MAX_STRING_CHARS, config.LOOP_MAX_REPEATS)   # 2000, 3
for chunk in resp:
    text = chunk["choices"][0]["text"]
    parts.append(text)
    if guard.feed(text):                 # "long_string" | "repeated_value"
        reason = guard.reason
        break`, "ai-service/app/services/generator.py (rút gọn)"));
C.push(H2("Sinh nối tiếp khi output bị cắt"));
C.push(P("Khi JSON bị cắt (chạm trần token hoặc bị LoopGuard dừng), `plan_continuation` tìm điểm cuối cùng mà JSON còn hoàn chỉnh, bỏ phần tử dở dang, rồi mồi lại mô hình bằng phần JSON đó cộng tên khoá cấp cao còn thiếu tiếp theo (ví dụ `\"skills\": [`). Mô hình viết tiếp phần đuôi; `merge_outputs` ghép hai phần. Bước này lấy lại được các mục cuối CV (kỹ năng, chứng chỉ, ngoại ngữ) vốn hay bị mất ở CV dài."));
C.push(...code(`def _continue_llama(prompt, raw_text, first):
    plan = plan_continuation(raw_text, first.reason)     # (tiền tố JSON hoàn chỉnh, khoá tiếp theo)
    if plan is None:
        return first
    seed, next_key = plan
    second = _generate_llama(prompt + seed, max_tokens=budget, prefix=seed)
    return merge_outputs(first, second)`, "ai-service/app/services/generator.py (rút gọn)"));
C.push(H2("Parse JSON và ghép mảnh"));
C.push(P("Đôi khi mô hình đóng ngoặc quá sớm khiến JSON tách thành nhiều mảnh. `merge_fragments` ghép lại: khoá cấp cao của mảnh sau bổ sung vào object chính; mảnh có dạng dự án/kinh nghiệm/học vấn được đưa về đúng danh sách. Nếu vẫn không thu được object có nội dung, AI service trả 502."));
C.push(H2("Hậu kiểm"));
C.push(...code(`def postprocess(data, cv_text):
    profile = normalize_profile(data, stats)              # đúng schema, đúng kiểu
    profile["skills"] = clean_skill_list(profile["skills"], stats)   # tách/sửa ngoặc "AWS (IAM"
    profile = ground_profile(profile, cv_text, stats)     # mọi giá trị phải có trong CV
    profile = fix_date_order(profile, stats)              # đổi start/end nếu start > end
    profile = cleanup_profile(profile, stats)             # công ty trùng tên dự án, địa chỉ, kỹ năng rác
    return profile, stats`, "ai-service/app/postprocess/pipeline.py (rút gọn)"));
C.push(B("**Grounding**: mọi chuỗi phải xuất hiện trong văn bản CV (so khớp đã chuẩn hoá, mờ ≥ 85); chức danh phải nằm gần tên công ty; email, điện thoại phải có trong CV."));
C.push(B("**Sửa ngày**: nếu ngày bắt đầu sau ngày kết thúc thì đổi chỗ."));
C.push(B("**Dọn rác**: bỏ \"công ty\" trùng tên một dự án, bỏ công ty chỉ là địa chỉ (toàn từ địa danh hoặc ≥ 3 phần cách nhau bằng dấu phẩy, không có từ khoá tổ chức), bỏ kỹ năng chỉ có chữ số hoặc dài quá 8 từ."));
C.push(H2("Chuẩn hoá KB, làm giàu KG và lắp response"));
C.push(...code(`raw_profile = deepcopy(data)                                   # sau hậu kiểm
enriched = enrich(data, kb, pp_stats, cv_text=cv_text)         # KG luôn chạy
base = {k: v for k, v in raw_profile.items() if k not in KG_FIELDS}
base = normalize_profile_with_kb(base, kb)                     # KB: tên chuẩn
if "kg" in include:  base |= {k: enriched[k] for k in KG_FIELDS}
if "raw" in include: base["raw_profile"] = raw_profile
return {"data": base}`, "ai-service/app/api/routes.py (rút gọn)"));
C.push(H2("Output thật của mô hình v4"));
C.push(H3("CV một cột – output mặc định"));
C.push(P(`Gọi \`POST /api/v1/extract-cv\` với văn bản layout của CV một cột (${num(TXT_ONE.length)} ký tự) cho kết quả dưới đây sau khoảng 21–34 giây trên CPU. Đối chiếu với hồ sơ gốc: đúng cả hai công việc (gồm ngày bắt đầu, ngày kết thúc và end_date = null cho công việc hiện tại), đủ 13/13 kỹ năng, đúng trường, dự án, chứng chỉ và hai ngoại ngữ; không có giá trị bịa.`));
function pretty(v, ind = "") {
  const flat = JSON.stringify(v);
  if (flat.length + ind.length <= 100 || v === null || typeof v !== "object") return flat;
  const nx = ind + "  ";
  if (Array.isArray(v) && v.every((x) => typeof x === "string" && x.length < 40)) {
    const lines = []; let cur = "";
    v.map((x) => JSON.stringify(x)).forEach((x) => { if (cur && (nx + cur + ", " + x).length > 100) { lines.push(cur + ","); cur = x; } else cur = cur ? cur + ", " + x : x; });
    lines.push(cur);
    return "[\n" + lines.map((l) => nx + l).join("\n") + "\n" + ind + "]";
  }
  if (Array.isArray(v)) return "[\n" + v.map((x) => nx + pretty(x, nx)).join(",\n") + "\n" + ind + "]";
  return "{\n" + Object.entries(v).map(([k, x]) => nx + JSON.stringify(k) + ": " + pretty(x, nx)).join(",\n") + "\n" + ind + "}";
}
C.push(...code(pretty({ data: OUT1 }), "Response của AI service (mô hình v4, CV một cột)"));
C.push(H3("Output khi gọi ?include=kg"));
const kg = OUT1KG;
const kgShow = {
  skills_normalized: kg.skills_normalized.slice(0, 5).map((s) => ({ raw: s.raw, name: s.name, category: s.category, method: s.method })),
  implied_skills: kg.implied_skills.map((s) => ({ name: s.name, via: s.via })),
  related_skills: kg.related_skills.slice(0, 4).map((s) => ({ name: s.name, weight: s.weight, via: s.via })),
  flags: kg.flags,
};
C.push(...code(pretty(kgShow), "Các trường KG (rút gọn: 5/13 skills_normalized, 4/" + kg.related_skills.length + " related_skills)"));
C.push(P(`Kết quả cho thấy cả mặt mạnh và giới hạn của lớp KB/KG. 8/13 kỹ năng link được về KB (Go, Python, PostgreSQL, Redis, RabbitMQ, Docker, Grafana và gRPC – hiển thị theo tên chuẩn \"GRPC\" của nguồn Stack Overflow); 5 kỹ năng chưa có trong KB (Echo, Chi, ScyllaDB, NATS, OpenTelemetry) được giữ nguyên như CV và báo bằng cờ \`SKILLS_UNLINKED\`. \`related_skills\` lấy từ hai cuốn sách (Python → Git, Object-oriented programming). implied_skills suy từ quan hệ \"programmed in\" của Wikidata cho gRPC ra C, C++, Elixir – đúng với Wikidata (thư viện gRPC được cài đặt bằng nhiều ngôn ngữ) nhưng không phải bằng chứng ứng viên biết các ngôn ngữ đó; vì vậy các trường KG chỉ là gợi ý và được ẩn khỏi output mặc định.`));
C.push(H3("CV hai cột – phân tích lỗi"));
C.push(P("Cùng hồ sơ ở bố cục hai cột L11 (Hình 5.2, phải), mô hình v4 trích đúng họ tên, liên hệ, tóm tắt, trường, cả hai công ty và chức danh, toàn bộ mô tả công việc, dự án, chứng chỉ và hai ngoại ngữ; skills đạt 12/13 (thiếu \"Chi\" nằm trong ngoặc ở dòng \"Frameworks: Echo (Chi, gRPC)\"). Lỗi đáng kể nằm ở ngày làm việc:"));
C.push(tabCap("Ngày làm việc trên CV hai cột dòng thời gian (mô hình v4)"));
const g2 = [["Chotot", "Aug 2020", "Dec 2022"], ["Kyber Network", "Jan 2023", "null (Present)"]];
C.push(table(["Công ty", "Hồ sơ gốc (bắt đầu – kết thúc)", "Output v4 (bắt đầu – kết thúc)", "Đánh giá"],
  OUT2.experience.map((e, i) => [e.company, g2[i][1] + " – " + g2[i][2], (e.start_date || "null") + " – " + (e.end_date || "null"), i === 0 ? "Sai: lấy ngày kết thúc làm ngày bắt đầu" : "Đúng"]),
  [1800, 2500, 2500, 2271]));
C.push(P("Ở bố cục dòng thời gian, ngày kết thúc in phía trên công ty và ngày bắt đầu in sau mô tả cuối cùng (xem đoạn text layout ở trên: \"Dec 2022 / Chotot / … / Aug 2020\"). Mô hình hiểu ngày đầu tiên gặp là ngày bắt đầu. Cùng lỗi này xuất hiện trên một CV thật hai cột trong tập kiểm thử; dataset v5 bổ sung bố cục L15 và thêm dữ liệu dòng thời gian để khắc phục (mục 6.4)."));
C.push(H2("Kết luận chương"));
C.push(P("Luồng xử lý gồm hai nửa rõ ràng: backend chịu trách nhiệm đưa văn bản về đúng thứ tự đọc, AI service chịu trách nhiệm biến văn bản thành JSON đáng tin cậy. Output thật của mô hình v4 trên CV hư cấu cho thấy hệ thống trích xuất chính xác CV một cột và phần lớn thông tin của CV hai cột; lỗi còn lại tập trung ở ngày tháng của bố cục dòng thời gian."));

// =====================================================================================
// CHƯƠNG 6 – experiments
C.push(H1("Thử nghiệm, đánh giá và triển khai")); resetH();
C.push(H2("Môi trường và dữ liệu thử nghiệm"));
C.push(tabCap("Môi trường thử nghiệm"));
C.push(table(["Hạng mục", "Cấu hình"], [
  ["Huấn luyện, đánh giá GPU", "Google Colab, GPU NVIDIA T4 16 GB"],
  ["Chạy cục bộ", "Máy cá nhân Linux, CPU (không GPU), llama.cpp"],
  ["Mô hình", "Qwen3-1.7B + LoRA, GGUF Q4_K_M (~1,1 GB)"],
  ["Dữ liệu đánh giá", "val (99 CV tổng hợp), val_swap (99, đổi tên), dev (45 CV bố cục thật), test_real (20 CV thật chưa từng dùng để train; 19 CV dùng cho so sánh text, cộng 1 CV hai cột bổ sung)"],
], [2600, 6471]));
C.push(P("Mọi con số trên CV thật trong chương này là số đếm và điểm F1 tổng hợp; nội dung CV thật không được đưa vào đồ án."));
C.push(H2("So sánh các mô hình"));
C.push(P("Bốn mô hình được chấm bằng cùng một bộ đánh giá (biến thể B): **rule-based** (luật + regex của backend), và ba lần tinh chỉnh **v1, v2, v3**. Các LLM chạy bằng file GGUF qua đúng mã nguồn serving."));
{
  const splits = CMP.splits, models = CMP.models.filter((m) => m !== "base");
  const mean = (cell) => { if (!cell) return null; const v = CMP.fields.filter(([f]) => f !== "experience.job_title").map(([f]) => cell[f]).filter((x) => x !== null && x !== undefined); return v.length ? v.reduce((a, b) => a + b, 0) / v.length : null; };
  C.push(tabCap("F1 trung bình 7 trường (company, school, skills, project, certificates, honours, languages)"));
  C.push(table(["Mô hình", "val (99)", "val_swap (99)", "dev (45)", "test_real (20)"],
    models.map((m) => [CMP.label[m], ...splits.map((sp) => fmt(mean(CMP.table[m + "|" + sp])))]),
    [2471, 1650, 1650, 1650, 1650], { zebra: true }));
  C.push(P("Mô hình Qwen3-1.7B gốc (chưa tinh chỉnh, zero-shot) đã được chuẩn bị trong notebook `eval_models_colab.ipynb` nhưng chưa chạy trên GPU nên chưa có số liệu; ô \"–\" là cấu hình chưa đo."));
  C.push(...figure("chart_mean_f1.png", 600, "F1 trung bình theo mô hình và tập dữ liệu"));
  C.push(tabCap("F1 từng trường trên 20 CV thật (văn bản trích xuất cũ)"));
  C.push(table(["Trường", ...models.map((m) => CMP.label[m])],
    CMP.fields.map(([f, name]) => [name, ...models.map((m) => fmt((CMP.table[m + "|test_real"] || {})[f]))]),
    [2271, 1700, 1700, 1700, 1700], { zebra: true }));
}
C.push(P("Phương pháp dựa trên luật đạt F1 trung bình chỉ khoảng 0,32 trên CV thật, kém mô hình tinh chỉnh hơn 30 điểm. Từ v1 đến v3, điểm trên CV tổng hợp gần tuyệt đối nhưng trên CV thật vẫn thấp hơn rõ rệt – khoảng cách này dẫn tới việc xử lý lại khâu trích xuất văn bản (mục 6.3)."));
C.push(H2("Ảnh hưởng của trích xuất theo bố cục và các bước serving"));
C.push(P("Cùng mô hình v3 được chạy trên 19 CV thật với ba cấu hình: văn bản PDFBox cũ (legacy), văn bản theo bố cục (feature 011) và văn bản theo bố cục cộng sinh nối tiếp, hậu kiểm mở rộng (feature 012)."));
C.push(tabCap("F1 trên 19 CV thật – mô hình v3"));
C.push(table(["Trường", "Legacy", "Layout", "Layout + 012"], [
  ["company", "0,667", "0,780", "**0,941**"], ["job_title", "0,800", "0,929", "**0,966**"], ["school", "0,865", "1,000", "1,000"],
  ["project", "0,729", "0,860", "**0,882**"], ["skills", "0,737", "0,822", "**0,857**"], ["certificates", "0,308", "**0,556**", "0,500"],
  ["languages", "0,667", "**0,759**", "0,750"], ["tỷ lệ bịa", "1,6 %", "0,7 %", "**0 %**"],
], [2471, 2200, 2200, 2200], { zebra: true }));
C.push(...figure("c_textmode.png", 600, "Ảnh hưởng của văn bản theo bố cục và các bước serving (19 CV thật, mô hình v3)"));
C.push(P("Chỉ riêng việc đưa văn bản về đúng thứ tự đọc đã tăng F1 ở mọi trường mà không cần huấn luyện lại (company +0,11, school +0,14, project +0,13). Sinh nối tiếp và hậu kiểm tăng thêm company lên 0,941 và đưa tỷ lệ bịa về 0. certificates giảm nhẹ vì mô hình lấy thêm 2 chứng chỉ có trong CV nhưng không có trong nhãn nháp; trường này chỉ có 9 giá trị nên dao động lớn."));
C.push(H2("Mô hình v4"));
C.push(P("Mô hình v4 được huấn luyện trên dataset v4 (toàn bộ văn bản theo bố cục, thêm bố cục L11–L14) và đánh giá qua API trên Colab với đúng pipeline serving của mô hình v3."));
C.push(tabCap("So sánh v3 và v4 trên 19 CV thật (cùng pipeline serving)"));
C.push(table(["Trường", "v3 + 012", "v4 + 012", "Chênh lệch"], [
  ["company", "0,941", "0,788", "−0,153"], ["job_title", "0,966", "0,909", "−0,057"], ["school", "1,000", "1,000", "0"],
  ["project", "0,882", "0,822", "−0,060"], ["skills", "0,857", "**0,889**", "+0,032"], ["skills (tên chuẩn)", "0,864", "**0,896**", "+0,032"],
  ["certificates", "0,500", "0,526", "+0,026"], ["honours", "0,000", "0,286", "+0,286"], ["languages", "0,750", "**0,815**", "+0,065"],
  ["tỷ lệ bịa", "0 %", "0 %", "0"],
], [2471, 2200, 2200, 2200], { zebra: true }));
C.push(...figure("c_v3_v4.png", 600, "F1 của v3 và v4 trên 19 CV thật"));
C.push(P("Trên CV hai cột bổ sung (CV thật có các công việc ở trang 2), v4 lấy đủ 3/3 công ty trong khi v3 chỉ lấy được 1/3 – đây là mục tiêu chính của v4. Ngược lại, toàn bộ phần giảm của company trên 19 CV đến từ 2 CV: một CV có 5 công việc liên tiếp, mỗi công việc một dòng mô tả, v4 chỉ giữ công việc đầu; một CV sinh viên chỉ có dự án, v4 đưa 2 dự án vào kinh nghiệm. Phân tích dataset cho thấy nguyên nhân: v3 và v4 đều có **0** mẫu huấn luyện dạng \"≥ 4 công việc, mỗi công việc ≤ 2 dòng\", và 184 CV sinh thêm ở v4 đều có kinh nghiệm làm việc khiến tỷ lệ CV không có kinh nghiệm giảm từ 9,7 % xuống 7,7 %."));
C.push(P("Dataset v5 (đã chuẩn bị, Bảng 3.3) bổ sung đúng ba dạng còn thiếu: 65 CV 4–6 công việc ngắn, CV sinh viên (tỷ lệ CV không có kinh nghiệm tăng lên 12,1 %) và 74 CV bố cục L15 cho lỗi ngày tháng ở mục 5.10.3. Tiêu chí chấp nhận v5: company ≥ 0,90 và skills ≥ 0,85 trên 19 CV thật, đồng thời giữ 3/3 công ty và đúng ngày trên CV hai cột."));
C.push(H2("Hiệu năng"));
C.push(tabCap("Thời gian xử lý một CV"));
C.push(table(["Cấu hình", "Thời gian / CV", "Ghi chú"], [
  ["Rule-based (CPU)", "~9 ms", "Không dùng mô hình"],
  ["Mô hình v4, GPU T4 (Colab)", "5–26 s", "20 CV thật qua API"],
  ["Mô hình v4, CPU máy cá nhân", "21–37 s", "CV minh hoạ Chương 5; CV dài hơn 40–70 s"],
  ["KB + KG", "~7 ms", "Đo trong bộ đánh giá (biến thể C)"],
], [3200, 2000, 3871]));
C.push(H2("Đánh giá KB"));
C.push(P(KB.coverage_note));
C.push(H2("Triển khai"));
C.push(...code(`# 1. Knowledge Graph (Neo4j trong docker, cổng 7687; mật khẩu trong infra/kg/.env)
docker compose -f infra/kg/docker-compose.yml --env-file infra/kg/.env up -d
cd ai-service && set -a && . ../infra/kg/.env && set +a
python -m kb.neo4j_load --uri bolt://localhost:7687 --user neo4j --password-env NEO4J_PASSWORD --reset

# 2. AI service với mô hình v4 (~1,1 GB)
gdown 1mKd0SmhnUKpJTXkH3xQs0puEwYgqFQWn -O merged_model/model-v4-q4_k_m.gguf
PROMPT_VERSION=v4 NEO4J_URI=bolt://localhost:7687 uvicorn main:app --port 8000

# 3. Backend (gọi AI service tại ai.service.url)
cd ../backend && ./mvnw spring-boot:run`, "Cài đặt và chạy trên máy cá nhân"));
C.push(P("Khi không có GPU, AI service có thể chạy trên Colab bằng notebook `ai-service/run_on_colab.ipynb` (đặt `MODEL = \"v4\"`): notebook clone mã nguồn, tải GGUF, chạy service và mở Cloudflare tunnel; backend trỏ `ai.service.url` vào URL được in ra."));
C.push(tabCap("Biến môi trường chính của AI service"));
C.push(table(["Biến", "Mặc định", "Ý nghĩa"], [
  ["PROMPT_VERSION", "v3", "Phiên bản prompt + mô hình: v1, v2, v3, v4, v5"],
  ["GGUF_MODEL_PATH", "merged_model/model-<phiên bản>-q4_k_m.gguf", "File mô hình"],
  ["MAX_NEW_TOKENS", "2048", "Số token tối đa mô hình được sinh"],
  ["LOOP_MAX_STRING_CHARS / LOOP_MAX_REPEATS", "2000 / 3", "Ngưỡng chặn lặp"],
  ["CONTINUATION_ENABLED", "true", "Sinh nối tiếp khi JSON bị cắt"],
  ["KG_ENABLED", "true", "Nạp KB, chuẩn hoá, chạy KG"],
  ["NEO4J_URI / NEO4J_USER / NEO4J_PASSWORD", "– / neo4j / –", "Kho KG chính; không đặt thì dùng PostgreSQL (KB_DSN) hoặc CSV"],
], [3300, 2900, 2871], { zebra: true }));
C.push(H2("Kết luận chương"));
C.push(P("Mô hình tinh chỉnh vượt xa phương pháp dựa trên luật và mô hình gốc. Đóng góp lớn nhất trên CV thật đến từ việc trích xuất văn bản theo bố cục, tiếp theo là sinh nối tiếp và hậu kiểm. Mô hình v4 cải thiện skills, languages và CV hai cột nhiều trang nhưng giảm company do thiếu hai dạng dữ liệu, đã được bổ sung trong dataset v5."));

// =====================================================================================
C.push(H1U("KẾT LUẬN VÀ HƯỚNG PHÁT TRIỂN"));
C.push(new Paragraph({ children: [new TextRun({ text: "1. Kết quả đạt được", bold: true })], spacing: { before: 120, after: 80 } }));
C.push(B("Xây dựng hoàn chỉnh Module 1: backend Spring Boot trích xuất văn bản PDF theo bố cục bằng XY-cut, AI service FastAPI chạy mô hình Qwen3-1.7B tinh chỉnh bằng LoRA, trả CandidateProfile cho Module 2."));
C.push(B("Xây dựng quy trình dữ liệu tái lập được: 15 bố cục CV mẫu, CV hư cấu được render và trích xuất bằng chính bộ trích xuất của hệ thống, CV thật được căn nhãn và hoán đổi thực thể; 5 phiên bản dataset."));
C.push(B("Xây dựng KB từ 6 nguồn công khai và 2 sách PDF, mọi dòng có nguồn; KG trên Neo4j gộp KB1 và KB2; KB chuẩn hoá output, KG cung cấp suy luận quan hệ kỹ năng."));
C.push(B("Trên 19 CV thật chưa từng dùng để huấn luyện: company 0,941, job_title 0,966, school 1,000, skills 0,857–0,889, không có giá trị bịa; thời gian 5–26 s/CV trên GPU T4."));
C.push(new Paragraph({ children: [new TextRun({ text: "2. Hạn chế", bold: true })], spacing: { before: 120, after: 80 } }));
C.push(B("Tập kiểm thử CV thật nhỏ (20 CV) nên một CV lỗi làm điểm một trường dao động tới 0,15."));
C.push(B("Ngày tháng trên bố cục dòng thời gian, kỹ năng nằm trong ngoặc, honours và certificates còn sai sót."));
C.push(B("Chưa hỗ trợ CV dạng ảnh scan; KB chưa phủ hết công nghệ mới (Echo, ScyllaDB, NATS…); quan hệ REQUIRES từ Wikidata có thể thừa."));
C.push(new Paragraph({ children: [new TextRun({ text: "3. Hướng phát triển", bold: true })], spacing: { before: 120, after: 80 } }));
C.push(B("Huấn luyện v5 trên dataset đã chuẩn bị và mở rộng tập kiểm thử CV thật."));
C.push(B("Bổ sung OCR cho CV dạng ảnh; thử nghiệm KB + RAG (gợi ý kỹ năng từ KB trong prompt) kết hợp grounding."));
C.push(B("Cập nhật KB định kỳ từ khảo sát Stack Overflow và Wikidata mới; lọc quan hệ REQUIRES theo ngữ cảnh."));

// =====================================================================================
C.push(H1U("TÀI LIỆU THAM KHẢO"));
[
  "[1] Qwen Team, \"Qwen3 Technical Report\", arXiv:2505.09388, 2025.",
  "[2] E. J. Hu, Y. Shen, P. Wallis et al., \"LoRA: Low-Rank Adaptation of Large Language Models\", ICLR, 2022.",
  "[3] T. Dettmers, A. Pagnoni, A. Holtzman, L. Zettlemoyer, \"QLoRA: Efficient Finetuning of Quantized LLMs\", NeurIPS, 2023.",
  "[4] A. Vaswani, N. Shazeer, N. Parmar et al., \"Attention Is All You Need\", NeurIPS, 2017.",
  "[5] G. Nagy, S. Seth, \"Hierarchical Representation of Optically Scanned Documents\", Proc. 7th International Conference on Pattern Recognition, pp. 347–349, 1984.",
  "[6] The Apache Software Foundation, \"Apache PDFBox\", https://pdfbox.apache.org.",
  "[7] G. Gerganov et al., \"llama.cpp – LLM inference in C/C++\", https://github.com/ggml-org/llama.cpp.",
  "[8] Unsloth AI, \"Unsloth: faster LLM fine-tuning\", https://github.com/unslothai/unsloth.",
  "[9] Hugging Face, \"TRL – Transformer Reinforcement Learning\", https://github.com/huggingface/trl.",
  "[10] Stack Overflow, \"Developer Survey 2024, 2025, 2026\", https://survey.stackoverflow.co (ODbL 1.0).",
  "[11] Wikimedia Foundation, \"Wikidata\", https://www.wikidata.org (CC0 1.0).",
  "[12] European Commission, \"ESCO – European Skills, Competences, Qualifications and Occupations v1.2.1\", https://esco.ec.europa.eu (CC BY 4.0).",
  "[13] GitHub, \"Linguist – languages.yml\", https://github.com/github-linguist/linguist (MIT).",
  "[14] S. Chacon, B. Straub, Pro Git, 2nd ed., Apress, 2014 (CC BY-NC-SA 3.0).",
  "[15] A. B. Downey, Think Python: How to Think Like a Computer Scientist, 2nd ed., Green Tea Press, 2015 (CC BY-NC 3.0).",
  "[16] Neo4j, Inc., \"Neo4j 5 Documentation – Cypher Manual\", https://neo4j.com/docs.",
  "[17] A. Hogan, E. Blomqvist, M. Cochez et al., \"Knowledge Graphs\", ACM Computing Surveys, vol. 54, no. 4, 2021.",
  "[18] P. Lewis, E. Perez, A. Piktus et al., \"Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks\", NeurIPS, 2020.",
  "[19] S. Ramírez, \"FastAPI\", https://fastapi.tiangolo.com; VMware, \"Spring Boot Reference Documentation\", https://spring.io/projects/spring-boot.",
  "[20] W. Shen, J. Wang, J. Han, \"Entity Linking with a Knowledge Base: Issues, Techniques, and Solutions\", IEEE TKDE, vol. 27, no. 2, pp. 443–460, 2015.",
].forEach((r) => C.push(new Paragraph({ children: [new TextRun(r)], spacing: { after: 100, line: 300 }, indent: { left: 567, hanging: 567 }, alignment: AlignmentType.LEFT })));

// =====================================================================================
C.push(H1U("PHỤ LỤC A. SYSTEM PROMPT V3"));
{
  const src = fs.readFileSync(B_ + "/../../ai-service/app/services/prompt_v3.py", "utf8");
  const sp = src.split('SYSTEM_PROMPT = """')[1].split('"""')[0];
  const wrapped = sp.split("\n").flatMap((l) => { const out = []; let s = l; while (s.length > 105) { let k = s.lastIndexOf(" ", 105); if (k < 40) k = 105; out.push(s.slice(0, k)); s = "  " + s.slice(k).trimStart(); } out.push(s); return out; });
  C.push(...code(wrapped.join("\n"), "ai-service/app/services/prompt_v3.py – SYSTEM_PROMPT (dòng dài được ngắt để in)"));
}
C.push(H1U("PHỤ LỤC B. VĂN BẢN ĐẦU VÀO CỦA CV MINH HOẠ"));
C.push(P("Văn bản layout của CV hư cấu một cột (bố cục L5) – chính là `cv_text` gửi tới AI service ở mục 5.10.1."));
C.push(...code(TXT_ONE.split("\n").filter((l) => l.trim()).map((l) => l.length > 110 ? l.slice(0, 107) + "…" : l).join("\n"), "cv_text – CV hư cấu b03-015, bố cục L5"));

// =====================================================================================
const numbering = { config: [
  { reference: "bullets", levels: [{ level: 0, format: LevelFormat.BULLET, text: "–", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 720, hanging: 300 } } } },
    { level: 1, format: LevelFormat.BULLET, text: "+", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 1300, hanging: 300 } } } }] },
  ...Array.from({ length: numRef }, (_, i) => ({ reference: `n${i + 1}`, levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] })),
] };
const pageProps = (fmtType, start) => ({ page: { size: { width: 11906, height: 16838 }, margin: { top: 1134, right: 1134, bottom: 1134, left: 1701 },
  pageNumbers: fmtType ? { start, formatType: fmtType } : undefined } });
const footer = () => ({ default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ children: [PageNumber.CURRENT], size: 24 })] })] }) });
const dbl = { style: BorderStyle.DOUBLE, size: 12, color: "1F3864", space: 20 };
const doc = new Document({
  features: { updateFields: true },
  creator: "recruit_system", title: "Đồ án – Module 1 trích xuất thông tin CV",
  styles: {
    default: { document: { run: { font: FONT, size: 26 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { font: FONT, size: 30, bold: true }, paragraph: { alignment: AlignmentType.CENTER, spacing: { before: 0, after: 360 }, keepNext: true, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { font: FONT, size: 27, bold: true }, paragraph: { spacing: { before: 240, after: 120 }, keepNext: true, outlineLevel: 1 } },
      { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { font: FONT, size: 26, bold: true, italics: true }, paragraph: { spacing: { before: 180, after: 100 }, keepNext: true, outlineLevel: 2 } },
      { id: "FrontTitle", name: "Front Title", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { font: FONT, size: 30, bold: true }, paragraph: { alignment: AlignmentType.CENTER, spacing: { before: 0, after: 360 }, keepNext: true } },
      { id: "HinhCaption", name: "Hinh Caption", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { font: FONT, size: 24, italics: true }, paragraph: { alignment: AlignmentType.CENTER, spacing: { before: 60, after: 240 } } },
      { id: "BangCaption", name: "Bang Caption", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { font: FONT, size: 24, italics: true }, paragraph: { alignment: AlignmentType.CENTER, spacing: { before: 200, after: 100 }, keepNext: true } },
    ],
  },
  numbering,
  sections: [
    { properties: { page: { size: { width: 11906, height: 16838 }, margin: { top: 1134, right: 1134, bottom: 1134, left: 1701 },
        borders: { pageBorderTop: dbl, pageBorderBottom: dbl, pageBorderLeft: dbl, pageBorderRight: dbl } } }, children: cover },
    { properties: pageProps(NumberFormat.LOWER_ROMAN, 1), footers: footer(), children: front },
    { properties: pageProps(NumberFormat.DECIMAL, 1), footers: footer(), children: C },
  ],
});
Packer.toBuffer(doc).then((buf) => { fs.writeFileSync(process.argv[2], buf); console.log("written", process.argv[2]); });

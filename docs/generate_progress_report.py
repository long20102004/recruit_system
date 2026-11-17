#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Sinh báo cáo tiến độ HireLens (DOCX)."""

from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "Bao_cao_tien_do_HireLens.docx"


def load_stats() -> dict:
    qpath = ROOT / "AI" / "data" / "questions.json"
    apath = ROOT / "AI" / "data" / "answers.csv"
    bundle = json.loads(qpath.read_text(encoding="utf-8"))
    questions = bundle["questions"]
    tracks = Counter(q.get("track") or "khac" for q in questions)
    topics = Counter(q.get("topic") or "khac" for q in questions)
    scores = []
    by_q = Counter()
    with apath.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            scores.append(float(row["human_score"]))
            by_q[row["question_id"]] += 1
    n = len(scores)
    return {
        "n_questions": len(questions),
        "n_answers": n,
        "score_min": min(scores) if scores else 0,
        "score_max": max(scores) if scores else 0,
        "score_mean": (sum(scores) / n) if n else 0,
        "per_q_min": min(by_q.values()) if by_q else 0,
        "per_q_max": max(by_q.values()) if by_q else 0,
        "tracks": tracks,
        "topics": topics,
        "role": bundle.get("meta", {}).get("role", ""),
    }


def set_run_font(run, size=13, bold=False, italic=False, color=None, name="Times New Roman"):
    run.font.name = name
    run.bold = bold
    run.italic = italic
    run.font.size = Pt(size)
    if color:
        run.font.color.rgb = RGBColor(*color)
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.append(rfonts)
    for attr in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
        rfonts.set(qn(attr), name)


def shade_cell(cell, hex_color: str):
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), hex_color)
    shd.set(qn("w:val"), "clear")
    tcPr.append(shd)


def set_cell_border(cell, color="B0B0B0"):
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    tcBorders = OxmlElement("w:tcBorders")
    for edge in ("top", "left", "bottom", "right"):
        el = OxmlElement(f"w:{edge}")
        el.set(qn("w:val"), "single")
        el.set(qn("w:sz"), "8")
        el.set(qn("w:color"), color)
        tcBorders.append(el)
    tcPr.append(tcBorders)


def set_row_height(row, twips: int):
    tr = row._tr
    trPr = tr.get_or_add_trPr()
    trHeight = OxmlElement("w:trHeight")
    trHeight.set(qn("w:val"), str(twips))
    trHeight.set(qn("w:hRule"), "atLeast")
    trPr.append(trHeight)


def para(doc, text, *, size=13, bold=False, italic=False, align="justify",
         space_before=0, space_after=3, indent=True, color=None):
    p = doc.add_paragraph()
    p.alignment = {
        "justify": WD_ALIGN_PARAGRAPH.JUSTIFY,
        "center": WD_ALIGN_PARAGRAPH.CENTER,
        "left": WD_ALIGN_PARAGRAPH.LEFT,
        "right": WD_ALIGN_PARAGRAPH.RIGHT,
    }[align]
    pf = p.paragraph_format
    pf.line_spacing = 1.15
    pf.space_before = Pt(space_before)
    pf.space_after = Pt(space_after)
    pf.first_line_indent = Cm(1.0) if indent and align == "justify" else Cm(0)
    run = p.add_run(text)
    set_run_font(run, size=size, bold=bold, italic=italic, color=color)
    return p


def heading_chapter(doc, text):
    doc.add_page_break()
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    pf = p.paragraph_format
    pf.space_before = Pt(12)
    pf.space_after = Pt(16)
    pf.line_spacing = 1.5
    pf.first_line_indent = Cm(0)
    run = p.add_run(text)
    set_run_font(run, size=16, bold=True, color=(0, 0, 0))
    p.style = doc.styles["Heading 1"]
    for r in p.runs:
        set_run_font(r, size=16, bold=True, color=(0, 0, 0))
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    return p


def heading2(doc, text):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    pf = p.paragraph_format
    pf.space_before = Pt(12)
    pf.space_after = Pt(6)
    pf.line_spacing = 1.5
    pf.first_line_indent = Cm(0)
    run = p.add_run(text)
    set_run_font(run, size=14, bold=True, color=(0, 0, 0))
    p.style = doc.styles["Heading 2"]
    for r in p.runs:
        set_run_font(r, size=14, bold=True, color=(0, 0, 0))
    return p


def heading3(doc, text):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    pf = p.paragraph_format
    pf.space_before = Pt(8)
    pf.space_after = Pt(4)
    pf.line_spacing = 1.5
    pf.first_line_indent = Cm(0)
    run = p.add_run(text)
    set_run_font(run, size=13, bold=True, italic=True, color=(0, 0, 0))
    p.style = doc.styles["Heading 3"]
    for r in p.runs:
        set_run_font(r, size=13, bold=True, italic=True, color=(0, 0, 0))
    return p


def bullet(doc, text, level=0):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    pf = p.paragraph_format
    pf.line_spacing = 1.15
    pf.space_before = Pt(0)
    pf.space_after = Pt(1)
    pf.left_indent = Cm(1.25 + 0.75 * level)
    pf.first_line_indent = Cm(0)
    run = p.add_run("•  " + text)
    set_run_font(run, size=13)
    return p


def caption(doc, text):
    return para(doc, text, size=12, italic=True, align="center", indent=False, space_before=2, space_after=10)


def figure(doc, number: str, caption_text: str):
    gap = doc.add_paragraph()
    gap.paragraph_format.space_before = Pt(28)
    gap.paragraph_format.space_after = Pt(0)
    gap.paragraph_format.line_spacing = 1.0
    para(doc, "Chèn ảnh.", size=12, italic=True, align="center", indent=False, space_before=0, space_after=2)
    caption(doc, f"Hình {number}. {caption_text}")


def add_table(doc, headers, rows, font=11):
    table = doc.add_table(rows=1 + len(rows), cols=len(headers))
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, h in enumerate(headers):
        cell = table.rows[0].cells[i]
        cell.text = ""
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(h)
        set_run_font(run, size=font, bold=True)
        shade_cell(cell, "E7EEF5")
    for r_idx, row in enumerate(rows):
        for c_idx, val in enumerate(row):
            cell = table.rows[r_idx + 1].cells[c_idx]
            cell.text = ""
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT if c_idx == 0 else WD_ALIGN_PARAGRAPH.CENTER
            run = p.add_run(str(val))
            set_run_font(run, size=font)
    doc.add_paragraph()
    return table


def add_page_number(paragraph):
    run = paragraph.add_run()
    set_run_font(run, size=11)

    def fld(kind):
        el = OxmlElement("w:fldChar")
        el.set(qn("w:fldCharType"), kind)
        return el

    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = " PAGE "
    run._r.append(fld("begin"))
    run._r.append(instr)
    run._r.append(fld("end"))


def setup_styles(doc):
    normal = doc.styles["Normal"]
    normal.font.name = "Times New Roman"
    normal.font.size = Pt(13)
    rpr = normal.element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.append(rfonts)
    for attr in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
        rfonts.set(qn(attr), "Times New Roman")
    pf = normal.paragraph_format
    pf.line_spacing = 1.5


def setup_section(doc):
    sec = doc.sections[0]
    sec.page_width = Cm(21.0)
    sec.page_height = Cm(29.7)
    sec.top_margin = Cm(2.0)
    sec.bottom_margin = Cm(2.0)
    sec.left_margin = Cm(3.0)
    sec.right_margin = Cm(2.0)
    sec.header_distance = Cm(0.8)
    sec.footer_distance = Cm(0.8)
    header = sec.header
    header.is_linked_to_previous = False
    hp = header.paragraphs[0]
    hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    run = hp.add_run("Báo cáo tiến độ đồ án")
    set_run_font(run, size=10, italic=True, color=(90, 90, 90))
    footer = sec.footer
    footer.is_linked_to_previous = False
    fp = footer.paragraphs[0]
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r1 = fp.add_run("Trang ")
    set_run_font(r1, size=11)
    add_page_number(fp)



def cover(doc):
    for _ in range(2):
        para(doc, "", align="center", indent=False, space_after=0)
    para(doc, "HỌC VIỆN CÔNG NGHỆ BƯU CHÍNH VIỄN THÔNG", size=14, bold=True, align="center", indent=False, space_after=2)
    para(doc, "KHOA CÔNG NGHỆ THÔNG TIN I", size=13, bold=True, align="center", indent=False, space_after=18)
    para(doc, "BÁO CÁO TIẾN ĐỘ ĐỒ ÁN", size=16, bold=True, align="center", indent=False, space_before=12, space_after=10)
    para(
        doc,
        "HỆ THỐNG TUYỂN DỤNG THÔNG MINH DỰA TRÊN BERTSCORE\nĐỂ PHÂN TÍCH VÀ ĐÁNH GIÁ CV CHO ỨNG VIÊN\nNGÀNH CÔNG NGHỆ THÔNG TIN",
        size=14, bold=True, align="center", indent=False, space_after=16,
    )
    para(doc, "Thành viên nhóm", size=13, bold=True, align="center", indent=False, space_after=6)
    add_table(
        doc,
        ["Họ và tên", "Mã sinh viên"],
        [
            ["Hoàng Hải Long", "B22DCCN496"],
            ["Nguyễn Hữu Lộc", "B22DCCN508"],
            ["Nguyễn Văn Học", "B22DCCN352"],
        ],
    )
    para(doc, "Hà Nội – 2026", size=13, bold=True, align="center", indent=False, space_before=18)


def front_matter(doc, stats):
    doc.add_page_break()
    para(doc, "MỤC LỤC", size=16, bold=True, align="center", indent=False, space_after=12)
    p = doc.add_paragraph()
    run = p.add_run()
    fld_begin = OxmlElement("w:fldChar")
    fld_begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = r' TOC \o "1-3" \h \z \u '
    fld_sep = OxmlElement("w:fldChar")
    fld_sep.set(qn("w:fldCharType"), "separate")
    fld_end = OxmlElement("w:fldChar")
    fld_end.set(qn("w:fldCharType"), "end")
    run._r.append(fld_begin)
    run._r.append(instr)
    run._r.append(fld_sep)
    hint = p.add_run(
        "Chương 1. Tổng quan bài toán và hiện trạng\n"
        "Chương 2. Kỹ thuật học sâu theo từng module\n"
        "Chương 3. Ontology kỹ năng và bộ đặc trưng đối sánh\n"
        "Chương 4. Thiết kế hệ thống, service và pipeline\n"
        "Chương 5. Kết quả thực nghiệm và giao diện\n"
        "Kết luận\n"
        "Tài liệu tham khảo\n"
        "Phụ lục"
    )
    set_run_font(hint, size=13)
    run2 = p.add_run()
    run2._r.append(fld_end)

    doc.add_page_break()
    para(doc, "DANH MỤC HÌNH VẼ", size=16, bold=True, align="center", indent=False, space_after=10)
    for item in [
        "Hình 1.1. Ba module của hệ thống",
        "Hình 2.1. Hai nhánh trích xuất CV",
        "Hình 2.2. Năm tầng đối sánh CV và mô tả công việc",
        "Hình 2.3. Pipeline chấm câu trả lời phỏng vấn",
        "Hình 4.1. Kiến trúc các thành phần",
        "Hình 4.2. Các nhóm bảng dữ liệu",
        "Hình 4.3. Pipeline từ CV đến kết quả đối sánh và phỏng vấn",
        "Hình B.1. Request và response của một câu chấm điểm",
        "Hình 5.1. Loss huấn luyện Module 1",
        "Hình 5.2. Màn hình đăng nhập",
        "Hình 5.3. Danh sách việc làm",
        "Hình 5.4. Tải và xác nhận CV",
        "Hình 5.5. Kết quả đối sánh",
        "Hình 5.6. Phiên ôn tập và điểm câu trả lời",
        "Hình 5.7. Màn hình nhà tuyển dụng",
    ]:
        para(doc, item, align="left", indent=False, space_after=2)

    doc.add_page_break()
    para(doc, "DANH MỤC BẢNG", size=16, bold=True, align="center", indent=False, space_after=10)
    for item in [
        "Bảng 1.1. Hiện trạng ba module",
        "Bảng 2.1. Cấu hình huấn luyện Qwen3-1.7B và LoRA",
        "Bảng 2.2. Công nghệ học sâu của Module 2",
        "Bảng 2.3. Siêu tham số chấm câu trả lời phỏng vấn",
        "Bảng 2.4. Kết quả lexical trên 52 mẫu",
        "Bảng 3.1. Quan hệ trong ontology kỹ năng",
        "Bảng 3.2. Mười một đặc trưng và trọng số prior",
        "Bảng 4.1. Thành phần triển khai",
        "Bảng 4.2. Nhóm API",
        "Bảng 5.1. Loss theo bước huấn luyện Module 1",
        "Bảng 5.2. Kiểm tra suy luận Module 1",
        "Bảng 5.3. Hiện vật mô hình Module 1",
        "Bảng 5.4. Vector đặc trưng minh họa của một cặp CV và JD",
        "Bảng 5.5. Chỉ số Module 3 chưa đo",
    ]:
        para(doc, item, align="left", indent=False, space_after=2)

    doc.add_page_break()
    para(doc, "DANH MỤC TỪ VIẾT TẮT", size=16, bold=True, align="center", indent=False, space_after=10)
    add_table(
        doc,
        ["Từ viết tắt", "Diễn giải"],
        [
            ["BGE", "BAAI General Embedding"],
            ["BM25", "Best Matching 25"],
            ["CV", "Curriculum Vitae"],
            ["JD", "Job description — mô tả công việc"],
            ["LLM", "Large language model"],
            ["LoRA", "Low-Rank Adaptation"],
            ["MAE", "Mean Absolute Error"],
            ["NDCG", "Normalized Discounted Cumulative Gain"],
            ["RRF", "Reciprocal Rank Fusion"],
        ],
    )
    para(
        doc,
        f"Tập câu hỏi phỏng vấn trong mã nguồn có {stats['n_questions']} câu và {stats['n_answers']} câu trả lời đã gán điểm. "
        f"Điểm nằm trong [{stats['score_min']:g}, {stats['score_max']:g}], trung bình {stats['score_mean']:.2f}. "
        f"Số câu trả lời trên mỗi câu từ {stats['per_q_min']} đến {stats['per_q_max']}. Đối tượng nội dung: {stats['role']}.",
    )


def chapter1(doc):
    heading_chapter(doc, "CHƯƠNG 1. TỔNG QUAN BÀI TOÁN VÀ HIỆN TRẠNG")

    heading2(doc, "1.1. Bối cảnh")
    para(
        doc,
        "Tuyển dụng ngành công nghệ thông tin bắt đầu từ việc đọc CV có bố cục khác nhau và đối chiếu với mô tả công việc. "
        "Đồ án xây dựng hệ thống hỗ trợ ba việc nối tiếp. Module 1 chuyển CV dạng PDF thành hồ sơ có cấu trúc. "
        "Module 2 nhận hồ sơ đó cùng mô tả công việc để chấm mức phù hợp, xếp hạng và giải thích. "
        "Module 3 tổ chức ôn tập phỏng vấn và chấm câu trả lời ngắn trên thang 0–10.",
    )
    para(
        doc,
        "Báo cáo tiến độ trước trình bày Module 1 và Module 2. Cơ sở dữ liệu của báo cáo đó đã có nhóm bảng cho Module 3, và module này nằm ngoài phạm vi số liệu của báo cáo trước. "
        "Bản mã hiện tại đã có dịch vụ chấm câu trả lời và đã nối dịch vụ đó với backend, nên báo cáo này ghi kỹ thuật của cả ba module.",
    )
    figure(doc, "1.1", "Ba module của hệ thống")

    heading2(doc, "1.2. Bài toán")
    para(
        doc,
        "Module 1 phải phục hồi thứ tự đọc của CV nhiều cột, nhận các tiêu đề mục dù cách gọi khác nhau, và gắn đúng dòng công nghệ với đúng dự án. "
        "Ngày tháng không đủ, dòng bullet lặp do PDF và mục bị lược bớt là các lỗi cấu trúc, không chỉ là lỗi nhận ký tự. "
        "Đầu ra là CandidateProfile, gồm thông tin cá nhân, mục tiêu, học vấn, kinh nghiệm, dự án, kỹ năng, chứng chỉ, danh hiệu và ngoại ngữ. "
        "Kinh nghiệm và dự án là các bản ghi riêng. Mô tả tách theo bullet. tech_stack gắn với từng dự án.",
    )
    para(
        doc,
        "Module 2 nhận CandidateProfile và mô tả công việc. Đầu ra gồm điểm phù hợp trên thang 0–100, điểm từng đặc trưng, kỹ năng còn thiếu, trách nhiệm còn thiếu, các cờ ràng buộc và một đoạn giải thích. "
        "Mọi kỹ năng đưa vào điểm phải có đoạn nguyên văn trong CV. Tên, giới tính, ảnh và tên trường không đi vào điểm. "
        "Trường Module 1 không trích được được đánh dấu missing và không bị tính là 0.",
    )
    para(
        doc,
        "Module 3 nhận câu hỏi, đáp án mẫu, barem và câu trả lời. Đầu ra là điểm trên thang 0–10, các ý đã nêu, các ý còn thiếu và một câu nhận xét. "
        "Điểm bám điểm người chấm trên tập huấn luyện. Ý đủ và ý thiếu bám từng tiêu chí của barem.",
    )

    heading2(doc, "1.3. Phạm vi kỹ thuật")
    para(
        doc,
        "Module 1 dùng PDFBox, biểu thức chính quy, máy trạng thái và Qwen3-1.7B tinh chỉnh bằng LoRA. "
        "Module 2 dùng ontology kỹ năng, BGE-M3, BERTScore-Recall, BM25, Reciprocal Rank Fusion, XGBoost hoặc LambdaMART, và một mô hình ngôn ngữ chỉ để diễn giải số liệu đã có. "
        "Module 3 dùng bert-base-multilingual-cased theo hai cách: BERTScore cộng hồi quy Ridge, và fine-tune đầu hồi quy. "
        "Thiết kế lưu trữ trong báo cáo trước là PostgreSQL. Bản mã đang chạy dùng MySQL 8.",
    )

    heading2(doc, "1.4. Hiện trạng")
    caption(doc, "Bảng 1.1. Hiện trạng ba module")
    add_table(
        doc,
        ["Module", "Trong báo cáo trước", "Trong mã hiện tại"],
        [
            ["1. Trích xuất CV", "Đã huấn luyện Qwen3-1.7B + LoRA; đã có loss và kiểm tra JSON", "Tải PDF, điền các mục field–value, người dùng xác nhận; chưa gắn PDFBox và Qwen"],
            ["2. Đối sánh CV–JD", "Thiết kế 5 tầng, 11 đặc trưng, 4 cờ; chưa có tập nhãn", "Đối sánh theo tên kỹ năng trong cv_data và số năm kinh nghiệm"],
            ["3. Phỏng vấn", "Có bảng dữ liệu; chưa báo cáo kỹ thuật", "Đã có tập câu trả lời, API chấm điểm và lời gọi từ Spring Boot"],
        ],
        font=10,
    )
    para(
        doc,
        "Điểm đối sánh trong mã hiện tại chưa phải điểm 0–100 của bộ 11 đặc trưng. "
        "Hàm đang chạy tính tỷ lệ kỹ năng bắt buộc trùng tên, tỷ lệ số năm kinh nghiệm, đặt điểm ngữ nghĩa bằng 0,9 lần điểm kỹ năng, rồi lấy tổng trọng số 0,5, 0,3 và 0,2. "
        "Tên mô hình ghi trong cơ sở dữ liệu là hybrid-matcher, phiên bản v0. Chương 3 ghi công thức này cùng thiết kế ontology và 11 đặc trưng.",
    )

    heading2(doc, "1.5. Kết luận Chương 1")
    para(
        doc,
        "Đồ án gồm trích xuất CV, đối sánh với mô tả công việc và chấm câu trả lời phỏng vấn. "
        "Module 1 đã có số liệu huấn luyện ở báo cáo trước và chưa được gắn vào bản web hiện tại. "
        "Module 2 đã có thiết kế đặc trưng và chưa có số đo xếp hạng; bản web đang dùng đối sánh theo tên kỹ năng. "
        "Module 3 đã có pipeline chấm điểm trong mã nguồn. Các chương sau tách kỹ thuật theo đúng ba module này.",
    )


def chapter2(doc, stats):
    heading_chapter(doc, "CHƯƠNG 2. KỸ THUẬT HỌC SÂU THEO TỪNG MODULE")

    heading2(doc, "2.1. Module 1 — Trích xuất CV")
    para(
        doc,
        "Module 1 có hai nhánh cùng trả CandidateProfile. Nhánh luật chạy trong backend. Nhánh mô hình ngôn ngữ chạy trong AI-Service. "
        "Cả hai nhánh đi qua cùng lớp kiểm định trước khi ghi cơ sở dữ liệu.",
    )
    heading3(doc, "2.1.1. Nhánh luật")
    para(
        doc,
        "PDFBox lấy văn bản kèm tọa độ. Các khối chữ được dựng lại để phục hồi thứ tự đọc của trang một cột và nhiều cột. "
        "Tiêu đề mục được nhận bằng từ điển, gồm các biến thể như kỹ năng chuyên môn, kỹ năng khác và ngoại ngữ. "
        "Biểu thức chính quy và máy trạng thái lấy email, điện thoại, URL, GPA, mốc thời gian, kinh nghiệm và dự án. "
        "CvJsonMapper ánh xạ sang JSON. CvValidator kiểm tra ngày, GPA và bullet trùng. Nhánh này chạy cục bộ, không bắt buộc gọi AI-Service.",
    )
    heading3(doc, "2.1.2. Nhánh Qwen3-1.7B và LoRA")
    para(
        doc,
        "Nhánh thứ hai tinh chỉnh Qwen3-1.7B bằng LoRA. Prompt ràng buộc đúng schema JSON. No-Thinking Mode đặt enable_thinking = False để phần suy luận nội bộ không cắt cụt JSON. "
        "json_repair sửa lỗi cú pháp nhỏ. Pydantic kiểm tra kiểu trước khi nhận kết quả. "
        "Mô hình không được phép thêm thông tin không có trong CV. Lớp kiểm định đứng sau cả hai nhánh.",
    )
    caption(doc, "Bảng 2.1. Cấu hình huấn luyện đã ghi trong báo cáo tiến độ trước")
    add_table(
        doc,
        ["Hạng mục", "Giá trị"],
        [
            ["Dữ liệu", "494 CV; 395 train và 99 validation; nhãn JSON sinh bằng Gemini"],
            ["Mô hình nền", "unsloth/Qwen3-1.7B, nạp 4-bit, độ dài tối đa 4096"],
            ["LoRA", "r = 16, alpha = 16, 7 module đích; 17,4 triệu tham số (khoảng 1%)"],
            ["Huấn luyện", "5 epoch, 250 bước, learning rate 2×10⁻⁴, batch hiệu dụng 8, adamw_8bit"],
            ["Môi trường", "Google Colab, Tesla T4 14,56 GB, 58 phút 44 giây"],
        ],
        font=10,
    )
    para(
        doc,
        "Loss cuối của tập huấn luyện và tập validation cùng là 0,000121. Bảng từng mốc và kiểm tra 10 mẫu JSON nằm ở Chương 5. "
        "Loss thấp cho thấy mô hình học được khuôn JSON của tập nhãn tự sinh. Độ chính xác từng trường trên nhãn người gán chưa có.",
    )
    figure(doc, "2.1", "Hai nhánh trích xuất CV")
    para(
        doc,
        "Trong cây mã web hiện tại, CvService nhận tệp PDF, lưu đĩa và ghi các dòng nội bộ file_name, file_url, parsing_status trong bảng cv_data. "
        "Danh sách mục trên màn hình lấy từ dòng CV_FIELD của bảng setting. Mỗi mục là một hoặc nhiều dòng cv_data theo cặp field–value. "
        "Người dùng kiểm tra rồi xác nhận. Lớp PDFBox, máy trạng thái và adapter LoRA chưa nằm trong cây mã này.",
    )

    heading2(doc, "2.2. Module 2 — Đối sánh CV và mô tả công việc")
    para(
        doc,
        "Module 2 xử lý theo năm tầng: biểu diễn dữ liệu, trích đặc trưng, chấm điểm và xếp hạng, giải thích, đánh giá. "
        "Học sâu được dùng ở những chỗ cần so nghĩa. Kỹ năng, số năm và cấp bậc dùng ontology cùng quy tắc, vì embedding dễ kéo Java lại gần JavaScript.",
    )
    caption(doc, "Bảng 2.2. Thành phần học sâu của Module 2")
    add_table(
        doc,
        ["Thành phần", "Vai trò"],
        [
            ["BGE-M3", "Mã hóa CV và JD thành dense, sparse và multi-vector"],
            ["BERTScore-Recall", "Đặc trưng B4: mức CV bao phủ các trách nhiệm của JD"],
            ["LLM trích xuất", "Bổ sung kỹ năng, vai trò, lĩnh vực mà quy tắc bỏ sót; mỗi mục có evidence"],
            ["Cross-encoder", "Chấm lại Top-10 trong thí nghiệm đối chứng"],
            ["LLM giải thích", "Viết đoạn văn từ số liệu đã tính"],
            ["XGBoost / LambdaMART", "Học trọng số đặc trưng theo NDCG khi đã có nhãn"],
        ],
        font=10,
    )
    heading3(doc, "2.2.1. BGE-M3")
    para(
        doc,
        "CV tiếng Anh và mô tả công việc tiếng Việt là trường hợp thường gặp, nên bộ mã hóa là BGE-M3, mô hình Transformer đa ngôn ngữ huấn luyện bằng contrastive learning. "
        "Một lần encode cho ba biểu diễn. Vector dense dùng lọc thô. Vector sparse mang trọng số từ vựng kiểu BM25. Multi-vector, một vector cho mỗi token, dùng cho MaxSim của đặc trưng B4. "
        "Độ giống dense tính bằng cosine. Vector được lưu theo hash nội dung, tên mô hình và phiên bản tiền xử lý, vì chi phí nằm ở bước encode.",
    )
    heading3(doc, "2.2.2. BERTScore-Recall cho đặc trưng B4")
    para(
        doc,
        "B4 so từng gạch trách nhiệm của mô tả công việc với các gạch mô tả trong CV. Với x là phía mô tả công việc và y là phía CV, Recall lấy với mỗi token của x một token y có cosine lớn nhất, rồi lấy trung bình. "
        "Công thức này trùng MaxSim của ColBERT. Recall được chọn vì Precision trừ điểm mọi nội dung CV nằm ngoài mô tả công việc, trong khi CV thường có các mục không thuộc vị trí đang xét. "
        "Điểm thô của từng gạch được đưa về đoạn [0, 1] bằng hai ngưỡng lo và hi: cal(j) = clip((sim(j) − lo) / (hi − lo), 0, 1). B4 là trung bình cal(j). "
        "Backend ngữ nghĩa có thể đổi giữa cosine dense, BERTScore F1, BERTScore-Recall, multi-vector của BGE-M3 và cross-encoder. Backend được giữ lại sau thực nghiệm. Thực nghiệm đó chưa chạy.",
    )
    heading3(doc, "2.2.3. Lọc Top-K, học trọng số và giải thích")
    para(
        doc,
        "Khi có nhiều CV, hệ thống lấy Top-K từ 50 đến 100 bằng BM25 trên biểu diễn sparse và bằng vector dense, rồi trộn hạng bằng Reciprocal Rank Fusion. B4 chỉ chạy trên tập đã lọc. "
        "Điểm cuối là tổng có trọng số của 11 đặc trưng ở Chương 3. Giai đoạn chưa có nhãn dùng trọng số prior, bỏ đặc trưng NaN và chuẩn hóa lại tổng trọng số. "
        "Khi có 40 đến 60 cặp CV–JD do người chấm, trọng số chuyển sang XGBoost hoặc LambdaMART, tối ưu NDCG, có ràng buộc đơn điệu và giá trị SHAP. "
        "Cross-encoder chỉ chấm lại Top-10 như nhánh đối chứng. Điểm của mô hình sinh không thay điểm từ đặc trưng.",
    )
    para(
        doc,
        "Chuỗi xử lý giải thích đi qua Extractor, Scorer, Skill-Gap, Responsibility-Gap, Flag và Explainer. Chỉ Explainer gọi mô hình ngôn ngữ. "
        "Explainer diễn giải số đã có. Một bước kiểm tra xác định loại câu có số hoặc tên kỹ năng không nằm trong đầu vào. Cách diễn đạt dùng “chưa thấy bằng chứng” khi CV không chứa mục đó.",
    )
    para(
        doc,
        "Thiết kế đo Module 2 gồm Precision@K, Recall@K, NDCG@K, MRR, MAE và Spearman trên tập 40–60 cặp. "
        "Khâu trích xuất kỹ năng có mốc F1 đề xuất 0,85. Ablation lần lượt thêm BM25, dense, ontology, đặc trưng phi ngữ nghĩa, B4, XGBoost và re-rank. "
        "Phép thử bất biến đổi tên, giới tính và tên trường. Phép thử bẫy gồm cặp Java với JavaScript và C với C++. Các mốc này là thiết kế đo, chưa có kết quả.",
    )
    figure(doc, "2.2", "Năm tầng đối sánh CV và mô tả công việc")

    heading2(doc, "2.3. Module 3 — Chấm câu trả lời phỏng vấn")
    para(
        doc,
        f"Module 3 chấm một câu trả lời ngắn. Đầu vào là câu hỏi, đáp án mẫu, barem và câu trả lời. "
        f"Tập trong mã nguồn có {stats['n_questions']} câu, phủ backend, cơ sở dữ liệu, frontend, kiểm thử và kiến thức máy tính cơ sở, bậc intern và fresher. "
        f"Tệp câu trả lời có {stats['n_answers']} mẫu, điểm người chấm trung bình {stats['score_mean']:.2f} trên thang 0–10. "
        "Mỗi tiêu chí của barem có khóa, nhãn, trọng số và các từ khóa tiếng Việt hoặc tiếng Anh.",
    )
    heading3(doc, "2.3.1. Độ tương đồng và độ phủ barem")
    para(
        doc,
        "Chế độ lexical tách token sau chuẩn hóa Unicode và chữ thường, rồi tính precision, recall và F1 trên tập token. Chế độ này không tải mô hình. "
        "Chế độ BERTScore dùng bert-base-multilingual-cased: mỗi token của câu trả lời lấy cosine lớn nhất với token của đáp án mẫu, và ngược lại, rồi tính F1. Tham số rescale theo baseline của thư viện được tắt. "
        "Độ phủ duyệt từng tiêu chí. Một ý được tính là đã nêu khi nhãn xuất hiện trong câu trả lời, hoặc khi có ít nhất một từ khóa là chuỗi con. Điểm phủ là tổng trọng số các ý đã nêu. API chia lại trọng số cho tổng bằng 1.",
    )
    para(
        doc,
        "Năm đặc trưng đưa vào hồi quy là precision, recall, F1, điểm phủ và độ dài chuẩn hóa. Độ dài chuẩn hóa bằng số ký tự chia cho 300 và cắt trên tại 1. "
        "Ridge có alpha bằng 1, phạt L2. Tập chia 75% huấn luyện và 25% kiểm tra, seed 42. Điểm dự đoán cắt về [0, 10]. "
        "Baseline trên cùng tập kiểm tra là F1 nhân 10. Hệ số lưu trong calibration_fast.json hoặc calibration_bertscore.json. "
        "Câu nhận xét lắp từ danh sách ý đã nêu và ý còn thiếu.",
    )
    heading3(doc, "2.3.2. Fine-tune BERT hồi quy")
    para(
        doc,
        "Nhánh fine-tune đặt đầu phân loại của bert-base-multilingual-cased thành một nhãn, problem_type là regression. Hàm mất mát là sai số bình phương. "
        "Chuỗi vào gồm câu hỏi, đáp án mẫu và câu trả lời, cắt ở 256 token. "
        "Tập Mohler ASAG, phần open_ended, có điểm gốc 0–5 và được nhân 2 để cùng thang 0–10. Tập này dùng để học dạng bài chấm câu ngắn trước khi học tiếp trên tập phỏng vấn của đồ án.",
    )
    para(doc, "Bốn kịch bản dùng chung seed 42 và tỷ lệ kiểm tra 0,2.", indent=True)
    bullet(doc, "mohler: học và đánh giá trên Mohler.")
    bullet(doc, "self: học và đánh giá trên tập phỏng vấn của đồ án.")
    bullet(doc, "combined: trộn hai tập huấn luyện, đánh giá riêng từng tập kiểm tra.")
    bullet(doc, "transfer: học Mohler trước, rồi học tiếp tập của đồ án. Số epoch mặc định là 2 rồi 3.")
    caption(doc, "Bảng 2.3. Siêu tham số trong mã Module 3")
    add_table(
        doc,
        ["Thành phần", "Giá trị"],
        [
            ["Encoder", "bert-base-multilingual-cased, 12 lớp, hidden 768"],
            ["Ridge", "alpha 1,0; test 0,25; seed 42"],
            ["Fine-tune", "độ dài 256; batch 8; learning rate 2×10⁻⁵; weight decay 0,01; 3 epoch"],
            ["Điểm", "cắt về đoạn [0, 10]"],
        ],
        font=11,
    )
    para(
        doc,
        "Tệp cấu hình trong AI/output/model là BertForSequenceClassification, một nhãn, bài toán regression. "
        "Tệp finetune_metrics.json của bốn kịch bản chưa có trong cây mã, nên MAE của fine-tune và của BERTScore chưa ghi ở báo cáo này. "
        "Lần chạy lexical trên 52 mẫu, trước khi tập được mở rộng, đã được ghi trong tài liệu module: MAE kiểm tra của Ridge khoảng 0,99, MAE của baseline F1×10 khoảng 3,68. "
        "Hai số này kiểm tra luồng hiệu chuẩn. Lần đo trên toàn bộ tập hiện có được chừa ở Bảng 5.5.",
    )
    caption(doc, "Bảng 2.4. Lexical và Ridge trên 52 mẫu")
    add_table(
        doc,
        ["Mô hình", "MAE kiểm tra"],
        [
            ["Baseline F1 × 10", "≈ 3,68"],
            ["Ridge, alpha = 1", "≈ 0,99"],
        ],
    )
    figure(doc, "2.3", "Pipeline chấm câu trả lời phỏng vấn")
    para(
        doc,
        "Spring Boot gửi đáp án mẫu và barem lấy từ MySQL tới POST /v1/interview/evaluate. FastAPI tính độ tương đồng theo mode trong cấu hình, tính độ phủ, áp hệ số Ridge và trả điểm cùng hai danh sách ý. "
        "Mode mặc định trong application.yml là fast, tức lexical. Cột precision, recall và F1 chi tiết chưa được ghi vào evaluation_results ở lần nối hiện tại.",
    )

    heading2(doc, "2.4. Kết luận Chương 2")
    para(
        doc,
        "Module 1 đã huấn luyện Qwen3-1.7B bằng LoRA trên 494 CV và có loss cuối 0,000121. Nhánh luật dùng PDFBox và máy trạng thái. Cả hai nhánh chưa gắn vào bản web đang chạy. "
        "Module 2 dùng BGE-M3 và BERTScore-Recall cho mức bao phủ trách nhiệm, dùng XGBoost khi có nhãn, và dùng mô hình ngôn ngữ để diễn giải số đã tính. Phần này đang ở mức thiết kế. "
        "Module 3 đã có mã chấm câu trả lời bằng BERTScore hoặc lexical, độ phủ barem và Ridge, cùng mã fine-tune BERT. Số đo đầy đủ của Module 3 chưa có trong cây mã.",
    )


def chapter3(doc):
    heading_chapter(doc, "CHƯƠNG 3. ONTOLOGY KỸ NĂNG VÀ BỘ ĐẶC TRƯNG ĐỐI SÁNH")

    heading2(doc, "3.1. Vai trò của ontology")
    para(
        doc,
        "Điểm kỹ năng của Module 2 không lấy từ embedding. Ontology kỹ năng có hướng, quy mô dự kiến 150 đến 300 nút trong miền công nghệ thông tin, chuẩn hóa tên và quyết định một kỹ năng trên CV có đáp ứng một yêu cầu của mô tả công việc hay không. "
        "Embedding giữ cho đặc trưng B4 ở Chương 2, nơi cần so các câu trách nhiệm.",
    )
    para(
        doc,
        "Thứ tự trích kỹ năng là quy tắc và từ điển trước, mô hình ngôn ngữ sau, rồi kiểm chứng. Mỗi kỹ năng do mô hình trả về phải kèm đoạn evidence nguyên văn. Đoạn đó phải là chuỗi con của CV. Mục không qua kiểm chứng bị loại. "
        "Báo cáo trước đề xuất lưu evidence trên bảng kỹ năng của từng CV. Lược đồ hiện tại gộp nội dung CV vào cv_data, nên bằng chứng từng kỹ năng vẫn chưa có cột riêng.",
    )

    heading2(doc, "3.2. Các quan hệ")
    caption(doc, "Bảng 3.1. Quan hệ ontology trong thiết kế Module 2")
    add_table(
        doc,
        ["Quan hệ", "Ý nghĩa", "Ví dụ"],
        [
            ["synonym", "Hai tên cùng một kỹ năng", "ReactJS và React"],
            ["implies", "Có hướng, không đảo ngược", "Spring Boot kéo theo Java"],
            ["is_a", "Quan hệ loại", "PostgreSQL là một hệ quản trị SQL"],
            ["sibling", "Cùng nhóm, không thay thế cho nhau", "Các thư viện cùng họ"],
            ["distinct", "Cấm coi là trùng", "Java khác JavaScript; C khác C++"],
        ],
        font=11,
    )
    para(
        doc,
        "implies cho phép ghi nhận một phần khi CV nêu kỹ năng hẹp hơn yêu cầu, và chiều ngược lại không được suy. "
        "distinct chặn các cặp tên gần nhau mà cosine của embedding hay gộp nhầm. "
        "Bản mã hiện tại chưa có bảng skill_aliases và skill_relations. So khớp đang thực hiện là so chuỗi tên đã viết thường.",
    )

    heading2(doc, "3.3. Giá trị thiếu")
    para(
        doc,
        "Thiết kế phân biệt ba trạng thái. Giá trị 0 là CV có mục và mục đó không đáp ứng yêu cầu. "
        "missing là Module 1 không trích được trường, và trường này không bị phạt điểm. "
        "n/a là mô tả công việc không đặt yêu cầu tương ứng, và đặc trưng bị bỏ khỏi mẫu số khi chuẩn hóa trọng số. "
        "Ví dụ ở Chương 5 gán B5 là missing vì phần dự án bị cắt, và gán C2 là n/a vì tin không yêu cầu chứng chỉ.",
    )

    heading2(doc, "3.4. Mười một đặc trưng và bốn cờ")
    para(
        doc,
        "Điểm trước khi có nhãn là tổng prior của các đặc trưng còn hiệu lực, chia cho tổng prior của các đặc trưng đó, rồi nhân 100. "
        "Cổng must-have áp sau bước này: nếu độ phủ kỹ năng bắt buộc A1 nhỏ hơn 0,70 thì điểm không vượt 70; nếu A1 nhỏ hơn 0,50 thì điểm không vượt 50.",
    )
    caption(doc, "Bảng 3.2. Mười một đặc trưng và trọng số prior")
    add_table(
        doc,
        ["ID", "Đặc trưng", "Cách tính", "Prior"],
        [
            ["A1", "Kỹ năng bắt buộc", "Ontology và evidence", "0,25"],
            ["A2", "Kỹ năng ưu tiên", "Ontology và evidence", "0,05"],
            ["A3", "Độ sâu và độ mới kỹ năng", "Thời lượng và thời điểm", "0,08"],
            ["B1", "Họ vai trò", "Từ khóa và xác nhận bằng LLM", "0,10"],
            ["B2", "Kinh nghiệm liên quan", "Số năm liên quan", "0,10"],
            ["B3", "Cấp bậc", "Quy tắc", "0,07"],
            ["B4", "Khớp trách nhiệm", "BERTScore-Recall", "0,15"],
            ["B5", "Bằng chứng dự án", "Ontology và quy tắc", "0,08"],
            ["B6", "Lĩnh vực", "Từ điển thực thể và LLM", "0,04"],
            ["C1", "Học vấn", "Quy tắc", "0,05"],
            ["C2", "Chứng chỉ", "Từ điển, khi JD yêu cầu", "0,03"],
        ],
        font=10,
    )
    para(
        doc,
        "Bốn cờ D1 đến D4 là địa điểm, tiếng Anh, loại hợp đồng và lương. Mỗi cờ nhận ok, warning hoặc unknown và không cộng vào điểm. "
        "Nguồn dữ liệu đã được ánh xạ: A1 và A2 từ job_skills cùng field Kỹ năng trong cv_data; A3 và B2 từ field Kinh nghiệm và số năm trên hồ sơ; B4 từ responsibilities của tin; B5, C1, C2 từ các field dự án, học vấn và chứng chỉ nếu CV_FIELD có các mục đó; D1, D3, D4 từ địa điểm, loại hình và mức lương.",
    )
    para(
        doc,
        "Lược đồ matching_results hiện có semantic_score, skills_score, experience_score, overall_score, matched_skills, missing_skills và explanation. "
        "Chưa có feature_scores, feature_status và flags để lưu đủ 11 đặc trưng, trạng thái missing hoặc n/a, và bốn cờ. "
        "Chưa có bảng ontology. cv_data chưa lưu evidence từng kỹ năng. Các mục honours, languages và objective chỉ xuất hiện nếu được thêm vào CV_FIELD.",
    )

    heading2(doc, "3.5. Công thức đang chạy trong mã")
    para(
        doc,
        "MatchingService chỉ chạy khi hồ sơ đã có file_name và parsing_status COMPLETED trong cv_data. "
        "Kỹ năng ứng viên lấy từ các dòng field Kỹ năng, tách theo dấu phẩy. "
        "Điểm kỹ năng bằng số kỹ năng bắt buộc có tên trùng, sau khi viết thường, chia cho số kỹ năng bắt buộc. Tin không khai báo kỹ năng bắt buộc thì điểm này bằng 1. "
        "Điểm kinh nghiệm bằng số năm của ứng viên chia cho số năm yêu cầu, cắt trên tại 1. Tin không yêu cầu số năm thì điểm này bằng 1. "
        "Điểm ngữ nghĩa bằng điểm kỹ năng nhân 0,9. Điểm tổng bằng 0,5 lần điểm kỹ năng, cộng 0,3 lần điểm ngữ nghĩa, cộng 0,2 lần điểm kinh nghiệm. "
        "Câu giải thích ghép danh sách kỹ năng đã trùng và danh sách còn thiếu. Bản ghi được cập nhật theo cùng ứng viên, cùng tin và cùng phiên bản hybrid-matcher v0.",
    )
    para(
        doc,
        "Công thức này giữ được API và màn hình đối sánh trong lúc bộ 11 đặc trưng chưa được cài. "
        "Điểm tổng của bản này nằm trên đoạn [0, 1], khác thang 0–100 của thiết kế Module 2. "
        "Khi ontology và B4 được nối, ba cột điểm thành phần nhận A1, B4 và B2, và overall_score nhận điểm đã qua cổng must-have.",
    )

    heading2(doc, "3.6. Kết luận Chương 3")
    para(
        doc,
        "Ontology kỹ năng quyết định khớp tên, kéo theo có hướng và các cặp phải tách riêng. Mười một đặc trưng và bốn cờ là đầu ra đã thiết kế của Module 2, với trọng số prior cho đến khi có tập nhãn. "
        "Mã web hiện ghi một điểm kỹ năng theo trùng tên, một điểm kinh nghiệm theo số năm và một điểm ngữ nghĩa dẫn xuất từ điểm kỹ năng. "
        "Bảng quan hệ kỹ năng, cột bằng chứng và các cột đủ 11 đặc trưng vẫn là phần lược đồ cần bổ sung.",
    )


def chapter4(doc):
    heading_chapter(doc, "CHƯƠNG 4. THIẾT KẾ HỆ THỐNG, SERVICE VÀ PIPELINE")

    heading2(doc, "4.1. Thành phần")
    para(
        doc,
        "Hệ thống có giao diện web, backend Spring Boot, AI-Service viết bằng FastAPI và một cơ sở dữ liệu quan hệ. "
        "Backend nhận yêu cầu, lưu tệp, giữ giao dịch và gọi AI-Service khi chấm câu trả lời. AI-Service không giữ phiên đăng nhập và không ghi hồ sơ ứng viên.",
    )
    caption(doc, "Bảng 4.1. Thành phần trong bản mã hiện tại")
    add_table(
        doc,
        ["Thành phần", "Công nghệ", "Cổng"],
        [
            ["Giao diện", "React 19, Vite, TypeScript", "5173"],
            ["Backend", "Spring Boot 4.1.1, Java 17", "8080"],
            ["Cơ sở dữ liệu", "MySQL 8.4, Flyway", "3306"],
            ["AI-Service", "FastAPI, scikit-learn, Transformers", "8000"],
            ["Tệp CV", "Thư mục uploads", "cấu hình app.upload.path"],
        ],
        font=10,
    )
    para(
        doc,
        "Báo cáo trước chọn PostgreSQL và gọi AI-Service qua Spring Cloud OpenFeign. "
        "Bản mã hiện tại dùng MySQL và gọi HTTP bằng java.net.http.HttpClient tới /v1/interview/evaluate. "
        "Thời gian chờ kết nối là 3 giây, thời gian chờ đọc là 60 giây. Mode gửi sang AI-Service lấy từ app.ai.mode.",
    )
    figure(doc, "4.1", "Kiến trúc các thành phần")

    heading2(doc, "4.2. Dữ liệu")
    para(
        doc,
        "Flyway chạy V1 cho lược đồ ban đầu, V2 cho dữ liệu mẫu, V3 đưa điểm tối đa của câu hỏi phỏng vấn về 10, "
        "V5 thêm role_chosen để hỏi vai trò một lần, V6 tạo setting và cv_data rồi gỡ các bảng CV con cùng toàn bộ khóa ngoại. "
        "JPA để ddl-auto ở chế độ validate. Khóa chính trong MySQL là INT tự tăng. Quan hệ giữa các bảng được kiểm tra trong mã.",
    )
    bullet(doc, "Người dùng: users, candidate_profiles, companies, recruiter_profiles. Vai trò là CANDIDATE, RECRUITER và ADMIN. Cột role_chosen đánh dấu đã chọn vai trò.")
    bullet(doc, "Hồ sơ CV: cv_data (candidate_id, field, value) và setting. Dòng CV_FIELD liệt kê các mục trên màn hình, cách nhau bằng dấu phẩy.")
    bullet(doc, "Việc làm: jobs, job_skills, skills, job_applications, matching_results. Trạng thái tin là DRAFT, PUBLISHED, CLOSED.")
    bullet(doc, "Phỏng vấn: interview_questions, evaluation_rubrics, interview_sessions, interview_session_questions, interview_responses, evaluation_results, model_versions.")
    para(
        doc,
        "skills là danh mục dùng chung cho tin tuyển dụng. job_skills nối tin với kỹ năng và có cờ is_required. "
        "job_applications duy nhất theo cặp ứng viên và tin. matching_results lưu model_name và model_version cho từng lần chấm. "
        "Cột cv_id trên đơn và kết quả đối sánh được giữ như số nguyên, không còn khóa ngoại.",
    )
    figure(doc, "4.2", "Các nhóm bảng dữ liệu")

    heading2(doc, "4.3. Xác thực")
    para(
        doc,
        "Mật khẩu lưu bằng BCrypt. Đăng nhập đúng thì backend ký JWT HS256, thời hạn mặc định một ngày. Phiên không lưu trên server. "
        "Đăng ký chỉ nhận email và mật khẩu. Lần vào tài khoản đầu tiên người dùng chọn ứng viên hoặc nhà tuyển dụng; role_chosen được ghi và không hỏi lại. "
        "Xem tin đã xuất bản được mở. Các đường dẫn còn lại yêu cầu token. "
        "Ứng viên chỉ đọc hồ sơ và phiên phỏng vấn của mình. Nhà tuyển dụng chỉ đối sánh trên tin của công ty mình. CORS mặc định mở http://localhost:5173.",
    )

    heading2(doc, "4.4. Service")
    bullet(doc, "AuthService phát hành JWT, ghi vai trò một lần và trả workspace tương ứng.")
    bullet(doc, "JobService tạo, sửa và lọc tin. ApplicationService ghi đơn ứng tuyển và trạng thái hồ sơ.")
    bullet(doc, "CvService lưu PDF và upsert các dòng cv_data. SettingService đọc danh sách field từ CV_FIELD.")
    bullet(doc, "MatchingService tính điểm theo mục 3.5 và lưu matching_results khi hồ sơ đã được xác nhận.")
    bullet(doc, "InterviewService tạo phiên, lưu câu trả lời, gọi AiScoringClient và lưu evaluation_results.")
    bullet(doc, "DashboardService đọc số đếm cho trang nhà tuyển dụng.")
    caption(doc, "Bảng 4.2. Nhóm API")
    add_table(
        doc,
        ["Nhóm", "Việc chính"],
        [
            ["/api/auth", "Đăng nhập, đăng ký và chọn vai trò"],
            ["/api/jobs", "Xem và đăng tin"],
            ["/api/cvs", "Tải PDF, xem và xác nhận hồ sơ field–value"],
            ["/api/applications", "Nộp và theo dõi hồ sơ"],
            ["/api/matching", "Tính và xem độ phù hợp"],
            ["/api/interviews", "Tạo phiên, nộp bài và xem điểm"],
            ["/api/dashboard", "Số liệu trang nhà tuyển dụng"],
        ],
        font=11,
    )
    para(
        doc,
        "Hai endpoint trích xuất trong thiết kế Module 1 là /api/v1/cv/extract-rule-based và /api/v1/cv/analyze-pdf. "
        "Bản mã hiện chưa phát hai đường này. Hợp đồng đầu ra vẫn là CandidateProfile cho cả hai nhánh. "
        "Endpoint đối sánh đầy đủ, trả feature_scores, feature_status, responsibility_gaps và flags, chưa được chốt trong báo cáo trước và chưa có trong controller hiện tại.",
    )

    heading2(doc, "4.5. Pipeline")
    heading3(doc, "4.5.1. CV")
    para(
        doc,
        "Ứng viên đã đăng nhập gửi tệp PDF. Backend lưu file và ghi file_name, file_url, parsing_status vào cv_data. "
        "Các mục trống trong CV_FIELD được điền sẵn để người dùng kiểm tra. Khi xác nhận, từng field được ghi lại; một field có nhiều dòng thì mỗi dòng một bản ghi cv_data. "
        "Thiết kế tiếp theo là thay bước điền sẵn bằng nhánh luật hoặc nhánh Qwen, rồi vẫn ghi vào cùng bảng field–value. "
        "Màn hình chỉ hiện các field có trong CV_FIELD, nên đổi cấu hình là đổi các mục hồ sơ.",
    )
    heading3(doc, "4.5.2. Đối sánh")
    para(
        doc,
        "Nhà tuyển dụng đăng tin vào jobs và job_skills. is_required tách kỹ năng bắt buộc và kỹ năng ưu tiên. "
        "Thiết kế Module 2 nhận CandidateProfile và tin, làm sạch, bỏ thuộc tính nhạy cảm, chuẩn hóa kỹ năng bằng ontology, mã hóa bằng BGE-M3, tính 11 đặc trưng và 4 cờ, lọc Top-K, áp cổng must-have, rồi ghi matching_results. "
        "Đường đang chạy gọi MatchingService. Ứng viên chỉ thấy danh sách sau khi hồ sơ đã có file và trạng thái hoàn tất. Nhà tuyển dụng truyền thêm candidateId và phải sở hữu tin. "
        "Màn hình ứng viên ghi phần còn thiếu so với yêu cầu và mở trang chi tiết tin, gồm mô tả, yêu cầu, trách nhiệm và đãi ngộ.",
    )
    heading3(doc, "4.5.3. Phỏng vấn")
    para(
        doc,
        "Ứng viên tạo phiên, có thể gắn với một tin hoặc một đơn. Danh sách câu hỏi lấy theo questionIds, hoặc lấy tối đa ba câu đang hoạt động. "
        "Mỗi câu được gắn thứ tự và điểm tối đa 10. Khi nộp bài, phiên chuyển sang IN_PROGRESS. Rubric trong MySQL được gửi thành criteria. "
        "Nếu câu chưa có rubric, backend tạo một tiêu chí tạm từ token của đáp án mẫu, tối đa 12 cụm. "
        "Điểm trả về bị chặn bởi điểm tối đa của câu. evaluation_method ghi là AI. Cùng một câu trong phiên có thể nộp lại và ghi đè kết quả.",
    )
    figure(doc, "4.3", "Pipeline từ CV đến kết quả đối sánh và phỏng vấn")
    para(
        doc,
        "AI-Service trả lỗi khi thiếu đáp án mẫu, thiếu tiêu chí hoặc câu trả lời rỗng. Mất kết nối cổng 8000 trả mã 503. HTTP lỗi từ FastAPI được đưa về mã 502. "
        "Cấu hình fallback-to-rule đang tắt, nên backend không tự sinh điểm khi AI-Service không trả predicted_score.",
    )

    heading2(doc, "4.6. Giao diện")
    para(
        doc,
        "Khách xem danh sách việc làm công khai. Sau đăng nhập, trang chủ là trang tài khoản theo vai trò. "
        "Nhóm /candidate gồm việc làm, hồ sơ CV, đối sánh, chi tiết tin và phỏng vấn. "
        "Nhóm /recruiter gồm bảng điều khiển, tin, ứng viên, đối sánh và ngân hàng câu hỏi. "
        "RequireAuth chuyển người chưa đăng nhập về trang đăng nhập, chuyển người chưa chọn vai trò về /choose-role, và chuyển người sai vai trò về workspace của vai trò đó. "
        "Ô tải CV chỉ nhận PDF. Giới hạn multipart là 10 MB cho tệp.",
    )

    heading2(doc, "4.7. Kết luận Chương 4")
    para(
        doc,
        "Bản triển khai gồm React, Spring Boot, MySQL và FastAPI. Ba pipeline đã có đường đi: lưu PDF và xác nhận hồ sơ field–value, đối sánh theo tên kỹ năng, tạo phiên phỏng vấn rồi chấm bằng AI-Service. "
        "Hai nhánh trích xuất CV và bộ 11 đặc trưng của Module 2 đã có hợp đồng dữ liệu trong thiết kế, và chưa có endpoint tương ứng trong bản mã này.",
    )


def chapter5(doc):
    heading_chapter(doc, "CHƯƠNG 5. KẾT QUẢ THỰC NGHIỆM VÀ GIAO DIỆN")

    heading2(doc, "5.1. Module 1 — loss huấn luyện")
    para(
        doc,
        "Số liệu dưới đây lấy từ báo cáo tiến độ trước. Loss giảm nhanh trong các bước đầu và giữ mức thấp đến bước 250. Bước 50 là hết epoch 1. Checkpoint lưu theo epoch. Giá trị ở bước 50 được làm tròn như trong nguồn.",
    )
    caption(doc, "Bảng 5.1. Loss theo bước")
    add_table(
        doc,
        ["Step", "Epoch", "Training loss", "Validation loss"],
        [
            ["10", "0,20", "1,671044", "1,576772"],
            ["20", "0,40", "0,612884", "0,512537"],
            ["30", "0,60", "0,033218", "0,025106"],
            ["50", "1,00", "0,004000", "0,003400"],
            ["100", "2,00", "0,000216", "0,000213"],
            ["150", "3,00", "0,000152", "0,000151"],
            ["200", "4,00", "0,000128", "0,000127"],
            ["250", "5,00", "0,000121", "0,000121"],
        ],
        font=11,
    )
    para(
        doc,
        "Training loss và validation loss cuối cùng cùng bằng 0,000121. Hai đường cùng giảm trên các mốc đã ghi, và validation loss không tăng lại ở các mốc đó. "
        "Kết luận dừng ở mức mô hình hội tụ trên khuôn JSON của tập nhãn tự sinh. Nhãn do Gemini tạo và chưa có tập kiểm thử người gán, nên loss này không đủ để kết luận độ đúng từng trường.",
    )
    figure(doc, "5.1", "Loss huấn luyện Module 1")

    heading2(doc, "5.2. Module 1 — suy luận và hiện vật")
    caption(doc, "Bảng 5.2. Kiểm tra suy luận đã ghi")
    add_table(
        doc,
        ["Chỉ số", "Kết quả"],
        [
            ["JSON hợp lệ", "10/10 mẫu qua CandidateProfile.model_validate()"],
            ["Kết thúc bằng EOS", "10/10 mẫu"],
            ["Độ dài đầu ra", "896–1399 token mỗi mẫu"],
            ["LoRA", "392 tensor; max|lora_B| = 0,6488"],
            ["Độ chính xác từng trường", "Chưa có"],
        ],
        font=10,
    )
    para(
        doc,
        "Tỷ lệ 10/10 thuộc một đợt kiểm tra suy luận riêng với lần chia 395/99. Nguồn chưa ghi cách chọn 10 mẫu và chưa ghi các mẫu này có nằm trong tập huấn luyện hay không. "
        "Khi báo cáo chính thức, tập đo, cách lấy mẫu và giao với tập train cần được ghi cùng bảng precision, recall và F1 theo trường.",
    )
    caption(doc, "Bảng 5.3. Hiện vật mô hình đã đóng gói")
    add_table(
        doc,
        ["Hiện vật", "Dung lượng", "Mục đích"],
        [
            ["LoRA adapter", "Khoảng 70 MB", "Nạp cùng mô hình nền, checkpoint-250"],
            ["Merged 16-bit", "Khoảng 3,44 GB", "Đã gộp adapter, Float16"],
            ["GGUF Q4_K_M", "Khoảng 1,11 GB", "Bản lượng tử hóa cho llama.cpp"],
        ],
        font=10,
    )
    para(
        doc,
        "Nguồn ước lượng bản GGUF khoảng 15–30 token mỗi giây trên CPU thông dụng và dưới một phút cho một CV. "
        "Số này phụ thuộc CPU, độ dài CV và tham số suy luận, nên chưa dùng làm mốc tốc độ chính thức.",
    )
    para(
        doc,
        "Nhánh luật xác định khi quy tắc khớp và truy được trạng thái parser. Nhánh LoRA linh hoạt hơn trên bố cục lạ và có chi phí nạp mô hình. "
        "Chưa có phép so cùng một tập CV về độ đúng trường, thời gian và tỷ lệ lỗi giữa hai nhánh.",
    )

    heading2(doc, "5.3. Module 2 — ví dụ minh họa")
    para(
        doc,
        "Module 2 chưa có số đo trên tập nhãn. Bảng dưới đây là vector minh họa trong báo cáo trước cho một CV backend của sinh viên năm cuối, 8 tháng thực tập, job_title để trống, và một JD Junior Java Backend Developer. "
        "B4 phụ thuộc embedding và được ghi là giá trị minh họa.",
    )
    caption(doc, "Bảng 5.4. Vector minh họa")
    add_table(
        doc,
        ["ID", "Giá trị", "Ghi chú trong nguồn"],
        [
            ["A1", "0,74", "Thiếu Git; SQL khớp một phần với MySQL và PostgreSQL"],
            ["A2", "0,00", "Chưa thấy Docker, Redis, Microservices, CI/CD, JUnit"],
            ["A3", "0,67", "8/12 tháng, còn mới"],
            ["B1", "1,00", "Backend, suy từ mô tả vì job_title trống"],
            ["B2", "0,67", "0,67 năm trên 1 năm tối thiểu"],
            ["B3", "0,70", "Fresher so với yêu cầu Junior"],
            ["B4", "0,70", "Minh họa; chưa thấy unit test và code review"],
            ["B5", "NaN", "missing, phần dự án bị cắt"],
            ["B6", "0,80", "Lĩnh vực thương mại điện tử"],
            ["C1", "0,88", "Ngành CNTT, dự kiến tốt nghiệp 2027"],
            ["C2", "NaN", "n/a, JD không yêu cầu chứng chỉ"],
        ],
        font=10,
    )
    para(
        doc,
        "Sau khi bỏ B5 và C2, nguồn tính điểm thô 0,6356 / 0,89 = 71,4. A1 bằng 0,74 nên cổng must-have không hạ trần. Điểm cuối khoảng 71 trên thang 100. "
        "Cờ D3 nhận warning vì ứng viên còn là sinh viên đến năm 2027 trong khi tin yêu cầu toàn thời gian. "
        "Bản đối sánh hybrid-matcher v0 trong mã web chưa tính vector này.",
    )

    heading2(doc, "5.4. Module 3 — chỉ số đã có và chỉ số chưa đo")
    para(
        doc,
        "Chỉ số đã có của Module 3 là Bảng 2.4 trên 52 mẫu lexical. "
        "Lần đo trên toàn bộ answers.csv với mode lexical, mode BERTScore và bốn kịch bản fine-tune chưa có tệp metrics trong cây mã. Các ô tương ứng để trống.",
    )
    caption(doc, "Bảng 5.5. Chỉ số Module 3")
    add_table(
        doc,
        ["Mô hình", "Tập", "MAE", "RMSE", "Pearson"],
        [
            ["Baseline F1×10", "self test", "…", "…", "…"],
            ["Ridge lexical", "test", "…", "…", "…"],
            ["Ridge BERTScore", "test", "…", "…", "…"],
            ["Fine-tune self", "self test", "…", "…", "…"],
            ["Fine-tune transfer", "self test", "…", "…", "…"],
            ["Fine-tune transfer", "mohler test", "…", "…", "…"],
        ],
        font=10,
    )

    heading2(doc, "5.5. Giao diện đang chạy")
    para(
        doc,
        "Các ảnh dưới đây thuộc bản web nối với MySQL và, với màn hình điểm phỏng vấn, với AI-Service cổng 8000. "
        "Tài khoản dữ liệu mẫu nằm ở Phụ lục A.",
    )
    figure(doc, "5.2", "Màn hình đăng nhập")
    figure(doc, "5.3", "Danh sách việc làm")
    figure(doc, "5.4", "Tải và xác nhận CV")
    figure(doc, "5.5", "Kết quả đối sánh")
    figure(doc, "5.6", "Phiên ôn tập và điểm câu trả lời")
    figure(doc, "5.7", "Màn hình nhà tuyển dụng")
    para(
        doc,
        "Màn hình đối sánh phản ánh công thức mục 3.5 và ghi điều còn chưa khớp yêu cầu. "
        "Màn hình chi tiết tin hiện mô tả, yêu cầu, trách nhiệm, đãi ngộ và nút ôn tập phỏng vấn. "
        "Màn hình CV hiện đúng các mục trong CV_FIELD; một field có từ hai dòng trở lên dùng danh sách gạch đầu dòng. "
        "Trích xuất tự động từ PDF chưa có trên giao diện hiện tại.",
    )

    heading2(doc, "5.6. Việc còn lại")
    bullet(doc, "Module 1: đo precision, recall và F1 theo trường trên tập người gán; so nhánh luật với nhánh LoRA trên cùng tập CV; gắn hai endpoint vào backend.")
    bullet(doc, "Module 2: lập ontology 150–300 nút; gán 40–60 cặp CV–JD; chọn backend của B4; học trọng số bằng XGBoost; bổ sung cột feature_scores, flags và evidence.")
    bullet(doc, "Module 3: điền Bảng 5.5; thêm một lần chia tập kiểm tra theo mã câu hỏi.")
    bullet(doc, "Hệ thống: thống nhất thang điểm đối sánh với thiết kế 0–100 khi bộ 11 đặc trưng được nối.")

    heading2(doc, "5.7. Kết luận Chương 5")
    para(
        doc,
        "Module 1 có 250 bước huấn luyện, loss cuối 0,000121, 10/10 mẫu JSON hợp lệ và ba hiện vật mô hình. Độ đúng từng trường chưa đo. "
        "Module 2 có một vector minh họa khoảng 71 điểm và chưa có chỉ số xếp hạng. "
        "Module 3 có MAE lexical trên tập 52 mẫu và chưa có bảng đủ trên tập hiện hành. Giao diện đã có chỗ cho cả ba nghiệp vụ.",
    )


def conclusion(doc):
    heading_chapter(doc, "KẾT LUẬN")
    para(
        doc,
        "Đồ án xây dựng hệ thống tuyển dụng cho ứng viên công nghệ thông tin với ba module: trích xuất CV, đối sánh CV với mô tả công việc, và chấm câu trả lời phỏng vấn.",
    )
    para(doc, "Phần đã có số liệu hoặc đã chạy trong mã gồm các mục sau.", indent=True)
    bullet(doc, "Qwen3-1.7B tinh chỉnh bằng LoRA trên 494 CV, loss cuối 0,000121, kiểm tra JSON 10/10 mẫu, adapter và bản GGUF đã đóng gói.")
    bullet(doc, "Ứng dụng web với JWT, MySQL, chọn vai trò một lần, hồ sơ field–value, đối sánh và ôn tập phỏng vấn cho ứng viên và nhà tuyển dụng.")
    bullet(doc, "Đối sánh hybrid-matcher v0 theo trùng tên kỹ năng và tỷ lệ kinh nghiệm.")
    bullet(doc, "Dịch vụ chấm phỏng vấn bằng độ tương đồng, độ phủ barem và Ridge, đã được Spring Boot gọi khi nộp bài. Tập hiện có 47 câu và 940 câu trả lời.")
    para(doc, "Phần đã thiết kế và chưa có số đo hoặc chưa gắn vào bản chạy gồm các mục sau.", indent=True)
    bullet(doc, "Nhánh luật PDFBox và endpoint trích xuất bằng LoRA.")
    bullet(doc, "Ontology kỹ năng, BGE-M3, BERTScore-Recall cho đặc trưng B4, mười một đặc trưng, bốn cờ, cổng must-have và XGBoost.")
    bullet(doc, "Bảng MAE đầy đủ của BERTScore và của bốn kịch bản fine-tune ở Module 3.")
    para(
        doc,
        "Thứ tự làm tiếp là đo độ đúng trường của Module 1, lập ontology cùng tập nhãn của Module 2, và hoàn thành bảng chỉ số của Module 3. "
        "Hợp đồng CandidateProfile và các cột điểm đối sánh được giữ để phần gắn sau không đổi màn hình.",
    )


def references(doc):
    heading_chapter(doc, "TÀI LIỆU THAM KHẢO")
    refs = [
        "Devlin, J., Chang, M.-W., Lee, K., và Toutanova, K. (2019). BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding. NAACL-HLT.",
        "Zhang, T., Kishore, V., Wu, F., Weinberger, K. Q., và Artzi, Y. (2020). BERTScore: Evaluating Text Generation with BERT. ICLR.",
        "Hu, E. J., Shen, Y., Wallis, P., Allen-Zhu, Z., Li, Y., Wang, S., Wang, L., và Chen, W. (2022). LoRA: Low-Rank Adaptation of Large Language Models. ICLR.",
        "Chen, J., Xiao, S., Zhang, P., Luo, K., Lian, D., và Liu, Z. (2024). M3-Embedding: Multi-Linguality, Multi-Functionality, Multi-Granularity. arXiv:2402.03216.",
        "Khattab, O., và Zaharia, M. (2020). ColBERT: Efficient and Effective Passage Search via Contextualized Late Interaction over BERT. SIGIR.",
        "Chen, T., và Guestrin, C. (2016). XGBoost: A Scalable Tree Boosting System. KDD.",
        "Qwen Team (2025). Qwen3 Technical Report.",
        "Mohler, M., Bunescu, R., và Mihalcea, R. (2011). Learning to Grade Short Answer Questions using Semantic Similarity Measures and Dependency Graph Alignments. ACL.",
        "Robertson, S., và Zaragoza, H. (2009). The Probabilistic Relevance Framework: BM25 and Beyond. Foundations and Trends in Information Retrieval.",
    ]
    for i, ref in enumerate(refs, start=1):
        para(doc, f"[{i}]  {ref}", align="left", indent=False, space_after=4, size=12)


def appendix(doc):
    heading_chapter(doc, "PHỤ LỤC")
    heading2(doc, "Phụ lục A. Tài khoản dữ liệu mẫu và lệnh chạy")
    add_table(
        doc,
        ["Vai trò", "Email", "Mật khẩu"],
        [
            ["Ứng viên", "candidate@hirelens.local", "demo1234"],
            ["Nhà tuyển dụng", "recruiter@hirelens.local", "demo1234"],
            ["Quản trị", "admin@hirelens.local", "demo1234"],
        ],
    )
    commands = [
        "docker compose up -d",
        "cd backend && ./mvnw spring-boot:run",
        "cd frontend && npm install && npm run dev",
        "cd AI && python -m src.train_calibration --mode fast",
        "cd AI && python -m src.train_calibration --mode bertscore",
        "cd AI && python -m src.finetune_bert --scenario transfer --epochs 3 --mohler-epochs 2",
        "cd AI && uvicorn src.api:app --host 0.0.0.0 --port 8000",
    ]
    for cmd in commands:
        p = doc.add_paragraph()
        p.paragraph_format.line_spacing = 1.15
        p.paragraph_format.space_after = Pt(2)
        p.paragraph_format.left_indent = Cm(1)
        run = p.add_run(cmd)
        set_run_font(run, size=11, name="Courier New")

    heading2(doc, "Phụ lục B. Hợp đồng chấm một câu trả lời")
    para(
        doc,
        "Backend gửi answer, question, reference_answer, criteria và mode. Mỗi tiêu chí có key, label, weight và hints. "
        "Phản hồi có predicted_score, score_scale bằng 0-10, covered_points, missing_points, comment, model_version và mode.",
    )
    figure(doc, "B.1", "Request và response của một câu chấm điểm")


def main():
    stats = load_stats()
    doc = Document()
    setup_styles(doc)
    setup_section(doc)
    settings = doc.settings.element
    update = OxmlElement("w:updateFields")
    update.set(qn("w:val"), "true")
    settings.append(update)

    cover(doc)
    front_matter(doc, stats)
    chapter1(doc)
    chapter2(doc, stats)
    chapter3(doc)
    chapter4(doc)
    chapter5(doc)
    conclusion(doc)
    references(doc)
    appendix(doc)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    doc.save(OUT)
    print(f"Wrote {OUT}")
    print(
        f"stats questions={stats['n_questions']} answers={stats['n_answers']} "
        f"mean={stats['score_mean']:.2f}"
    )


if __name__ == "__main__":
    main()

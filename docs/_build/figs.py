"""Diagrams and charts for the thesis-format report (no real CV content; counts only).

Run from ai-service/:  <python with matplotlib> ../docs/_build/figs.py ../docs/_build/fig
"""
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle  # noqa: E402

OUT = Path(sys.argv[1])
OUT.mkdir(parents=True, exist_ok=True)
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.spines.top": False,
                     "axes.spines.right": False, "axes.edgecolor": "#8a8a8a", "axes.labelcolor": "#333333",
                     "xtick.color": "#444444", "ytick.color": "#444444"})
# reference categorical palette (dataviz skill), fixed order
BLUE, ORANGE, AQUA, YELLOW, MAGENTA, GREEN = "#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300"
GRAY, INK = "#9a9a9a", "#2b2b2b"
FILL = {"fe": "#E2EFDA", "be": "#DEEAF6", "ai": "#FCE4D6", "kb": "#FFF2CC", "ext": "#EDEDED", "train": "#E4DFEC"}


def box(ax, x, y, w, h, text, fill="#DEEAF6", edge="#2E75B6", size=9, bold_first=True, r=0.02):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad=0.004,rounding_size={r}", fc=fill, ec=edge, lw=1.1))
    lines = text.split("\n")
    n = len(lines)
    for i, line in enumerate(lines):
        yy = y + h / 2 + (n - 1) * 0.5 * size * 0.0042 - i * size * 0.0042
        ax.text(x + w / 2, yy, line, ha="center", va="center", fontsize=size if i else size + (0.5 if bold_first else 0),
                weight="bold" if (i == 0 and bold_first) else "normal", color=INK)


def arrow(ax, a, b, text=None, color="#4a4a4a", style="-|>", ls="-", off=(0, 0.012), size=8, rad=0.0):
    ax.add_patch(FancyArrowPatch(a, b, arrowstyle=style, mutation_scale=11, color=color, lw=1.1, linestyle=ls,
                                 connectionstyle=f"arc3,rad={rad}"))
    if text:
        ax.text((a[0] + b[0]) / 2 + off[0], (a[1] + b[1]) / 2 + off[1], text, ha="center", va="bottom", fontsize=size,
                color="#333333", bbox=dict(fc="white", ec="none", pad=0.6, alpha=0.9))


def canvas(w, h):
    fig = plt.figure(figsize=(w, h))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    return fig, ax


def save(fig, name):
    fig.savefig(OUT / name, dpi=170, bbox_inches="tight", pad_inches=0.08, facecolor="white")
    plt.close(fig)


# ---------------------------------------------------------------- architecture
fig, ax = canvas(10, 5.6)
box(ax, 0.02, 0.62, 0.17, 0.2, "Người dùng\nnhà tuyển dụng\n(trình duyệt)", FILL["fe"], "#548235")
box(ax, 0.25, 0.62, 0.2, 0.2, "Frontend\nReact 19 + Vite\nupload CV, xem hồ sơ", FILL["fe"], "#548235")
box(ax, 0.52, 0.55, 0.22, 0.34, "Backend\nJava 21 · Spring Boot\nCvAnalysisService\nPdfTextExtractor (PDFBox,\nXY-cut theo cột)\nAiServiceClient (Feign)", FILL["be"], "#2E75B6")
box(ax, 0.8, 0.62, 0.18, 0.2, "Module 2\nso khớp CV – JD\n(dùng CandidateProfile)", FILL["ext"], "#7f7f7f")
box(ax, 0.47, 0.06, 0.32, 0.36, "AI service\nPython · FastAPI · llama.cpp\nprompt v3 → mô hình v4 (GGUF)\nchặn lặp · sinh nối tiếp\nhậu kiểm grounding\nchuẩn hoá KB · KG enrich", FILL["ai"], "#C55A11")
box(ax, 0.06, 0.06, 0.3, 0.36, "Knowledge Base / Graph\nNeo4j 5.26 (kho chính)\nKB2: 813 kỹ năng, 2.284 alias,\n387 trường, 743 nghề\nKB1: 2 sách PDF, 353 mục\nfallback: PostgreSQL / CSV", FILL["kb"], "#BF9000")
box(ax, 0.83, 0.12, 0.16, 0.24, "Huấn luyện\nGoogle Colab T4\nUnsloth + TRL\nGoogle Drive\n(dataset, GGUF)", FILL["train"], "#7030A0", size=8.5)
arrow(ax, (0.19, 0.72), (0.25, 0.72), "HTTPS", off=(0, 0.015))
arrow(ax, (0.45, 0.72), (0.52, 0.72), "PDF", off=(0, 0.015))
arrow(ax, (0.74, 0.72), (0.8, 0.72), "JSON", off=(0, 0.015))
arrow(ax, (0.6, 0.55), (0.6, 0.42), "POST /api/v1/extract-cv\n{cv_text}", off=(-0.085, -0.03))
arrow(ax, (0.68, 0.42), (0.68, 0.55), "{data: CandidateProfile}", off=(0.09, -0.02))
arrow(ax, (0.47, 0.24), (0.36, 0.24), "nạp KB khi khởi động\n(Bolt 7687)", off=(0, 0.01))
arrow(ax, (0.83, 0.24), (0.79, 0.24), style="-|>", ls="--")
ax.text(0.905, 0.385, "file GGUF", ha="center", fontsize=8, color="#333333")
save(fig, "d_architecture.png")

# ---------------------------------------------------------------- sequence diagram
fig, ax = canvas(10.5, 7.2)
actors = ["Người dùng /\nFrontend", "Backend\nCvAnalysisService", "PdfTextExtractor\n(PDFBox + XY-cut)", "AI service\n/api/v1/extract-cv",
          "llama.cpp\nmô hình v4", "KB / KG\n(trong RAM)"]
xs = [0.075, 0.24, 0.405, 0.57, 0.745, 0.915]
for x, a in zip(xs, actors):
    box(ax, x - 0.072, 0.9, 0.144, 0.08, a, "#DEEAF6", "#2E75B6", size=8, bold_first=False)
    ax.plot([x, x], [0.04, 0.9], color="#b0b0b0", lw=1, ls="--")
msgs = [
    (0, 1, "POST /api/v1/cv/analyze-pdf (multipart PDF)", 0.86),
    (1, 2, "extract(bytes, mode=layout)", 0.81),
    (2, 2, "1. lấy từng glyph + toạ độ\n2. ghép từ, tách đoạn\n3. XY-cut: chia cột / hàng\n4. ghép text theo thứ tự đọc", 0.705),
    (2, 1, "cv_text (thứ tự đọc đúng)", 0.63),
    (1, 3, "Feign: POST {cv_text}", 0.585),
    (3, 3, "clean_cv_text · kiểm tra độ dài\nrender_prompt (prompt v3)", 0.52),
    (3, 4, "stream sinh token (greedy)", 0.465),
    (4, 3, "JSON từng phần · LoopGuard theo dõi", 0.425),
    (3, 4, "(nếu bị cắt) sinh nối tiếp từ khoá còn thiếu", 0.38),
    (3, 3, "parse + ghép mảnh · hậu kiểm grounding\nsửa ngày · dọn rác", 0.31),
    (3, 5, "link kỹ năng / trường · duyệt quan hệ", 0.25),
    (5, 3, "tên chuẩn, implied / related skills", 0.21),
    (3, 1, "200 {data: CandidateProfile}", 0.16),
    (1, 0, "CandidateProfile (JSON) → hiển thị / Module 2", 0.1),
]
for a, b, text, y in msgs:
    if a == b:
        ax.add_patch(Rectangle((xs[a] - 0.006, y - 0.03), 0.012, 0.06, fc="#FCE4D6", ec="#C55A11", lw=0.8))
        ax.text(xs[a] + 0.015, y, text, fontsize=7.6, va="center", ha="left", color=INK,
                bbox=dict(fc="white", ec="#dddddd", pad=1.5))
        continue
    ls = "--" if xs[b] < xs[a] else "-"
    ax.add_patch(FancyArrowPatch((xs[a], y), (xs[b], y), arrowstyle="-|>", mutation_scale=10, color="#333333", lw=1, linestyle=ls))
    ax.text((xs[a] + xs[b]) / 2, y + 0.006, text, ha="center", va="bottom", fontsize=7.8, color=INK)
save(fig, "d_sequence.png")

# ---------------------------------------------------------------- ai-service pipeline
steps = [
    ("1. Nhận request", "routes.py: kiểm tra cv_text, tham số include (kg, raw)", FILL["ai"]),
    ("2. Làm sạch + prompt", "clean_cv_text → render_prompt v3 (system + CV + mồi JSON); quá dài → 413", FILL["ai"]),
    ("3. Sinh có kiểm soát", "llama.cpp stream, temperature 0, ≤ 2.048 token; LoopGuard dừng khi chuỗi > 2.000 ký tự\nhoặc một giá trị lặp 3 lần trong một danh sách", FILL["ai"]),
    ("4. Sinh nối tiếp", "nếu JSON bị cắt: giữ phần hoàn chỉnh, mồi lại từ khoá cấp cao còn thiếu, ghép hai phần (feature 012)", FILL["ai"]),
    ("5. Parse JSON", "extract_json + json_repair + merge_fragments; không còn object → 502", FILL["ai"]),
    ("6. Hậu kiểm", "normalize_profile → clean_skill_list (sửa ngoặc) → ground_profile (mọi giá trị phải có trong CV)\n→ fix_date_order → cleanup_profile (bỏ công ty trùng tên dự án, địa chỉ, kỹ năng rác)", "#F8CBAD"),
    ("7. KG (chạy ngầm)", "enrich: skills_normalized, implied_skills (REQUIRES/PART_OF), related_skills (sách),\nskills_detected, flags", FILL["kb"]),
    ("8. Chuẩn hoá bằng KB", "kỹ năng, tech_stack → tên chuẩn; tên trường → tên chính thức; kỹ năng mềm giữ nguyên", FILL["kb"]),
    ("9. Trả kết quả", "{data: CandidateProfile}; + trường KG nếu include=kg; + raw_profile nếu include=raw", FILL["fe"]),
]
fig, ax = canvas(10, 8.2)
h, gap = 0.088, 0.022
for i, (t, d, f) in enumerate(steps):
    y = 1 - (i + 1) * (h + gap) + gap / 2
    ax.add_patch(FancyBboxPatch((0.01, y), 0.23, h, boxstyle="round,pad=0.003,rounding_size=0.015", fc=f, ec="#7f7f7f", lw=1))
    ax.text(0.125, y + h / 2, t, ha="center", va="center", fontsize=10, weight="bold", color=INK)
    ax.add_patch(FancyBboxPatch((0.25, y), 0.74, h, boxstyle="round,pad=0.003,rounding_size=0.015", fc="white", ec="#bfbfbf", lw=1))
    ax.text(0.265, y + h / 2, d, ha="left", va="center", fontsize=8.6, color=INK, linespacing=1.4)
    if i < len(steps) - 1:
        ax.add_patch(FancyArrowPatch((0.125, y), (0.125, y - gap), arrowstyle="-|>", mutation_scale=9, color="#555555", lw=1))
save(fig, "d_ai_pipeline.png")

# ---------------------------------------------------------------- synthetic data pipeline
fig, ax = canvas(10.5, 5.4)
row = [
    (0.0, "Hồ sơ hư cấu\nJSONL (Gemini /\nChatGPT theo\nprofile_prompt.md)", FILL["train"]),
    (0.17, "Biến thể\nvariants.py\nnhiều công ty,\nsinh viên (v5)", FILL["train"]),
    (0.34, "Render HTML\n15 bố cục L1–L15\n(1 cột, 2 cột,\nbảng, timeline)", FILL["be"]),
    (0.51, "LibreOffice\nHTML → PDF\n(headless)", FILL["be"]),
    (0.68, "Backend\nPdfTextDumpRunner\ntext layout\n(như khi serve)", FILL["be"]),
    (0.85, "Nhãn = hồ sơ gốc\nground_label:\nbỏ giá trị không\nin ra trong text", FILL["kb"]),
]
for x, t, f in row:
    box(ax, x + 0.005, 0.6, 0.14, 0.3, t, f, "#7f7f7f", size=8.3)
for i in range(len(row) - 1):
    arrow(ax, (row[i][0] + 0.145, 0.75), (row[i + 1][0] + 0.005, 0.75))
box(ax, 0.02, 0.1, 0.25, 0.3, "CV thật (31, chỉ trên máy)\nnhãn v3 căn lại theo text layout\n+ hoán đổi tên công ty/trường\n(×3 ở v4, ×4 ở v5)", "#F8CBAD", "#C55A11", size=8.3)
box(ax, 0.31, 0.1, 0.22, 0.3, "CV tổng hợp cũ (silver)\n250 mẫu, nhãn LLM\náp quy ước v3", FILL["ext"], "#7f7f7f", size=8.3)
box(ax, 0.6, 0.06, 0.38, 0.38, "build_dataset_v4 / v5\n· prompt = render_prompt (giống serve)\n· completion = JSON nhãn\n· tách dev theo hồ sơ, chống rò rỉ test\n· loại mẫu > 4.096 token\n→ train / dev / val / val_swap / test_real", "#E2EFDA", "#548235", size=8.3)
arrow(ax, (0.92, 0.6), (0.85, 0.44))
arrow(ax, (0.145, 0.1), (0.6, 0.12), rad=0.25)
arrow(ax, (0.53, 0.32), (0.6, 0.32))
save(fig, "d_data_pipeline.png")

# ---------------------------------------------------------------- XY-cut illustration
fig, axes = plt.subplots(1, 2, figsize=(10, 5.2))
for k, ax in enumerate(axes):
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 140)
    ax.invert_yaxis()
    ax.set_aspect("equal")
    ax.axis("off")
    ax.add_patch(Rectangle((0, 0), 100, 140, fc="white", ec="#7f7f7f", lw=1))
    head = [(6, 5, 60, 6), (6, 13, 40, 3), (6, 18, 35, 3)]
    left = [(6, 28, 30, 4), (6, 34, 26, 3), (6, 39, 28, 3), (6, 48, 30, 4), (6, 54, 24, 3), (6, 59, 27, 3), (6, 68, 30, 4), (6, 74, 22, 3)]
    right = [(44, 28, 50, 4), (44, 34, 48, 3), (44, 39, 50, 3), (44, 44, 46, 3), (44, 53, 50, 4), (44, 59, 49, 3), (44, 64, 47, 3),
             (44, 69, 50, 3), (44, 74, 44, 3), (44, 83, 50, 4), (44, 89, 48, 3), (44, 94, 45, 3)]
    for (x, y, w, h) in head:
        ax.add_patch(Rectangle((x, y), w, h, fc="#cfcfcf", ec="none"))
    for (x, y, w, h) in left:
        ax.add_patch(Rectangle((x, y), w, h, fc="#9ec5f4", ec="none"))
    for (x, y, w, h) in right:
        ax.add_patch(Rectangle((x, y), w, h, fc="#f8b99b", ec="none"))
    ax.add_patch(Rectangle((2, 25), 36, 55, fc="none", ec="#7f7f7f", lw=0.6, ls=":"))
    if k == 0:
        ax.set_title("PDFBox mặc định: đọc theo từng dòng ngang", fontsize=10)
        for y in (30, 36, 41, 50, 56, 61):
            ax.annotate("", xy=(96, y), xytext=(4, y), arrowprops=dict(arrowstyle="-|>", color=MAGENTA, lw=0.9))
        ax.text(50, 112, "→ mỗi dòng trộn cột trái + cột phải\n\"Education Summary\"\n\"(HCMUT) high-throughput financial …\"",
                ha="center", fontsize=8.5, color=INK)
    else:
        ax.set_title("Layout (XY-cut): cắt khoảng trắng rồi đọc từng khối", fontsize=10)
        ax.plot([0, 100], [24, 24], color=BLUE, lw=1.6, ls="--")
        ax.plot([40, 40], [24, 140], color=ORANGE, lw=1.6, ls="--")
        ax.text(98, 22.5, "cắt ngang (hàng)", ha="right", fontsize=8, color=BLUE)
        ax.text(4, 96, "cắt dọc (cam):\ncột thật khi có\n≥ 3 đoạn và rộng\n≥ 25 % vùng", fontsize=8, color=ORANGE)
        for (lbl, x, y) in (("①", 70, 9), ("②", 20, 84), ("③", 70, 101)):
            ax.text(x, y, lbl, fontsize=15, ha="center", color=INK)
        ax.text(50, 133, "thứ tự đọc: ① đầu trang → ② cột trái → ③ cột phải", ha="center", fontsize=8.5, color=INK,
                bbox=dict(fc="white", ec="none", pad=1))
save(fig, "d_xycut.png")

# ---------------------------------------------------------------- LoRA
fig, ax = canvas(9, 3.8)
box(ax, 0.03, 0.3, 0.12, 0.4, "x\n(đầu vào\nlớp)", "#EDEDED", "#7f7f7f", size=9)
box(ax, 0.25, 0.55, 0.26, 0.38, "W₀ (d × d)\ntrọng số gốc Qwen3\nĐÓNG BĂNG\n(nạp 4-bit)", "#DEEAF6", "#2E75B6", size=9)
box(ax, 0.25, 0.06, 0.11, 0.36, "A\n(r × d)\nhọc", "#FCE4D6", "#C55A11", size=9)
box(ax, 0.4, 0.06, 0.11, 0.36, "B\n(d × r)\nhọc", "#FCE4D6", "#C55A11", size=9)
box(ax, 0.62, 0.32, 0.11, 0.36, "+", "#ffffff", "#7f7f7f", size=16)
box(ax, 0.82, 0.3, 0.16, 0.4, "h = W₀x\n+ (α/r)·BAx", "#E2EFDA", "#548235", size=9)
arrow(ax, (0.15, 0.55), (0.25, 0.72))
arrow(ax, (0.15, 0.45), (0.25, 0.25))
arrow(ax, (0.36, 0.24), (0.4, 0.24))
arrow(ax, (0.51, 0.72), (0.62, 0.55))
arrow(ax, (0.51, 0.24), (0.62, 0.45))
arrow(ax, (0.73, 0.5), (0.82, 0.5))
ax.text(0.38, 0.0, "r = 16, α = 32, gắn vào q, k, v, o, gate, up, down — chỉ ~1 % tham số được học", ha="center", fontsize=8.5, color=INK)
save(fig, "d_lora.png")

# ---------------------------------------------------------------- training notebook flow
fig, ax = canvas(10.5, 2.6)
cells = [("Build dataset\n(máy local)", FILL["be"]), ("Upload Drive\nretrain_vN/", FILL["ext"]), ("[1–3] cấu hình,\nclone code,\nkiểm prompt", FILL["train"]),
         ("[4] Qwen3-1.7B\n4-bit + LoRA", FILL["train"]), ("[5–6] SFT 2 epoch\nloss chỉ trên JSON\nchọn dev loss tốt nhất", FILL["train"]),
         ("[7–8] dự đoán +\nchấm 20 CV thật", FILL["kb"]), ("[9] gộp adapter\nxuất GGUF Q4_K_M", FILL["ai"]), ("[10–11] API +\nCloudflare tunnel", FILL["fe"])]
w = 0.112
for i, (t, f) in enumerate(cells):
    x = 0.005 + i * (w + 0.013)
    box(ax, x, 0.2, w, 0.6, t, f, "#7f7f7f", size=7.8, bold_first=False)
    if i < len(cells) - 1:
        arrow(ax, (x + w, 0.5), (x + w + 0.013, 0.5))
save(fig, "d_train_flow.png")

# ---------------------------------------------------------------- KB build
fig, ax = canvas(10.5, 4.4)
srcs = ["Stack Overflow\nSurvey 2024–2026", "Stack Overflow\ntags", "Wikidata\n(SPARQL)", "GitHub\nLinguist", "ESCO v1.2.1", "Wikipedia vi\n+ web trường", "Sách PDF\nPro Git,\nThink Python"]
for i, s in enumerate(srcs):
    box(ax, 0.005 + i * 0.142, 0.74, 0.13, 0.22, s, FILL["ext"] if i < 6 else "#FBE5D6", "#7f7f7f", size=7.8, bold_first=False)
box(ax, 0.03, 0.38, 0.25, 0.22, "kb.fetch_sources\nsnapshot + MANIFEST\n(URL, SHA-256, giấy phép)", FILL["be"], "#2E75B6", size=8)
box(ax, 0.35, 0.38, 0.25, 0.22, "kb.build_external\nchọn kỹ năng, alias, quan hệ\nmỗi dòng có cột source", FILL["be"], "#2E75B6", size=8)
box(ax, 0.67, 0.38, 0.3, 0.22, "kb.books (KB1)\nmục lục → mục → MENTIONS\nđồng xuất hiện → RELATED_TO", "#FBE5D6", "#C55A11", size=8)
box(ax, 0.2, 0.04, 0.3, 0.22, "seed CSV (KB2)\nskills · aliases · edges\nuniversities · job_titles", FILL["kb"], "#BF9000", size=8)
box(ax, 0.58, 0.04, 0.38, 0.22, "kb.neo4j_load → Neo4j\nKB2 + KB1 + gộp (RELATED_TO, ABOUT)\n→ AI service: KnowledgeBase.from_neo4j()", FILL["kb"], "#BF9000", size=8)
for i in range(6):
    arrow(ax, (0.07 + i * 0.142, 0.74), (0.155, 0.6), color="#9a9a9a")
arrow(ax, (0.92, 0.74), (0.82, 0.6), color="#9a9a9a")
arrow(ax, (0.28, 0.49), (0.35, 0.49))
arrow(ax, (0.475, 0.38), (0.36, 0.26))
arrow(ax, (0.5, 0.15), (0.58, 0.15))
arrow(ax, (0.82, 0.38), (0.8, 0.26))
arrow(ax, (0.6, 0.49), (0.67, 0.49), "kỹ năng KB2", off=(0, 0.01), size=7)
save(fig, "d_kb_build.png")

# ================================================================ charts
data = Path("data")


def bars(groups, series, values, colors, title_y, name, ylim=(0, 1.05), figsize=(10, 4.2), label_fmt="{:.2f}", labels=True):
    fig, ax = plt.subplots(figsize=figsize)
    n = len(series)
    w = 0.8 / n
    for i, (s, c) in enumerate(zip(series, colors)):
        xs = [j + (i - (n - 1) / 2) * w for j in range(len(groups))]
        ys = [values[s][g] for g in groups]
        b = ax.bar(xs, ys, w - 0.02, label=s, color=c, edgecolor="white", linewidth=1)
        if labels:
            for rect, y in zip(b, ys):
                ax.text(rect.get_x() + rect.get_width() / 2, y + 0.012, label_fmt.format(y).replace(".", ","), ha="center",
                        fontsize=7, color="#444444")
    ax.set_xticks(range(len(groups)))
    ax.set_xticklabels(groups)
    ax.set_ylabel(title_y)
    ax.set_ylim(*ylim)
    ax.grid(axis="y", color="#e6e6e6", lw=0.8)
    ax.set_axisbelow(True)
    ax.legend(ncol=n, frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.1), fontsize=9)
    fig.tight_layout()
    fig.savefig(OUT / name, dpi=170, facecolor="white")
    plt.close(fig)


# text mode effect, model v3, 19 real CVs (specs 011, 012)
F = ["company", "job_title", "school", "project", "skills", "certificates", "languages"]
tm = {"Text PDFBox cũ (legacy)": [0.667, 0.800, 0.865, 0.729, 0.737, 0.308, 0.667],
      "Text theo cột (layout, 011)": [0.780, 0.929, 1.0, 0.860, 0.822, 0.556, 0.759],
      "Layout + sinh nối tiếp, hậu kiểm (012)": [0.941, 0.966, 1.0, 0.882, 0.857, 0.500, 0.750]}
bars(F, list(tm), {k: dict(zip(F, v)) for k, v in tm.items()}, [GRAY, BLUE, AQUA], "F1 (19 CV thật, mô hình v3)", "c_textmode.png")

# v3 vs v4 (serving path, 19 real CVs, spec 013)
vv = {"v3 + 012": [0.941, 0.966, 1.0, 0.882, 0.857, 0.500, 0.750], "v4 + 012": [0.788, 0.909, 1.0, 0.822, 0.889, 0.526, 0.815]}
bars(F, list(vv), {k: dict(zip(F, v)) for k, v in vv.items()}, [BLUE, ORANGE], "F1 (19 CV thật, qua pipeline serve)", "c_v3_v4.png")

# dataset composition v3 -> v5
comp = {}
for v in ("retrain_v3", "retrain_v4", "retrain_v5"):
    comp[v.split("_")[1]] = json.load(open(data / v / "summary.json"))["train_by_source"]
srcs = [("generated", "CV sinh theo bố cục (hư cấu)", BLUE), ("synthetic", "CV tổng hợp cũ (silver)", GRAY),
        ("real", "CV thật", ORANGE), ("real_swap", "CV thật hoán đổi tên", YELLOW)]
fig, ax = plt.subplots(figsize=(9, 3.6))
vers = list(comp)
left = [0] * len(vers)
for key, lbl, col in srcs:
    vals = [comp[v].get(key, 0) for v in vers]
    ax.barh(vers, vals, left=left, color=col, edgecolor="white", linewidth=2, label=lbl, height=0.55)
    for i, (l, val) in enumerate(zip(left, vals)):
        if val >= 60:
            ax.text(l + val / 2, i, str(val), ha="center", va="center", fontsize=8.5, color="white" if col != YELLOW else INK)
    left = [l + val for l, val in zip(left, vals)]
for i, t in enumerate(left):
    ax.text(t + 12, i, f"{t} mẫu", va="center", fontsize=9, color=INK)
ax.invert_yaxis()
ax.set_xlabel("số mẫu train")
ax.set_xlim(0, 1300)
ax.grid(axis="x", color="#e6e6e6", lw=0.8)
ax.set_axisbelow(True)
ax.legend(ncol=2, frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.22), fontsize=8.5)
fig.tight_layout()
fig.savefig(OUT / "c_dataset.png", dpi=170, facecolor="white")
plt.close(fig)

# training curves v3 / v4
logs = {"v3": data / "finetune_output_v3/finetune_output_v3/train_log.json", "v4": data / "finetune_output_v4/train_log.json"}
fig, axes = plt.subplots(1, 2, figsize=(10, 3.6), sharey=False)
for (name, p), col in zip(logs.items(), (BLUE, ORANGE)):
    lg = json.load(open(p))
    axes[0].plot([s for s, _ in lg["train_loss"]], [v for _, v in lg["train_loss"]], color=col, lw=1.6, label=f"mô hình {name}")
    axes[1].plot([s for s, _ in lg["dev_loss"]], [v for _, v in lg["dev_loss"]], color=col, lw=2, marker="o", ms=4, label=f"mô hình {name}")
for a, t in zip(axes, ("train loss", "dev loss")):
    a.set_title(t, fontsize=10)
    a.set_xlabel("bước (batch hiệu dụng 8)")
    a.set_yscale("log")
    a.grid(color="#eeeeee", lw=0.8)
    a.legend(frameon=False, fontsize=8.5)
fig.tight_layout()
fig.savefig(OUT / "c_loss.png", dpi=170, facecolor="white")
plt.close(fig)
print("figures written to", OUT)

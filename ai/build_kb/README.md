# build_kb: Knowledge Base kỹ năng IT

Schema ở `docs/Knowledge base.md`, kế hoạch KB1 ở `docs/ke-hoach-kb1-roadmap-pdf.md`, trạng thái ở `docs/trang-thai-kb.md`.

```
build_kb/
├── load_kb.py        gộp KB1 + KB2 vào out/, rồi nạp Neo4j
├── out/              KB đã gộp: kb_nodes.jsonl, kb_edges.jsonl, kb_checks.json
├── shared/           hàm và hằng dùng chung
├── kb1/              nguồn PDF roadmap, cộng alias từ Stack Overflow
│   ├── pipeline/     code
│   ├── data/         đầu vào: pdf/, sources.csv, tag_synonyms.csv
│   └── out/          kết quả: kb1_nodes.jsonl, kb1_edges.jsonl, so_alias_report.csv, file trung gian
├── kb2/              nguồn web: chức danh ITviec
│   ├── pipeline/     code
│   ├── data/         đầu vào: sources.csv, itviec_titles_raw.csv, itviec_title_map.csv, levels.csv
│   └── out/          kết quả: kb2_nodes.jsonl, kb2_edges.jsonl, kb2_level_nodes.jsonl, kb2_checks.json
├── tests/
└── docs/
```

## Cài đặt

```powershell
conda activate module2
pip install -r requirements.txt
copy .env.example .env        # điền groq_api_key (console.groq.com)
docker start neo4j            # lần đầu: docker run -d --name neo4j -p 7474:7474 -p 7687:7687 -e NEO4J_AUTH=neo4j/changeme123 neo4j:5-community
```

Mọi lệnh chạy từ thư mục `build_kb/`.

## KB1 lấy từ roadmap.sh

```powershell
python -m kb1.pipeline.s1_survey      # ảnh có khung ở kb1/out/survey/
python -m kb1.pipeline.s2_nodes       # --only backend,ai-engineer để chạy thử
python -m kb1.pipeline.s3_groups
python -m kb1.pipeline.s4_classify    # gọi Groq, có cache ở kb1/out/label_cache.json; hết hạn mức thì chạy lại để tiếp tục
python -m kb1.pipeline.s5_triples     # ghi kb1_nodes.jsonl, kb1_edges.jsonl, thêm alias Stack Overflow
python -m kb1.pipeline.s6_report      # số liệu ở kb1/out/report/
```

Mỗi bước đọc kết quả của bước trước trong `kb1/out/`, nên sai ở bước nào thì chạy lại từ bước đó.

### Alias từ Stack Overflow

`python -m kb1.pipeline.so_tag_synonyms --key YOUR_API_KEY` tải `kb1/data/tag_synonyms.csv`. `s5_triples` đọc file này và thêm alias qua `so_aliases.py`. Mặc định loại: tag chỉ được nhận khi cùng tên với tag đích hoặc nằm trong danh sách duyệt tay ở `kb1/pipeline/config.py` (`SO_KEEP`, `SO_AMBIGUOUS`, `SO_BRIDGE`). Từng quyết định và lý do ghi ở `kb1/out/so_alias_report.csv`; dòng `conflict` là tag đang thuộc skill khác, nên xem có cần gộp hai skill không.

### Kiểm tay cho báo cáo

Điền `parent_expected` trong `kb1/out/gold_groups.csv` và `type_expected` trong `kb1/out/gold_labels.csv` (`technology`, `concept`, `category`, `not_skill`), rồi chạy lại `s6_report`. Chưa điền thì `accuracy.csv` ghi "chưa có đáp án".

## KB2 lấy từ itviec_title

```powershell
python -m kb2.pipeline.s1_crawl_itviec   # cào bản Việt và Anh về kb2/data/itviec_titles_raw.csv
python -m kb2.pipeline.s2_titles         # ghi kb2/out/kb2_nodes.jsonl, kb2_edges.jsonl, kb2_checks.json
python -m kb2.pipeline.s4_levels         # ghi kb2/out/kb2_level_nodes.jsonl
```

`kb2/data/itviec_title_map.csv` là bảng duyệt tay: cặp Việt - Anh, tên chuẩn (`canonical`, để trống thì lấy tên tiếng Anh), `role_groups`, alias thêm. Hai bản trên ITviec sắp theo bảng chữ cái riêng nên không ghép được theo vị trí; `s2_titles` dừng nếu bảng này lệch với dữ liệu đã cào. Chức danh chưa có nhóm vai trò nằm ở `titles_without_role_group` trong `kb2/out/kb2_checks.json`.

`kb2/data/levels.csv` (T4) giữ thang `rank` của thiết kế, `s4_levels` dừng nếu lệch thang. Alias tự soạn, nguồn `M02`, `trust = low`.

## Gộp và nạp

```powershell
python load_kb.py --merge-only   # chỉ gộp và kiểm tra vào out/
python load_kb.py                # gộp rồi nạp Neo4j
python -m pytest tests
```

`load_kb.py` thay toàn bộ `Skill`, `Category`, `JobTitle`, `Level`, `Source` trong một giao dịch và giữ `RoleGroup`. Có alias trùng hoặc quan hệ trỏ tới nút không tồn tại thì dừng, không ghi gì.

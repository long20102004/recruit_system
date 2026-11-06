# KB từ nguồn công khai

Chạy từ `ai-service/` (không cần dependency mới):

```sh
.venv/bin/python -m kb.fetch_sources
.venv/bin/python -m kb.build_external
.venv/bin/python -c 'from kb.load import read_seed, validate; assert not validate(read_seed("kb/seed"))'
```

Fetch dùng cache có kiểm tra SHA-256; `--refresh` tải lại. Snapshot công khai trong
`kb/sources/` và `MANIFEST.json` được lưu cùng mã nguồn. Fetch không đọc CV thật,
chỉ dùng tần suất nhãn của hai nguồn **tổng hợp/hư cấu** được phép để chọn truy vấn
gap-fill Wikidata; không lưu nhãn đầu vào hoặc nội dung hồ sơ vào snapshot.

Build hoàn toàn offline từ snapshot, kiểm tra checksum trước khi dựng. Lệnh cũ
`kb.build_seed` chỉ chuyển sang builder mới; không còn nhận train/curated inputs.
Không sửa tay CSV sinh tự động. Nguồn, giấy phép, phương pháp và số dòng nằm trong
[SOURCES.md](SOURCES.md), được sinh lại cùng seed.

| File | Nguồn |
|---|---|
| skills.csv | Stack Overflow 2024–2026, Wikidata gap-fill, ESCO transversal |
| skill_aliases.csv | Nhãn/alias Wikidata en/vi, Linguist, ESCO, tên khảo sát |
| skill_edges.csv | Wikidata P277/P361/P527, loại vòng lặp/chu trình |
| categories.csv | 16 nhóm hiện có của dự án, ánh xạ loại câu hỏi/lớp nguồn |
| universities.csv | Tên tiếng Việt từ Wikipedia revision 75654510 |
| university_aliases.csv | Tên khác Wikipedia và nhãn/alias/P1813 Wikidata |
| job_titles.csv | ESCO occupations ISCO 25/35, preferred + alternative labels |

Các bảng trường dẫn xuất từ Wikipedia được chia sẻ theo CC BY-SA 4.0;
xem attribution và liên kết giấy phép đầy đủ trong `SOURCES.md`.

Mỗi dòng trên có `source` khác rỗng, tiền tố tương ứng `prefix` trong manifest.
`source_id` của skill chứa Q-id hoặc ESCO URI nếu có. Các alias có cùng khóa nhưng
khác chủ sở hữu bị bỏ toàn bộ; thống kê trả về khi build. ID được cấp ổn định theo
thứ tự tên, không phải định danh vĩnh viễn qua các lần cập nhật nguồn.

`section_headings.csv` là cấu hình, giữ nguyên và không được builder ghi đè.
`university_alias_blocklist.csv` giữ nguyên như luật chặn alias mơ hồ (không phải
tri thức). Hai file này là ngoại lệ không cần cột source.

Schema PostgreSQL: loader áp dụng `001_schema.sql` rồi migration cộng thêm
`002_source.sql` trong cùng transaction trước khi nạp. CSV/DB readers chọn cột
theo tên nên các cột provenance không thay đổi hành vi liên kết hiện có.
Không có `KB_TEST_DSN` thì test tích hợp PostgreSQL được bỏ qua.

Trường đại học là tập mở: trường không có trong KB vẫn hợp lệ và không bị đổi tên.
Alias trường trùng/mơ hồ bị bỏ; blocklist ngăn gắn sai tên tiếng Anh đã biết.

# T01 · Xuất bản chụp KB và nạp vào Postgres

**Đọc trước:** [[00 Tổng quan kế hoạch]] · Thiết kế `02` (toàn bộ, đặc biệt mục 4, 7, 8, 10) · `03` mục "Knowledge Base được dùng ở đâu" · `tools/build_kb/docs/trang-thai-kb.md`, `tools/build_kb/README.md`.

**Phạm vi thư mục:** phần xuất làm trong `tools/build_kb/` (env `module2`, thư viện mới ghi vào `build_kb/requirements.txt`). Phần nạp làm trong `services/cvmatch-ai/src/cvmatch/core/kb/`. **Không** đọc `ai/matchCV/`.

## Mục tiêu

Có một **bản chụp KB phẳng, có phiên bản** mà tiền xử lý và rerank đọc được, không gọi Neo4j lúc chạy.

## Làm

### Phần 1 — trong `build_kb` (xuất)

1. **Cấp `skill_id`** (`S0001`, …) cho mọi `Skill`, ổn định qua các lần chạy (đã có thì giữ; mới thì cấp tiếp số lớn nhất). Ghi vào Neo4j và vào file ánh xạ `key → skill_id`.
2. **Kiểm tra trước khi xuất** (thiết kế 02 mục 10): alias trùng giữa hai kỹ năng, vòng `PARENT_OF`, chức danh không có `MAPS_TO`… Lỗi chặn (alias trùng) → dừng, in danh sách.
3. **Xuất** thư mục `build_kb/out/snapshot/<ontology_version>/` gồm 5 file JSONL + `manifest.json` (version, ngày, số dòng, sha256 từng file, nguồn đổi):
   - `skill_ontology.jsonl`: `skill_id, name, aliases[], type, parents[], categories_sibling_ok[]` — alias đã chuẩn hoá (NFC, chữ thường, gộp khoảng trắng; **phải cùng quy tắc với `core/text/normalize`** của T02 — chép quy tắc, ghi chú ở cả hai nơi).
   - `role_title_map.jsonl`: hai loại dòng `title_alias → role_group` và `level_alias → level_rank`.
   - `role_distance.jsonl`: `group_a, group_b, m, method`. Vì `computed` hiện quá thấp (trạng thái KB), xuất thêm bảng `hypothesis` từ thiết kế 07 mục 5.6.
   - `major_group.jsonl`: `major_alias, group`.
   - `ambiguous_aliases.jsonl`: `alias, candidates[]` (khởi đầu: go, c, r, spring… + các alias ngắn ≤ 2 ký tự).
4. **Đã chốt (Q-3): tạm thời xuất hết cả `candidate`.** Cài cờ `--include-candidate` và dùng nó làm mặc định của lệnh hiện tại; khi đó `ontology_version` có hậu tố `-dev` và mỗi dòng `skill_ontology` mang cột `status`. Khi KB đã duyệt thì đổi mặc định về chỉ `accepted`.

### Phần 2 — trong `cvmatch` (nạp)

5. Lệnh `cvmatch kb import <thư mục snapshot>`: kiểm `manifest` (sha256), nạp 5 bảng trong một giao dịch, từ chối nếu version đã tồn tại (trừ `--replace` với bản `-dev`).
6. `core/kb/snapshot.py`: `load_snapshot(version) -> KBSnapshot` (đọc từ Postgres hoặc từ thư mục file, cho test) — chứa dict alias → skill_id, cha, nhóm sibling_ok, bảng chức danh, cấp bậc, ngành, ma trận M.
7. `core/kb/rel.py`: `rel(a, b)` đúng bảng thiết kế 02 mục 7 (1,0 / 0,7 / 0,4 / 0, đọc hệ số từ config), và `M(g, g')` đối xứng, cùng nhóm = 1.

## Không làm

Duyệt `candidate`, gộp KB1+KB2 thêm, `df_jd`/`share_jd`. Ghi các thiếu sót KB phát hiện được vào ghi chú.

## Tiêu chí xong

- Chạy xuất trên Neo4j hiện tại ra được snapshot `-dev`, manifest hợp lệ.
- `cvmatch kb import` nạp thành công; chạy lại cùng version bị từ chối.
- Test `rel`: Spring Boot–Java 0,7; MySQL–PostgreSQL 0,4 (nếu nhóm sibling_ok); Python–Java 0.
- Báo cáo ngắn: số skill, số alias, số alias dễ nhầm, số chức danh có nhóm, số `PARENT_OF`.

## Ghi chú bàn giao

**Trạng thái: xong (16/11/2026).** Bản chụp đầu tiên: **`kb-2026-11-16-dev`** (cả candidate, theo Q-3), đã nạp vào Postgres và đặt trong `cvmatch/config/active.yaml`.

- **Xuất** (`build_kb/export_snapshot.py`, env `module2`; 4 test mới ở `build_kb/tests/test_export_snapshot.py`, 32 test build_kb qua):
  - `python export_snapshot.py [--accepted-only] [--dry-run] [--version …]` → `build_kb/out/snapshot/<version>/` (5 JSONL + `manifest.json` có sha256, thống kê, cảnh báo).
  - `skill_id` ổn định lưu ở **`build_kb/out/skill_ids.csv`** (không lưu trong Neo4j vì `load_kb.py` xoá và tạo lại `Skill` mỗi lần nạp). Mã đã dùng không cấp lại.
  - Chặn xuất khi: alias trùng giữa hai kỹ năng (tính cả tên), vòng `PARENT_OF`. Cảnh báo: chức danh không có nhóm, chức danh nhiều nhóm, kỹ năng không có bằng chứng.
  - Alias dễ nhầm = `ambiguous_aliases` của KB + **mọi alias ≤ 2 ký tự không có ký tự đặc biệt** (`if`, `ip`, `js`, `s3`, `vm`, `xp`…, tổng 32). Alias dễ nhầm chỉ thuộc một kỹ năng vẫn nằm trong `aliases` để khớp được khi là nguyên phần tử mảng `skills`.
  - `sibling_ok`: chưa ai duyệt nên bản dev dùng `sibling_ok_suggest` (chỉ 3 nhóm: ai models, ml algorithms, vector dbs → 21 kỹ năng).
  - `role_distance`: xuất cả `hypothesis` (bảng 07 mục 5.6) và `computed` (Jaccard, giá trị rất thấp, không dùng làm M).
  - Chức danh nhiều nhóm → chọn nhóm đầu theo thứ tự `ROLE_GROUPS`: DataOps/MLOps → Data, Data Scientist → Data, DevSecOps → DevOps.
- **Nạp** (`cvmatch/core/kb/store.py`, `rel.py`): `python -m cvmatch.cli kb import <thư mục> [--replace]`, `kb list`; `load_snapshot_db(conn, version)`; `SkillRelations.rel/relation`, `RoleDistance`. Lệnh `ingest cv|jd` không có `--kb-dir` thì đọc KB từ Postgres theo `active.yaml`.
- **Số liệu `kb-2026-11-16-dev`:** 1.470 kỹ năng (591 technology), 1.974 alias, 32 alias dễ nhầm, **chỉ 15 `PARENT_OF`**, 146 alias chức danh (9 nhóm, có AI/ML), 25 alias cấp bậc, 176 alias ngành; 54/96 chức danh chưa có nhóm. `SkillMatcher` trên KB thật: dựng 0,1 s, ~28 µs/câu.
- **Thiếu sót KB phát hiện (cho người làm KB):**
  - **Không có "Spring Boot"** (và có thể nhiều framework phổ biến khác) → CV/JD Java backend mất kỹ năng quan trọng.
  - `PARENT_OF` quá ít (không có Java → Spring, JavaScript → React…) → feature A1/A2 qua `rel` (T15) gần như không có tác dụng.
  - Tên chuẩn viết thường lẫn lộn ("java", "javascript", "jenkins") → bước đổi alias trước BERTScore sẽ đổi "Java" thành "java"; nên sửa `name` trong KB.
  - Q-2: KB có 9 nhóm vai trò (thêm AI/ML), thiết kế ghi 8 — ma trận M giả thuyết chưa có cặp nào với AI/ML.

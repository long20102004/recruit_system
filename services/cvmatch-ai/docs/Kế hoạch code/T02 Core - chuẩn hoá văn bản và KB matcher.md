# T02 · Core: chuẩn hoá văn bản, tách từ, nhận diện kỹ năng

**Đọc trước:** [[00 Tổng quan kế hoạch]] · Thiết kế `03` mục "Thuật ngữ" · `04` A4, A5, A6 (phần tra bảng), A9 · `05` B2, B4 · `02` mục 4 (quy tắc alias) · `01` mục 2.

## Mục tiêu

Viết **một bản duy nhất** các hàm xử lý chữ mà cả CV lẫn JD dùng. Toàn bộ là hàm thuần, không DB, không GPU.

## Làm

### `core/text/`

1. `normalize.py`
   - `to_raw(s) -> str`: bước 1 + 3 của A4 (NFC, bỏ ký tự trang trí •●★…, gộp khoảng trắng/xuống dòng). **Giữ dấu và hoa/thường.** Đây là nguồn của `text_raw`.
   - `normalize(s) -> str`: bước 1–4 (thêm chữ thường), **không** phá token được bảo vệ (`c#`, `c++`, `.net`, `node.js`, `ci/cd`…). Danh sách token bảo vệ lấy từ alias KB có ký tự đặc biệt + danh sách cứng trong config.
   - `normalize_location(s) -> str | None` theo `config/patterns/locations.yaml`.
   - `parse_ym(s) -> str | None`: đưa "03/2022", "tháng 3/2022", "2022", "Mar 2022"… về `YYYY-MM` (năm đơn → quy ước ghi trong docstring, vd `YYYY-01` cho start, `YYYY-12` cho end). Không đọc được → `None` (caller gắn cờ `date_unparsed`).
2. `diacritics.py`: `diacritic_ratio(texts) -> float` (tỉ lệ âm tiết có dấu tiếng Việt), `is_vietnamese(texts)`, `no_diacritics(texts, threshold)` theo `no_diacritics.threshold` = 5%.
3. `segment.py`: interface `Segmenter` + bản `PyViSegmenter` (Q-4). Phải giữ nguyên token bảo vệ (thay bằng placeholder trước khi tách, trả lại sau).
4. `bm25_tokens.py`: `tokens_acc(text)`, `tokens_noacc(tokens)` (bỏ dấu: `lập_trình_viên` → `lap_trinh_vien`, `đ` → `d`), `skill_tokens(skill_ids)` → `skill_s0002`. Đúng thứ tự A9.
5. `patterns.py`: đọc các file mẫu, hàm `has_negation(text)`, `is_coursework(text)`, `is_generic_resp(text)`, `suspected_injection(text)`.

### `core/kb/`

6. `matcher.py` — `SkillMatcher(snapshot)`:
   - `find(text_norm) -> list[Match(skill_id, start, end, alias)]` trên văn bản **đã normalize**.
   - Cụm dài khớp trước; khớp theo ranh giới từ ("java" không khớp trong "javascript"; xử lý đúng ranh giới với `c++`, `.net`).
   - Alias trong `ambiguous_aliases` **không** khớp trong văn bản tự do.
   - `match_list_item(item_norm)`: dùng cho phần tử của mảng `skills`/`technologies` — cho phép alias dễ nhầm khi nó là **nguyên một phần tử** (đề xuất A5).
   - Kỹ năng `type = concept` không khớp bằng alias từ đơn ngắn (vd "api").
   - `canonical_name(skill_id)` (dùng cho bước đổi alias của BERTScore ở T10).
   - Cài đặt: Aho-Corasick hoặc regex gộp theo độ dài; cần đủ nhanh cho 100.000 CV (ghi tốc độ đo được).
7. `lookup.py`:
   - `split_title(title_norm) -> (level_rank | None, base_title)`: tách từ cấp bậc ("senior", "sr", "chuyên viên cao cấp"…).
   - `role_group_of(base_title) -> str | None` qua `role_title_map`.
   - `major_group_of(major_norm) -> 'it'|'related'|'other'|None`.

### Fixtures

8. `tests/fixtures/kb_mini/`: snapshot nhỏ tự soạn cùng định dạng T01 (≈30 kỹ năng: Java, Spring Boot, PostgreSQL, MySQL, Kafka, Docker, Kubernetes(k8s), Microservices, REST API, React, React Native, JavaScript, Go(golang), C, C++, C#, .NET, Node.js, CI/CD, Python, Django…; vài chức danh, cấp bậc, ngành). Mọi test của T02–T13 dùng KB này, **không chờ** KB thật.

## Không làm

Logic của từng bước A/B (gán `ev`, metadata…) — đó là T04, T06.

## Tiêu chí xong

Test đơn vị tối thiểu:

- NFC: hai cách gõ "á" → cùng chuỗi. `to_raw` giữ "Xây dựng API"; `normalize` → "xây dựng api"; "C#" / "Node.js" còn nguyên.
- "TP.HCM", "Sài Gòn", "Ho Chi Minh City" → `ho_chi_minh`.
- `SkillMatcher`: "spring boot" khớp Spring Boot chứ không khớp Spring; "javascript" không ra Java; "go" trong câu không khớp; phần tử `"Go"` trong mảng khớp; "K8s" → Kubernetes; "api" đơn lẻ không ra REST API.
- `split_title("senior java developer")` → (4, "java developer") → Backend.
- Tách từ giữ nguyên `c++`, `node.js`; bản không dấu đúng.

## Ghi chú bàn giao

**Trạng thái: xong (15/11/2026).** 43 test đơn vị mới (`tests/unit/test_text.py`, `test_kb_matcher.py`), toàn bộ 57 test qua.

- **API chính:**
  - `core/text/normalize.py`: `to_raw`, `normalize`, `strip_diacritics`, `LocationNormalizer` / `normalize_location`, `parse_ym(s, role="start"|"end")`, `is_present`, `is_year_only`.
  - `core/text/diacritics.py`: `diacritic_ratio`, `is_vietnamese`, `no_diacritics(texts, threshold)` (cần ≥ 20 âm tiết; CV tiếng Anh không bị gắn cờ).
  - `core/text/segment.py`: `Segmenter` protocol, `PyViSegmenter`, `WhitespaceSegmenter`, `make_segmenter`. Token bảo vệ được thay bằng placeholder chỉ gồm chữ cái (`zzptok…zz`) rồi trả lại; pyvi giữ nguyên.
  - `core/text/bm25_tokens.py`: `tokens_acc`, `tokens_noacc`, `skill_tokens`, `bm25_fields` (bỏ token chỉ là dấu câu).
  - `core/text/patterns.py`: `Patterns.from_config(cfg)` → `has_negation`, `is_coursework`, `is_generic_resp`, `suspected_injection`.
  - `core/kb/snapshot.py`: `KBSnapshot.from_dir` / `from_rows` (định dạng thư mục snapshot ghi trong docstring — **T01 xuất đúng định dạng này**). Alias được `normalize` lại khi nạp; alias trùng giữa hai kỹ năng → `ValueError`.
  - `core/kb/matcher.py`: `SkillMatcher.find`, `find_ids`, `match_list_item`, `canonical_name`, `protected_tokens`.
  - `core/kb/lookup.py`: `TitleLookup.split_title`, `role_group_of`, `parse_title`, `major_group_of` (khớp cả dạng không dấu).
- **Quyết định đã đưa vào code:**
  - `normalize` không xoá dấu câu nào nên token bảo vệ tự nhiên giữ nguyên; bảo vệ thực sự cần ở bước tách từ (pyvi tách `c++` → `c + +`).
  - Mọi alias 1 ký tự tự động coi là dễ nhầm (ngoài danh sách `ambiguous_aliases`).
  - Concept chỉ khớp văn bản tự do khi alias ≥ 2 từ hoặc ≥ 5 ký tự (`concept_min_len`): "api", "rest" không khớp, "restful", "microservices" khớp.
  - `split_title` gặp nhiều từ cấp bậc → lấy cấp cao nhất. Năm đơn lẻ: `start` → `YYYY-01`, `end` → `YYYY-12`.
- **Tốc độ:** `SkillMatcher.find` ≈ 13 µs/câu với KB mini (regex dạng trie). **Chưa đo với KB thật (~1.470 skill)** — đo lại khi có snapshot T01.
- **Còn lưu ý:** danh sách mẫu so khớp cả dạng không dấu nên CV gõ không dấu có thể bị khớp nhầm (vd "khoa hoc" ↔ "khoá học"); ít gặp, theo dõi khi có dữ liệu thật. Fixture KB dùng 8 nhóm vai trò (chưa có AI/ML, chờ Q-2).

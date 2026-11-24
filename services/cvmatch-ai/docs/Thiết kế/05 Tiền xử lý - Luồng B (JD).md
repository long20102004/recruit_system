# 05 · Tiền xử lý — Luồng B: đưa JD vào hệ thống

> Thuộc Tầng 0. Bảng, thuật ngữ và cách ghi xuống database: [[03 Tiền xử lý - Lưu trữ và dữ liệu]]. Luồng CV: [[04 Tiền xử lý - Luồng A (CV)]].

Mỗi JD JSON đi qua **8 bước**, chạy khi JD được tạo hoặc sửa. JD không cần ẩn danh hoá, nhưng có thêm bước **chọn phần nào dùng để match**, vì JD thường chứa nhiều nội dung không liên quan đến yêu cầu công việc.

**Dữ liệu đi qua các bước** theo cách giống Luồng A: một đối tượng `jd_record` trong bộ nhớ được B1–B7 thêm dần trường, và B8 ghi tất cả xuống PostgreSQL trong một giao dịch. Mỗi phiên bản JD được xác định bằng cặp `(jd_id, version)`; mọi bảng con của JD đều mang cặp này.

**JD JSON giả định** (đầu ra Module 1, rút gọn):

```json
{
  "title": "Senior Backend Developer (Java)",
  "company_intro": "Công ty fintech hàng đầu, môi trường năng động...",
  "location": "Hồ Chí Minh", "work_mode": "hybrid",
  "min_years": 4,
  "skills": [
    {"name": "Java", "required": true, "importance": "core"},
    {"name": "Spring Boot", "required": true, "importance": "core"},
    {"name": "PostgreSQL", "required": true, "importance": "medium"},
    {"name": "Kafka", "required": false, "importance": "minor"}
  ],
  "requirements": ["Tối thiểu 4 năm kinh nghiệm backend", "Hiểu biết về microservices"],
  "responsibilities": [
    "Thiết kế và phát triển API cho hệ thống thanh toán",
    "Tối ưu hiệu năng truy vấn cơ sở dữ liệu",
    "Tham gia các buổi họp của team"
  ],
  "benefits": ["Lương tháng 13", "Bảo hiểm sức khoẻ"],
  "status": "open"
}
```

## B1. Nhận JSON và kiểm tra schema

Giống A1. Trường tối thiểu phải có: `title` và ít nhất một trong `skills`, `requirements`, `responsibilities`. Thiếu cả ba thì JD không đủ thông tin để match → `status = invalid`, báo HR bổ sung.

**Kết quả và nơi lưu**

- Thêm vào `jd_record`: `jd_id` (lấy từ Module 1), `version` (JD mới = 1; JD đã có = phiên bản lớn nhất + 1), `raw_json`.
- Ghi ở B8 vào bảng `jd`: `jd_id` (text), `version` (int), `raw_json` (JSONB). Khoá chính `(jd_id, version)`.
- JD sai schema: ghi ngay `ingest_log` (`status = 'invalid'`, danh sách lỗi) rồi dừng.

## B2. Chuẩn hoá

Dùng **đúng hàm chuẩn hoá của A4** (cùng code, cùng `pipeline_version`): NFC, chữ thường, bảo vệ token công nghệ, chuẩn hoá địa điểm ("Hồ Chí Minh" → `ho_chi_minh`). Nếu CV và JD chuẩn hoá khác nhau, cùng một từ sẽ không khớp.

**Kết quả và nơi lưu**

- Thêm vào `jd_record`: `norm_json`, bản JSON đã chuẩn hoá.
- Ghi ở B8 vào `jd.norm_json` (JSONB); `jd.raw_json` vẫn là bản gốc.

```json
{ "title": "senior backend developer (java)", "location": "ho_chi_minh", "work_mode": "hybrid", … }
```

## B3. Chọn phần dùng để match

Không phải trường nào của JD cũng nói về công việc:

| Dùng để match | Không dùng để match (vẫn lưu) |
| --- | --- |
| `title`, `skills`, `requirements`, `responsibilities` | `company_intro`, `benefits`, cách ứng tuyển, thông tin liên hệ |

**Vì sao?** Các cụm như "môi trường năng động", "lương tháng 13" khớp ngẫu nhiên với nhiều CV, làm nhiễu cả BM25 lẫn vector. Các phần được chọn được ghép thành **văn bản truy vấn** theo mẫu cố định, giống A8:

```text
Chức danh: senior backend developer (java)
Kỹ năng: java, spring boot, postgresql, kafka
Yêu cầu: tối thiểu 4 năm kinh nghiệm backend. hiểu biết về microservices
Trách nhiệm: thiết kế và phát triển api cho hệ thống thanh toán. tối ưu hiệu năng truy vấn cơ sở dữ liệu. tham gia các buổi họp của team
```

**Kết quả và nơi lưu**

- Thêm vào `jd_record`: `query_text`, chính là đoạn văn ví dụ ở trên.
- Ghi ở B8 vào `jd.query_text` (text). Các trường bị loại (`company_intro`, `benefits`) không mất: chúng vẫn nằm trong `raw_json`.

## B4. Gắn mã kỹ năng

- Mỗi phần tử trong `skills` → tra alias trong `skill_ontology` → `skill_id`, theo cùng quy tắc khớp ở A5.
- Dò thêm `requirements` để bắt kỹ năng Module 1 bỏ sót ("hiểu biết về microservices" → Microservices). Kỹ năng tìm thêm theo cách này được coi là **ưu tiên**, không phải bắt buộc, vì không chắc chắn.
- Giữ cờ `required` (bắt buộc / ưu tiên) từ Module 1.
- Nhóm **"A hoặc B"** ("Java hoặc Kotlin", "MySQL/PostgreSQL"): các kỹ năng cùng nhóm nhận chung một `group_id`. Rerank (feature A1) tính cả nhóm như **một** yêu cầu, lấy lựa chọn tốt nhất.
- Đổi `importance` sang trọng số **`w_imp`**: `core` = 1,0; `medium` = 0,7; `minor` = 0,4 (ƯL). Module 1 không có `importance` thì đặt mọi `w_imp` = 1,0.
- Kỹ năng không khớp alias nào → ghi vào `unknown_skill`. Chữ gốc vẫn nằm trong văn bản truy vấn, nên BM25 và vector vẫn bắt được.

Với JD mẫu, kết quả:

| Kỹ năng | `skill_id` | `required` | `w_imp` |
| --- | --- | --- | --- |
| Java | S0001 | có | 1,0 |
| Spring Boot | S0002 | có | 1,0 |
| PostgreSQL | S0015 | có | 0,7 |
| Kafka | S0040 | không | 0,4 |
| Microservices | S0102 | không (tìm thêm từ `requirements`) | 0,4 |

**Kết quả và nơi lưu**

Thêm vào `jd_record` danh sách `skills_found`. Ở B8, danh sách này được ghi vào bảng `jd_skill`, **mỗi kỹ năng một dòng**, khoá chính `(jd_id, version, skill_id)`. Mỗi dòng của bảng ngay trên là một dòng của `jd_skill`.

| Cột | Kiểu | Ý nghĩa |
| --- | --- | --- |
| `jd_id`, `version` | text, int | JD nào |
| `skill_id` | text | mã kỹ năng trong KB |
| `required` | bool | bắt buộc hay ưu tiên |
| `w_imp` | real | mức quan trọng |
| `group_id` | int, có thể NULL | các kỹ năng "A hoặc B" chung một `group_id` |
| `source` | text (`module1` / `requirements`) | kỹ năng do Module 1 đưa hay do B4 tìm thêm |
| `raw_text` | text | chữ gốc trong JD, để đối chiếu |

Kỹ năng không gắn được mã được ghi vào `unknown_skill`, như ở A5. Sau khi ghi, trọng số `w_imp` của các kỹ năng bắt buộc tạo thành **vector kỹ năng của JD**, để tầng Retrieve nhân với ma trận CV × kỹ năng.

## B5. Trích yêu cầu dạng metadata

Các trường này là **yêu cầu** của JD, đặt cùng tên với metadata của CV ở A6 để tầng Retrieve so được. Trường nào là lọc cứng thì **HR quyết định** lúc match, không phải bước này.

| Trường | Cách lấy | Với JD mẫu |
| --- | --- | --- |
| `location`, `work_mode` | từ JSON, chuẩn hoá ở B2 | `ho_chi_minh`, `hybrid` |
| `min_years` | từ JSON; không có thì tìm trong `requirements` ("tối thiểu 4 năm") | 4 |
| `max_years` | từ JSON hoặc `requirements` ("3–5 năm" → 5); thường không có | NULL |
| `level_rank` | từ cấp bậc trong `title` qua `role_title_map` | 4 (Senior) |
| `role_group` | `title` bỏ từ cấp bậc → `role_title_map` | Backend |
| `edu_required` | `none` / `it_related` / `any_degree` / NULL, từ `requirements` ("tốt nghiệp CNTT hoặc liên quan" → `it_related`) | NULL (JD không nêu) |

**Phân loại từng dòng yêu cầu.** Mỗi phần tử của `requirements` được gán một `kind`, để Rerank biết dòng nào chấm bằng luật, dòng nào chấm bằng BERTScore:

| `kind` | Nhận biết (quy tắc, ƯL) | Ai chấm | Ví dụ |
| --- | --- | --- | --- |
| `years` | có số + "năm"/"years" + "kinh nghiệm" | luật (feature B2) | "Tối thiểu 4 năm kinh nghiệm backend" |
| `degree` | "tốt nghiệp", "bằng", "đại học", "degree" | luật (feature C1) | "Tốt nghiệp ĐH chuyên ngành CNTT" |
| `language` | "tiếng Anh", "TOEIC", "IELTS", "English" | chỉ hiện cờ, không cộng điểm | "Đọc hiểu tài liệu tiếng Anh" |
| `skill_only` | sau khi bỏ kỹ năng đã gắn mã ở B4 chỉ còn từ nối ("Thành thạo Java, Spring") | feature A1, A2 (đã có trong `jd_skill`) | "Thành thạo Java và Spring Boot" |
| `text` | còn lại: yêu cầu chuyên môn diễn đạt bằng chữ | **BERTScore (feature B5)** | "Hiểu biết về microservices", "Có kinh nghiệm thiết kế hệ thống chịu tải cao" |

Một dòng có thể vừa nêu số năm vừa nêu chuyên môn ("4 năm kinh nghiệm backend"): gán `years`, vì phần "backend" đã được B1, B2 xét qua nhóm vai trò.

**Kết quả và nơi lưu**

Thêm vào `jd_record` đối tượng `meta` và danh sách `requirement_items`. Ở B8:

- `jd_meta`, mỗi phiên bản JD một dòng: `jd_id`, `version`, `location` (text), `work_mode` (text), `min_years`, `max_years` (numeric(4,1)), `level_rank` (smallint), `role_group` (text), `edu_required` (text). Giá trị của JD mẫu là cột cuối của bảng trên. Trường không tìm được ghi NULL.
- `jd_requirement_item`, mỗi dòng yêu cầu một dòng: `jd_id`, `version`, `idx`, `text`, `text_raw`, `kind`. Với JD mẫu: 0 · "Tối thiểu 4 năm kinh nghiệm backend" · `years`; 1 · "Hiểu biết về microservices" · `text`.

Các cột được đặt **cùng tên và cùng kiểu** với `cv_meta`, để tầng Retrieve so trực tiếp, ví dụ `cv_meta.years_experience >= jd_meta.min_years`.

## B6. Tách trách nhiệm

- Mỗi phần tử trong `responsibilities` là một trách nhiệm; bỏ phần tử dưới 4 từ (ƯL).
- Đánh dấu **trách nhiệm chung chung** (`is_generic = true`) theo một danh sách mẫu: "tham gia họp", "làm việc nhóm", "viết tài liệu", "báo cáo công việc"… Các dòng này khớp với gần như mọi CV nên làm loãng điểm. Retrieve và Rerank quyết định bỏ qua hay giảm trọng số (mặc định: bỏ qua). Với JD mẫu, "Tham gia các buổi họp của team" bị đánh dấu.
- Gắn ngữ cảnh giống A7: `chức danh + ": " + trách nhiệm` khi tạo vector.
- Lưu `text_raw` (giữ dấu và hoa/thường) cho BERTScore ở Rerank, như A7.

**Kết quả và nơi lưu**

Thêm vào `jd_record` danh sách `responsibilities`. Ở B8, danh sách này được ghi vào bảng `jd_responsibility`, **mỗi trách nhiệm một dòng**: `jd_id`, `version`, `idx` (int), `text`, `text_raw`, `context_text`, `is_generic` (bool), `dense` (`halfvec(1024)`, điền ở B7).

| `idx` | `text` | `is_generic` |
| --- | --- | --- |
| 0 | thiết kế và phát triển api cho hệ thống thanh toán | false |
| 1 | tối ưu hiệu năng truy vấn cơ sở dữ liệu | false |
| 2 | tham gia các buổi họp của team | true |

## B7. Tạo token BM25 và embedding

- **Token truy vấn BM25**: xử lý văn bản truy vấn ở B3 giống A9 (bảo vệ token, tách từ, bản không dấu), cộng skill token của các kỹ năng ở B4.
- **Vector JD**: BGE-M3 dense (và sparse) của văn bản truy vấn.
- **Vector trách nhiệm**: dense, mỗi trách nhiệm một vector.
- Kết quả được **lưu đệm (cache)** theo bộ khoá `(jd_id, version, pipeline_version, ontology_version, embed_model)`. Lúc match chỉ đọc lại, không tính lại.

**Kết quả và nơi lưu**

- Bảng `jd_vector`, mỗi phiên bản JD một dòng: `jd_id`, `version`, `dense` (`halfvec(1024)`), `sparse` (JSONB), `bm25_query_tokens` (text\[\]), `embed_model` (text).
- Cột `dense` của từng dòng trong `jd_responsibility`.

```text
jd_vector cho JD mẫu:
  dense             = [0.0187, -0.0122, 0.0398, …]       (đủ 1.024 số)
  bm25_query_tokens = ["senior", "backend", "developer", "java", "spring", "boot", "postgresql",
                       "kafka", "microservices", "thiet_ke", "phat_trien", "api", "thanh_toan", …,
                       "skill_s0001", "skill_s0002", "skill_s0015", "skill_s0040", "skill_s0102"]
  embed_model       = "bge-m3@5617a9f61b"
```

Khác với CV, JD lưu sẵn **token truy vấn** chứ không vào chỉ mục BM25, vì JD là bên đi hỏi (truy vấn), còn CV là bên được tìm.

## B8. Kiểm tra và kích hoạt

Cảnh báo cho HR (không chặn) khi:

- JD không có kỹ năng bắt buộc nào → view kỹ năng của tầng Retrieve sẽ không dùng được;
- JD không có trách nhiệm nào (hoặc toàn bộ là chung chung) → view trách nhiệm sẽ không dùng được;
- văn bản truy vấn dưới \~50 từ → chất lượng match thấp;
- trên 30% kỹ năng không gắn được mã (ƯL) → KB có thể đang thiếu kỹ năng của mảng này.

Sau đó ghi mọi bảng của JD trong một giao dịch, giữ `status` từ JSON (`open` / `draft` / `closed`), ghi kèm `ontology_version`, `pipeline_version`, `embed_model`.

**Kết quả và nơi lưu**

Cảnh báo được ghi vào `jd.warnings` (JSONB, danh sách). Thứ tự ghi trong một giao dịch:

1. `jd`: thêm dòng mới; phiên bản cũ của cùng `jd_id` chuyển `is_latest = false`.
2. `jd_meta` và `jd_requirement_item` (B5), `jd_skill` (B4), `jd_responsibility` (B6, B7), `jd_vector` (B7).
3. `unknown_skill` (B4).
4. `ingest_log`: `status = 'ok'`.

Dòng `jd` cuối cùng của JD mẫu:

| Cột | Giá trị |
| --- | --- |
| `jd_id` / `version` / `is_latest` | JD-0412 / 1 / true |
| `status` | open |
| `raw_json`, `norm_json`, `query_text` | như ở B1, B2, B3 |
| `warnings` | `[]` (rỗng: JD có 3 kỹ năng bắt buộc và 2 trách nhiệm không chung chung) |
| `ontology_version` / `pipeline_version` / `embed_model` | kb-2026-11-06 / prep-1.0 / bge-m3@5617a9f61b |

Bộ khoá cache `(jd_id, version, pipeline_version, ontology_version, embed_model)` ở B7 chính là các cột của dòng này.

# 04 · Tiền xử lý — Luồng A: đưa CV vào hệ thống

> Thuộc Tầng 0. Bảng, thuật ngữ và cách ghi xuống database: [[03 Tiền xử lý - Lưu trữ và dữ liệu]]. Luồng JD: [[05 Tiền xử lý - Luồng B (JD)]]. Dữ liệu tạo ra ở đây được dùng ở [[06 Retrieve]] và [[07 Rerank - BERTScore với bge-m3]].

Mỗi CV JSON đi qua **11 bước**, chạy một lần khi CV vào kho hoặc khi CV được cập nhật. Có thể chạy từng CV hoặc theo lô (batch).

**Dữ liệu đi qua các bước như thế nào?** Khi bắt đầu xử lý một CV, hệ thống tạo một đối tượng `cv_record` trong bộ nhớ và cấp cho nó một `cv_id` (UUID). Từ A1 đến A10, mỗi bước **thêm trường vào `cv_record`** và chưa ghi gì xuống database. Đến A11, toàn bộ `cv_record` được ghi vào các bảng PostgreSQL trong **một giao dịch**, nên không bao giờ có CV bị ghi dở dang.

Ngoại lệ: CV bị dừng giữa chừng (sai schema ở A1, trùng ở A2) được ghi ngay một dòng vào `ingest_log` để biết lý do.

Cuối mỗi bước có mục **Kết quả và nơi lưu**, cho biết bước đó thêm gì vào `cv_record`, và ở A11 phần đó được ghi vào bảng nào, cột nào, kiểu dữ liệu gì.

**CV JSON giả định** (rút gọn; tên trường cần đối chiếu với schema thật):

```json
{
  "full_name": "Nguyễn Văn A",
  "email": "a.nguyen@example.com",
  "phone": "0901234567",
  "birth_year": 1998,
  "location": "TP.HCM",
  "summary": "Backend developer 4 năm kinh nghiệm Java",
  "skills": ["Java", "Spring Boot", "PostgreSQL", "Docker"],
  "experiences": [
    {
      "title": "Senior Java Developer",
      "company": "Công ty X",
      "start": "2022-03", "end": null, "is_current": true,
      "description": [
        "Xây dựng API thanh toán bằng Spring Boot",
        "Tối ưu truy vấn PostgreSQL, giảm 40% thời gian"
      ],
      "technologies": ["Java", "Spring Boot", "Kafka"]
    }
  ],
  "projects": [],
  "education": [{"school": "ĐH Bách Khoa", "major": "Kỹ thuật phần mềm", "end": "2020"}],
  "certificates": [], "languages": ["Tiếng Anh"]
}
```

## A1. Nhận JSON và kiểm tra schema

Hệ thống **validate** JSON theo schema trước khi làm gì khác.

- Thiếu trường bắt buộc hoặc sai kiểu (ví dụ `experiences` không phải danh sách) → `status = invalid`, đưa vào hàng đợi cho người xem, **không** nạp tiếp.
- Trường tuỳ chọn bị thiếu (ví dụ không có `projects`) → vẫn nạp, coi là danh sách rỗng.
- Ngày tháng sai định dạng (`"tháng 3/2022"`) → thử chuyển về `YYYY-MM`; không chuyển được thì đặt `null` và gắn cờ `date_unparsed`.
- CV quá nghèo thông tin (không có kinh nghiệm, dự án và kỹ năng nào) → vẫn nạp nhưng gắn cờ `low_content`.

**Kết quả và nơi lưu**

- Thêm vào `cv_record`: `cv_id`, `raw_json` (JSON gốc, ngày tháng đã sửa về `YYYY-MM`), `flags` (danh sách cờ).
- Ghi ở A11 vào bảng `cv`: `cv_id` (UUID), `raw_json` (JSONB), `flags` (text\[\]).
- CV sai schema: dừng tại đây, ghi ngay một dòng vào `ingest_log` (`status = 'invalid'`, danh sách lỗi), không tạo dòng nào trong `cv`.

```json
{ "cv_id": "7c1e2a90-…", "raw_json": { … }, "flags": [] }
```

## A2. Chống trùng

- Tính **hash** của **canonical JSON**. Trùng hash với một CV đã có → bỏ qua, chỉ ghi nhận "đã tồn tại".
- Tính **candidate\_key** = hash của email đã chuẩn hoá (chữ thường, bỏ khoảng trắng); không có email thì dùng số điện thoại đã chuẩn hoá (bỏ `+84`, dấu cách).
- Cùng `candidate_key` với một CV có sẵn → đây là **phiên bản mới** của người cũ, không phải người mới.
- Không có cả email lẫn số điện thoại → `candidate_key = null`, gắn cờ `no_identity`. Những CV này có nguy cơ bị trùng người, nên cần đối soát định kỳ.

**Vì sao cần?** Nếu một người có 3 bản CV trong kho, họ có thể chiếm 3 chỗ trong top-200 của tầng Retrieve.

**Kết quả và nơi lưu**

- Đọc bảng `cv` (cột `content_hash`, `candidate_key`) để kiểm tra trùng và tìm phiên bản trước. Hai cột này có index để tra nhanh.
- Thêm vào `cv_record`: `content_hash`, `candidate_key`, `version`, `is_latest = true`.
- Ghi ở A11 vào bảng `cv`: `content_hash` (text, SHA-256 dạng hex), `candidate_key` (text), `version` (int), `is_latest` (bool).
- Trùng hash: ghi `ingest_log` (`status = 'duplicate'`, kèm `cv_id` của bản đã có) rồi dừng.
- `candidate_key` nên băm có khoá bí mật (HMAC) thay vì băm thường, vì email băm thường có thể bị dò ngược bằng cách thử một danh sách email.

```json
{ "content_hash": "9f2c4a…e1", "candidate_key": "hmac:4b1e…77", "version": 2, "is_latest": true }
```

## A3. Ẩn danh hoá

Tạo một bản CV **đã bỏ thông tin cá nhân**, dùng cho mọi bước phía sau. Bản gốc vẫn lưu riêng, có phân quyền.

| Bỏ khỏi bản dùng để chấm | Giữ lại |
| --- | --- |
| họ tên, email, số điện thoại, địa chỉ chi tiết, link mạng xã hội | tỉnh/thành phố (để lọc địa điểm) |
| năm sinh, tuổi, giới tính, ảnh, tình trạng hôn nhân | ngành học, bằng cấp, năm tốt nghiệp |
| tên trường | chức danh, mô tả công việc, kỹ năng |

Vì CV đã là JSON, phần lớn việc này chỉ là **bỏ trường**. Riêng các ô văn bản tự do (`summary`, `description`) có thể lẫn tên người hoặc email, nên quét thêm bằng quy tắc (email, số điện thoại) và so với chính `full_name` của CV để xoá.

**Kết quả và nơi lưu**

- Thêm vào `cv_record`: `anon_json`, cùng cấu trúc với `raw_json` nhưng đã bỏ các trường ở bảng trên.
- Ghi ở A11 vào `cv.anon_json` (JSONB). Từ đây trở đi, mọi bước chỉ đọc `anon_json`, không đọc `raw_json`.

```json
{
  "location": "TP.HCM",
  "summary": "Backend developer 4 năm kinh nghiệm Java",
  "skills": ["Java", "Spring Boot", "PostgreSQL", "Docker"],
  "experiences": [{ "title": "Senior Java Developer", "company": "Công ty X", "start": "2022-03", … }],
  "education": [{ "major": "Kỹ thuật phần mềm", "end": "2020" }]
}
```

## A4. Chuẩn hoá

**Chuẩn hoá giá trị có cấu trúc:**

- Địa điểm → mã tỉnh/thành: "TP.HCM", "HCM", "Sài Gòn", "Ho Chi Minh City" → `ho_chi_minh`; "Remote", "làm từ xa" → `remote`.
- Ngày tháng → `YYYY-MM`; `is_current = true` thì `end` = tháng nạp CV.

**Chuẩn hoá văn bản** (áp cho mọi ô chữ), theo đúng thứ tự:

1. Đưa về **Unicode NFC**.
2. Chuyển chữ thường.
3. Bỏ ký tự trang trí (•, ●, ★), gộp khoảng trắng và xuống dòng thừa.
4. **Không** xoá `#`, `+`, `.`, `/` khi chúng nằm trong tên công nghệ. Danh sách **token được bảo vệ** lấy từ alias của KB (`c#`, `c++`, `.net`, `node.js`, `ci/cd`…).

Cùng một hàm chuẩn hoá phải được dùng cho CV, JD và alias trong KB. Khác hàm là khớp lệch.

**Bản gốc cho BERTScore.** Bước 2 (chữ thường) chỉ có ích cho khớp từ (A5, A9). BERTScore ở Rerank lại rất nhạy với dạng chữ (test F05, T11 ở [[10 Kết quả test BERTScore bge-m3]]), nên với các ô gạch đầu dòng, `summary` và mô tả dự án, hệ thống **giữ thêm một bản chỉ qua bước 1 và 3** (NFC, dọn ký tự trang trí, giữ dấu và hoa/thường). Bản này được lưu thành cột `text_raw` ở A7.

**Phát hiện CV gõ không dấu.** Tính tỉ lệ âm tiết tiếng Việt có dấu trên các ô chữ tự do. Nếu CV viết tiếng Việt mà tỉ lệ này dưới 5% (ƯL) → gắn cờ `no_diacritics`. Rerank sẽ không phạt điểm ngữ nghĩa của CV này mà coi là thiếu dữ liệu phía CV ([[07 Rerank - BERTScore với bge-m3]] mục 3). Phục hồi dấu tự động là phương án để sau, cần chọn công cụ và đo.

**Kết quả và nơi lưu**

- Sửa `anon_json` **tại chỗ**: địa điểm thành mã, ngày tháng dạng `YYYY-MM`, `end` của việc hiện tại = tháng nạp, chữ đã NFC và viết thường.
- Không tạo bảng mới. `cv.anon_json` ghi ở A11 là bản **đã chuẩn hoá**; `cv.raw_json` vẫn là bản gốc.

```json
{
  "location": "ho_chi_minh",
  "summary": "backend developer 4 năm kinh nghiệm java",
  "experiences": [{ "title": "senior java developer", "start": "2022-03", "end": "2026-11", … }]
}
```

## A5. Nhận diện kỹ năng và gắn mã

Dò từng ô chữ của CV theo từ điển alias trong `skill_ontology`. Bước này chạy trên văn bản đã chuẩn hoá ở A4, **trước** bước tách từ (A9), vì công cụ tách từ hay cắt sai tên công nghệ.

**Quy tắc khớp** (theo KB mục 4):

- **Cụm dài khớp trước**: "spring boot" trước "spring", "react native" trước "react".
- **Khớp theo ranh giới từ**: "java" không được khớp bên trong "javascript".
- **Alias dễ nhầm** ("go", "c", "r", "spring") không tự khớp trong văn bản tự do. Đề xuất: cho khớp khi alias đó là **nguyên một phần tử** trong mảng `skills` (ví dụ phần tử `"Go"`), vì ngữ cảnh đã rõ.
- Kỹ năng loại `concept` ("REST API", "Microservices") chỉ khớp bằng alias đủ dài, không khớp từ đơn như "api".

**Gán mức bằng chứng `ev`** theo nơi kỹ năng xuất hiện. Một kỹ năng xuất hiện ở nhiều nơi thì lấy **giá trị cao nhất**.

| Kỹ năng xuất hiện ở | `ev` |
| --- | --- |
| `description` của một kinh nghiệm hoặc dự án | 1,0 |
| `technologies` của một kinh nghiệm hoặc dự án, nhưng không có trong mô tả | 0,8 (ƯL) |
| chỉ trong `skills`, `summary` hoặc `certificates` | 0,6 (ƯL) |
| không xuất hiện | 0 |

Với CV mẫu: Spring Boot có trong mô tả → 1,0; Kafka chỉ có trong `technologies` → 0,8; Docker chỉ trong `skills` → 0,6.

Với mỗi kỹ năng, lưu thêm: `evidence_snippet` (câu chứa kỹ năng, để giải thích kết quả) và `last_used` (tháng kết thúc của kinh nghiệm gần nhất có kỹ năng đó). Nếu bằng chứng nằm trong một gạch đầu dòng thì lưu thêm `bullet_id` của gạch đó, để Explain dẫn đúng chỗ. Hiện chưa feature nào dùng `last_used`; nó dành cho feature A3 (độ mới kỹ năng) để sau.

Cụm trông giống tên công nghệ mà không có trong KB (phần tử của `skills` hoặc `technologies` không khớp alias nào) → ghi vào `unknown_skill`.

**Kết quả và nơi lưu**

Thêm vào `cv_record` danh sách `skills_found`. Ở A11, danh sách này được ghi vào bảng `cv_skill`, **mỗi kỹ năng một dòng**, khoá chính `(cv_id, skill_id)`:

| Cột | Kiểu | Ý nghĩa |
| --- | --- | --- |
| `cv_id` | UUID | CV nào |
| `skill_id` | text | mã kỹ năng trong KB |
| `ev` | real (0–1) | mức bằng chứng cao nhất |
| `source_field` | text | vị trí trong JSON nơi cho ra `ev` cao nhất |
| `evidence_snippet` | text | câu chứa kỹ năng, dùng để giải thích kết quả |
| `bullet_id` | bigint, có thể NULL | gạch chứa bằng chứng (NULL nếu bằng chứng ở `skills` hay `technologies`) |
| `last_used` | text `YYYY-MM`, có thể NULL | tháng cuối dùng kỹ năng trong một kinh nghiệm |

Với CV mẫu, bảng `cv_skill` có 5 dòng:

| `skill_id` | `ev` | `source_field` | `evidence_snippet` | `last_used` |
| --- | --- | --- | --- | --- |
| S0002 (Spring Boot) | 1,0 | `experiences[0].description[0]` | xây dựng api thanh toán bằng spring boot | 2026-11 |
| S0015 (PostgreSQL) | 1,0 | `experiences[0].description[1]` | tối ưu truy vấn postgresql, giảm 40% thời gian | 2026-11 |
| S0001 (Java) | 0,8 | `experiences[0].technologies` | java | 2026-11 |
| S0040 (Kafka) | 0,8 | `experiences[0].technologies` | kafka | 2026-11 |
| S0050 (Docker) | 0,6 | `skills[3]` | docker | NULL |

Java xuất hiện ở cả `summary` (0,6), `skills` (0,6) và `technologies` (0,8), nên lấy 0,8. Từ "api" đứng một mình không khớp kỹ năng REST API, theo quy tắc cho kỹ năng loại `concept`.

Ngoài ra:

- Cụm lạ được ghi vào `unknown_skill` trong cùng giao dịch: nếu cụm đã có thì tăng `count` thêm 1; chưa có thì thêm dòng mới (`text`, `count = 1`, `first_seen`, `example`).
- Sau khi ghi, các dòng `cv_skill` được thêm vào **ma trận CV × kỹ năng** trong bộ nhớ (hàng = CV, cột = kỹ năng, ô = `ev`).

## A6. Trích metadata

Các trường này dùng cho **lọc cứng** (khi HR bật) hoặc **tín hiệu mềm** ở tầng Retrieve. **Thiếu dữ liệu thì để `null`, không đoán.**

| Trường | Cách tính |
| --- | --- |
| `location` | từ A4 |
| `years_experience` | tính từ **mốc thời gian** các kinh nghiệm, không lấy con số người viết tự ghi trong `summary` |
| `intern_months` | số tháng thực tập, tính riêng, không cộng vào `years_experience` |
| `role_group` | chức danh gần nhất → tra `role_title_map` ("Senior Java Developer" → bỏ từ cấp bậc → "java developer" → Backend) |
| `level_rank` | từ cấp bậc trong chức danh gần nhất ("Senior" → 4). Không có thì suy từ `years_experience` và ghi `level_source = inferred` |
| `major_group` | ngành học → tra `major_group` ("Kỹ thuật phần mềm" → `it`) |

**Cách tính `years_experience`:** gộp các khoảng thời gian chồng lấn rồi cộng lại, để hai việc làm song song không bị tính hai lần. Ví dụ:

- Việc 1: 2019-01 đến 2020-06; việc 2: 2020-03 đến 2022-12.
- Cộng thẳng: 18 + 34 = 52 tháng (sai, vì 2020-03 đến 2020-06 bị tính hai lần).
- Gộp trước: 2019-01 đến 2022-12 = 48 tháng = **4,0 năm**.

Kinh nghiệm thiếu `start` → không tính vào tổng và gắn cờ `years_uncertain`.

**Kết quả và nơi lưu**

Thêm vào `cv_record` một đối tượng `meta`. Ở A11, nó được ghi vào bảng `cv_meta`, **mỗi CV một dòng**:

| Cột | Kiểu | CV mẫu |
| --- | --- | --- |
| `cv_id` | UUID | 7c1e2a90-… |
| `location` | text | `ho_chi_minh` |
| `years_experience` | numeric(4,1) | 4,7 (từ 2022-03 đến 2026-11 = 56 tháng) |
| `intern_months` | smallint | 0 |
| `role_group` | text | `Backend` |
| `level_rank` | smallint | 4 |
| `level_source` | text (`title` / `inferred`) | `title` |
| `major_group` | text (`it` / `related` / `other`) | `it` |

Để ý: CV tự ghi "4 năm kinh nghiệm" nhưng hệ thống tính được 4,7 năm từ mốc thời gian. Hệ thống dùng số tự tính. Trường nào không tính được thì ghi NULL; cờ `years_uncertain` (nếu có) ghi vào `cv.flags`.

**Từng mục kinh nghiệm và học vấn (cho Rerank).** `cv_meta` chỉ giữ con số tổng. Các feature B1, B2, B3, C1 của Rerank cần biết *từng mục* thuộc nhóm vai trò nào và kéo dài bao lâu, nên A6 ghi thêm hai bảng:

| Bảng | Cột | Cách tính |
| --- | --- | --- |
| `cv_experience` (mỗi mục một dòng) | `cv_id`, `idx`, `kind` (`job` / `intern` / `project_personal` / `project_team`), `title_raw`, `role_group`, `role_group_conf`, `role_group_src` (`rule` / `keyword`), `start_ym`, `end_ym`, `is_current`, `months`, `dates_quality` (`ok` / `partial` / `missing`) | `role_group` theo thứ tự: tra `role_title_map` theo chức danh → nếu không ra, đếm từ khoá theo nhóm trong các gạch của mục (nhận nhóm đầu nếu gấp ≥2 lần nhóm thứ hai, ƯL) → không ra thì NULL |
| `cv_education` (mỗi mục một dòng) | `cv_id`, `idx`, `level`, `major_raw`, `major_group`, `status` (`graduated` / `studying` / `unknown`), `end_year`, `expected_end_ym` | `status = studying` khi `end` ở tương lai hoặc ghi "đang học" |

Với CV mẫu: `cv_experience` có 1 dòng (`job`, `senior java developer`, Backend, `rule`, 2022-03 → 2026-11, 56 tháng, `ok`); `cv_education` có 1 dòng (`kỹ thuật phần mềm`, `it`, `graduated`, 2020). Tên trường học **không** được ghi vào đây.

## A7. Tách gạch đầu dòng

- Lấy từ `description` của mỗi kinh nghiệm và dự án. Nếu `description` là mảng, mỗi phần tử là một gạch. Nếu là một đoạn văn, tách theo xuống dòng, ký tự gạch đầu dòng hoặc dấu chấm câu.
- Bỏ gạch dưới 4 từ (ƯL) và gạch chỉ chứa ngày tháng.
- Gắn **ngữ cảnh** khi tạo vector: `chức danh + ": " + gạch` (với dự án: `tên dự án + ": " + gạch`). Ví dụ: "senior java developer: tối ưu truy vấn postgresql, giảm 40% thời gian". Không có ngữ cảnh, câu "tối ưu, giảm 40%" rất mơ hồ.
- Lưu vị trí gạch (thuộc kinh nghiệm nào, thứ mấy) để giải thích sau này.
- CV không có gạch nào → `n_bullets = 0`. Tầng Retrieve và Rerank phải coi đây là **thiếu dữ liệu**, không phải điểm 0.
- Lưu `text_raw` (bản gốc giữ dấu và hoa/thường, xem A4) cho mỗi gạch. Rerank chạy BERTScore trên `text_raw`, và Explain hiển thị đúng chuỗi này.
- **Gắn cờ phủ định và học tập** bằng danh sách mẫu (ƯL, cần duy trì như danh sách trách nhiệm chung chung ở B6), vì BERTScore không hiểu phủ định (test T05) và không phân biệt "học" với "làm" (T04):
  - `has_negation`: "chưa từng", "chưa có kinh nghiệm", "không có kinh nghiệm", "chưa làm", "never", "no experience", "not yet"…
  - `is_coursework`: "môn học", "bài tập", "bài tập lớn", "khoá học", "học qua", "course", "coursework", "tutorial"…
  - Cờ chỉ là tín hiệu; cách dùng (giảm trọng số gạch) do Rerank quyết định.

**Kết quả và nơi lưu**

Thêm vào `cv_record` danh sách `bullets`. Ở A11, danh sách này được ghi vào bảng `cv_bullet`, **mỗi gạch một dòng**:

| Cột | Kiểu | Ý nghĩa |
| --- | --- | --- |
| `bullet_id` | bigint, tự tăng | mã gạch |
| `cv_id` | UUID | CV nào |
| `section` | text (`experience` / `project`) | gạch thuộc phần nào |
| `item_idx` | int | kinh nghiệm hoặc dự án thứ mấy (0 = mới nhất) |
| `pos` | int | gạch thứ mấy trong mục đó |
| `text` | text | nội dung gạch, đã chuẩn hoá (chữ thường) |
| `text_raw` | text | bản gốc: NFC, giữ dấu và hoa/thường; đầu vào BERTScore và nội dung hiển thị ở Explain |
| `context_text` | text | gạch đã gắn ngữ cảnh, dùng để tạo vector ở A10 |
| `has_negation` | bool | gạch có mẫu phủ định |
| `is_coursework` | bool | gạch mô tả việc học, bài tập |

Với CV mẫu:

| `bullet_id` | `section` | `item_idx` | `pos` | `text_raw` | `context_text` | cờ |
| --- | --- | --- | --- | --- | --- | --- |
| 90001 | experience | 0 | 0 | Xây dựng API thanh toán bằng Spring Boot | senior java developer: xây dựng api thanh toán bằng spring boot | — |
| 90002 | experience | 0 | 1 | Tối ưu truy vấn PostgreSQL, giảm 40% thời gian | senior java developer: tối ưu truy vấn postgresql, giảm 40% thời gian | — |

Số gạch (`n_bullets`, int) được ghi thêm vào `cv_meta`. CV mẫu có `n_bullets = 2`.

## A8. Ghép văn bản tài liệu

BM25 và vector cần **một đoạn văn**, trong khi CV là JSON nhiều trường. Bước này ghép các trường đã ẩn danh theo **một mẫu cố định**:

```text
Chức danh: senior java developer
Tóm tắt: backend developer 4 năm kinh nghiệm java
Kinh nghiệm: senior java developer. xây dựng api thanh toán bằng spring boot. tối ưu truy vấn postgresql, giảm 40% thời gian. Công nghệ: java, spring boot, kafka
Dự án: (không có)
Kỹ năng: java, spring boot, postgresql, docker
Học vấn: kỹ thuật phần mềm
```

- Không đưa vào: thông tin cá nhân, tên trường, tên công ty, sở thích, người tham chiếu.
- Kinh nghiệm xếp từ **mới đến cũ**, vì phần đầu văn bản thường ảnh hưởng vector nhiều hơn.
- Mẫu ghép có phiên bản (nằm trong `pipeline_version`). Đổi mẫu là phải chạy lại A8–A10 cho toàn kho.

**Kết quả và nơi lưu**

- Thêm vào `cv_record`: `doc_text`, chính là đoạn văn ví dụ ở trên.
- Ghi ở A11 vào `cv.doc_text` (text).
- Vì sao lưu lại thay vì ghép lại mỗi lần cần: khi đổi model embedding chỉ cần chạy lại A10 trên `doc_text`; tầng Rerank có thể đọc trực tiếp; và người kiểm tra xem được máy "nhìn thấy" gì.

## A9. Tạo token BM25

Thứ tự xử lý văn bản tài liệu:

1. Đánh dấu các **token được bảo vệ** để không bị cắt.
2. **Tách từ tiếng Việt**: "lập trình viên" → `lập_trình_viên`.
3. Tạo bản **không dấu**: `lập_trình_viên` → `lap_trinh_vien`, để khớp cả CV gõ không dấu.
4. Thêm **skill token** cho mỗi kỹ năng ở A5: `skill_s0002`…

Lưu thành **ba trường riêng**, không trộn vào nhau, để mỗi từ không bị đếm hai lần:

| Trường | Nội dung | Vai trò |
| --- | --- | --- |
| `bm25_noacc` | token không dấu | mặc định dùng cho BM25 |
| `bm25_acc` | token có dấu | giữ lại để thí nghiệm |
| `skill_tokens` | các `skill_*` | tầng Retrieve quyết định có ghép vào BM25 hay không |

Chỉ mục BM25 được **dựng lại theo lô** (ví dụ mỗi đêm). CV mới nạp trong ngày được chấm bằng thống kê IDF của lần dựng gần nhất, nên vẫn tìm thấy được ngay.

**Kết quả và nơi lưu**

Thêm vào `cv_record` đối tượng `bm25`. Ở A11, nó được ghi vào bảng `cv_bm25_doc`, **mỗi CV một dòng**: `cv_id` (UUID), `bm25_noacc` (text\[\]), `bm25_acc` (text\[\]), `skill_tokens` (text\[\]).

```json
{
  "bm25_noacc": ["senior", "java", "developer", "backend", "xay_dung", "api", "thanh_toan", "spring", "boot", "toi_uu", "truy_van", "postgresql", …],
  "bm25_acc":   ["senior", "java", "developer", "backend", "xây_dựng", "api", "thanh_toán", "spring", "boot", "tối_ưu", "truy_vấn", "postgresql", …],
  "skill_tokens": ["skill_s0001", "skill_s0002", "skill_s0015", "skill_s0040", "skill_s0050"]
}
```

**Chỉ mục BM25 không nằm trong Postgres.** Nó được dựng trong bộ nhớ (ví dụ bằng thư viện `bm25s`) từ bảng `cv_bm25_doc`. Có thể lưu chỉ mục ra file trên đĩa để khởi động nhanh, kèm ngày dựng; file này luôn dựng lại được từ Postgres.

## A10. Tạo embedding

Chạy **BGE-M3** trên GPU, theo lô:

- **Vector tài liệu**: dense (1.024 số) và sparse, từ văn bản tài liệu **có dấu** ở A8 (model hiểu tiếng Việt có dấu tốt hơn).
- **Vector gạch đầu dòng**: dense, mỗi gạch một vector, từ văn bản đã gắn ngữ cảnh ở A7.
- Văn bản dài hơn giới hạn của model (\~8.000 token): tách theo mục, tạo vector từng phần rồi lấy trung bình. Hiếm gặp với CV.
- Lưu dạng float16 để tiết kiệm một nửa bộ nhớ. Với 100.000 CV × \~30 gạch = 3 triệu vector gạch ≈ **6 GB** (float16); vector tài liệu chỉ ≈ **200 MB**.
- Ghi `embed_model` kèm mỗi vector.

**Kết quả và nơi lưu**

Thêm vào `cv_record` đối tượng `vectors`. Ở A11, nó được ghi vào hai bảng:

| Bảng | Mỗi dòng | Cột và kiểu |
| --- | --- | --- |
| `cv_vector` | một CV | `cv_id` (UUID), `dense` (`halfvec(1024)` của pgvector, tức 1.024 số float16), `sparse` (JSONB, từ → trọng số), `embed_model` (text) |
| `cv_bullet_vector` | một gạch | `bullet_id` (bigint), `dense` (`halfvec(1024)`) |

```text
cv_vector cho CV mẫu:
  dense       = [0.0213, -0.0087, 0.0441, …]        (đủ 1.024 số)
  sparse      = {"spring": 0.21, "boot": 0.19, "postgresql": 0.17, "thanh_toán": 0.12, …}
  embed_model = "bge-m3@5617a9f61b"

cv_bullet_vector:
  bullet_id 90001 → dense = [0.0175, 0.0032, …]
  bullet_id 90002 → dense = [-0.0098, 0.0261, …]
```

Không tạo chỉ mục ANN (HNSW) trên các cột `dense`: tầng Retrieve quét toàn bộ trong bộ nhớ, nên Postgres chỉ làm nơi lưu.

## A11. Ghi và kích hoạt

- Ghi mọi bảng của CV trong **một giao dịch (transaction)**: hoặc ghi đủ tất cả, hoặc không ghi gì, để không có CV "nửa vời" (có kỹ năng mà thiếu vector).
- Đặt `status = active`, `is_latest = true`. Phiên bản cũ của cùng `candidate_key` chuyển `is_latest = false` (vẫn lưu, nhưng không được chấm).
- Ghi kèm `ontology_version`, `pipeline_version`, `embed_model`.
- Cập nhật các cấu trúc trong bộ nhớ của tầng Retrieve (ma trận vector, ma trận CV × kỹ năng).

**Kết quả và nơi lưu**

A11 là bước duy nhất ghi xuống database. Thứ tự ghi trong **một giao dịch**:

1. `cv`: thêm một dòng. Nếu có bản cũ cùng `candidate_key` thì cập nhật bản cũ thành `is_latest = false`.
2. `cv_meta` (từ A6, A7), `cv_experience` và `cv_education` (từ A6).
3. `cv_skill` (từ A5).
4. `cv_bullet` (từ A7), rồi `cv_bullet_vector` (từ A10). `cv_skill.bullet_id` được điền sau khi có `bullet_id`.
5. `cv_vector` (từ A10).
6. `cv_bm25_doc` (từ A9).
7. `unknown_skill` (từ A5).
8. `ingest_log`: một dòng `status = 'ok'`.

Bất kỳ lệnh nào lỗi → **hoàn tác (rollback)** toàn bộ, không bảng nào bị ghi, rồi thử lại. Chỉ sau khi giao dịch thành công (commit) mới cập nhật bộ nhớ: thêm hàng vào ma trận vector tài liệu, ma trận vector gạch (kèm `bullet_cv_index`) và ma trận CV × kỹ năng, đồng thời bỏ bản cũ khỏi danh sách được chấm.

Dòng `cv` cuối cùng của CV mẫu:

| Cột | Giá trị |
| --- | --- |
| `cv_id` | 7c1e2a90-… |
| `candidate_key` | hmac:4b1e…77 |
| `version` / `is_latest` | 2 / true |
| `status` | active |
| `content_hash` | 9f2c4a…e1 |
| `raw_json`, `anon_json`, `doc_text` | như ở A1, A4, A8 |
| `flags` | `{}` (rỗng) |
| `ontology_version` | kb-2026-11-06 |
| `pipeline_version` | prep-1.0 |
| `embed_model` | bge-m3@5617a9f61b |
| `created_at` | 2026-11-08 20:10 |

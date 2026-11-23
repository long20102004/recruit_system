# 03 · Tiền xử lý: lưu trữ, bảng dữ liệu và vận hành

> Tầng 0 của module (trước đây gọi là profile-indexer). Gồm 3 file: **03** (file này: lưu trữ, thuật ngữ, dữ liệu đầu ra, vận hành) · [[04 Tiền xử lý - Luồng A (CV)]] · [[05 Tiền xử lý - Luồng B (JD)]]. Quy ước tên: [[00 Tổng quan và quy ước]].

## File này nói về gì

Tài liệu này mô tả mọi việc hệ thống làm từ lúc nhận một **CV dạng JSON** hoặc một **JD dạng JSON** cho đến khi dữ liệu **sẵn sàng để tầng Retrieve và Rerank dùng**. Việc chấm điểm và xếp hạng CV nằm ở [[06 Retrieve]] và [[07 Rerank - BERTScore với bge-m3]].

**Đầu vào:**

- **CV dạng JSON**: đã được tách thành các trường (kinh nghiệm, dự án, kỹ năng, học vấn…). Việc đọc file PDF/DOCX và OCR đã xong ở bước trước, không thuộc phạm vi tài liệu này.
- **JD dạng JSON**: đầu ra của **Module 1** (chức danh, yêu cầu, kỹ năng, trách nhiệm, địa điểm…).
- **Bản chụp Knowledge Base (KB)**: từ điển kỹ năng, chức danh, cấp bậc và ngành học, xuất từ Neo4j.

**Đầu ra:** với mỗi CV và mỗi JD, một **hồ sơ đã xử lý** gồm:

- văn bản đã **chuẩn hoá** (với CV thì đã **ẩn danh hoá**);
- danh sách **kỹ năng đã gắn mã** `skill_id`, kèm mức bằng chứng `ev` (CV) hoặc mức quan trọng `w_imp` (JD);
- các **gạch đầu dòng** công việc (CV) hoặc **trách nhiệm** và **yêu cầu dạng chữ** (JD), giữ cả bản gốc `text_raw` (có dấu, giữ hoa/thường) để Rerank chạy BERTScore;
- từng **mục kinh nghiệm** và **mục học vấn** ở dạng có cấu trúc (cho các feature luật của Rerank);
- **vector** (embedding) và **token BM25**;
- các trường **metadata**: địa điểm, số năm kinh nghiệm, cấp bậc, nhóm vai trò, nhóm ngành học.

**Vì sao tách thành một bước riêng?** Nguyên tắc là *làm nặng lúc nạp, làm nhẹ lúc match*. Gọi model AI để tạo vector hay dò kỹ năng trên 100.000 CV là việc chậm, nên chỉ làm **một lần** khi dữ liệu vào. Khi HR bấm tìm, tầng Retrieve chỉ đọc lại kết quả và tính toán nhanh.

**Cách đọc:** người mới nên đọc mục *Thuật ngữ cần biết* trước. Thuật ngữ được giữ nguyên tiếng Anh vì đó là tên gọi chuẩn trong ngành. Con số có ký hiệu **(ƯL)** là giá trị đề xuất, chưa đo. Tên các trường JSON trong tài liệu là **giả định**; khi đối chiếu với schema thật, chỉ cần đổi tên, logic giữ nguyên.

## Lưu trữ: dùng gì, có những bảng nào

Toàn bộ dữ liệu đã xử lý được lưu trong **một cơ sở dữ liệu duy nhất là PostgreSQL**. Hệ thống **không dùng Qdrant, Elasticsearch hay vector database riêng**. Mục này giải thích lý do, liệt kê các bảng, và nói rõ `cv_record` mà các bước phía sau nhắc tới là gì.

### Dùng những thành phần nào

| Thành phần | Là gì | Lưu gì |
| --- | --- | --- |
| **PostgreSQL** | cơ sở dữ liệu quan hệ: dữ liệu nằm trong các **bảng**, mỗi bảng có hàng và cột, giống một sheet Excel | mọi thứ: JSON gốc, kỹ năng, metadata, vector, token |
| **pgvector** | tiện ích cài thêm vào PostgreSQL, cho phép một cột chứa **vector** (dãy 1.024 số) | các cột vector |
| **Bộ nhớ (RAM) của dịch vụ Retrieve** | chương trình Python chạy tầng Retrieve, khi khởi động sẽ đọc dữ liệu từ PostgreSQL lên RAM | ma trận vector, ma trận CV × kỹ năng, chỉ mục BM25 |

PostgreSQL là **nguồn sự thật**: nếu dịch vụ Retrieve tắt đi, mọi thứ trong RAM được dựng lại từ PostgreSQL.

**Vì sao không dùng Qdrant?** Qdrant (và các vector database khác) mạnh nhất ở việc tìm *gần đúng* rất nhanh trên hàng chục triệu vector. Hệ thống này không cần điều đó:

- 100.000 CV là quy mô nhỏ. Toàn bộ vector tài liệu chỉ khoảng 200 MB, nằm gọn trong RAM.
- Tầng Retrieve chấm **toàn bộ** CV bằng phép nhân ma trận, nên kết quả chính xác tuyệt đối thay vì gần đúng.
- Một hệ thống lưu trữ thì dễ giữ đồng bộ hơn hai. Ghi một CV chỉ cần một giao dịch, không sợ PostgreSQL có CV mà Qdrant chưa có.

Nếu sau này kho lên hàng triệu CV, có thể chuyển phần vector sang Qdrant mà không phải đổi các bước tiền xử lý.

### Cách đọc ký hiệu trong tài liệu

- **`cv.anon_json`** nghĩa là *cột `anon_json` của bảng `cv`*. Tương tự, `cv_meta.years_experience` là cột `years_experience` của bảng `cv_meta`.
- **"Mỗi CV một dòng"** nghĩa là bảng đó có đúng một hàng cho mỗi CV. **"Mỗi kỹ năng một dòng"** nghĩa là một CV có 5 kỹ năng thì chiếm 5 hàng.
- Các bảng nối với nhau qua **mã chung**: mọi bảng có tên bắt đầu bằng `cv_` đều có cột `cv_id`, nhờ đó biết hàng đó thuộc CV nào.

Các kiểu dữ liệu hay gặp:

| Kiểu | Nghĩa | Ví dụ |
| --- | --- | --- |
| `UUID` | mã định danh ngẫu nhiên, không trùng | `7c1e2a90-4f1b-…` |
| `text` | chuỗi chữ | `ho_chi_minh` |
| `int`, `smallint`, `bigint` | số nguyên (nhỏ/vừa/lớn) | `4` |
| `real`, `numeric(4,1)` | số thập phân | `0.8`, `4.7` |
| `bool` | đúng/sai | `true` |
| `JSONB` | một ô chứa cả một đối tượng JSON | cả CV JSON |
| `text[]` | một ô chứa danh sách chuỗi | `["java", "spring"]` |
| `halfvec(1024)` | kiểu của pgvector: một vector 1.024 số, mỗi số 2 byte | `[0.0213, -0.0087, …]` |

### Các bảng

Tiền xử lý ghi **17 bảng** chia làm 3 nhóm, cộng các bảng của bản chụp KB. Bảng của Retrieve (`match_run`, `match_result`) nằm ở [[06 Retrieve]]; bảng của Rerank (`rerank_run`, `rerank_result`, cache BERTScore) nằm ở [[07 Rerank - BERTScore với bge-m3]].

| Nhóm | Bảng | Giải thích ngắn | Số dòng | Bước ghi |
| --- | --- | --- | --- | --- |
| CV | `cv` | bảng chính: JSON gốc, JSON đã ẩn danh, trạng thái, phiên bản | mỗi CV một dòng | A1–A4, A8 |
| CV | `cv_meta` | địa điểm, số năm kinh nghiệm, cấp bậc, nhóm vai trò | mỗi CV một dòng | A6, A7 |
| CV | `cv_experience` | từng mục kinh nghiệm/dự án: loại, nhóm vai trò, tháng bắt đầu/kết thúc | mỗi mục một dòng | A6 |
| CV | `cv_education` | từng mục học vấn: nhóm ngành, tình trạng bằng | mỗi mục một dòng | A6 |
| CV | `cv_skill` | kỹ năng CV có và mức bằng chứng `ev` | mỗi kỹ năng một dòng | A5 |
| CV | `cv_bullet` | từng câu mô tả việc đã làm (bản chuẩn hoá và bản gốc `text_raw`), cờ phủ định/học tập | mỗi gạch một dòng | A7 |
| CV | `cv_vector` | vector của cả CV | mỗi CV một dòng | A10 |
| CV | `cv_bullet_vector` | vector của từng gạch | mỗi gạch một dòng | A10 |
| CV | `cv_bm25_doc` | danh sách từ đã tách, dùng để dựng BM25 | mỗi CV một dòng | A9 |
| JD | `jd` | bảng chính: JSON gốc, văn bản truy vấn, trạng thái, phiên bản | mỗi phiên bản JD một dòng | B1–B3 |
| JD | `jd_meta` | yêu cầu về địa điểm, số năm (min/max), cấp bậc, học vấn | mỗi phiên bản JD một dòng | B5 |
| JD | `jd_skill` | kỹ năng JD cần, bắt buộc hay không, mức quan trọng, nhóm "A hoặc B" | mỗi kỹ năng một dòng | B4 |
| JD | `jd_responsibility` | từng trách nhiệm (bản chuẩn hoá và `text_raw`), kèm vector | mỗi trách nhiệm một dòng | B6, B7 |
| JD | `jd_requirement_item` | từng dòng yêu cầu, đã phân loại (số năm / bằng cấp / ngoại ngữ / chỉ tên kỹ năng / yêu cầu chuyên môn dạng chữ) | mỗi dòng một dòng | B5 |
| JD | `jd_vector` | vector và token truy vấn của JD | mỗi phiên bản JD một dòng | B7 |
| Chung | `unknown_skill` | cụm trông như kỹ năng nhưng chưa có trong KB | mỗi cụm một dòng | A5, B4 |
| Chung | `ingest_log` | nhật ký: mỗi lần nạp thành công hay lỗi, vì sao | mỗi lần nạp một dòng | mọi bước |

Các bảng của bản chụp KB (`skill_ontology`, `role_title_map`, `role_distance`, `major_group`, `ambiguous_aliases`) được xuất từ Neo4j ([[02 Knowledge Base kỹ năng IT]] mục 8) và chỉ đọc, tiền xử lý không ghi vào đó.

```
cv ─┬─ cv_meta            jd ─┬─ jd_meta
    ├─ cv_experience          ├─ jd_skill
    ├─ cv_education           ├─ jd_responsibility
    ├─ cv_skill               ├─ jd_requirement_item
    ├─ cv_bullet ── cv_bullet_vector   └─ jd_vector
    ├─ cv_vector
    └─ cv_bm25_doc
```

Bảng `cv` và `jd` là bảng chính. Mọi bảng khác trong nhóm trỏ về bảng chính qua mã (`cv_id` hoặc `(jd_id, version)`). Riêng `cv_bullet_vector` trỏ về `cv_bullet` qua `bullet_id`.

### `cv_record` là gì

`cv_record` **không phải một bảng**. Nó là một biến trong chương trình Python (kiểu `dict`), chỉ tồn tại trong RAM trong lúc một CV đang được xử lý. Hãy hình dung nó như một **phiếu xử lý**: mỗi bước từ A1 đến A10 điền thêm vài ô vào phiếu, đến A11 thì nội dung phiếu được chép vào các bảng PostgreSQL, rồi phiếu bị bỏ đi.

**Vì sao không ghi xuống database ngay sau mỗi bước?** Nếu A10 lỗi (ví dụ GPU hết bộ nhớ) mà A5 đã ghi kỹ năng, kho sẽ có một CV có kỹ năng mà không có vector, và tầng Retrieve chấm sai CV đó. Gom lại ghi một lần thì hoặc CV có đủ mọi thứ, hoặc chưa có gì.

`cv_record` sau khi đi hết A1–A10 trông như sau (rút gọn):

```python
cv_record = {
    "cv_id": "7c1e2a90-...",            # A1
    "raw_json": {...},                  # A1: CV JSON gốc
    "flags": [],                        # A1, A6: các cờ cảnh báo
    "content_hash": "9f2c4a...",        # A2
    "candidate_key": "hmac:4b1e...",    # A2
    "version": 2,                       # A2
    "anon_json": {...},                 # A3, A4: JSON đã ẩn danh và chuẩn hoá
    "skills_found": [...],              # A5: 5 kỹ năng
    "meta": {...},                      # A6: địa điểm, số năm, cấp bậc...
    "experiences": [...],               # A6: từng mục kinh nghiệm có cấu trúc
    "education": [...],                 # A6: từng mục học vấn có cấu trúc
    "bullets": [...],                   # A7: 2 gạch đầu dòng
    "doc_text": "Chức danh: ...",       # A8
    "bm25": {...},                      # A9: danh sách từ
    "vectors": {...},                   # A10: vector CV và vector từng gạch
}
```

Ở A11, mỗi ô của phiếu được chép vào một chỗ trong database:

| Ô trong `cv_record` | Bước tạo ra | Chép vào đâu |
| --- | --- | --- |
| `cv_id`, `raw_json`, `flags`, `content_hash`, `candidate_key`, `version`, `anon_json`, `doc_text` | A1–A4, A8 | các cột cùng tên của bảng `cv` (một dòng) |
| `skills_found` | A5 | bảng `cv_skill` (mỗi kỹ năng một dòng) |
| `meta` | A6 | bảng `cv_meta` (một dòng) |
| `experiences`, `education` | A6 | bảng `cv_experience`, `cv_education` (mỗi mục một dòng) |
| `bullets` | A7 | bảng `cv_bullet` (mỗi gạch một dòng) |
| `bm25` | A9 | bảng `cv_bm25_doc` (một dòng) |
| `vectors` | A10 | bảng `cv_vector` (một dòng) và `cv_bullet_vector` (mỗi gạch một dòng) |

JD làm y hệt với một phiếu tên `jd_record`, chép vào các bảng `jd_*` ở bước B8.

Từ đây, mỗi bước của Luồng A và B có mục **Kết quả và nơi lưu**: bước đó điền ô nào vào phiếu, và ô đó cuối cùng nằm ở bảng nào, cột nào, trông như thế nào.

## Bức tranh tổng thể

```
          ┌──────── cùng hàm chuẩn hoá (A4 = B2) · cùng bản chụp KB ────────┐
CV JSON → A1 schema → A2 chống trùng → A3 ẩn danh → A4 chuẩn hoá → A5 kỹ năng → A6 metadata
          → A7 gạch đầu dòng → A8 văn bản tài liệu → A9 token BM25 → A10 embedding → A11 ghi
JD JSON → B1 schema → B2 chuẩn hoá → B3 chọn phần để match → B4 kỹ năng → B5 yêu cầu
          → B6 trách nhiệm → B7 token BM25 + embedding → B8 kiểm tra và ghi
```

CV và JD đi qua hai luồng song song, có cấu trúc giống nhau: tiếp nhận, làm sạch, gắn nghĩa bằng KB, rồi biểu diễn thành token và vector. Hai luồng dùng **cùng một hàm chuẩn hoá** và **cùng một bản chụp KB**, nên kết quả hai bên so được với nhau.


## Thuật ngữ cần biết

Bảng dưới giải thích mọi thuật ngữ dùng trong tài liệu, xếp theo thứ tự xuất hiện trong quy trình.

| Thuật ngữ | Nghĩa đơn giản | Ví dụ |
| --- | --- | --- |
| **Schema** | bản mô tả JSON phải có những trường nào, kiểu gì | `experiences` phải là một danh sách; `start` phải có dạng `YYYY-MM` |
| **Validate (kiểm tra schema)** | so JSON với schema, báo lỗi nếu thiếu trường hoặc sai kiểu | `start: "tháng 3"` bị báo sai định dạng |
| **Hash** | một chuỗi ngắn đại diện cho nội dung; nội dung giống hệt thì hash giống hệt | dùng để phát hiện một CV bị nạp hai lần |
| **Canonical JSON** | JSON đã sắp xếp khoá và bỏ khoảng trắng thừa, để hai bản cùng nội dung có cùng hash | `{"b":1,"a":2}` và `{"a":2, "b":1}` cho cùng một hash |
| **candidate\_key** | mã định danh một *người*, để gom các phiên bản CV của cùng người | hash của email đã chuẩn hoá |
| **Ẩn danh hoá (anonymization)** | bỏ thông tin cá nhân khỏi phần dữ liệu dùng để chấm điểm | bỏ tên, email, năm sinh, giới tính, tên trường |
| **Chuẩn hoá (normalization)** | làm sạch văn bản để cùng một thứ luôn được viết giống nhau | `Python` → `python`; "TP.HCM", "Sài Gòn" → `ho_chi_minh` |
| **Unicode NFC** | một cách mã hoá chữ có dấu thống nhất; tiếng Việt có hai cách gõ dấu, nhìn giống nhau nhưng máy coi là khác | "á" dạng dựng sẵn và "a" + dấu sắc → một dạng |
| **Token được bảo vệ** | tên công nghệ có ký tự đặc biệt, không được cắt hay xoá ký tự khi chuẩn hoá | `c#`, `c++`, `.net`, `node.js` |
| **Knowledge Base (KB) / ontology** | từ điển chuẩn về kỹ năng, chức danh, cấp bậc, ngành học và quan hệ giữa chúng | Spring Boot thuộc hệ sinh thái Java |
| **Bản chụp KB (snapshot)** | bản xuất cố định của KB ra các bảng phẳng; tiền xử lý đọc bản này thay vì hỏi Neo4j | bảng `skill_ontology` phiên bản `kb-2026-11-06` |
| **skill\_id** | mã duy nhất của một kỹ năng chuẩn | `S0002` = Spring Boot |
| **Alias** | tên gọi khác của cùng một kỹ năng (hoặc chức danh, cấp bậc) | "k8s", "K8S" → Kubernetes |
| **Alias dễ nhầm (ambiguous alias)** | alias trùng với từ thường hoặc có nhiều nghĩa, không được tự động khớp | "go", "c", "r", "spring" |
| **Nhận diện kỹ năng (skill extraction)** | dò văn bản theo từ điển alias để tìm kỹ năng và gắn `skill_id` | "Triển khai lên K8s" → `Kubernetes` |
| **ev (evidence)** | mức bằng chứng rằng CV thật sự dùng kỹ năng, từ 0 đến 1 | có trong mô tả dự án = 1,0; chỉ ở `technologies` = 0,8; chỉ liệt kê = 0,6 |
| **w\_imp** | mức quan trọng của một kỹ năng trong JD. Khác với `rel` của KB (mức liên quan giữa hai kỹ năng) | cốt lõi = 1,0; phụ = 0,4 |
| **Metadata** | các trường có cấu trúc dùng để lọc hoặc làm tín hiệu phụ | địa điểm, số năm kinh nghiệm, cấp bậc |
| **Nhóm vai trò (role group)** | một trong 8 nhóm nghề của KB | Backend, Frontend, Fullstack, Mobile, Data, DevOps, QA, Security |
| **level\_rank** | cấp bậc dạng số | Intern 0, Fresher 1, Junior 2, Mid 3, Senior 4, Lead 5 |
| **Gạch đầu dòng (bullet)** | một câu mô tả một việc đã làm trong kinh nghiệm hoặc dự án | "Tối ưu truy vấn, giảm 40% thời gian" |
| **`text_raw`** | bản gốc của một gạch, trách nhiệm hoặc yêu cầu: chỉ đưa về NFC và dọn ký tự trang trí, **giữ dấu và hoa/thường**, chưa ghép chức danh | đầu vào của BERTScore ở Rerank (BERTScore rất nhạy với dấu) |
| **Cờ phủ định / học tập** | gạch có dấu hiệu "chưa từng làm" hoặc "chỉ học qua", gắn ở A7 | "Chưa từng triển khai Kubernetes…" → `has_negation` |
| **Trách nhiệm (responsibility)** | một việc JD yêu cầu người được tuyển sẽ làm | "Thiết kế và phát triển API thanh toán" |
| **Văn bản tài liệu (document text)** | một đoạn văn duy nhất ghép từ các trường JSON theo thứ tự cố định, dùng cho BM25 và vector | chức danh + tóm tắt + kinh nghiệm + kỹ năng |
| **Tách từ tiếng Việt (word segmentation)** | gom các âm tiết thành từ ghép, vì tiếng Việt viết cách theo âm tiết | "lập trình viên" là một từ, không phải ba |
| **Token** | một đơn vị từ sau khi tách | `lập_trình_viên`, `python` |
| **Skill token** | token đặc biệt đại diện cho một `skill_id`, để BM25 khớp được dù hai bên viết khác chữ | `skill_s0002` |
| **BM25** | công thức chấm điểm theo từ khoá, không dùng AI; từ hiếm được điểm cao hơn từ phổ biến | "kubernetes" đáng giá hơn "excel" |
| **Embedding / vector** | biến một đoạn văn thành dãy số, sao cho hai đoạn cùng nghĩa thì hai dãy số gần nhau | "xây API thanh toán" gần "phát triển backend giao dịch" |
| **Dense vector** | vector mà mọi vị trí đều có số | 1.024 số cho mỗi đoạn văn |
| **Sparse vector** | danh sách từ kèm trọng số do model học, phần lớn vị trí bằng 0 | `{python: 1.8, api: 0.9}` |
| **BGE-M3** | model embedding đa ngôn ngữ (có tiếng Việt), tạo được cả dense và sparse; embedding từng token của nó là backbone của BERTScore | model mặc định của hệ thống |
| **ontology\_version** | phiên bản bản chụp KB đã dùng để xử lý một CV/JD | `kb-2026-11-06` |
| **pipeline\_version** | phiên bản của code tiền xử lý (hàm chuẩn hoá, quy tắc `ev`…) | `prep-1.0` |
| **embed\_model** | tên và phiên bản model đã tạo vector | `bge-m3@5617a9f61b` |

## Knowledge Base được dùng ở đâu

Tiền xử lý **không hỏi Neo4j cho từng CV**. Nó đọc **bản chụp KB** gồm các bảng phẳng, chỉ chứa tri thức có `status = accepted`. Cách này nhanh hơn, và chạy lại bao nhiêu lần cũng ra cùng kết quả (tái lập được).

| Bảng trong bản chụp | Chứa gì | Dùng ở bước |
| --- | --- | --- |
| `skill_ontology` | kỹ năng chuẩn, alias, loại (`technology` / `concept`), cha, nhóm | A5 (kỹ năng CV), B4 (kỹ năng JD) |
| `role_title_map` | alias chức danh → nhóm vai trò; alias cấp bậc → `level_rank` | A6, B5 |
| `major_group` | alias ngành học → nhóm `it` / `related` / `other` | A6 |
| `role_distance` | khoảng cách giữa các nhóm vai trò | không dùng ở tiền xử lý; dùng ở Rerank (feature B1, B2) |
| `ambiguous_aliases` | danh sách alias dễ nhầm | A5, B4 |

**Ba quy tắc khi dùng KB:**

1. **Một lần chạy dùng đúng một bản chụp.** Mỗi CV và JD ghi lại `ontology_version` đã dùng.
2. **CV và JD chỉ được so với nhau khi cùng `ontology_version`.** Nếu JD được gắn kỹ năng theo KB mới mà CV theo KB cũ, kỹ năng vừa thêm sẽ không khớp với CV nào.
3. **Kỹ năng không có trong KB không bị bỏ qua im lặng.** Nó được ghi vào bảng `unknown_skill` (kèm số lần gặp), và định kỳ được đưa vào KB dưới dạng `candidate` để người duyệt.

**Lưu ý đặt tên:** KB dùng `rel` cho *mức liên quan giữa hai kỹ năng* (cùng kỹ năng 1,0; cha/con 0,7; anh em 0,4). Để không nhầm, tài liệu này gọi mức quan trọng của kỹ năng trong JD là `w_imp`. Ngoài ra, KB hiện dùng khoá `key` và chưa cấp `skill_id`; cần cấp trước khi chạy tiền xử lý. Định nghĩa chuẩn của các đại lượng: [[00 Tổng quan và quy ước]] mục 3.2.

## Dữ liệu đầu ra

Tiền xử lý ghi vào **PostgreSQL** (nguồn sự thật) và dựng một số **cấu trúc trong bộ nhớ** cho tầng Retrieve. Rerank đọc thẳng từ PostgreSQL theo `cv_id` (chỉ ≤200 CV mỗi lần). Nếu bộ nhớ bị mất, mọi thứ được dựng lại từ Postgres mà không cần chạy lại tiền xử lý.

Mục này là bản tổng hợp. Kiểu dữ liệu của từng cột và ví dụ cụ thể nằm ở mục **Kết quả và nơi lưu** cuối mỗi bước của Luồng A và Luồng B.

**Các bảng trong PostgreSQL:**

| Bảng | Mỗi dòng là | Cột chính | Retrieve / Rerank dùng cho |
| --- | --- | --- | --- |
| `cv` | một phiên bản CV | `cv_id`, `candidate_key`, `version`, `is_latest`, `status`, `content_hash`, `raw_json` (bản gốc), `anon_json`, `doc_text`, flags (các cờ chất lượng), 3 cột phiên bản | chọn CV được chấm |
| `cv_meta` | metadata của một CV | `location`, `years_experience`, `intern_months`, `level_rank`, `level_source`, `role_group`, `major_group`, n\_bullets | lọc cứng, tín hiệu mềm |
| `cv_experience` | một mục kinh nghiệm/dự án | `cv_id`, `idx`, `kind`, `title_raw`, `role_group`, `role_group_src`, `start_ym`, `end_ym`, `months`, `dates_quality` | Rerank feature B1, B2, B3 |
| `cv_education` | một mục học vấn | `cv_id`, `idx`, `level`, `major_group`, `status`, `expected_end_ym` | Rerank feature C1 |
| `cv_skill` | một kỹ năng của một CV | `cv_id`, `skill_id`, `ev`, source\_field, `evidence_snippet`, `bullet_id`, `last_used` | view kỹ năng; Rerank feature A1, A2; Explain |
| `cv_bullet` | một gạch đầu dòng | `bullet_id`, `cv_id`, `section`, item\_idx, pos, `text`, `text_raw`, `context_text`, `has_negation`, `is_coursework` | view trách nhiệm; **Rerank BERTScore** (đọc `text_raw`); Explain |
| `cv_vector` | vector của một CV | `dense`, `sparse`, `embed_model` | view dense |
| `cv_bullet_vector` | vector của một gạch | `bullet_id`, `dense` | view trách nhiệm |
| `cv_bm25_doc` | token BM25 của một CV | `bm25_noacc`, `bm25_acc`, `skill_tokens` | dựng chỉ mục BM25 |
| `jd` | một phiên bản JD | `jd_id`, `version`, `is_latest`, `status`, `raw_json`, `norm_json, query_text, warnings`, 3 cột phiên bản | chọn JD để match |
| `jd_meta` | yêu cầu của một JD | `location`, `work_mode`, `min_years`, `max_years`, `level_rank`, `role_group`, `edu_required` | lọc cứng, tín hiệu mềm; Rerank feature B1–B3, C1 |
| `jd_skill` | một kỹ năng của một JD | `jd_id`, version, `skill_id`, `required`, `w_imp`, `group_id`, `source` (Module 1 / tìm thêm), raw\_text | view kỹ năng; Rerank feature A1, A2 |
| `jd_responsibility` | một trách nhiệm | `jd_id`, `version`, `idx`, `text`, `text_raw`, `context_text`, `is_generic`, `dense` | view trách nhiệm; **Rerank feature B4** |
| `jd_requirement_item` | một dòng yêu cầu | `jd_id`, `version`, `idx`, `text`, `text_raw`, `kind` | **Rerank feature B5** (chỉ `kind = text`) |
| `jd_vector` | vector và token của một JD | `dense`, `sparse`, `bm25_query_tokens`, `embed_model` | view dense, BM25 |
| `unknown_skill` | một cụm chưa có trong KB | `text`, `count`, `first_seen`, ví dụ ngữ cảnh | bổ sung KB |
| `ingest_log` | một lần nạp | thời gian, kết quả, lỗi, các cờ | theo dõi, gỡ lỗi |

"3 cột phiên bản" là `ontology_version`, `pipeline_version`, `embed_model`.

**Cấu trúc trong bộ nhớ** (dựng từ các bảng trên, chỉ gồm CV `active` và `is_latest`):

| Cấu trúc | Hình dạng | Kích thước với 100.000 CV |
| --- | --- | --- |
| Ma trận vector tài liệu | 100.000 × 1.024, float16 | ≈ 200 MB |
| Ma trận vector gạch + mảng `bullet_cv_index` (gạch thứ i thuộc CV nào) | \~3 triệu × 1.024, float16 | ≈ 6 GB |
| Ma trận thưa CV × kỹ năng, ô = `ev` | 100.000 × số kỹ năng trong KB | vài chục MB |
| Chỉ mục BM25 | từ `cv_bm25_doc` | vài trăm MB (cần đo) |

Số liệu kích thước là ước lượng, giả định trung bình 30 gạch mỗi CV.

## Khi có thay đổi

Quy tắc chung: **chỉ chạy lại những bước bị ảnh hưởng**, và không bao giờ để kho ở trạng thái nửa cũ nửa mới trong lúc match.

| Sự kiện | Chạy lại | Ghi chú |
| --- | --- | --- |
| CV mới của người đã có | toàn bộ Luồng A cho bản mới | bản cũ `is_latest = false`, vẫn lưu |
| CV trùng hệt (cùng hash) | không chạy gì | chỉ ghi log |
| JD được sửa | toàn bộ Luồng B, tạo `version` mới | kết quả match cũ vẫn giữ để tra cứu |
| JD mở / đóng / hết hạn | chỉ cập nhật `status` | không tính lại vector |
| **KB có bản chụp mới** (thêm kỹ năng, alias, chức danh) | A5, A6, A9 cho **toàn bộ CV**; B4, B5, B7 cho toàn bộ JD; dựng lại chỉ mục BM25 và ma trận CV × kỹ năng | vector tài liệu và vector gạch **không** cần tính lại |
| Đổi hàm chuẩn hoá hoặc mẫu ghép văn bản | từ A4 (hoặc A8) trở đi, toàn kho | tăng `pipeline_version` |
| Đổi model embedding | A10 và vector của B7, toàn kho | xem quy trình bên dưới |
| Xóa CV (ứng viên yêu cầu, hết hạn lưu) | không chạy lại | `status = deleted`; xoá JSON gốc, vector, `evidence_snippet`, gạch đầu dòng; gỡ khỏi cấu trúc trong bộ nhớ ngay |
| Đổi cấu hình BERTScore (model, layer, chuẩn hoá đầu vào) | không chạy lại tiền xử lý | xoá cache embedding token của Rerank (khoá có `bertscore_config`), chạy lại golden test ([[10 Kết quả test BERTScore bge-m3]]) |

**Vì sao KB mới phải chạy lại toàn bộ CV?** Không dò lại văn bản thì không biết CV nào chứa alias vừa thêm. Bước dò kỹ năng khá nhanh (không dùng GPU), nên chạy lại toàn kho theo lịch là chấp nhận được.

**Chuyển phiên bản an toàn** (áp cho KB mới, hàm chuẩn hoá mới, model mới):

1. Xử lý lại toàn kho với phiên bản mới, ghi **song song** với dữ liệu cũ (cột hoặc bảng mới).
2. Trong lúc đó, hệ thống vẫn match bằng phiên bản cũ.
3. Chạy bộ đánh giá trên phiên bản mới. Chỉ khi không tệ hơn mới chuyển.
4. Chuyển **cùng lúc** cả CV lẫn JD sang phiên bản mới. Giữ bản cũ một thời gian để quay lại nếu cần.

Không bao giờ so một vector của model cũ với một vector của model mới: hai model tạo ra hai "hệ toạ độ" khác nhau, phép so không có nghĩa.

## Lỗi thường gặp và kiểm tra chất lượng

Lỗi ở tiền xử lý **lan thẳng sang tầng Retrieve**: kỹ năng nhận diện sai thì view kỹ năng sai, số năm tính sai thì tín hiệu cấp bậc sai. Vì vậy cần vừa xử lý lỗi khi chạy, vừa đo chất lượng từng bước.

**Xử lý lỗi khi chạy:**

| Lỗi | Xử lý |
| --- | --- |
| JSON sai schema | `status = invalid`, vào hàng đợi cho người xem (A1, B1) |
| Ngày tháng không đọc được | đặt `null`, gắn cờ `date_unparsed`, vẫn nạp |
| Tạo vector lỗi giữa chừng (GPU hết bộ nhớ, model lỗi) | không ghi gì cho CV đó (giao dịch), thử lại tự động tối đa 3 lần, rồi để `status = failed` |
| CV không nhận diện được kỹ năng nào | vẫn nạp; BM25 và dense vẫn chấm được |
| CV không có gạch đầu dòng | vẫn nạp; `n_bullets = 0` |
| Bộ nhớ và Postgres lệch nhau | lệnh "dựng lại từ Postgres"; Postgres là nguồn sự thật |
| Bản chụp KB có alias trỏ tới hai kỹ năng | dừng, không nạp KB đó (KB mục 10 đáng lẽ đã chặn) |

**Đo chất lượng tiền xử lý** (nên báo trong chương thực nghiệm của đồ án): lấy ngẫu nhiên **50 CV và 30 JD**, kiểm tra tay từng bước.

| Bước | Đo gì | Cách đo |
| --- | --- | --- |
| A5, B4 – nhận diện kỹ năng | **precision** (kỹ năng tìm ra có đúng không) và **recall** (kỹ năng thật có bị bỏ sót không) | người đọc CV, liệt kê kỹ năng, so với máy |
| A5 – gán `ev` | tỉ lệ `ev` đúng mức | so với người đánh giá trên cùng mẫu |
| A6 – `years_experience` | sai số trung bình (năm) | người tính tay từ mốc thời gian |
| A6, B5 – `role_group`, `level_rank` | tỉ lệ đúng | người gán nhãn |
| A3 – ẩn danh hoá | số CV còn sót tên, email, số điện thoại trong `doc_text` | tìm bằng quy tắc + đọc tay |
| A7 – gạch đầu dòng | tỉ lệ gạch tách sai (dính hai việc, cắt giữa câu) | đọc tay |
| B6 – trách nhiệm chung chung | tỉ lệ đánh dấu đúng | đọc tay |

Theo dõi thêm trên toàn kho (không cần nhãn): tỉ lệ CV `invalid`, tỉ lệ có cờ `no_identity`, `years_uncertain`, `n_bullets = 0`, số kỹ năng trung bình mỗi CV, và 20 cụm xuất hiện nhiều nhất trong `unknown_skill`. Một con số đột ngột thay đổi sau khi sửa code là dấu hiệu lỗi.

## Quyền riêng tư và giảm thiên vị

CV chứa dữ liệu cá nhân, nên dữ liệu được chia hai vùng:

- **Vùng gốc** (`raw_json`): đầy đủ thông tin cá nhân. Chỉ HR có quyền mới xem được, lưu mã hoá, có thời hạn lưu.
- **Vùng chấm điểm** (`anon_json`, `doc_text`, gạch đầu dòng, vector, token): đã ẩn danh hoá ở A3. Tầng Retrieve và Rerank chỉ đọc vùng này.

**Về giảm thiên vị:** bỏ tên, năm sinh, giới tính, ảnh, tình trạng hôn nhân và tên trường giúp model không dựa vào những thông tin này. Tuy vậy, đây chỉ là **giảm**, không loại bỏ hoàn toàn: một số trường còn lại vẫn có thể gián tiếp tiết lộ thông tin (ví dụ năm tốt nghiệp gợi ý tuổi). Báo cáo đồ án nên viết đúng mức này.

**Xoá CV:** khi xoá, phải xoá ở cả vùng gốc, vùng chấm điểm, cấu trúc trong bộ nhớ và mọi log chứa nội dung CV (ví dụ `evidence_snippet`).

Quy định cụ thể về thời hạn lưu và sự đồng ý của ứng viên phụ thuộc pháp luật áp dụng (ở Việt Nam là các quy định về bảo vệ dữ liệu cá nhân); tài liệu này không phải tư vấn pháp lý.

## Điểm còn mở

Đã gom vào [[11 Tham số, lộ trình và điểm còn mở]] (nhóm "Tiền xử lý").

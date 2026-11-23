# 02 · Knowledge Base (KB) kỹ năng IT cho module match CV ↔ JD

> **Phiên bản:** 1.2 (09/11/2026): sửa tham chiếu theo bộ tài liệu 2.0
> **Nơi lưu:** Neo4j (đồ thị). Module match **không** đọc Neo4j trực tiếp mà đọc **bản chụp** xuất ra (mục 8).
> **Liên quan:** [[00 Tổng quan và quy ước]] (tên `rel`, `w_imp`, 8 nhóm vai trò) · [[03 Tiền xử lý - Lưu trữ và dữ liệu]] (cách tiền xử lý đọc bản chụp) · [[07 Rerank - BERTScore với bge-m3]] (feature A1, A2, B1, B2, C1).
> **Ký hiệu:** **(ƯL)** là giá trị đề xuất chưa đo.

---

## 0. Đọc nhanh

**KB dùng để làm gì?** Máy so chữ rất "máy móc". Nó không biết:

- "k8s" và "Kubernetes" là một;
- CV có "Spring Boot" thì gần như đã biết "Java";
- "MySQL" có thể thay cho "PostgreSQL";
- "Lập trình viên Java" là vị trí Backend.

KB là **cuốn từ điển + bản đồ quan hệ** giúp module match hiểu những điều đó.

**KB chứa 6 loại tri thức**, mỗi loại phục vụ một chỗ trong thiết kế:

| Mã | Tri thức | Ví dụ | Thiết kế dùng ở đâu |
|---|---|---|---|
| **T1** | Kỹ năng chuẩn và tên gọi khác (alias) | "k8s", "K8s" → Kubernetes | Tiền xử lý A5, B4 (gắn mã kỹ năng); token BM25; Rerank: đổi alias về tên chuẩn trước khi chạy BERTScore |
| **T2** | Quan hệ giữa các kỹ năng | Java → Spring Boot; MySQL ~ PostgreSQL | Rerank feature A1, A2 (hệ số `rel`) |
| **T3** | Kỹ năng điển hình của từng nhóm vai trò | Backend hay dùng Spring Boot, PostgreSQL | Explain (kỹ năng điển hình của vai trò); tính `M` kiểu `computed` |
| **T4** | Chức danh và cấp bậc | "Lập trình viên Java" → Backend; "Senior" → cấp 4 | Tiền xử lý A6, B5 (`role_group`, `level_rank`) |
| **T5** | Khoảng cách giữa các nhóm vai trò | Backend – Fullstack gần nhau (0,8) | Rerank feature B1, B2 (ma trận `M`) |
| **T6** | Nhóm ngành học | "Kỹ thuật phần mềm" → ngành CNTT | Tiền xử lý A6; Rerank feature C1 |

**Hình dung KB** (một lát cắt nhỏ):

```
 (Source: docs.spring.io)                         (Source: roadmap Backend)
        ▲ bằng chứng                                       ▲ bằng chứng
 (Java) ──PARENT_OF──► (Spring Boot) ──USED_IN──► (Backend) ◄──NEAR 0,8──► (Fullstack)
                                                     ▲
                                                     │ MAPS_TO
                                  (JobTitle "Lập trình viên Java")

 (PostgreSQL) ──IN_CATEGORY──► (Relational Databases, sibling_ok = true) ◄──IN_CATEGORY── (MySQL)
        └──────────── suy ra: anh em → rel = 0,4 ────────────┘
```

---

## 1. Các loại nút

Mỗi "nút" là một thực thể. Mọi nút đều có `status`, `kb_origin`, `updated_at` (giải thích ở mục 3).

| Nút | Là gì | Thuộc tính chính | Ví dụ | Tri thức |
|---|---|---|---|---|
| `Skill` | một kỹ năng chuẩn | `skill_id` (khoá), `name`, `aliases[]`, `type`, `esco_uri` | `S0002`, "Spring Boot", ["springboot", "spring-boot"], `technology` | T1 |
| `Category` | một nhóm kỹ năng | `name` (khoá), `sibling_ok` | "Relational Databases", `sibling_ok = true` | T2 |
| `RoleGroup` | nhóm vai trò | `name` (khoá) | Backend, Frontend, Fullstack, Mobile, Data, DevOps, QA, Security | T3, T5 |
| `JobTitle` | chức danh gốc (không kèm cấp) | `name` (khoá), `aliases[]` | "Java Developer", ["lập trình viên java", "java dev"] | T4 |
| `Level` | cấp bậc | `name` (khoá), `rank`, `aliases[]` | Senior, 4, ["senior", "sr", "chuyên viên cao cấp"] | T4 |
| `Major` | ngành học | `name` (khoá), `aliases[]`, `group` | "Kỹ thuật phần mềm", `group = it` | T6 |
| `Source` | một nguồn tri thức | `source_id` (khoá), `type`, `title`, `uri`, `trust`, `license`, `sha256`, `accessed` | P01, pdf, "roadmap Backend", `medium` | nguồn gốc |
| `KBVersion` | một lần gộp KB | `id`, `created`, `n_skills`, `n_relations`, `n_candidates`, `sources_changed[]` | kb-2026-11-06 | phiên bản |

**Giải thích một số thuộc tính:**

- `Skill.type`: `technology` (công cụ, ngôn ngữ, framework cụ thể) hoặc `concept` (khái niệm như "REST API", "Microservices"). Một số câu kiểm tra ở Explain chỉ áp với `technology` ([[08 Explain]]).
- `Level.rank`: thang Intern 0 · Fresher 1 · Junior 2 · Mid 3 · Senior 4 · Lead 5 ([[00 Tổng quan và quy ước]] mục 3.2).
- `Major.group`: `it` (CNTT) · `related` (Toán–Tin, Điện tử–Viễn thông) · `other`. Tương ứng 1,0 · 0,7 · 0,3 ở feature C1 ([[07 Rerank - BERTScore với bge-m3]]).
- `Source.trust`: mức tin cậy, dùng khi gộp (mục 6).
  - `high`: ESCO, tài liệu chính thức của công nghệ.
  - `medium`: roadmap, báo cáo thị trường, chương trình đào tạo, Stack Overflow.
  - `low`: một trang JD lẻ.

**Vì sao chức danh và cấp bậc là hai nút riêng?** "Senior Java Developer" = chức danh "Java Developer" + từ bổ nghĩa "Senior". Nếu ghép chung, phải tạo nút cho mọi tổ hợp (Junior/Mid/Senior × mọi chức danh). Tách ra thì bước A6 (tiền xử lý) dò hai thứ độc lập: chức danh → nhóm vai trò, từ bổ nghĩa → cấp bậc.

---

## 2. Các loại quan hệ

Mỗi "quan hệ" nối hai nút. Mọi quan hệ đều có `status`, `sources[]`, `evidence[]`, `updated_at` (mục 3).

| Quan hệ | Nghĩa | Thuộc tính riêng | Ví dụ | Dùng ở |
|---|---|---|---|---|
| `(Skill)-[:PARENT_OF]->(Skill)` | con **được xây trên / thuộc hệ sinh thái** của cha | `confidence` | Java → Spring Boot | `rel = 0,7` (feature A1) |
| `(Skill)-[:IN_CATEGORY]->(Category)` | kỹ năng **là một loại** trong nhóm | | PostgreSQL → Relational Databases | suy anh em, `rel = 0,4` |
| `(Skill)-[:USED_IN]->(RoleGroup)` | kỹ năng thường dùng ở nhóm vai trò | `df_jd`, `share_jd`, `in_roadmap` | Spring Boot → Backend | Explain (kỹ năng điển hình của vai trò); tính `M` kiểu `computed` |
| `(RoleGroup)-[:NEAR]->(RoleGroup)` | hai nhóm vai trò gần nhau | `m`, `method` | Backend – Fullstack, `m = 0,8` | ma trận `M` (B1, B2) |
| `(JobTitle)-[:MAPS_TO]->(RoleGroup)` | chức danh thuộc nhóm vai trò | | Java Developer → Backend | tiền xử lý A6, B5 |
| `(Skill)-[:EVIDENCED_BY]->(Source)` | kỹ năng được nhắc trong nguồn | `page`, `snippet` | Spring Boot → P01, trang 1 | dẫn nguồn cho RAG, Explain |

### 2.1 Phân biệt `PARENT_OF` và `IN_CATEGORY` (quan trọng)

Hai quan hệ này dễ nhầm, nhưng cho điểm khác nhau:

| | `PARENT_OF` | `IN_CATEGORY` |
|---|---|---|
| Câu hỏi để kiểm tra | "B **được xây trên** A, hoặc dùng B là đang dùng A?" | "B **là một loại** của nhóm X?" |
| Ví dụ đúng | Java → Spring Boot; JavaScript → React; Python → Django | PostgreSQL ∈ Relational Databases; Jenkins ∈ CI/CD tools |
| Ví dụ **sai** | Relational Databases → PostgreSQL (đây là "một loại") | |
| Điểm khi khớp | cha/con: 0,7 | anh em trong nhóm `sibling_ok = true`: 0,4 |

### 2.2 Thuộc tính `sibling_ok` của `Category`

Không phải nhóm nào cũng cho anh em được điểm:

- **Nhóm hẹp, thay thế được cho nhau** → `sibling_ok = true`. Ví dụ "Relational Databases" (MySQL thay PostgreSQL được), "CI/CD tools", "Message brokers".
- **Nhóm rộng** → `sibling_ok = false`. Ví dụ "Programming Languages": JD cần Java mà CV có Python thì **không** nên được 0,4 điểm.

Giá trị mặc định là `false`. Người duyệt bật lên cho từng nhóm khi gộp KB.

### 2.3 Thuộc tính của `USED_IN`

Roadmap (1 tài liệu chuẩn cho cả nhóm) và JD (nhiều tài liệu lẻ) khác bản chất, nên đếm riêng:

- `df_jd`: số JD của nhóm vai trò có nhắc kỹ năng.
- `share_jd = df_jd / tổng số JD của nhóm`. Ví dụ 14/20 = 0,7 nghĩa là 70% JD Backend nhắc Spring Boot.
- `in_roadmap`: kỹ năng có trong roadmap của nhóm đó không (true/false).

### 2.4 Thuộc tính của `NEAR`

- `M` là đối xứng: **lưu một chiều**, truy vấn không quan tâm hướng. Cùng nhóm thì ngầm định `m = 1`, không lưu.
- `method`:
  - `hypothesis`: lấy từ bảng giả thuyết của thiết kế.
  - `computed`: tính từ KB, ví dụ độ trùng kỹ năng `USED_IN` giữa hai nhóm (hệ số Jaccard).

  Có thể lưu cả hai để so sánh trong báo cáo.

### 2.5 Không có quan hệ "anh em" riêng

Hai kỹ năng là anh em khi:

- cùng thuộc một `Category` có `sibling_ok = true`, **hoặc**
- cùng có một cha qua `PARENT_OF`.

Quan hệ này **suy ra lúc truy vấn**, không lưu. Lý do: lưu thêm thì phải giữ hai bản luôn khớp nhau, dễ sai.

---

## 3. Thuộc tính chung: trạng thái, nguồn, bằng chứng

| Thuộc tính | Có ở | Giải thích |
|---|---|---|
| `status` | mọi nút và quan hệ | `accepted` (đã nhận), `candidate` (chờ duyệt), `rejected` (đã loại). **Chỉ `accepted` được xuất cho module match** |
| `kb_origin[]` | mọi nút | nút đến từ `KB1`, `KB2` hay cả hai |
| `sources[]` | mọi quan hệ | danh sách `source_id` ủng hộ quan hệ này, ví dụ `["P05", "W05"]` |
| `evidence[]` | mọi quan hệ | danh sách `{source_id, page, quote}`; `quote` là đoạn nguyên văn trong nguồn (đã được code kiểm là chuỗi con) |
| `confidence` | `PARENT_OF` (có thể thêm cho các quan hệ khác) | độ tin cậy 0–1 tính khi gộp (mục 6) |
| `updated_at` | mọi nút và quan hệ | lần sửa gần nhất |

**Vì sao bằng chứng phải nằm trên quan hệ?** Bằng chứng quan trọng nhất của KB là cho **quan hệ**, ví dụ câu "Spring Boot là framework dựa trên Java". Neo4j không cho một quan hệ trỏ tới một nút khác, nên lưu bằng chứng ngay trong thuộc tính của quan hệ.

---

## 4. Quy tắc cho alias

1. **Mỗi alias thuộc đúng một kỹ năng.** Alias trỏ tới hai kỹ năng là lỗi, phải sửa trước khi xuất.
2. Alias lưu ở dạng chuẩn hoá: NFC, chữ thường, gộp khoảng trắng (cùng hàm chuẩn hoá của bước A4).
3. **Alias dễ nhầm** không dùng để khớp tự động, ghi vào danh sách `ambiguous_aliases`. Ví dụ "go" (từ thường), "c", "r", "spring" (Spring Framework hay Spring Boot?). Dùng dạng dài thay thế: "golang", "c++", "c#".
4. Khi khớp, cụm dài khớp trước ("spring boot" trước "spring", "react native" trước "react").

Quy tắc tương tự áp cho `JobTitle.aliases`, `Level.aliases`, `Major.aliases`.

---

## 5. KB1, KB2 nằm ở đâu

Neo4j bản Community chỉ có một database, nên tách KB1/KB2 bằng **tiền tố nhãn**:

| Giai đoạn | Nhãn | Nguồn |
|---|---|---|
| **KB1** (tạm) | `KB1_Skill`, `KB1_Category`, `KB1_JobTitle`, `KB1_Source`, … | file PDF: roadmap, báo cáo thị trường, chương trình đào tạo, sách |
| **KB2** (tạm) | `KB2_Skill`, `KB2_Category`, `KB2_JobTitle`, `KB2_Source`, … | web: ESCO, Stack Overflow, trang JD, tài liệu chính thức |
| **KB** (sau gộp) | `Skill`, `Category`, `JobTitle`, `Source`, … (bảng ở mục 1, 2) | gộp KB1 + KB2 |

Trong KB1, KB2, mọi thứ đều là `candidate`. Chỉ bước gộp mới quyết định `accepted`.

---

## 6. Quy tắc gộp KB1 + KB2 → KB

**Bước 1. Hợp nhất thực thể.** "ReactJS" (KB1) và "React" (KB2) phải thành một nút. Hai kỹ năng là một khi có ít nhất một điều sau:

- cùng `esco_uri`;
- tên chuẩn hoá trùng nhau;
- alias của bên này trùng tên hoặc alias của bên kia.

Không chắc chắn thì để `candidate`, người duyệt quyết định.

**Bước 2. Quyết định nhận quan hệ.** Một quan hệ thành `accepted` khi:

- có ít nhất **2 nguồn độc lập** ủng hộ, **hoặc**
- có **1 nguồn `trust = high`**.

Còn lại giữ `candidate` và vào hàng đợi duyệt. Hai nguồn mâu thuẫn nhau, ví dụ một nguồn ghi cha/con, một nguồn ghi cùng nhóm: ưu tiên nguồn `trust` cao hơn và ghi lại trong `evidence`.

**Bước 3. Tính `confidence`** (công thức đề xuất, ƯL):

```
confidence = 1 − Π (1 − w_trust)      với w_trust: high = 0,9 · medium = 0,6 · low = 0,3
```

Ví dụ: một nguồn medium + một nguồn low → 1 − 0,4 × 0,7 = 0,72.

**Bước 4. Tính thống kê.** Tính lại `USED_IN` (`df_jd`, `share_jd`, `in_roadmap`) và `NEAR` (`method = computed`) từ toàn bộ KB.

**Bước 5. Ghi phiên bản.** Tạo `KBVersion` mới (số kỹ năng, số quan hệ, số `candidate`, nguồn nào đổi).

---

## 7. Hệ số `rel` được tính từ KB thế nào

Đây là chỗ KB đi thẳng vào điểm số của Rerank (feature A1, A2):

| Quan hệ giữa kỹ năng CV có (`a`) và kỹ năng JD cần (`b`) | `rel` (ƯL) |
|---|---|
| cùng kỹ năng | 1,0 |
| cha/con: `a PARENT_OF b` hoặc `b PARENT_OF a` | 0,7 |
| anh em: chung cha, hoặc chung `Category` có `sibling_ok = true` | 0,4 |
| còn lại | 0 |

```cypher
MATCH (a:Skill {skill_id:$a}), (b:Skill {skill_id:$b})
RETURN CASE
  WHEN a = b THEN 1.0
  WHEN EXISTS { (a)-[r:PARENT_OF {status:'accepted'}]-(b) } THEN 0.7
  WHEN EXISTS { (a)<-[:PARENT_OF {status:'accepted'}]-(:Skill)-[:PARENT_OF {status:'accepted'}]->(b) }
    OR EXISTS { (a)-[:IN_CATEGORY {status:'accepted'}]->(c:Category {sibling_ok:true})
                   <-[:IN_CATEGORY {status:'accepted'}]-(b) } THEN 0.4
  ELSE 0.0 END AS rel
```

Ví dụ:

- `rel("Spring Boot", "Java") = 0,7`
- `rel("MySQL", "PostgreSQL") = 0,4`
- `rel("Python", "Java") = 0`, vì "Programming Languages" có `sibling_ok = false`.

---

## 8. Bản chụp xuất cho module match

Sau mỗi lần gộp, KB được xuất ra **5 bảng phẳng** trong PostgreSQL. Tiền xử lý (Luồng A, B) và Rerank đọc các bảng này, **không** truy vấn Neo4j cho từng CV (nhanh và tái lập được). **Chỉ xuất `status = accepted`.**

| Bảng | Cột | Ai dùng |
|---|---|---|
| `skill_ontology` | `skill_id, name, aliases[], type, parents[], categories_sibling_ok[], ontology_version` | Tiền xử lý A5, B4; Rerank feature A1, A2 và bước đổi alias trước BERTScore; Explain |
| `role_title_map` | `title_alias, role_group` và `level_alias, level_rank` | Tiền xử lý A6, B5 |
| `role_distance` | `group_a, group_b, m, method` | Rerank feature B1, B2 |
| `major_group` | `major_alias, group` | Tiền xử lý A6; Rerank feature C1 |
| `ambiguous_aliases` | `alias, candidates[]` | Tiền xử lý A5, B4 (không tự khớp trong văn bản tự do) |

`ontology_version` = `KBVersion.id`, được tiền xử lý ghi vào mỗi CV và JD để biết bản ghi đó được gắn kỹ năng theo phiên bản KB nào. CV và JD chỉ được so với nhau khi cùng `ontology_version` ([[03 Tiền xử lý - Lưu trữ và dữ liệu]]).

---

## 9. Lệnh tạo schema (Neo4j 5)

```cypher
CREATE CONSTRAINT skill_id     IF NOT EXISTS FOR (n:Skill)     REQUIRE n.skill_id  IS UNIQUE;
CREATE CONSTRAINT category     IF NOT EXISTS FOR (n:Category)  REQUIRE n.name      IS UNIQUE;
CREATE CONSTRAINT role_group   IF NOT EXISTS FOR (n:RoleGroup) REQUIRE n.name      IS UNIQUE;
CREATE CONSTRAINT job_title    IF NOT EXISTS FOR (n:JobTitle)  REQUIRE n.name      IS UNIQUE;
CREATE CONSTRAINT level        IF NOT EXISTS FOR (n:Level)     REQUIRE n.name      IS UNIQUE;
CREATE CONSTRAINT major        IF NOT EXISTS FOR (n:Major)     REQUIRE n.name      IS UNIQUE;
CREATE CONSTRAINT source_id    IF NOT EXISTS FOR (n:Source)    REQUIRE n.source_id IS UNIQUE;
CREATE INDEX skill_name        IF NOT EXISTS FOR (n:Skill)     ON (n.name);
-- KB1_*, KB2_*: tạo ràng buộc tương tự cho các nhãn tạm

// Dữ liệu cố định ban đầu
UNWIND ['Backend','Frontend','Fullstack','Mobile','Data','DevOps','QA','Security'] AS g
  MERGE (:RoleGroup {name:g});
UNWIND [['Intern',0],['Fresher',1],['Junior',2],['Mid',3],['Senior',4],['Lead',5]] AS l
  MERGE (x:Level {name:l[0]}) SET x.rank = l[1];
```

Dùng `MERGE` (tạo nếu chưa có) thay vì `CREATE`, nên chạy lại script bao nhiêu lần cũng không nhân đôi dữ liệu.

---

## 10. Kiểm tra KB trước khi xuất

| Kiểm tra | Truy vấn hoặc cách làm | Kỳ vọng |
|---|---|---|
| Alias trùng giữa hai kỹ năng | gom alias, đếm số kỹ năng mỗi alias | 0 |
| Vòng lặp cha/con | tìm đường `PARENT_OF*` quay về chính nó | 0 |
| Kỹ năng `accepted` không có nguồn | `Skill` không có `EVIDENCED_BY` và không có `esco_uri` | 0 |
| Quan hệ `accepted` không có `evidence` | | 0 |
| Chức danh không thuộc nhóm nào | `JobTitle` không có `MAPS_TO` | 0 |
| Độ chính xác trích xuất KB1 | kiểm tay mẫu 30–50 quan hệ | báo tỉ lệ đúng trong Chương 4 |

---

## 11. Điểm cần xác nhận

1. **8 nhóm vai trò** có khớp với nhóm vai trò mà Module 1 dùng cho JD không.
2. **Quan hệ bất đối xứng** (CV có Spring Boot đáp ứng yêu cầu Java tốt hơn chiều ngược lại): thiết kế để "thử sau", nên bản này **chưa** thêm.
3. Giá trị `rel` (1,0 / 0,7 / 0,4), trọng số `w_trust` và ma trận `M` giả thuyết là **(ƯL)**, chưa đo.
4. Ai là người duyệt các `candidate` và bật `sibling_ok` (bạn, hay cả nhóm).
5. **Khoá `skill_id`:** thiết kế dùng `skill_id` (`S0002`…), nhưng KB đang cài đặt trên Neo4j dùng khoá `key`. Cần cấp `skill_id` trước khi chạy tiền xử lý.
6. Danh sách câu hỏi mở của toàn module nằm ở [[11 Tham số, lộ trình và điểm còn mở]].

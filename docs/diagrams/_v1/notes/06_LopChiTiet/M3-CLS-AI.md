# M3-CLS-AI — Biểu đồ lớp chi tiết phía AI: cv-matching-ai (Module 3)

## 1. Diễn giải vai trò từng lớp/module và luồng gọi chính

### 1.1. Vai trò từng phần tử theo mô hình MVC / Phân tầng

Hệ thống dịch vụ AI `cv-matching-ai` được xây dựng bằng Python (FastAPI). Theo quy tắc mô hình hóa cho các module Python không có định nghĩa `class` mà chỉ chứa hàm nghiệp vụ:
- Các phần tử mang tên module đúng như tệp mã nguồn (`main`, `extraction_adapter`, `normalize`, `features`, `graph`, `scoring`, `embeddings`) với stereotype `«module»` (riêng `main` mang stereotype `«boundary»` do chứa FastAPI app và các API route).
- Các lớp tồn tại thực tế trong mã nguồn (`MatchRequest`, `EmbeddingService`) giữ nguyên tên lớp và stereotype hướng đối tượng tương ứng (`«entity»`, `«service»`).
- **Tầng View (Boundary):** Điểm tiếp nhận request từ bên ngoài qua HTTP route trong module `main`.
- **Tầng Controller (Control):** Các module xử lý logic, chuyển đổi dữ liệu và thuật toán đối sánh (`extraction_adapter`, `normalize`, `features`, `graph`, `scoring`).
- **Tầng Model (Service / Entity):** Bao gồm lớp Pydantic DTO `MatchRequest`, lớp xử lý mô hình nhúng `EmbeddingService`, và module hỗ trợ vector `embeddings`.

| Phần tử | Stereotype | Gói (Package) | Vai trò trong hệ thống HireLens |
|---|---|---|---|
| `main` | «boundary» | `View` | Module khởi tạo FastAPI (`app = FastAPI(...)`), tiếp nhận HTTP POST `/match/no-llm` qua hàm `match_without_llm`, điều phối luồng thực thi `_run_match` và quản lý sự kiện nạp trước mô hình `load_required_embedding_model`. |
| `MatchRequest` | «entity» | `Model` | Lớp Pydantic model (`class MatchRequest(BaseModel)`) định nghĩa cấu trúc dữ liệu đầu vào của API đối sánh gồm thông tin ứng viên (`candidate`), công việc (`jd`), và bộ trọng số tùy chọn (`weights`). |
| `extraction_adapter` | «module» | `Controller` | Module đóng vai trò Adapter: chuyển đổi cấu trúc dữ liệu hồ sơ ứng viên trích xuất từ Module 1 (`cv-extraction-ai`) sang hợp đồng đầu vào chuẩn của bài toán đối sánh (`adapt_candidate`); tính số năm kinh nghiệm thực tế không trùng lặp (`experience_years`). |
| `normalize` | «module» | `Controller` | Module làm sạch chuỗi, chuẩn hóa danh sách kỹ năng qua từ điển tĩnh `skills_dictionary.json` (`normalize_candidate`, `normalize_jd`, `load_skill_dictionary`), và chuẩn hóa bậc học yêu cầu. |
| `features` | «module» | `Controller` | Module trích xuất và định lượng 4 nhóm đặc trưng đối sánh (`extract_features`): độ khớp kỹ năng (`skill_match_details`), điểm kinh nghiệm (`score_experience`), điểm học vấn (`score_education`), và điểm ngữ cảnh văn bản (`score_context`). |
| `graph` | «module» | `Controller` | Module quản trị và tra cứu đồ thị tri thức kỹ năng NetworkX (`kb_skill_graph.json` / `skills_graph.json`): tra cứu alias kỹ năng (`skill_to_node_id`), xác định quan hệ trực tiếp (`direct_relation`), tính khoảng cách ngắn nhất (`graph_distance`, `graph_match_score`), và tìm kỹ năng theo chức danh (`skills_for_title`). |
| `scoring` | «module» | `Controller` | Module thẩm định trọng số (`validate_weights`) và tính điểm đối sánh tổng hợp theo thang điểm 100 (`compute_final_score`) kết hợp các điểm thành phần. |
| `embeddings` | «module» | `Model` | Module cung cấp hàm tính tương đồng ngữ nghĩa vector `cosine_similarity`, đồng thời khởi tạo biến singleton `embedding_service = EmbeddingService()`. |
| `EmbeddingService` | «service» | `Model` | Lớp dịch vụ vector hóa văn bản (Sentence Transformers `paraphrase-multilingual-MiniLM-L12-v2` 384 chiều) kết hợp bộ nhớ đệm và thuật toán băm dự phòng (`_hash_embedding`) khi không có kết nối internet hoặc thiếu tài nguyên nạp model. |

---

### 1.2. Luồng gọi chính trong Module 3 (POST `/match/no-llm`)

Luồng xử lý diễn ra tuần tự và tất định:
1. **Tiếp nhận Request:** Microservice `recruitment-service` (qua lớp `CvMatchingModule.java:18`) gửi HTTP POST đến endpoint `/match/no-llm` của module `main`. Request body được Pydantic tự động validate và ánh xạ vào đối tượng `MatchRequest`.
2. **Kích hoạt hàm điều phối:** `main.match_without_llm` gọi hàm nội bộ `main._run_match(request, use_llm=False)`. Bắt đầu đo thời gian xử lý (`time.perf_counter()`).
3. **Chuẩn hóa dữ liệu ứng viên:**
   - `main._run_match` gọi `normalize.normalize_candidate(request.candidate)`.
   - `normalize` gọi `extraction_adapter.adapt_candidate(candidate)` để chuyển đổi các trường trích xuất từ Module 1 (`personal_info`, `experience`, `education`, `objective`) sang hợp đồng đối sánh. Trong đó, `extraction_adapter.experience_years` duyệt các khoảng thời gian công việc, loại bỏ các tháng trùng lặp và tính tổng số năm kinh nghiệm chính xác.
   - `normalize` nạp từ điển kỹ năng qua `load_skill_dictionary()`, đưa các kỹ năng về danh từ chuẩn và trả về dictionary dữ liệu ứng viên đã chuẩn hóa.
4. **Chuẩn hóa tin tuyển dụng (JD):**
   - `main._run_match` gọi `normalize.normalize_jd(request.jd)`.
   - `normalize` chuẩn hóa danh sách kỹ năng qua từ điển, chuẩn hóa bậc học yêu cầu qua `_education_requirement()` và trả về dictionary tin tuyển dụng chuẩn hóa.
5. **Trích xuất đặc trưng đối sánh:**
   - `main._run_match` gọi `features.extract_features(candidate, jd)`.
   - `features` tính toán 4 nhóm đặc trưng:
     - **Kỹ năng (`skill_match_details`):** Gọi `graph.default_skill_graph()` và `graph.skills_for_title()` để bổ sung kỹ năng đặc thù chức danh. Với từng cặp kỹ năng (CV - JD), gọi `score_skill_pair()` để tính điểm: tra cứu quan hệ bản thể (`graph.direct_relation` cho quan hệ `REQUIRES`/`PART_OF`/`IS_A`), tính khoảng cách đồ thị tri thức (`graph.graph_match_score`), và tính tương đồng ngữ nghĩa vector (`embeddings.cosine_similarity`).
     - **Kinh nghiệm (`score_experience`):** So sánh tỷ lệ số năm kinh nghiệm tích lũy với số năm yêu cầu, kết hợp độ tương đồng chức danh bằng `embeddings.cosine_similarity`.
     - **Học vấn (`score_education`):** So khớp thứ bậc học vấn theo thang điểm phân cấp `EDUCATION_LEVELS` (tiến sĩ > thạc sĩ > cử nhân/đại học > cao đẳng > trung học).
     - **Ngữ cảnh (`score_context`):** Tính độ tương đồng ngữ nghĩa giữa toàn bộ tóm tắt CV và mô tả công việc bằng `embeddings.cosine_similarity`.
6. **Tính điểm tổng hợp:**
   - `main._run_match` gọi `scoring.validate_weights()` để kiểm tra tính hợp lệ của trọng số (mặc định: skill=0.4, experience=0.3, education=0.15, context=0.15).
   - Gọi `scoring.compute_final_score(features, weights)` để tính tổng điểm có trọng số, chuẩn hóa về thang điểm [0, 100].
7. **Tạo kết quả giải thích tất định và phản hồi:**
   - Vì `use_llm=False`, `main._run_match` không gọi OpenAI API (không dùng module `explain.py`), mà trực tiếp sinh chuỗi lý giải tất định: `"Điểm tự động: {score:.2f}/100. Khớp {len(matched)}/{len(jd['required_skills'])} kỹ năng yêu cầu."`.
   - Đóng gói toàn bộ thông tin vào cấu trúc dictionary kết quả và trả về mã HTTP 200 JSON cho `recruitment-service`.

---

## 2. Phân tích Design Patterns thực sự có trong mã nguồn

Mã nguồn dịch vụ `cv-matching-ai` áp dụng các mẫu thiết kế hướng đối tượng và kiến trúc phần mềm thực tế sau:

### 2.1. Adapter Pattern
- **Module tham gia:** `extraction_adapter` (`source/recruit_system/services/cv-matching-ai/app/extraction_adapter.py:40`).
- **Vai trò:** Đóng vai trò **Adapter** chuyển đổi giao diện dữ liệu. Đầu ra của dịch vụ trích xuất CV (Module 1 / `cv-extraction-ai`) sử dụng cấu trúc `personal_info`, `experience` (danh sách công ty, ngày bắt đầu/kết thúc), `education_text`, `objective`. Thuật toán đối sánh của `cv-matching-ai` lại yêu cầu dữ liệu phẳng hơn: `name`, `experience_years` (số thực), `job_titles`, `education`, `summary`, `raw_context`. Hàm `adapt_candidate()` chuyển đổi tương thích giữa hai cấu trúc này.
- **Ưu điểm cụ thể cho HireLens:** Giúp cô lập hoàn toàn (decoupling) tầng đối sánh khỏi sự thay đổi của tầng trích xuất CV. Nếu cấu trúc trích xuất CV của mô hình Qwen GGUF có thay đổi theo phiên bản, chỉ cần cập nhật logic chuyển đổi trong `extraction_adapter` mà không ảnh hưởng đến các hàm tính toán đặc trưng và điểm số trong `features.py`. Đồng thời, hàm `experience_years()` giải quyết bài toán nghiệp vụ phức tạp về việc hợp nhất các khoảng thời gian đi làm trùng lặp (overlapping employment intervals) để tính chính xác thâm niên nghề nghiệp của ứng viên.

### 2.2. DTO (Data Transfer Object) / Schema Pattern
- **Lớp tham gia:** `MatchRequest` (`source/recruit_system/services/cv-matching-ai/app/main.py:27`) kế thừa `pydantic.BaseModel`.
- **Vai trò:** Đóng vai trò đối tượng truyền tải dữ liệu qua biên giới tiến trình (Process Boundary) giữa Spring Boot (`recruitment-service`) và FastAPI (`cv-matching-ai`).
- **Ưu điểm cụ thể cho HireLens:** Đảm bảo tính toàn vẹn kiểu dữ liệu (type safety) và tự động xác thực schema (schema validation) ngay tại cổng vào của API. Các lỗi thiếu trường hoặc sai định dạng dữ liệu (ví dụ JSON sai cú pháp) sẽ bị chặn ngay tại tầng biên với mã lỗi HTTP 422 Unprocessable Entity, ngăn ngừa lỗi ngoại lệ runtime làm crash tiến trình tính toán AI.

### 2.3. Singleton Pattern
- **Lớp tham gia:** `EmbeddingService` (`source/recruit_system/services/cv-matching-ai/app/embeddings.py:15, :63`).
- **Vai trò:** Biến `embedding_service = EmbeddingService()` được khởi tạo duy nhất một lần ở phạm vi module (module-level singleton) trong `embeddings.py` và được nạp dùng chung cho toàn bộ ứng dụng.
- **Ưu điểm cụ thể cho HireLens:** Mô hình SentenceTransformer `paraphrase-multilingual-MiniLM-L12-v2` có kích thước gần 500MB và tiêu tốn nhiều tài nguyên/thời gian khởi tạo trọng số vào bộ nhớ RAM. Việc áp dụng Singleton đảm bảo mô hình chỉ được nạp một lần duy nhất vào bộ nhớ, tránh rò rỉ bộ nhớ (memory leak) và giảm thời gian phản hồi của mỗi request đối sánh từ vài giây xuống dưới 50 mili-giây.

### 2.4. Lazy Initialization (Khởi tạo lười) kết hợp Caching
- **Lớp / Module tham gia:**
  - `EmbeddingService._load_model` (`source/recruit_system/services/cv-matching-ai/app/embeddings.py:25`): Chỉ tải mô hình SentenceTransformer khi có request mã hóa văn bản đầu tiên hoặc khi có biến môi trường `MATCHMAKING_REQUIRE_MODEL=true`.
  - `EmbeddingService._hash_embedding` (`source/recruit_system/services/cv-matching-ai/app/embeddings.py:50`): Sử dụng `@lru_cache(maxsize=2048)` để lưu trữ kết quả vector băm của các token thường gặp.
  - `graph.default_skill_graph` và `graph.skill_node_lookup` (`source/recruit_system/services/cv-matching-ai/app/graph.py:73, :80`): Áp dụng `@lru_cache(maxsize=1)` để lưu trữ đồ thị tri thức NetworkX trong bộ nhớ RAM, tránh đọc lại tệp JSON từ đĩa mỗi lần đối sánh.
- **Ưu điểm cụ thể cho HireLens:** Tối ưu hóa tối đa thời gian khởi động container Docker (startup time) của service `cv-matching-ai`. Trong quá trình vận hành, việc cache đồ thị tri thức và lookup table giúp giảm thiểu đáng kể chi phí I/O đĩa và CPU khi phục vụ hàng loạt ứng viên xem danh sách việc phù hợp cùng lúc.

### 2.5. Strategy Pattern / Multi-criteria Scoring Strategy
- **Module tham gia:** `scoring` (`source/recruit_system/services/cv-matching-ai/app/scoring.py:7, :10, :22`) kết hợp các hàm tính điểm thành phần trong `features` (`features.py:54, :81, :91, :103`).
- **Vai trò:** Cung cấp chiến lược tính điểm đa tiêu chí linh hoạt. Mỗi tiêu chí đối sánh (kỹ năng, kinh nghiệm, học vấn, ngữ cảnh) là một thuật toán trích xuất độc lập. Điểm tổng hợp được tính theo chiến lược trọng số cấu hình được (`DEFAULT_WEIGHTS = {"skill": 0.4, "experience": 0.3, "education": 0.15, "context": 0.15}`).
- **Ưu điểm cụ thể cho HireLens:** Cho phép hệ thống linh hoạt điều chỉnh chiến lược chấm điểm theo từng nhóm ngành nghề hoặc cho phép nhà tuyển dụng tùy biến trọng số trong tương lai mà không cần sửa đổi mã nguồn thuật toán cốt lõi.

### 2.6. Facade Pattern (Bộ điều phối)
- **Module tham gia:** `main` qua hàm `_run_match` (`source/recruit_system/services/cv-matching-ai/app/main.py:57`).
- **Vai trò:** Cung cấp một giao diện đơn giản duy nhất (`_run_match`) che giấu sự phức tạp của toàn bộ hệ thống con (subsystems) bên dưới gồm: chuyển đổi dữ liệu (`extraction_adapter`), chuẩn hóa (`normalize`), tra cứu đồ thị (`graph`), mã hóa vector (`embeddings`/`EmbeddingService`), trích xuất đặc trưng (`features`) và tính điểm (`scoring`).
- **Ưu điểm cụ thể cho HireLens:** Giữ cho router FastAPI (`match_without_llm`) cực kỳ gọn gàng, tách biệt hoàn toàn tầng giao thức web khỏi logic nghiệp vụ trí tuệ nhân tạo, giúp việc kiểm thử tự động (unit test) từng module độc lập trở nên thuận tiện và rõ ràng.

### 2.7. Fallback / Graceful Degradation Pattern
- **Lớp / Module tham gia:**
  - `EmbeddingService._load_model` và `_hash_embedding` (`source/recruit_system/services/cv-matching-ai/app/embeddings.py:29-60`).
  - `graph.default_skill_graph` (`source/recruit_system/services/cv-matching-ai/app/graph.py:74-77`).
- **Vai trò:** Cơ chế suy giảm tính năng nhẹ nhàng khi có sự cố. Khi mô hình SentenceTransformer không thể tải từ HuggingFace (ví dụ: máy chủ không có internet hoặc thiếu GPU/RAM), hệ thống tự động kích hoạt thuật toán băm SHA-256 nội bộ (`_hash_embedding`) để tạo vector 384 chiều thay thế mà không dừng tiến trình. Tương tự, nếu `kb_skill_graph.json` không tồn tại, hệ thống fallback về `skills_graph.json`.
- **Ưu điểm cụ thể cho HireLens:** Đảm bảo độ sẵn sàng cao (High Availability) cho hệ thống tuyển dụng. Ngay cả trong môi trường phát triển cục bộ không có kết nối internet hoặc tài nguyên hạn chế, toàn bộ quy trình Module 3 của ứng viên vẫn hoạt động thông suốt mà không trả lỗi HTTP 500.

---

## 3. Bảng truy vết phần tử -> file:dòng

| Phần tử trong Biểu đồ lớp | Loại | Nguồn truy vết (File:Dòng) |
|---|---|---|
| `View` (Package) | Package | `source/recruit_system/services/cv-matching-ai/app/main.py:18` |
| `Controller` (Package) | Package | `source/recruit_system/services/cv-matching-ai/app/main.py:57` |
| `Model` (Package) | Package | `source/recruit_system/services/cv-matching-ai/app/scoring.py:1` |
| `main` | Class («boundary») | `source/recruit_system/services/cv-matching-ai/app/main.py:41` |
| `main.app` | Attribute | `source/recruit_system/services/cv-matching-ai/app/main.py:18` |
| `main.match_without_llm` | Operation | `source/recruit_system/services/cv-matching-ai/app/main.py:91` |
| `main._run_match` | Operation | `source/recruit_system/services/cv-matching-ai/app/main.py:57` |
| `main.load_required_embedding_model` | Operation | `source/recruit_system/services/cv-matching-ai/app/main.py:41` |
| `MatchRequest` | Class («entity») | `source/recruit_system/services/cv-matching-ai/app/main.py:27` |
| `MatchRequest.candidate` | Attribute | `source/recruit_system/services/cv-matching-ai/app/main.py:28` |
| `MatchRequest.jd` | Attribute | `source/recruit_system/services/cv-matching-ai/app/main.py:29` |
| `MatchRequest.weights` | Attribute | `source/recruit_system/services/cv-matching-ai/app/main.py:30` |
| `extraction_adapter` | Class («module») | `source/recruit_system/services/cv-matching-ai/app/extraction_adapter.py:8` |
| `extraction_adapter.adapt_candidate` | Operation | `source/recruit_system/services/cv-matching-ai/app/extraction_adapter.py:40` |
| `extraction_adapter.experience_years` | Operation | `source/recruit_system/services/cv-matching-ai/app/extraction_adapter.py:28` |
| `extraction_adapter._month` | Operation | `source/recruit_system/services/cv-matching-ai/app/extraction_adapter.py:8` |
| `normalize` | Class («module») | `source/recruit_system/services/cv-matching-ai/app/normalize.py:17` |
| `normalize.ROOT` | Attribute | `source/recruit_system/services/cv-matching-ai/app/normalize.py:13` |
| `normalize.DICTIONARY_PATH` | Attribute | `source/recruit_system/services/cv-matching-ai/app/normalize.py:14` |
| `normalize.normalize_candidate` | Operation | `source/recruit_system/services/cv-matching-ai/app/normalize.py:44` |
| `normalize.normalize_jd` | Operation | `source/recruit_system/services/cv-matching-ai/app/normalize.py:67` |
| `normalize.load_skill_dictionary` | Operation | `source/recruit_system/services/cv-matching-ai/app/normalize.py:31` |
| `normalize._normalize_skills` | Operation | `source/recruit_system/services/cv-matching-ai/app/normalize.py:37` |
| `normalize._education_requirement` | Operation | `source/recruit_system/services/cv-matching-ai/app/normalize.py:80` |
| `normalize._text` | Operation | `source/recruit_system/services/cv-matching-ai/app/normalize.py:17` |
| `normalize._items` | Operation | `source/recruit_system/services/cv-matching-ai/app/normalize.py:21` |
| `features` | Class («module») | `source/recruit_system/services/cv-matching-ai/app/features.py:28` |
| `features.PARTIAL_MATCH_THRESHOLD` | Attribute | `source/recruit_system/services/cv-matching-ai/app/features.py:10` |
| `features.EDUCATION_LEVELS` | Attribute | `source/recruit_system/services/cv-matching-ai/app/features.py:11` |
| `features.extract_features` | Operation | `source/recruit_system/services/cv-matching-ai/app/features.py:111` |
| `features.skill_match_details` | Operation | `source/recruit_system/services/cv-matching-ai/app/features.py:28` |
| `features.score_skill_pair` | Operation | `source/recruit_system/services/cv-matching-ai/app/features.py:54` |
| `features.score_skill` | Operation | `source/recruit_system/services/cv-matching-ai/app/features.py:77` |
| `features.score_experience` | Operation | `source/recruit_system/services/cv-matching-ai/app/features.py:81` |
| `features.score_education` | Operation | `source/recruit_system/services/cv-matching-ai/app/features.py:91` |
| `features.score_context` | Operation | `source/recruit_system/services/cv-matching-ai/app/features.py:103` |
| `graph` | Class («module») | `source/recruit_system/services/cv-matching-ai/app/graph.py:31` |
| `graph.ROOT` | Attribute | `source/recruit_system/services/cv-matching-ai/app/graph.py:15` |
| `graph.GRAPH_PATH` | Attribute | `source/recruit_system/services/cv-matching-ai/app/graph.py:16` |
| `graph.KB_GRAPH_PATH` | Attribute | `source/recruit_system/services/cv-matching-ai/app/graph.py:17` |
| `graph._RELATION_RANK` | Attribute | `source/recruit_system/services/cv-matching-ai/app/graph.py:18` |
| `graph._BROAD_TYPES` | Attribute | `source/recruit_system/services/cv-matching-ai/app/graph.py:19` |
| `graph.default_skill_graph` | Operation | `source/recruit_system/services/cv-matching-ai/app/graph.py:74` |
| `graph.skill_node_lookup` | Operation | `source/recruit_system/services/cv-matching-ai/app/graph.py:81` |
| `graph.skill_to_node_id` | Operation | `source/recruit_system/services/cv-matching-ai/app/graph.py:90` |
| `graph.direct_relation` | Operation | `source/recruit_system/services/cv-matching-ai/app/graph.py:94` |
| `graph.skills_for_title` | Operation | `source/recruit_system/services/cv-matching-ai/app/graph.py:100` |
| `graph.graph_distance` | Operation | `source/recruit_system/services/cv-matching-ai/app/graph.py:120` |
| `graph.graph_match_score` | Operation | `source/recruit_system/services/cv-matching-ai/app/graph.py:129` |
| `graph.load_skill_graph` | Operation | `source/recruit_system/services/cv-matching-ai/app/graph.py:39` |
| `graph._load_kb_graph` | Operation | `source/recruit_system/services/cv-matching-ai/app/graph.py:52` |
| `graph.graph_key` | Operation | `source/recruit_system/services/cv-matching-ai/app/graph.py:31` |
| `scoring` | Class («module») | `source/recruit_system/services/cv-matching-ai/app/scoring.py:10` |
| `scoring.DEFAULT_WEIGHTS` | Attribute | `source/recruit_system/services/cv-matching-ai/app/scoring.py:7` |
| `scoring.validate_weights` | Operation | `source/recruit_system/services/cv-matching-ai/app/scoring.py:10` |
| `scoring.compute_final_score` | Operation | `source/recruit_system/services/cv-matching-ai/app/scoring.py:22` |
| `embeddings` | Class («module») | `source/recruit_system/services/cv-matching-ai/app/embeddings.py:66` |
| `embeddings.embedding_service` | Attribute | `source/recruit_system/services/cv-matching-ai/app/embeddings.py:63` |
| `embeddings.cosine_similarity` | Operation | `source/recruit_system/services/cv-matching-ai/app/embeddings.py:66` |
| `EmbeddingService` | Class («service») | `source/recruit_system/services/cv-matching-ai/app/embeddings.py:15` |
| `EmbeddingService.model_name` | Attribute | `source/recruit_system/services/cv-matching-ai/app/embeddings.py:19` |
| `EmbeddingService._model` | Attribute | `source/recruit_system/services/cv-matching-ai/app/embeddings.py:22` |
| `EmbeddingService._load_attempted` | Attribute | `source/recruit_system/services/cv-matching-ai/app/embeddings.py:23` |
| `EmbeddingService.__init__` | Operation | `source/recruit_system/services/cv-matching-ai/app/embeddings.py:18` |
| `EmbeddingService._load_model` | Operation | `source/recruit_system/services/cv-matching-ai/app/embeddings.py:25` |
| `EmbeddingService.encode` | Operation | `source/recruit_system/services/cv-matching-ai/app/embeddings.py:42` |
| `EmbeddingService._hash_embedding` | Operation | `source/recruit_system/services/cv-matching-ai/app/embeddings.py:50` |

---

## 4. Mâu thuẫn tài liệu và mã nguồn

1. **Khác biệt về định danh Module 3:**
   - Trong thư mục tài liệu `source/recruit_system/docs/Module3_Interview_Flow.md`, tài liệu đề tiêu đề "Module 3 Interview Flow" dùng để mô tả luồng luyện tập và phỏng vấn AI (tương ứng với service `interview-service` và `interview-ai`).
   - Tuy nhiên, trong phân rã ca sử dụng của hệ thống và bảng phân chia task dự án, **Module 3 (M3)** được xác định là "Đối sánh, xem chi tiết việc, ứng tuyển", tương ứng với nghiệp vụ của `recruitment-service` và `cv-matching-ai`.
   - *Kết luận:* Thực hiện vẽ theo đúng phạm vi nghiệp vụ được chỉ định của Module 3 (Đối sánh CV–JD) với mã nguồn tại `services/cv-matching-ai/app`.

2. **Kiến trúc Monolith trong tài liệu cũ vs Microservices trong mã nguồn:**
   - Báo cáo đồ án ban đầu (bản v6) mô tả một backend monolith Spring Boot kết nối trực tiếp CSDL MySQL duy nhất.
   - Mã nguồn thực tế tại commit `1c96706` đã tách hoàn chỉnh thành kiến trúc Microservices với 3 dịch vụ AI FastAPI độc lập. Dịch vụ `cv-matching-ai` chạy cổng riêng (8002 trên host, 8000 trong container), giao tiếp hoàn toàn qua HTTP REST JSON.
   - *Kết luận:* Thiết kế biểu đồ lớp tuân thủ 100% kiến trúc microservices thực tế trong mã nguồn.

3. **Cơ chế gọi Batch vs Single Match:**
   - Service `cv-matching-ai` cung cấp endpoint `/match_batch` (`main.py:95`) có sử dụng `hybrid_retrieve` (BM25 kết hợp vector dense embedding trong `retrieval.py`).
   - Tuy nhiên, trong luồng nghiệp vụ thực tế của Module 3 (`MatchingService.java:56-57` và `CvMatchingModule.java:18`), hệ thống duyệt tuần tự danh sách công việc `PUBLISHED` và gọi API `/match/no-llm` cho từng cặp (candidate, job). Do đó, `retrieval.py` và `hybrid_retrieve` không tham gia vào luồng hoạt động M3 và không được đưa vào biểu đồ lớp theo đúng quy tắc giới hạn phạm vi.

4. **Sử dụng LLM trong giải thích đối sánh:**
   - Trong `explain.py`, hệ thống có hàm `explain_match` gọi đến OpenAI API (`gpt-4o-mini`).
   - Nhưng trong luồng Module 3, `MatchingService` gọi `/match/no-llm`, hàm `_run_match(request, use_llm=False)` sinh trực tiếp giải thích tất định qua template nội bộ mà không gọi `explain.py`. Do đó, `explain.py` được loại bỏ khỏi biểu đồ lớp này.

---

## 5. Câu hỏi mở / Cần xác nhận

1. `[cần xác nhận]` Trong tương lai có dự định cho phép ứng viên chọn giải thích đối sánh bằng mô hình ngôn ngữ lớn (gọi `/match` kèm OpenAI API) trong luồng xem danh sách việc phù hợp hay cố định sử dụng giải thích tất định qua `/match/no-llm` để tối ưu chi phí và độ trễ?
2. `[cần xác nhận]` Đồ thị kỹ năng và từ điển kỹ năng hiện tại đọc từ tệp JSON tĩnh lưu cục bộ (`data/kb_skill_graph.json`, `data/skills_dictionary.json`). Hệ thống có kế hoạch đồng bộ động với bảng `skills` trong CSDL `hirelens_recruitment` khi quản trị viên thêm kỹ năng mới hay không?

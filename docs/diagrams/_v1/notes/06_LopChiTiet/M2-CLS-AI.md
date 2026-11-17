# M2-CLS-AI — Biểu đồ lớp chi tiết: Dịch vụ AI trích xuất CV (cv-extraction-ai)

## Tổng quan phạm vi và kiến trúc

Dịch vụ `cv-extraction-ai` là một microservice độc lập được xây dựng bằng Python và FastAPI (cổng 8001), chịu trách nhiệm thực thi tác vụ AI bóc tách thông tin từ văn bản CV (Node N10 trong `M2-ACT`). Dịch vụ này tiếp nhận yêu cầu từ `recruitment-service` qua endpoint `POST /api/v1/extract-cv?include=kg`, điều phối việc sinh JSON qua mô hình ngôn ngữ lớn (Qwen-1.7B finetuned định dạng GGUF / llama.cpp), đối soát và chuẩn hóa dữ liệu qua pipeline hậu xử lý (post-processing), và làm giàu tri thức thông qua Knowledge Graph (chuẩn hóa kỹ năng, suy diễn kỹ năng ngầm định `implied_skills`, chuẩn hóa trường đại học).

Theo đúng quy tắc mô hình hóa mã nguồn Python sang UML Class Diagram:
- Các lớp Python thực thụ (`class Ten`) được giữ đúng tên và chính tả như trong mã nguồn.
- Các module Python chỉ chứa tập hàm chức năng (functional module) được đặt tên theo đúng tên module thực tế của file (`routes`, `generator`, `continuation`, `json_parse`, `pipeline`, `enrich`, `normalize`), mang stereotype `«module»` (riêng tuyến định tuyến FastAPI `routes` mang stereotype `«boundary»`).
- Các lược đồ dữ liệu Pydantic, dataclass và cấu trúc đồ thị mang stereotype `«entity»` trong tầng Model.
- Các bộ điều phối nghiệp vụ và đối tượng quản lý trạng thái/giám sát mang stereotype `«control»` hoặc `«module»` trong tầng Controller.

Biểu đồ bao gồm 17 phần tử lớp/module phân bổ trên 3 package chính (`View`, `Controller`, `Model`), tuân thủ giới hạn ≤ 18 phần tử lớp.

---

## 1. Diễn giải vai trò từng lớp và module

### 1.1. Tầng View (Boundary)
- **`routes`** (`app/api/routes.py:26`): Module định tuyến API của FastAPI (stereotype `«boundary»`). Tiếp nhận HTTP request `POST /api/v1/extract-cv`, xác thực tham số truy vấn (`include: kg, raw`), kiểm tra tính hợp lệ của văn bản CV đầu vào, kiểm tra trạng thái nạp của mô hình AI (`state.engine`), và điều phối chuỗi xử lý qua các module/dịch vụ tầng Controller trước khi đóng gói trả về HTTP response.

### 1.2. Tầng Controller (Control / Module)
- **`generator`** (`app/services/generator.py:29`): Module điều phối suy luận AI chính (stereotype `«module»`). Quản lý khóa đồng bộ `_lock` (`threading.Lock`) để tuần tự hóa các yêu cầu vào GPU, xây dựng prompt ChatML (`build_prompt`), đếm số lượng token (`count_prompt_tokens`), kiểm tra giới hạn context window, và kích hoạt động cơ sinh văn bản theo luồng (`_generate_llama` hoặc `_generate_transformers`).
- **`ModelState`** (`app/services/model_loader.py:14`): Lớp đối tượng singleton nắm giữ trạng thái nạp và đối tượng thực thi của mô hình học máy (instance `Llama` của `llama_cpp` hoặc `model`/`tokenizer` của PyTorch Hugging Face), đường dẫn trọng số GGUF, số token ngữ cảnh và lý do fallback nếu có.
- **`LoopGuard`** (`app/services/loop_guard.py:14`): Lớp giám sát luồng sinh token theo thời gian thực (stream-level guard). Phát hiện và cắt ngắn chuỗi sinh ngay lập tức khi mô hình rơi vào trạng thái suy biến (vòng lặp vô hạn chuỗi ký tự hoặc lặp lại một giá trị quá số lần cấu hình).
- **`continuation`** (`app/services/continuation.py:20`): Module xử lý hoàn thiện khi output bị cắt cụt do chạm ngưỡng `MAX_NEW_TOKENS` hoặc do `LoopGuard` ngắt (stereotype `«module»`). Phân tích điểm dừng hợp lệ cuối cùng trong chuỗi JSON, mớm lại tiền tố để kích hoạt lần sinh thứ hai (`_continue_llama`), sau đó hợp nhất dữ liệu hai lần sinh (`merge_outputs`).
- **`json_parse`** (`app/utils/json_parse.py:11`): Module phân tích cú pháp JSON linh hoạt (stereotype `«module»`). Xóa bỏ thẻ suy nghĩ `</think>`, bóc tách khối mã markdown ````json ````, phân tích chuỗi JSON, và tích hợp cơ chế sửa lỗi cú pháp (`json_repair`) nhằm khắc phục các lỗi định dạng nhỏ do mô hình sinh ra.
- **`pipeline`** (`app/postprocess/pipeline.py:48`): Module đường ống hậu xử lý dữ liệu (stereotype `«module»`). Điều phối dữ liệu JSON trích xuất qua chuỗi 5 bước tuần tự: chuẩn hóa khóa schema (`normalize_profile`), làm sạch danh sách kỹ năng (`clean_skill_list`), đối soát thực thể với văn bản CV gốc (`ground_profile`), chuẩn hóa thứ tự ngày tháng (`fix_date_order`), và lọc bỏ thông tin rác (`cleanup_profile`).
- **`enrich`** (`app/kg/enrich.py:94`): Module làm giàu dữ liệu qua đồ thị tri thức (Knowledge Graph, stereotype `«module»`). Tra cứu kỹ năng xuất hiện trong văn bản CV qua `CandidateSkillFinder`, suy diễn các kỹ năng ngầm định dựa trên các cạnh quan hệ tiên quyết (`REQUIRES`) và thành phần (`PART_OF`) trong đồ thị `KnowledgeBase`, đồng thời gán nhãn cảnh báo (`flags`) khi phát hiện bất thường.
- **`normalize`** (`app/kb/normalize.py:11`): Module chuẩn hóa định danh thực thể (stereotype `«module»`). Thay thế tên kỹ năng và trường học do LLM sinh ra bằng tên chuẩn tắc (canonical name) được định nghĩa trong cơ sở tri thức thông qua liên kết thực thể (`SkillLinker` và `KnowledgeBase.link_school`).
- **`SkillLinker`** (`app/kb/linker.py:30`): Lớp liên kết thực thể kỹ năng dựa trên cấu trúc bộ nhớ. Thực hiện khớp kỹ năng đa cấp độ: khớp chính xác bề mặt (`exact`), khớp khóa chuẩn hóa không dấu (`normalized`), xử lý biến thể từ vựng/phiên bản (`variant`), tách ghép từ phức (`split`), và đối soát xấp xỉ (`fuzzy` bằng thư viện `rapidfuzz`).
- **`CandidateSkillFinder`** (`app/kb/candidates.py:15`): Lớp tìm kiếm kỹ năng ứng viên tối ưu trên toàn bộ văn bản thô của CV. Sử dụng kết hợp Regular Expression cho chuỗi ngắn (nhạy chữ hoa/thường để tránh nhận nhầm như "C", "R") và Regex theo lô (batch) cho chuỗi dài không dấu, sắp xếp theo thứ tự xuất hiện đầu tiên trong văn bản.

### 1.3. Tầng Model (Entity / DTO / Tri thức)
- **`CVRequest`** (`app/schemas/cv.py:4`): Mô hình dữ liệu Pydantic đại diện cho request body gửi đến từ `recruitment-service`, chứa trường văn bản thô `cv_text`.
- **`CVResponse`** (`app/schemas/cv.py:8`): Mô hình dữ liệu Pydantic đại diện cho response body trả về, chứa trường từ điển `data` bao gồm các mục thông tin hồ sơ đã qua xử lý.
- **`GenerationResult`** (`app/services/generator.py:20`): Dataclass chứa toàn bộ kết quả của tiến trình suy luận từ mô hình LLM, bao gồm văn bản sinh ra (`text`), cờ cắt cụt (`truncated`), lý do ngắt (`reason`), số lượng token sinh (`output_tokens`), và trạng thái tiếp tục sinh (`continued`).
- **`PostprocessStats`** (`app/postprocess/pipeline.py:21`): Dataclass tổng hợp định lượng các thao tác làm sạch dữ liệu trong pipeline (số khóa đổi tên, số kỹ năng làm sạch, số liên hệ bị hủy vì không có trong văn bản, số ngày đảo thứ tự...).
- **`KnowledgeBase`** (`app/kb/store.py:20`): Dataclass lưu trữ toàn bộ mạng tri thức trong bộ nhớ RAM, gồm bảng định danh kỹ năng (`skills`), các cạnh quan hệ tri thức (`edges`), ánh xạ bí danh trường đại học (`school_alias`), danh sách trường đại học chuẩn (`universities`), và liên kết kỹ năng liên quan (`related`).
- **`Link`** (`app/kb/linker.py:21`): Dataclass thể hiện một kết quả liên kết thực thể kỹ năng, lưu trữ chuỗi gốc (`raw`), mã định danh kỹ năng (`skill_id`), tên chuẩn tắc (`name`), phân loại (`category`), phương thức khớp (`method`), và điểm tin cậy (`score`).

---

## 2. Luồng gọi chính (Trích xuất CV)

1. `recruitment-service` (`CvExtractionModule` / `AiJsonClient`) gửi HTTP POST đến `/api/v1/extract-cv?include=kg` với body `{"cv_text": "..."}`.
2. `routes.extract_cv` nhận request, khởi tạo mã định danh truy vết `request_id`, kiểm tra `ModelState.engine` (trả về lỗi 503 nếu mô hình chưa sẵn sàng), và chuẩn hóa khoảng trắng văn bản bằng `clean_cv_text`.
3. `routes` gọi `generator.generate_cv_result(cv_text)`:
   - `generator` xin chiếm giữ `_lock` (nếu chờ quá 30 giây thì ném ngoại lệ `ModelBusyError`).
   - Xây dựng prompt ChatML qua `build_prompt` và kiểm tra độ dài token bằng `count_prompt_tokens` (nếu vượt quá context budget sẽ ném ngoại lệ `InputTooLongError`).
   - Kích hoạt suy luận `_generate_llama`: đọc luồng token, truyền từng ký tự qua `LoopGuard.feed`. Nếu `LoopGuard` phát hiện lặp bất thường thì ngắt luồng.
   - Nếu output bị ngắt sớm, gọi `continuation.plan_continuation` để sinh tiếp phần đuôi và gộp qua `merge_outputs`.
4. `routes` chuyển `raw_output` sang `json_parse.extract_json` để bóc tách đối tượng JSON.
5. `routes` gọi `pipeline.postprocess(data, cv_text)`:
   - Chuẩn hóa tên trường, ép kiểu số (start_year, end_year, team_size).
   - Làm sạch danh sách kỹ năng, đối soát thực thể với văn bản gốc (`ground_profile`), và sắp xếp lại mốc thời gian kinh nghiệm.
   - Thu thập kết quả thống kê vào `PostprocessStats`.
6. `routes` gọi `enrich.enrich(data, kb, pp_stats, cv_text)`:
   - Tạo hoặc lấy `CandidateSkillFinder` từ cache bộ nhớ của `KnowledgeBase`.
   - Tìm kiếm các kỹ năng xuất hiện trong văn bản CV và suy diễn kỹ năng ngầm định (`implied_skills`) từ đồ thị `kb.edges`.
7. `routes` gọi `normalize.normalize_profile_with_kb(base, kb)`:
   - Chuẩn hóa danh sách kỹ năng qua `SkillLinker.link_many`.
   - Chuẩn hóa tên trường học qua `KnowledgeBase.link_school`.
8. `routes` đóng gói dữ liệu hoàn chỉnh vào cấu trúc dictionary và trả về phản hồi theo lược đồ `CVResponse`.

---

## 3. Các mẫu thiết kế (Design Patterns) thực tế trong mã nguồn

### 3.1. Singleton Pattern
- **Lớp / Đối tượng tham gia:** 
  - `ModelState` và biến toàn cục `state = ModelState()` (`source/recruit_system/services/cv-extraction-ai/app/services/model_loader.py:25`).
  - `kb_state` dictionary toàn cục nắm giữ instance `KnowledgeBase` duy nhất (`source/recruit_system/services/cv-extraction-ai/app/kb/store.py:383`).
- **Ưu điểm cho HireLens:** 
  - Mô hình ngôn ngữ lớn Qwen GGUF và đồ thị tri thức có dung lượng bộ nhớ RAM/VRAM đáng kể (~1.5GB đến 4GB). Singleton đảm bảo mô hình và cơ sở tri thức chỉ nạp vào bộ nhớ duy nhất một lần tại thời điểm khởi động server (`startup event`), tránh việc nạp lại tốn tài nguyên và giảm thời gian xử lý mỗi request từ 15-20 giây xuống còn mức thời gian thực của GPU inference.

### 3.2. Data Transfer Object (DTO) Pattern
- **Lớp tham gia:**
  - `CVRequest`, `CVResponse` (`source/recruit_system/services/cv-extraction-ai/app/schemas/cv.py:4, 8`).
  - `GenerationResult` (`source/recruit_system/services/cv-extraction-ai/app/services/generator.py:20`).
  - `PostprocessStats` (`source/recruit_system/services/cv-extraction-ai/app/postprocess/pipeline.py:21`).
  - `Link` (`source/recruit_system/services/cv-extraction-ai/app/kb/linker.py:21`).
- **Ưu điểm cho HireLens:**
  - Tách bạch cấu trúc giao tiếp mạng (HTTP API) và dữ liệu trung gian giữa các tầng xử lý nội bộ. Tự động hóa kiểm tra kiểu dữ liệu đầu vào tại ranh giới API của FastAPI, đồng thời đóng gói trạng thái sinh văn bản và số liệu thống kê làm sạch một cách chặt chẽ.

### 3.3. Pipeline Pattern (Pipes and Filters)
- **Module tham gia:**
  - `pipeline` (`source/recruit_system/services/cv-extraction-ai/app/postprocess/pipeline.py:48-57`).
- **Ưu điểm cho HireLens:**
  - Các mô hình sinh văn bản thường tạo ra các định dạng không đồng nhất hoặc ảo giác (hallucination). Việc phân rã tiến trình làm sạch thành một chuỗi các filter độc lập tuần tự (`normalize_profile` → `clean_skill_list` → `ground_profile` → `fix_date_order` → `cleanup_profile`) giúp mã nguồn dễ bảo trì, dễ viết kiểm thử đơn vị độc lập cho từng quy tắc làm sạch, và dễ mở rộng các bộ lọc nghiệp vụ mới mà không ảnh hưởng tới tiến trình suy luận chính.

### 3.4. Strategy Pattern / Fallback Strategy
- **Module / Lớp / Hàm tham gia:**
  - Chiến lược suy luận mô hình: `generator._generate_llama` (GGUF qua llama.cpp) và `generator._generate_transformers` (PyTorch Hugging Face) (`source/recruit_system/services/cv-extraction-ai/app/services/generator.py:43, 156, 229`).
  - Chiến lược nạp cơ sở tri thức: `KnowledgeBase.from_neo4j`, `KnowledgeBase.from_db`, và `KnowledgeBase.from_csv` (`source/recruit_system/services/cv-extraction-ai/app/kb/store.py:340-381`).
- **Ưu điểm cho HireLens:**
  - Cung cấp cơ chế linh hoạt tối đa khi triển khai trên nhiều môi trường: ưu tiên sử dụng cấu hình phần cứng tối ưu nhất (GPU offload 99 layers với GGUF; đồ thị Neo4j/Postgres cho truy vấn phân tán), nhưng có khả năng tự động hạ cấp (fallback) sang CPU/PyTorch hoặc nạp từ file CSV tĩnh trong seed data khi thiếu các dịch vụ hạ tầng phụ trợ, bảo đảm hệ thống AI không bao giờ bị dừng hoạt động hoàn toàn.

### 3.5. Guard / Interceptor Pattern
- **Lớp tham gia:**
  - `LoopGuard` (`source/recruit_system/services/cv-extraction-ai/app/services/loop_guard.py:14`).
- **Ưu điểm cho HireLens:**
  - Can thiệp trực tiếp vào luồng stream ký tự ngay khi mô hình đang sinh dữ liệu. Khi gặp các trường hợp CV dị biệt khiến mô hình lặp từ bất tận hoặc sinh một chuỗi dài quá mức (`> 2000 ký tự`), `LoopGuard` chủ động ngắt sớm, giúp bảo vệ tài nguyên tính toán GPU, tránh nghẽn hàng đợi suy luận và đảm bảo thời gian phản hồi cho các ứng viên khác.

### 3.6. Facade Pattern
- **Module tham gia:**
  - `enrich.enrich` (`source/recruit_system/services/cv-extraction-ai/app/kg/enrich.py:94`).
  - `normalize.normalize_profile_with_kb` (`source/recruit_system/services/cv-extraction-ai/app/kb/normalize.py:11, 50`).
- **Ưu điểm cho HireLens:**
  - Đóng gói toàn bộ các thao tác tra cứu đồ thị phức tạp (quét regex, tra cứu cạnh quan hệ, chuẩn hóa danh xưng trường đại học, đối soát mờ fuzzy matching) đằng sau hai hàm nghiệp vụ đơn giản. Tuyến định tuyến `routes` chỉ cần truyền dữ liệu thô và nhận lại cấu trúc đã làm giàu mà không cần quan tâm đến cách thức duyệt đồ thị hay cấu trúc lưu trữ nội tại của tri thức.

### 3.7. Concurrency Guard / Critical Section (Đồng bộ hóa)
- **Cơ chế tham gia:**
  - `_lock = threading.Lock()` trong module `generator` (`source/recruit_system/services/cv-extraction-ai/app/services/generator.py:16, 219`).
- **Ưu điểm cho HireLens:**
  - Vì mô hình ngôn ngữ chạy trên GPU đòi hỏi gần như toàn bộ tài nguyên VRAM trong quá trình tính toán attention matrix, việc nhiều request truy cập đồng thời vào context của mô hình có thể dẫn đến lỗi phân bổ bộ nhớ CUDA (Out-Of-Memory). Khóa `_lock` kết hợp hàng đợi chờ có thời hạn timeout (`QUEUE_WAIT_SECONDS = 30s`) giúp đảm bảo an toàn tuyệt đối cho GPU khi có tải cao đột biến từ ứng viên tải CV lên cùng lúc.

---

## 4. Bảng truy vết phần tử → nguồn mã nguồn

| Phần tử | Loại | Stereotype | Gói | Tệp nguồn và dòng tham chiếu |
|---|---|---|---|---|
| `View` | package | — | — | `source/recruit_system/services/cv-extraction-ai/app/api/routes.py:20` |
| `Controller` | package | — | — | `source/recruit_system/services/cv-extraction-ai/app/services/generator.py:1` |
| `Model` | package | — | — | `source/recruit_system/services/cv-extraction-ai/app/schemas/cv.py:1` |
| `routes` | class | boundary | View | `source/recruit_system/services/cv-extraction-ai/app/api/routes.py:26` |
| `CVRequest` | class | entity | Model | `source/recruit_system/services/cv-extraction-ai/app/schemas/cv.py:4` |
| `CVResponse` | class | entity | Model | `source/recruit_system/services/cv-extraction-ai/app/schemas/cv.py:8` |
| `generator` | class | module | Controller | `source/recruit_system/services/cv-extraction-ai/app/services/generator.py:29` |
| `GenerationResult` | class | entity | Model | `source/recruit_system/services/cv-extraction-ai/app/services/generator.py:20` |
| `ModelState` | class | control | Controller | `source/recruit_system/services/cv-extraction-ai/app/services/model_loader.py:14` |
| `LoopGuard` | class | control | Controller | `source/recruit_system/services/cv-extraction-ai/app/services/loop_guard.py:14` |
| `continuation` | class | module | Controller | `source/recruit_system/services/cv-extraction-ai/app/services/continuation.py:20` |
| `json_parse` | class | module | Controller | `source/recruit_system/services/cv-extraction-ai/app/utils/json_parse.py:11` |
| `pipeline` | class | module | Controller | `source/recruit_system/services/cv-extraction-ai/app/postprocess/pipeline.py:48` |
| `PostprocessStats` | class | entity | Model | `source/recruit_system/services/cv-extraction-ai/app/postprocess/pipeline.py:21` |
| `enrich` | class | module | Controller | `source/recruit_system/services/cv-extraction-ai/app/kg/enrich.py:94` |
| `normalize` | class | module | Controller | `source/recruit_system/services/cv-extraction-ai/app/kb/normalize.py:11` |
| `KnowledgeBase` | class | entity | Model | `source/recruit_system/services/cv-extraction-ai/app/kb/store.py:20` |
| `SkillLinker` | class | control | Controller | `source/recruit_system/services/cv-extraction-ai/app/kb/linker.py:30` |
| `Link` | class | entity | Model | `source/recruit_system/services/cv-extraction-ai/app/kb/linker.py:21` |
| `CandidateSkillFinder` | class | control | Controller | `source/recruit_system/services/cv-extraction-ai/app/kb/candidates.py:15` |

---

## 5. Mâu thuẫn giữa tài liệu và mã nguồn, các điểm cần xác nhận

- **Mâu thuẫn kiến trúc monolith vs microservices:** Báo cáo đồ án v6 (IT_Recruitment_v6.pdf) ban đầu phác thảo hệ thống như một ứng dụng đơn khối backend phục vụ trực tiếp. Tuy nhiên, mã nguồn thực tế tại commit `1c96706` đã tách hẳn dịch vụ AI thành tiến trình Python riêng biệt (`cv-extraction-ai` chạy cổng 8001) với chuỗi xử lý LLM chuyên sâu và đồ thị tri thức in-memory. Toàn bộ thiết kế lớp trên đây tuân thủ 100% mã nguồn thực tế.
- **Mô hình hóa module Python chỉ chứa hàm:** Để tuân thủ nguyên tắc "tên đúng như source" và không bịa đặt các lớp kiểu "XxxService" hay "XxxGenerator", các file Python chỉ chứa hàm (`routes.py`, `generator.py`, `continuation.py`, `json_parse.py`, `pipeline.py`, `enrich.py`, `normalize.py`) được mô hình hóa thành các phần tử UML mang tên chính xác của module, stereotype `«module»` (hoặc `«boundary»` cho route) và chứa các hàm thực tế kèm type hints.
- **[cần xác nhận] Cấu hình môi trường chạy mô hình AI:** Hệ thống ưu tiên nạp GGUF 4-bit thông qua thư viện `llama-cpp-python` với tùy chọn offload 100% 99 tầng vào GPU (`n_gpu_layers=99`). Khi triển khai trên môi trường máy chủ không có card đồ họa chuyên dụng (chạy fallback sang Hugging Face Transformers trên CPU), thời gian suy luận có thể tăng đột biến. Cần xác nhận tiêu chuẩn hạ tầng triển khai thực tế để có phương án cấu hình `CONTEXT_TOKENS` và `QUEUE_WAIT_SECONDS` phù hợp.
- **[cần xác nhận] Mức độ ứng dụng của Knowledge Graph enrichment ở Backend:** Khi `recruitment-service` gọi AI với `include=kg`, dịch vụ AI trả về bổ sung các trường `implied_skills`, `skills_normalized`, và `school_normalized`. Cần xác nhận phía `recruitment-service` đã sử dụng các trường làm giàu này vào thuật toán chấm điểm đối sánh matching hay hiện tại mới chỉ lưu trữ dạng các dòng EAV trong bảng `cv_data`.

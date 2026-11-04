# AI Service - CV Information Extraction

Dịch vụ trích xuất thông tin CV (CV Parsing) ứng dụng Mô hình Ngôn ngữ Lớn (**Qwen3-1.7B**) đã được tinh chỉnh (Fine-tuned) với kỹ thuật LoRA và hỗ trợ lượng tử hóa **GGUF Q4_K_M** (chạy bằng `llama.cpp` hoặc `transformers`).

---

## 📂 Cấu trúc thư mục

```
ai-service/
├── checkpoint-250/             # Trọng số LoRA adapter (~78MB, đã có sẵn trong repo)
│   ├── adapter_config.json
│   ├── adapter_model.safetensors
│   ├── chat_template.jinja
│   ├── tokenizer.json
│   └── tokenizer_config.json
├── merged_model/               # Thư mục chứa file GGUF lượng tử hóa (tùy chọn)
│   └── .gitkeep
├── fine_tune_qwen3-1.7B.ipynb  # Notebook quy trình huấn luyện LoRA
├── run_on_colab.ipynb          # Notebook chạy thử nghiệm inference trên Google Colab
├── main.py                     # Entry point (shim): `uvicorn main:app`
├── app/
│   ├── main.py                 # Khởi tạo FastAPI, include router, load model khi startup
│   ├── api/routes.py           # /health, /api/v1/extract-cv
│   ├── core/                   # config.py (env), logging.py
│   ├── schemas/cv.py           # CVRequest, CVResponse
│   ├── services/               # model_loader, prompt, generator
│   └── utils/                  # text.py (clean_cv_text), json_parse.py (extract_json)
├── requirements.txt            # Danh sách thư viện Python cần thiết
└── README.md
```

---

## 🚀 Hướng Dẫn Cài Đặt & Chạy Service

### 1. Yêu cầu tiên quyết
- Python 3.10 trở lên.
- Đã cài đặt `pip` và `virtualenv`.
- Thư viện phụ thuộc mới: `rapidfuzz` (hỗ trợ fuzzy matching grounding cho tầng hậu kiểm), `psycopg[binary]` (kết nối PostgreSQL Knowledge Base).

### 2. Thiết lập môi trường ảo
```bash
cd ai-service

# Tạo môi trường ảo
python3 -m venv .venv

# Kích hoạt môi trường ảo
# Trên Linux/macOS:
source .venv/bin/activate
# Trên Windows:
# .venv\Scripts\activate

# Cài đặt các thư viện phụ thuộc
pip install -r requirements.txt
```

### 3. Biến môi trường (tùy chọn, tất cả có giá trị mặc định)

| Biến | Mặc định | Mô tả |
|---|---|---|
| `BASE_MODEL_NAME` | `unsloth/Qwen3-1.7B` | Base model dùng khi fallback `transformers` + LoRA |
| `LORA_PATH` | `./checkpoint-250` | Thư mục LoRA adapter |
| `GGUF_MODEL_PATH` | `./merged_model/model-qwen3-1.7b-q4_k_m.gguf` | Đường dẫn file GGUF; nếu không tồn tại thì tự dò file `*.gguf` trong `merged_model/` |
| `CONTEXT_TOKENS` | `8192` | Context window; nếu chưa set thì fallback sang `MAX_INPUT_TOKENS` |
| `MAX_INPUT_TOKENS` | `8192` | Giá trị fallback cũ của `CONTEXT_TOKENS` |
| `MAX_NEW_TOKENS` | `1500` | Giới hạn số token sinh ra cho mỗi request |
| `QUEUE_WAIT_SECONDS` | `30` | Thời gian tối đa chờ hàng đợi trước khi trả `503` "bận" |
| `POSTPROCESS_ENABLED` | `true` | Bật/tắt tầng hậu kiểm grounding (`0`/`false`/`no`/`off` để tắt — phục vụ ablation) |
| `KG_ENABLED` | `true` | Bật/tắt tầng làm giàu KG (`0`/`false`/`no`/`off` để tắt) |
| `KB_DSN` | unset | Connection string PostgreSQL KB (ví dụ: `postgresql://user:pass@host:5433/recruit_kb`) |
| `KB_SEED_DIR` | `./kb/seed` | Thư mục chứa các file seed CSV dùng khi offline hoặc fallback |
| `LOG_CV_CONTENT` | tắt | Đặt `1`/`true`/`yes`/`on` để log nội dung CV và raw output của model |

---

## 🧪 Chạy Test

```bash
cd ai-service
pip install -r requirements-dev.txt
python -m pytest -q
```

---

## ⚙️ Các Chế Độ Chạy Inference

Dịch vụ hỗ trợ **2 cơ chế suy luận** (tự động phát hiện khi khởi động `main.py`):

### 🔹 Cách 1: Chạy trực tiếp bằng LoRA Adapter (Mặc định - Sẵn sàng ngay sau khi clone)
- Thư mục `checkpoint-250/` đã chứa đầy đủ adapter và tokenizer.
- Khi khởi chạy, hệ thống sẽ tự động tải base model `unsloth/Qwen3-1.7B` từ Hugging Face và áp dụng LoRA adapter.
- **Lệnh khởi chạy:**
  ```bash
  python3 main.py
  # Hoặc: uvicorn main:app --host 0.0.0.0 --port 8000
  ```

### 🔹 Cách 2: Chạy tối ưu hóa với GGUF qua llama.cpp (Nhanh hơn, tiết kiệm RAM)
- **Yêu cầu:** `llama-cpp-python` (đã có trong `requirements.txt`; bản mặc định chỉ chạy CPU, muốn chạy GPU thì cài lại bản CUDA):
  ```bash
  pip install llama-cpp-python
  # Nếu dùng GPU NVIDIA (CUDA):
  CMAKE_ARGS="-DGGML_CUDA=on" pip install llama-cpp-python
  ```
- Do file GGUF (`model-qwen3-1.7b-q4_k_m.gguf` ~ 1.11 GB) vượt quá hạn mức 100MB của GitHub nên file này không được push trực tiếp lên repo.
- **Cách sử dụng:**
  1. Tải file `model-qwen3-1.7b-q4_k_m.gguf` từ link lưu trữ chia sẻ của dự án (Google Drive / Hugging Face).
  2. Đặt file vào thư mục `ai-service/merged_model/`:
     ```
     ai-service/merged_model/model-qwen3-1.7b-q4_k_m.gguf
     ```
  3. Khởi chạy: `python3 main.py`. Hệ thống sẽ tự động ưu tiên nạp GGUF và chạy qua engine `llama.cpp`.
- **Tự động nhận file GGUF:** nếu `GGUF_MODEL_PATH` không trỏ tới file tồn tại, service tự động dùng file `*.gguf` duy nhất trong `merged_model/`. Có nhiều hơn một file `.gguf` thì phải đặt `GGUF_MODEL_PATH` rõ ràng (không nạp được sẽ fallback sang `transformers` + LoRA).
- **Khi GGUF không được dùng** (thiếu file, chưa cài `llama-cpp-python`, lỗi nạp), `/health` báo `fallback_reason` kèm lý do.

---

## 📡 API Endpoints

### 1. Trích xuất thông tin CV
- **Method:** `POST`
- **URL:** `http://localhost:8000/api/v1/extract-cv`
- **Headers:** `Content-Type: application/json`
- **Request Body:**
  ```json
  {
    "cv_text": "Họ và tên: Nguyễn Văn A\nEmail: anguyen@example.com\nSố điện thoại: 0912345678\nKỹ năng: Java, Spring Boot, PostgreSQL..."
  }
  ```
- **Response:** `{"data": {...}}`, trong đó `data` gồm: `personal_info`, `objective`, `education`, `experience`, `personal_projects`, `skills`, `certificates`, `honours`, `languages`, kèm các trường làm giàu KG khi bật (`skills_normalized`, `implied_skills`, `flags`, và `school_normalized` trong `education`).
- **Header:** mọi response của endpoint này đều kèm `X-Request-ID: <12 hex>`.
- **Lỗi** (xem `specs/001-harden-ai-serving/contracts/extract-cv.md`):

  | Status | Khi nào | `detail` |
  |---|---|---|
  | `400` | `cv_text` rỗng/khoảng trắng | `cv_text không được rỗng` |
  | `413` | prompt tokens + output budget vượt context | `CV quá dài: <n> token, tối đa <max> token` |
  | `503` | model chưa load | `Model chưa được load` |
  | `503` | chờ xử lý quá `QUEUE_WAIT_SECONDS` | `Service đang bận, vui lòng thử lại sau` |
  | `500` | lỗi nội bộ (không lộ chi tiết exception) | `Trích xuất CV thất bại (request_id=<id>)` |

---

## 🧹 Hậu Kiểm (Post-processing)

Dịch vụ áp dụng tầng hậu kiểm (grounding) chạy ngay sau bước trích xuất JSON (`extract_json -> postprocess -> response`) nhằm loại bỏ ảo giác (hallucination) và chuẩn hóa dữ liệu:

- **Luồng xử lý**: `extract_json` → `postprocess` → `enrich` (nếu bật KG) → trả về `response`.
- **Các luật xử lý**:
  - **Chuẩn hoá khoá & kiểu**: Chuẩn hoá tên khoá alias (`honors` → `honours`, `certifications` → `certificates`, `projects` → `personal_projects`...), hoàn thiện schema với giá trị mặc định, ép kiểu dữ liệu (chuyển `description` chuỗi thành danh sách gạch đầu dòng, `team_size` thành số nguyên).
  - **Làm sạch kỹ năng (skills)**: Cắt bỏ nhãn nhóm tiền tố (ví dụ: `"Backend: Spring Boot"` → `"Spring Boot"`), loại bỏ ký tự phân tách dư thừa, deduplicate không phân biệt hoa thường và giữ nguyên thứ tự xuất hiện đầu tiên. Áp dụng tương tự cho `tech_stack` của dự án.
  - **Grounding thực thể**: Đối chiếu tên `company`, `school`, `project` với văn bản CV gốc. Nếu khớp mờ (fuzzy match) đạt điểm $\ge 85$, tự động snap (thay thế) về nguyên văn trong CV; nếu không tìm thấy căn cứ trong CV, mục đó sẽ bị loại bỏ.
  - **Kiểm tra thông tin liên hệ (contact)**: Đặt thành `null` đối với `email`, `github_url` và `phone` (so khớp chuỗi chữ số) nếu không xuất hiện trong CV; `full_name` bị `null` nếu fuzzy match $< 85$.
  - **Loại bỏ thông tin không có căn cứ**: Bỏ các mục trong `certificates`, `honours`, `languages` (theo tên ngôn ngữ hoặc ghi chú) và gán `objective` thành `null` nếu không có bằng chứng xuất hiện trong CV.
  - **Kiểm tra hợp lệ kinh nghiệm (type check experience)**: Loại bỏ các kinh nghiệm có chức danh là học viên/sinh viên (`sinh viên`, `student`, `học viên`), hoặc công ty là trường học/viện đào tạo nhưng chức danh không phải vai trò giảng dạy/nhân sự.
  - **Gộp bullet vào project**: Nếu một kinh nghiệm bị loại bỏ do không đạt grounding nhưng tên công ty chứa tên của một dự án cá nhân đã có, các dòng mô tả (bullets) của kinh nghiệm đó sẽ được gộp vào mô tả của dự án tương ứng.
- **Quy ước Response & Log**:
  - Response giữ nguyên cấu trúc schema (`CandidateProfile`), tuy nhiên các giá trị có thể bị sửa (snap về nguyên văn CV) hoặc bị loại bỏ/gán `null`.
  - Log an toàn dữ liệu: chỉ ghi lại số đếm các thao tác (số mục bị loại bỏ, số tên được snap, số contact bị null...), tuyệt đối không ghi nội dung/giá trị CV.

---

## 🕸️ Làm giàu KG (skills_normalized, implied_skills, flags)

Tầng làm giàu đồ thị tri thức (`enrich`) chạy sau tầng hậu kiểm nhằm chuẩn hóa thực thể và bổ sung tri thức suy diễn:

- **Luồng xử lý**: `extract_json` → `postprocess` → `enrich` → `response`.
- **Nguồn Knowledge Base (KB)**:
  - Khi khởi động, dịch vụ cố gắng kết nối PostgreSQL qua biến môi trường `KB_DSN`.
  - Nếu `KB_DSN` không được cấu hình hoặc kết nối thất bại, dịch vụ tự động fallback sang nạp offline từ thư mục seed CSV (`KB_SEED_DIR`, mặc định `./kb/seed`).
  - Trạng thái nạp KB được phản ánh trong endpoint `GET /health` qua trường `"kb": {"source": "postgres" | "csv", "skills": int, "universities": int}` (hoặc `null` nếu tắt/lỗi).
- **Các trường mới và ý nghĩa**:
  - `skills_normalized`: Danh sách kỹ năng chuẩn hóa tương ứng với các kỹ năng đã trích xuất, mỗi phần tử gồm `{raw, id, name, category, method}`. Phương thức liên kết `method` gồm `exact`, `normalized`, `split`, `fuzzy` hoặc `unlinked` (khi unlinked thì `id`, `name`, `category` là `null`). Kỹ năng trùng lặp ID được gom lại và giữ nguyên thứ tự xuất hiện ban đầu.
  - `implied_skills`: Các kỹ năng được suy diễn gián tiếp qua quan hệ tri thức (`REQUIRES`, `PART_OF`), mỗi phần tử gồm `{id, name, category, via: [{"from": str, "rel": str}]}`. **Quan trọng**: `implied_skills` không bao giờ trùng lặp với `skills_normalized` và **không bao giờ gộp vào danh sách `skills`** gốc của ứng viên.
  - `school_normalized` (trong từng mục `education`): Đối tượng `{id, name}` chuẩn hóa trường đại học/học viện từ KB. **Lưu ý**: Trường học và chức danh công việc là tập mở (open set); nếu trường học không có trong KB thì `school_normalized` mang giá trị `null` và đây **không phải lỗi, không gắn cờ**.
  - `flags`: Cờ cảnh báo hỗ trợ nhà tuyển dụng rà soát thủ công, mỗi phần tử gồm `{code, count, field}`. Cờ **tuyệt đối không chứa giá trị nội dung CV thô**. Các mã cờ gồm:
    - `UNGROUNDED_REMOVED`: Số mục bị tầng hậu kiểm loại bỏ do không tìm thấy căn cứ trong CV.
    - `CONTACT_NULLED`: Số trường liên hệ (`email`, `phone`, `github_url`, `full_name`) bị gán `null`.
    - `EXPERIENCE_REMOVED`: Số kinh nghiệm bị loại bỏ do không có căn cứ hoặc vi phạm phân loại (sinh viên, học viên...).
    - `SKILLS_UNLINKED`: Số lượng kỹ năng không liên kết được vào KB (`field: "skills"`).
    - `MISSING_CONTACT`: Cảnh báo khi hồ sơ thiếu cả email lẫn số điện thoại (`field: "personal_info"`).

**Ví dụ JSON tổng hợp**:
```json
{
  "data": {
    "personal_info": {"full_name": "Nguyễn Văn A", "email": "a@example.com", "phone": "0912345678"},
    "education": [
      {
        "school": "PTIT",
        "major": "Công nghệ thông tin",
        "school_normalized": {
          "id": 187,
          "name": "Học viện Công nghệ Bưu chính Viễn thông"
        }
      }
    ],
    "skills": ["React.js", "Postgress", "Spring Boot", "Chịu áp lực tốt"],
    "skills_normalized": [
      {"raw": "React.js", "id": 452, "name": "ReactJS", "category": "Frontend", "method": "exact"},
      {"raw": "Postgress", "id": 431, "name": "PostgreSQL", "category": "Database", "method": "fuzzy"},
      {"raw": "Spring Boot", "id": 305, "name": "Spring Boot", "category": "Backend Framework", "method": "exact"},
      {"raw": "Chịu áp lực tốt", "id": null, "name": null, "category": null, "method": "unlinked"}
    ],
    "implied_skills": [
      {
        "id": 300,
        "name": "Java",
        "category": "Programming Language",
        "via": [{"from": "Spring Boot", "rel": "REQUIRES"}]
      }
    ],
    "flags": [
      {"code": "UNGROUNDED_REMOVED", "count": 1, "field": null},
      {"code": "SKILLS_UNLINKED", "count": 1, "field": "skills"}
    ]
  }
}
```

---

## 📊 Đánh giá (Evaluation / Ablation)

Bộ công cụ đánh giá ngoại tuyến (`ai-service/eval/`) phục vụ đo lường chất lượng mô hình và ablation study so sánh giữa:
- **Biến thể A**: Mô hình thuần (Model-only raw output).
- **Biến thể B**: Mô hình kết hợp tầng hậu kiểm (`postprocess`), áp dụng offline trên cùng output của A.
- **Biến thể C**: Mô hình kết hợp hậu kiểm và tầng làm giàu tri thức KG (`enrich`).

### Dữ liệu đánh giá
Dữ liệu được lưu tại thư mục `ai-service/data/` (đã cấu hình trong `.gitignore`, tải về từ Google Drive dự án):
- `train.jsonl` (395 mẫu), `val.jsonl` (99 mẫu).
- **Lưu ý đối soát**:
  - Model v1 (`checkpoint-250` hoặc `merged_model/model.gguf`) **bắt buộc** đánh giá trên `val.jsonl`.
  - Model v2 phải đánh giá trên `val_v2.jsonl` (do tập `train_v2` có trùng lặp với `val.jsonl` của v1).
- **Tập hoán đổi thực thể (`val_swap.jsonl`)**: Sinh từ `val.jsonl` bằng cách thay thế tên công ty và trường học bằng các tên hư cấu hoàn toàn chưa từng xuất hiện trong tập huấn luyện (giữ nguyên các tên có độ dài $\le 3$ ký tự). Tập này dùng để kiểm tra mô hình thực sự đọc hiểu ngữ cảnh CV hay chỉ ghi nhớ thuộc lòng thực thể đã thấy khi huấn luyện.

### Chỉ số đánh giá (Metrics)
Báo cáo chỉ chứa số liệu tổng hợp (aggregate), tuyệt đối không để lộ nội dung CV thô:
- **F1 theo trường**: F1 cho các trường danh sách (`education.school`, `experience.company`, `personal_projects.name`, `experience.job_title`, `skills`, `certificates`, `honours`, `languages`) và Accuracy cho các trường liên hệ (`personal_info`).
- **`skills_canonical`**: F1 cho kỹ năng đã chuẩn hóa về KB ID (hoặc chuỗi chuẩn hóa nếu unlinked) giúp đo lường mức độ biểu diễn chuẩn xác thay vì so sánh chuỗi thô.
- **`hallucination_rate`**: Tỷ lệ các giá trị thực thể mô hình sinh ra nhưng không tìm thấy căn cứ (grounding) trong văn bản CV gốc.
- **`gold_ungrounded_rate`**: Tỷ lệ thực thể trong nhãn chuẩn (gold silver-label) không có căn cứ trong CV, phản ánh độ nhiễu của nhãn silver tạo bởi LLM.
- **`valid_rate`**: Tỷ lệ dự đoán hợp lệ theo đúng định dạng JSON/Schema.
- **Latency**: Thời gian phản hồi trung bình (`mean`), `p50`, `p95` (tính theo giây).

### Hướng dẫn chạy

```bash
cd ai-service

# 1. Sinh tập kiểm thử hư cấu entity-swapped (kết quả ghi vào data/val_swap.jsonl)
python -m eval.swap --val data/val.jsonl --train data/train.jsonl --out data/val_swap.jsonl --seed 42

# 2. Khởi động AI service ở chế độ tắt hậu kiểm (để thu thập output raw của Biến thể A)
POSTPROCESS_ENABLED=false python main.py &

# 3. Thu thập dự đoán và lưu cache vào data/runs/v1/ (mặc định port 8000, có thể chỉnh --base-url)
python -m eval.predict --split data/val.jsonl      --run data/runs/v1 --base-url http://localhost:8000
python -m eval.predict --split data/val_swap.jsonl --run data/runs/v1 --base-url http://localhost:8000

# 4. Tính toán điểm số các biến thể (mặc định A, B, C) và xuất báo cáo (report.md, report.json)
python -m eval.report  --run data/runs/v1 --splits data/val.jsonl data/val_swap.jsonl
```

---

### 2. Kiểm tra trạng thái service
- **Method:** `GET`
- **URL:** `http://localhost:8000/health`
- **Response:** `503` nếu model chưa load. Khi engine là `transformers`:
  ```json
  {
    "status": "ok",
    "engine": "transformers",
    "model": "unsloth/Qwen3-1.7B",
    "lora": "./checkpoint-250",
    "device": "cuda:0",
    "context_tokens": 8192,
    "fallback_reason": "Không tìm thấy file GGUF",
    "kb": {
      "source": "postgres",
      "skills": 1250,
      "universities": 180
    }
  }
  ```
  Khi engine là `llama_cpp`, `model` là đường dẫn file GGUF và không có `lora`, `device`.
- **Luôn có** `context_tokens` (số token context thực dùng). `fallback_reason` chỉ xuất hiện khi engine **không** phải `llama_cpp` (lý do không nạp được GGUF). Trường `"kb"` phản ánh trạng thái nạp Knowledge Base (`{"source": "postgres" | "csv", "skills": int, "universities": int}` hoặc `null` nếu tắt/chưa nạp).

---

## 🧠 Knowledge Base (KB) & Skill Linking

Hệ thống Knowledge Base lưu trữ đồ thị tri thức kỹ năng (skills graph) và hỗ trợ liên kết kỹ năng (skill linking) đa tầng (`exact` -> `normalized` -> `split` -> `fuzzy` -> `unlinked`).

### 1. Khởi động DB
```bash
cp infra/kb/.env.example infra/kb/.env
# Chỉnh sửa infra/kb/.env và đặt KB_PASSWORD an toàn
docker compose -f infra/kb/docker-compose.yml --env-file infra/kb/.env up -d
```
*Ghi chú: Service chạy trên cổng `5433` để tránh xung đột với các instance PostgreSQL khác trên máy.*

### 2. Làm sạch dữ liệu silver
```bash
cd ai-service
python -m kb.clean_silver --in data/*.jsonl --out-dir data/clean
```

### 3. Xây dựng seed kỹ năng
```bash
cd ai-service
python -m kb.build_seed \
  --train data/clean/train.jsonl \
  --out kb/seed \
  --curated kb/seed \
  --section-dict ../backend/src/main/java/recruit/demo/extraction/section/SectionDictionary.java
```
- Bộ seed CSV (`skills.csv`, `skill_aliases.csv`, `skill_edges.csv`, `skill_categories.csv`, `universities.csv`, `university_aliases.csv`) được commit vào repo để phục vụ offline linker (`from_csv`) và fallback khi không có DB.
- File `kb/seed/skill_aliases_curated.csv` dùng để gộp thủ công biến thể kỹ năng (cột: `variant,canonical,reviewed`): khi đặt `reviewed=true`, quá trình build sẽ ánh xạ biến thể sang canonical skill tương ứng.
- Các file `*_curated.csv` khác là đề xuất từ máy với `reviewed=false`.
- **Quy trình duyệt**: Chỉnh sửa category/edge/alias trong file curated, đổi cờ thành `reviewed=true`, sau đó chạy lại lệnh build để tích hợp.
- Thuật toán tự động gộp các lỗi chính tả hiếm gặp vào kỹ năng phổ biến bằng fuzzy matching ($\ge 90$).

### 4. Nạp dữ liệu vào DB (Load)
```bash
cd ai-service
python -m kb.load --dsn $KB_DSN
```
*Script đảm bảo tính idempotent (chạy nhiều lần không trùng lặp) và kiểm tra toàn vẹn dữ liệu (integrity check) sau khi nạp.*

### 5. Sử dụng Skill Linker
```python
from app.kb.linker import SkillLinker

# Nạp từ cơ sở dữ liệu PostgreSQL
linker = SkillLinker.from_db(dsn)

# Hoặc nạp offline từ thư mục seed CSV (không cần DB)
linker = SkillLinker.from_csv("kb/seed")

# Thực hiện liên kết thực thể kỹ năng
result = linker.link("ReactJS")
# result.method: 'exact' | 'normalized' | 'split' | 'fuzzy' | 'unlinked'
```

### 6. Đo lường chất lượng linking (Measure)
```bash
cd ai-service
python -m kb.measure --split data/clean/val.jsonl --seed kb/seed --out data/runs/kb [--dsn $KB_DSN]
```

### 7. Chạy kiểm thử tích hợp DB
```bash
cd ai-service
# Chỉ định KB_TEST_DSN trỏ tới DB test riêng biệt recruit_kb_test
# CẢNH BÁO: Bộ test sẽ TRUNCATE toàn bộ bảng dữ liệu, tuyệt đối KHÔNG trỏ vào DB thật!
export KB_TEST_DSN="postgresql://postgres:postgres@localhost:5433/recruit_kb_test"
pytest -m kb_db
```

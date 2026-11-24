# AI Service - CV Information Extraction

Dịch vụ trích xuất thông tin CV (CV Parsing) ứng dụng Mô hình Ngôn ngữ Lớn (**Qwen3-1.7B**) đã được tinh chỉnh (Fine-tuned) với kỹ thuật LoRA và hỗ trợ lượng tử hóa **GGUF Q4_K_M** (chạy bằng `llama.cpp` hoặc `transformers`).

---

## 📂 Cấu trúc thư mục

```
ai-service/extraction/
├── checkpoint-v4/              # LoRA adapter của model v4 (~78MB, có trong repo)
│   ├── adapter_config.json
│   ├── adapter_model.safetensors
│   ├── chat_template.jinja
│   ├── tokenizer.json
│   └── tokenizer_config.json
├── merged_model/               # GGUF lượng tử hóa: model-v4-q4_k_m.gguf (gitignore)
│   └── .gitkeep
├── training/                   # builder dataset v3/v4/v5 (cho lần train sau) + retrain_qwen3_v2.ipynb
├── serve_on_colab_gpu.ipynb    # Chạy API trên Colab T4 (llama.cpp bắt buộc CUDA) + Cloudflare tunnel
├── main.py                     # Entry point (shim): `uvicorn main:app`
├── app/
│   ├── main.py                 # Khởi tạo FastAPI, include router, load model khi startup
│   ├── api/routes.py           # /health, /api/v1/extract-cv
│   ├── core/                   # config.py (env), logging.py
│   ├── schemas/cv.py           # CVRequest, CVResponse
│   ├── services/               # model_loader, prompt_v3 (prompt của model v4), generator, loop_guard, continuation
│   └── utils/                  # text.py (clean_cv_text), json_parse.py (extract_json)
├── kb/                         # seed KB, script build KB, seed/extensions (skill hệ thống)
├── eval/                       # đánh giá ngoại tuyến / ablation
├── Dockerfile                  # image serving (GGUF, MODEL_ENGINE=llama_cpp)
├── requirements.txt            # thư viện serving (Docker)
├── requirements-train.txt      # thêm torch/transformers/peft cho LoRA, train, eval
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
cd ai-service/extraction

# Tạo môi trường ảo
python3 -m venv .venv

# Kích hoạt môi trường ảo
# Trên Linux/macOS:
source .venv/bin/activate
# Trên Windows:
# .venv\Scripts\activate

# Cài đặt các thư viện phụ thuộc
pip install -r requirements-train.txt   # chỉ serving GGUF: requirements.txt
```

### 3. Biến môi trường (tùy chọn, tất cả có giá trị mặc định)

Service tự nạp file `.env` ngay trong thư mục `ai-service/extraction/` khi khởi động và đọc các biến môi trường sau đó nếu chưa có giá trị nào. Copy file mẫu rồi sửa trong `.env`:

```bash
cd ai-service/extraction
cp .env.example .env
```

PowerShell (Windows):
```powershell
cd ai-service/extraction
Copy-Item .env.example .env
```

Trong `.env`, sửa các biến điều khiển engine/model: `MODEL_ENGINE` (`transformers` hoặc `llama_cpp`), `PROMPT_VERSION` (chỉ `v4`) và `GGUF_MODEL_PATH` (cho `llama_cpp`) hoặc `LORA_PATH` (cho `transformers`), rồi chạy service:

```bash
python main.py
```

Lưu ý: biến môi trường hệ điều hành luôn ưu tiên hơn giá trị trong `.env` (ví dụ `MODEL_ENGINE=llama_cpp python main.py` sẽ đè `MODEL_ENGINE` trong `.env`); sau khi đổi `.env` cần khởi động lại service để giá trị mới có hiệu lực.

| Biến | Mặc định | Mô tả |
|---|---|---|
| `BASE_MODEL_NAME` | `unsloth/Qwen3-1.7B` | Base model cho `transformers` + LoRA (có thể được thay bằng base khai trong adapter) |
| `MODEL_ENGINE` | `transformers` | Chọn `transformers` (LoRA) hoặc `llama_cpp` (GGUF) |
| `LORA_PATH` | `./checkpoint-v4` | Thư mục adapter LoRA của v4 (engine `transformers`) |
| `GGUF_MODEL_PATH` | `./merged_model/model-v4-q4_k_m.gguf` | File GGUF của v4 (engine `llama_cpp`) |
| `CONTEXT_TOKENS` | `8192` | Context window; nếu chưa set thì fallback sang `MAX_INPUT_TOKENS` |
| `MAX_INPUT_TOKENS` | `8192` | Giá trị fallback cũ của `CONTEXT_TOKENS` |
| `PROMPT_VERSION` | `v4` | Chỉ nhận `v4` (prompt v3 + trọng số v4); bản model sau này sẽ thêm giá trị mới |
| `MAX_NEW_TOKENS` | `2048` | Giới hạn số token sinh ra cho mỗi request |
| `LOOP_MAX_STRING_CHARS` | `2000` | Chặn lặp: dừng sinh khi một chuỗi JSON dài hơn ngưỡng này (feature 008) |
| `LOOP_MAX_REPEATS` | `3` | Chặn lặp: dừng sinh khi cùng một chuỗi (≥ 15 ký tự) lặp lại ngần này lần trong cùng một danh sách |
| `QUEUE_WAIT_SECONDS` | `30` | Thời gian tối đa chờ hàng đợi trước khi trả `503` "bận" |
| `POSTPROCESS_ENABLED` | `true` | Bật/tắt tầng hậu kiểm grounding (`0`/`false`/`no`/`off` để tắt — phục vụ ablation) |
| `KG_ENABLED` | `false` | Tầng làm giàu KB/KG (`skills_normalized`, `implied_skills`, `school_normalized`, `skills_detected`, `flags`). Tắt mặc định: module 1 chỉ trả nội dung CV, module 2 tự match. `true` để thử nghiệm / ablation |
| `KB_DSN` | unset | Connection string PostgreSQL KB (ví dụ: `postgresql://user:pass@host:5433/recruit_kb`) |
| `KB_SEED_DIR` | `./kb/seed` | Thư mục chứa các file seed CSV dùng khi offline hoặc fallback |
| `LOG_CV_CONTENT` | tắt | Đặt `1`/`true`/`yes`/`on` để log nội dung CV và raw output của model |

---

## 🧪 Chạy Test

```bash
cd ai-service/extraction
pip install -r requirements-dev.txt
python -m pytest -q
```

---

## ⚙️ Các Chế Độ Chạy Inference

Dịch vụ chọn một trong **2 cơ chế suy luận** qua `MODEL_ENGINE`. Đường dẫn `LORA_PATH` và `GGUF_MODEL_PATH` tương đối được tính từ thư mục `ai-service/extraction`, không phụ thuộc thư mục chạy lệnh.

### 🔹 Cách 1: LoRA v4 qua transformers (mặc định)
- Chuẩn bị adapter v4 tại `checkpoint-v4/`; base model có thể được tải từ Hugging Face.
- Chạy từ `ai-service/extraction` (các biến dưới đây cũng là mặc định):
  ```bash
  PROMPT_VERSION=v4 MODEL_ENGINE=transformers LORA_PATH=./checkpoint-v4 python main.py
  ```
  PowerShell (Windows):
  ```powershell
  $env:PROMPT_VERSION = "v4"
  $env:MODEL_ENGINE = "transformers"
  $env:LORA_PATH = "./checkpoint-v4"
  python main.py
  ```

### 🔹 Cách 2: Chạy tối ưu hóa với GGUF qua llama.cpp (Nhanh hơn, tiết kiệm RAM)
- **Yêu cầu:** `llama-cpp-python` (đã có trong `requirements.txt`; bản mặc định chỉ chạy CPU, muốn chạy GPU thì cài lại bản CUDA):
  ```bash
  pip install llama-cpp-python
  # Nếu dùng GPU NVIDIA (CUDA):
  CMAKE_ARGS="-DGGML_CUDA=on" pip install llama-cpp-python
  ```
- Chuẩn bị GGUF v4 tại `merged_model/model-v4-q4_k_m.gguf`, rồi chạy từ `ai-service/extraction`:
  ```bash
  PROMPT_VERSION=v4 MODEL_ENGINE=llama_cpp GGUF_MODEL_PATH=./merged_model/model-v4-q4_k_m.gguf python main.py
  ```
  PowerShell (Windows):
  ```powershell
  $env:PROMPT_VERSION = "v4"
  $env:MODEL_ENGINE = "llama_cpp"
  $env:GGUF_MODEL_PATH = "./merged_model/model-v4-q4_k_m.gguf"
  python main.py
  ```
- Chế độ GGUF nghiêm ngặt: thiếu file, thiếu thư viện hoặc lỗi nạp đều báo lỗi, **không fallback sang LoRA**. Nếu không đặt `GGUF_MODEL_PATH` và file mặc định không tồn tại, service chỉ tự chọn khi thư mục chứa đúng một file `*.gguf`; cần tự bảo đảm file đó khớp prompt. Nếu đã đặt biến, đường dẫn phải trỏ đúng file tồn tại.

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

Bộ công cụ đánh giá ngoại tuyến (`ai-service/extraction/eval/`) phục vụ đo lường chất lượng mô hình và ablation study so sánh giữa:
- **Biến thể A**: Mô hình thuần (Model-only raw output).
- **Biến thể B**: Mô hình kết hợp tầng hậu kiểm (`postprocess`), áp dụng offline trên cùng output của A.
- **Biến thể C**: Mô hình kết hợp hậu kiểm và tầng làm giàu tri thức KG (`enrich`).

### Dữ liệu đánh giá
Dữ liệu được lưu tại thư mục `ai-service/extraction/data/` (đã cấu hình trong `.gitignore`, tải về từ Google Drive dự án):
- `val.jsonl` (99 mẫu CV tổng hợp); CV thật: `retrain_v6.1/test_real.jsonl` (50 CV, thước đo chính).
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
cd ai-service/extraction

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
    "lora": "./checkpoint-v4",
    "device": "cuda:0",
    "context_tokens": 8192,
    "fallback_reason": null,
    "kb": {
      "source": "postgres",
      "skills": 1250,
      "universities": 180
    }
  }
  ```
  Khi engine là `llama_cpp`, `model` là đường dẫn file GGUF và không có `lora`, `device`.
- `context_tokens` là số token context thực dùng; không có fallback tự động từ GGUF sang LoRA. Trường `"kb"` phản ánh trạng thái nạp Knowledge Base (`{"source": "postgres" | "csv", "skills": int, "universities": int}` hoặc `null` nếu tắt/chưa nạp).

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

### 2. Xây dựng seed từ nguồn bên ngoài (feature 009)
KB chỉ được dựng từ nguồn công khai có giấy phép mở; mỗi dòng seed có cột `source`. Trích dẫn đầy đủ, số liệu và phương pháp: `kb/seed/SOURCES.md`.

| Nguồn | Giấy phép | Dùng cho |
|---|---|---|
| Stack Overflow Developer Survey 2024–2026 | ODbL 1.0 / DbCL 1.0 | Tên chuẩn kỹ năng + nhóm |
| Stack Overflow tags (tag ≥ 500 câu hỏi + tag đồng nghĩa) | CC BY-SA 4.0 | Thư viện/công cụ khảo sát không hỏi (Spring MVC, Lombok…) |
| Wikidata | CC0 1.0 | Alias en/vi, khái niệm (OOP, MVC…), quan hệ KG (P277, P361, P527), trường ĐH/CĐ |
| GitHub Linguist | MIT | Alias ngôn ngữ lập trình |
| ESCO v1.2.1 | CC BY 4.0 | Kỹ năng mềm, nghề ICT |
| Wikipedia tiếng Việt (rev. 75654510) | CC BY-SA 4.0 | Tên chính thức trường |

```bash
cd ai-service/extraction
python -m kb.fetch_sources            # tải snapshot -> kb/sources/ + MANIFEST.json (dùng cache; --refresh để tải lại)
python -m kb.build_external           # offline: kb/sources/ -> kb/seed/*.csv + SOURCES.md
```
- Từ vựng dùng để tra Wikidata / Stack Overflow tags chỉ lấy từ CV **tổng hợp/hư cấu** (`data/clean/silver_dataset.jsonl`, `data/synth_v3/profiles/`), không bao giờ từ CV thật.
- Cập nhật KB: chạy lại hai lệnh trên, xem diff CSV, rồi nạp DB (bước 4) và khởi động lại service. Không cần train lại mô hình.
- Khi serve: kỹ năng / tech_stack / trường link được KB được thay bằng tên chuẩn (kỹ năng mềm giữ như CV); phần KG (`skills_normalized`, `implied_skills`, `skills_detected`, `flags`, `school_normalized`) chỉ trả khi gọi `?include=kg`; `?include=raw` trả thêm `raw_profile` (trước chuẩn hoá).

### 3. KB1 từ sách PDF + Neo4j làm kho KG chính (feature 010)
- **KB1** — `python -m kb.books`: tải *Pro Git* 2nd ed. (Chacon & Straub, CC BY-NC-SA 3.0) và *Think Python* 2nd ed. (Downey, CC BY-NC 3.0) vào cache git-ignore `kb/.cache/`, đọc mục lục + text từng mục bằng `pdftotext`, đếm kỹ năng KB2 được nhắc → `kb/sources/kb1_books.json` (chỉ tiêu đề mục, số trang, số đếm; không chép văn bản sách).
- **KB2** = seed CSV từ nguồn liên kết (bước 2).
- **Neo4j** (`infra/kg`, cổng 127.0.0.1:7474 / 7687):
  ```bash
  cp infra/kg/.env.example infra/kg/.env    # đặt NEO4J_PASSWORD
  docker compose -f infra/kg/docker-compose.yml --env-file infra/kg/.env up -d
  cd ai-service/extraction && set -a && . ../../infra/kg/.env && set +a
  python -m kb.neo4j_load --uri bolt://localhost:7687 --user neo4j --password-env NEO4J_PASSWORD --reset
  NEO4J_URI=bolt://localhost:7687 uvicorn main:app --port 8000   # service đọc KB từ Neo4j
  ```
  Loader nạp KB2 (Skill, Alias, Category, REQUIRES/PART_OF, University, JobTitle), KB1 (Book, Section, MENTIONS) rồi gộp: `RELATED_TO` (kỹ năng cùng được nhắc trong ≥ 2 mục sách), `ABOUT` (mục sách có tiêu đề là một kỹ năng). Thứ tự nạp KB của service: Neo4j (`NEO4J_URI`) → PostgreSQL (`KB_DSN`) → CSV. Không có Neo4j (Colab, test), CSV vẫn có `RELATED_TO` đọc từ `kb1_books.json`. `include=kg` trả thêm `related_skills`.

### 4. Nạp dữ liệu vào DB (Load)
```bash
cd ai-service/extraction
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
cd ai-service/extraction
python -m kb.measure --split data/clean/val.jsonl --seed kb/seed --out data/runs/kb [--dsn $KB_DSN]
```

### 7. Chạy kiểm thử tích hợp DB
```bash
cd ai-service/extraction
# Chỉ định KB_TEST_DSN trỏ tới DB test riêng biệt recruit_kb_test
# CẢNH BÁO: Bộ test sẽ TRUNCATE toàn bộ bảng dữ liệu, tuyệt đối KHÔNG trỏ vào DB thật!
export KB_TEST_DSN="postgresql://postgres:postgres@localhost:5433/recruit_kb_test"
pytest -m kb_db
```

## 🧠 Model v4 (đang dùng)

Chỉ còn một model: **v4** = prompt v3 (`app/services/prompt_v3.py`) + trọng số train trên text tách theo cột (feature 013). Các bản v1/v2/v3/v5 và v6.1 đã bỏ: v6.1 kém v4 khi đo trên CV thật (xem `specs/` / báo cáo).

Chạy local bằng GGUF (~1,1 GB, file trên Drive dự án):
```bash
python -m gdown 1mKd0SmhnUKpJTXkH3xQs0puEwYgqFQWn -O merged_model/model-v4-q4_k_m.gguf
MODEL_ENGINE=llama_cpp uvicorn main:app --port 8000      # PROMPT_VERSION mặc định v4
```
Chạy trên Colab GPU: `serve_on_colab_gpu.ipynb` (Run all, gửi URL ở cell [6]).

Serving gồm chặn vòng lặp, sinh nối tiếp khi JSON bị cắt, ghép JSON đóng ngoặc sớm, hậu kiểm grounding, chuẩn hoá KB và KG (ẩn trừ khi `?include=kg`); `?include=raw` trả thêm `raw_profile` (trước chuẩn hoá KB) để đánh giá.

Train bản kế tiếp (v7): builder `training/build_dataset_v4.py` / `build_dataset_v5.py` + `training/retrain_qwen3_v2.ipynb`; dataset CV thật hiện có ở `data/retrain_v6.1/` (gitignore).

---

## 🐳 Serving bằng Docker (service `cv-extraction-ai`)

Serving code được lấy từ `origin/hocnv/DO-06`, commit `31e8a1d` tại thời điểm tách microservice. Giữ pipeline Qwen3-1.7B, sinh nối tiếp, grounding và KB/KG; dùng seed CSV khi không cấu hình Neo4j/PostgreSQL. Mã PDFBox đọc bố cục nằm trong `backend/recruitment-service/.../extraction/pdf`.

API: `POST /api/v1/extract-cv` với `{"cv_text":"..."}`, trả `{"data":{...}}`. Recruitment đọc PDF rồi gọi endpoint này. Health: `GET /health`.

Cài Python 3.11+, `pip install -r requirements.txt`, đặt `model-v4-q4_k_m.gguf` trong `merged_model/`, rồi chạy:

```bash
PROMPT_VERSION=v4 uvicorn main:app --host 0.0.0.0 --port 8001
```

Docker Compose dùng cổng host 8001 và mount trọng số tại `ai-service/models/cv-extraction/`. Image mặc định chỉ cài đường GGUF/llama.cpp CPU; nếu dùng Transformers/LoRA hoặc GPU cần cài dependencies và cấu hình tương ứng. Không kèm trọng số hoặc dữ liệu CV cá nhân.

Các test serving, postprocess và KG được giữ từ nhánh gốc. Cài thêm `pytest` và `httpx`, sau đó chạy `python -m pytest`. Các công cụ training/eval và test phụ thuộc dữ liệu CV thật không thuộc bản serving này.

### Cập nhật checkpoint v4

Đã đồng bộ checkpoint LoRA `checkpoint-v4/` từ `hocnv/DO-06@31e8a1d` (thay cho checkpoint-250). Commit này không thay đổi serving pipeline Python. Compose hiện chọn v4; đặt `ai-service/models/cv-extraction/model-v4-q4_k_m.gguf` trước khi chạy.

GGUF v4 được notebook của nhánh gốc khai báo tại https://drive.google.com/file/d/1mKd0SmhnUKpJTXkH3xQs0puEwYgqFQWn/view (công khai, tải được bằng `gdown`).

LoRA v4 không phải GGUF: nếu chạy trực tiếp adapter cần Qwen nền và `torch`, `transformers`, `peft`, `accelerate`, đặt `PROMPT_VERSION=v4 LORA_PATH=./checkpoint-v4`. Image mặc định chỉ cài đường GGUF để tránh tăng RAM và thời gian build. Không chỉ đổi tên trọng số v3 thành v4.

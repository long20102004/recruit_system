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
- **Response:** `{"data": {...}}`, trong đó `data` gồm: `personal_info`, `objective`, `education`, `experience`, `personal_projects`, `skills`, `certificates`, `honours`, `languages`.
- **Header:** mọi response của endpoint này đều kèm `X-Request-ID: <12 hex>`.
- **Lỗi** (xem `specs/001-harden-ai-serving/contracts/extract-cv.md`):

  | Status | Khi nào | `detail` |
  |---|---|---|
  | `400` | `cv_text` rỗng/khoảng trắng | `cv_text không được rỗng` |
  | `413` | prompt tokens + output budget vượt context | `CV quá dài: <n> token, tối đa <max> token` |
  | `503` | model chưa load | `Model chưa được load` |
  | `503` | chờ xử lý quá `QUEUE_WAIT_SECONDS` | `Service đang bận, vui lòng thử lại sau` |
  | `500` | lỗi nội bộ (không lộ chi tiết exception) | `Trích xuất CV thất bại (request_id=<id>)` |

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
    "fallback_reason": "Không tìm thấy file GGUF"
  }
  ```
  Khi engine là `llama_cpp`, `model` là đường dẫn file GGUF và không có `lora`, `device`.
- **Luôn có** `context_tokens` (số token context thực dùng). `fallback_reason` chỉ xuất hiện khi engine **không** phải `llama_cpp` (lý do không nạp được GGUF).

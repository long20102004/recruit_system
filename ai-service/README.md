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
├── main.py                     # FastAPI server phục vụ trích xuất CV
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
- Do file GGUF (`model-qwen3-1.7b-q4_k_m.gguf` ~ 1.11 GB) vượt quá hạn mức 100MB của GitHub nên file này không được push trực tiếp lên repo.
- **Cách sử dụng:**
  1. Tải file `model-qwen3-1.7b-q4_k_m.gguf` từ link lưu trữ chia sẻ của dự án (Google Drive / Hugging Face).
  2. Đặt file vào thư mục `ai-service/merged_model/`:
     ```
     ai-service/merged_model/model-qwen3-1.7b-q4_k_m.gguf
     ```
  3. Khởi chạy: `python3 main.py`. Hệ thống sẽ tự động ưu tiên nạp GGUF và chạy qua engine `llama.cpp`.

---

## 📡 API Endpoints

### 1. Trích xuất thông tin CV
- **Method:** `POST`
- **URL:** `http://localhost:8000/extract-cv`
- **Headers:** `Content-Type: application/json`
- **Request Body:**
  ```json
  {
    "cv_text": "Họ và tên: Nguyễn Văn A\nEmail: anguyen@example.com\nSố điện thoại: 0912345678\nKỹ năng: Java, Spring Boot, PostgreSQL..."
  }
  ```
- **Response:** JSON có cấu trúc chuẩn gồm: `personal_info`, `objective`, `education`, `work_experiences`, `personal_projects`, `skills`, `certifications`.

### 2. Kiểm tra trạng thái service
- **Method:** `GET`
- **URL:** `http://localhost:8000/health`
- **Response:**
  ```json
  {
    "status": "healthy",
    "engine": "transformers",
    "model": "unsloth/Qwen3-1.7B"
  }
  ```

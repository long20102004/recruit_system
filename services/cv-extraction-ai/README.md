# CV Extraction AI

Serving code được lấy từ `origin/hocnv/DO-06`, commit `31e8a1d` tại thời điểm tách microservice. Giữ pipeline Qwen3-1.7B, sinh nối tiếp, grounding và KB/KG; dùng seed CSV khi không cấu hình Neo4j/PostgreSQL. Mã PDFBox đọc bố cục nằm trong `backend/recruitment-service/.../extraction/pdf`.

API: `POST /api/v1/extract-cv` với `{"cv_text":"..."}`, trả `{"data":{...}}`. Recruitment đọc PDF rồi gọi endpoint này. Health: `GET /health`.

Cài Python 3.11+, `pip install -r requirements.txt`, đặt `model-v4-q4_k_m.gguf` trong `merged_model/`, rồi chạy:

```bash
PROMPT_VERSION=v4 uvicorn main:app --host 0.0.0.0 --port 8001
```

Docker Compose dùng cổng host 8001 và mount trọng số tại `models/cv-extraction/`. Image mặc định chỉ cài đường GGUF/llama.cpp CPU; nếu dùng Transformers/LoRA hoặc GPU cần cài dependencies và cấu hình tương ứng. Không kèm trọng số hoặc dữ liệu CV cá nhân.

Các test serving, postprocess và KG được giữ từ nhánh gốc. Cài thêm `pytest` và `httpx`, sau đó chạy `python -m pytest`. Các công cụ training/eval và test phụ thuộc dữ liệu CV thật không thuộc bản serving này.

## Cập nhật checkpoint v4

Đã đồng bộ checkpoint LoRA `checkpoint-v4/` từ `hocnv/DO-06@31e8a1d` (thay cho checkpoint-250). Commit này không thay đổi serving pipeline Python. Compose hiện chọn v4; đặt `models/cv-extraction/model-v4-q4_k_m.gguf` trước khi chạy. File GGUF v3 được giữ nguyên và không tự dùng thay cho v4.

GGUF v4 được notebook của nhánh gốc khai báo tại https://drive.google.com/file/d/1mKd0SmhnUKpJTXkH3xQs0puEwYgqFQWn/view (quyền truy cập chưa được kiểm chứng trong phiên này).

LoRA v4 không phải GGUF: nếu chạy trực tiếp adapter cần Qwen nền và `torch`, `transformers`, `peft`, `accelerate`, đặt `PROMPT_VERSION=v4 LORA_PATH=./checkpoint-v4`. Image mặc định chỉ cài đường GGUF để tránh tăng RAM và thời gian build. Không chỉ đổi tên trọng số v3 thành v4.

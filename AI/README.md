# HireLens AI — Đánh giá phỏng vấn Spring Boot (Intern / Fresher)

Folder **độc lập** (không phụ thuộc backend/frontend). Pipeline:

1. **Feature**: BERTScore (P/R/F1) *hoặc* fast lexical overlap + **coverage** theo barem  
2. **Train**: Ridge regression map feature → điểm người chấm (0–10)  
3. **Infer**: chấm 1 câu trả lời + ý đủ/thiếu

## Cấu trúc

```
AI/
├── data/
│   ├── questions.json      # 5 câu Spring Boot + barem (criteria + weight + hints)
│   └── answers.csv         # 52 câu trả lời đã gán human_score
├── src/
│   ├── coverage.py
│   ├── features.py
│   ├── scoring.py          # logic chấm (CLI + API dùng chung)
│   ├── api.py              # FastAPI — Spring gọi endpoint này
│   ├── train_calibration.py
│   ├── predict_answer.py
│   └── run_demo.py
├── notebooks/train_on_colab.ipynb
├── output/                 # calibration_*.json sau khi train
└── requirements.txt
```

## API (cho Spring Boot / frontend gọi)

Trước hết cần đã train (`output/calibration_fast.json`):

```bash
cd AI
source .venv/bin/activate
pip install fastapi "uvicorn[standard]" pydantic   # hoặc pip install -r requirements.txt
python -m src.train_calibration --mode fast        # nếu chưa có

uvicorn src.api:app --reload --host 0.0.0.0 --port 8000
```

- Swagger: http://localhost:8000/docs  
- Health: `GET /health`  
- Chấm điểm: `POST /v1/interview/evaluate`  

### Cách 1 — dùng `question_id` demo

```bash
curl -s http://localhost:8000/v1/interview/evaluate \
  -H 'Content-Type: application/json' \
  -d '{
    "question_id": "sb-01",
    "answer": "Spring Boot dựa trên Spring, có auto-configuration và starter, hay dùng REST API."
  }'
```

### Cách 2 — Spring gửi barem từ DB (khuyến nghị tích hợp)

```bash
curl -s http://localhost:8000/v1/interview/evaluate \
  -H 'Content-Type: application/json' \
  -d '{
    "answer": "DI là IoC, Spring inject qua constructor hoặc @Autowired.",
    "question": "Dependency Injection là gì?",
    "reference_answer": "DI là IoC: Spring tiêm dependency thay vì tự new. Có constructor, setter, field injection.",
    "criteria": [
      {"key": "ioc", "label": "Ý tưởng IoC", "weight": 0.4, "hints": ["ioc", "tiêm", "không tự new"]},
      {"key": "ctor", "label": "Constructor injection", "weight": 0.3, "hints": ["constructor"]},
      {"key": "auto", "label": "@Autowired / field", "weight": 0.3, "hints": ["autowired", "field"]}
    ]
  }'
```

Response (user-facing; thêm `"include_debug": true` nếu backend cần log P/R/F1):

```json
{
  "predicted_score": 8.2,
  "score_scale": "0-10",
  "covered_points": ["..."],
  "missing_points": ["..."],
  "comment": "...",
  "model_version": "ridge-on-fast-v1",
  "mode": "fast"
}
```

Biến môi trường: `HIRELENS_MODE=fast|bertscore`, `HIRELENS_DEVICE=cpu|cuda`, `HIRELENS_CORS=*`.

## Cài đặt (máy local)

```bash
cd AI

# Tạo venv (nếu `python3 -m venv .venv` lỗi thiếu ensurepip):
python3 -m venv --without-pip .venv
curl -sS https://bootstrap.pypa.io/get-pip.py -o /tmp/get-pip.py
.venv/bin/python /tmp/get-pip.py

# Linux / macOS
source .venv/bin/activate
# Windows: .venv\Scripts\activate

pip install -r requirements.txt
# Chỉ thử nhanh (không cần torch/bert-score):
# pip install numpy pandas scikit-learn tqdm
```

> Lần đầu `bertscore` sẽ tải `bert-base-multilingual-cased` (~700MB).  
> Muốn thử **ngay không tải model**: dùng `--mode fast`.

## Chạy nhanh (khuyến nghị lần đầu)

```bash
cd AI
source .venv/bin/activate   # nếu đã tạo venv
python -m src.run_demo
```

Đã chạy thử trên máy dev (`--mode fast`, 52 mẫu): Ridge test **MAE ≈ 0.99**, baseline F1×10 **MAE ≈ 3.68** — calibration cải thiện rõ.

Hoặc từng bước:

```bash
# 1) Train Ridge trên feature fast
python -m src.train_calibration --mode fast

# 2) Chấm thử 1 câu
python -m src.predict_answer --mode fast --question-id sb-01 \
  --answer "Spring Boot dựa trên Spring, có auto-configuration và starter, hay dùng REST API."
```

Kết quả nằm trong `output/`:

| File | Nội dung |
|------|----------|
| `features_fast.csv` | Feature từng mẫu |
| `calibration_fast.json` | Hệ số Ridge + metrics |
| `predictions_fast.csv` | Điểm dự đoán vs điểm người |

## Chạy BERTScore thật

```bash
python -m src.train_calibration --mode bertscore
# Có GPU:
python -m src.train_calibration --mode bertscore --device cuda

python -m src.predict_answer --mode bertscore --question-id sb-03 \
  --answer "DI là IoC, Spring inject dependency; nên dùng constructor injection, cũng có setter và @Autowired."
```

## Google Colab

1. Nén / upload folder `AI` lên Drive (hoặc copy vào `/content/AI`).  
2. Mở `notebooks/train_on_colab.ipynb`.  
3. Runtime → **GPU**.  
4. Sửa đường dẫn `%cd` cho đúng chỗ bạn upload.  
5. Chạy cell `fast` trước, rồi `bertscore`.

## Danh sách câu hỏi (`question_id`)

| ID | Chủ đề |
|----|--------|
| `sb-01` | Spring Boot là gì / ưu điểm |
| `sb-02` | `@SpringBootApplication` |
| `sb-03` | Dependency Injection |
| `sb-04` | `@RestController` vs `@Controller` |
| `sb-05` | Spring Data JPA / `JpaRepository` |

Xem barem chi tiết trong `data/questions.json`.

## Đọc metrics như thế nào?

Trong `calibration_*.json`:

- `baseline_f1x10_test`: quy đổi thô F1×10 (chưa train)  
- `ridge_test`: sau calibration — nhìn **MAE** (càng thấp càng tốt) và **pearson** (càng gần 1 càng tốt)

Kỳ vọng hợp lý với 52 mẫu demo: Ridge thường **tốt hơn** baseline; số liệu chỉ mang tính minh họa, chưa phải production.

## Mở rộng dataset

Thêm dòng vào `data/answers.csv`:

```text
id,question_id,rank_target,answer,human_score,human_covered_keys,notes
a053,sb-01,intern,"...",7.5,"based_on_spring;auto_config",
```

`human_covered_keys` tùy chọn (phục vụ phân tích). Bắt buộc: `answer` + `human_score`.

Rồi train lại:

```bash
python -m src.train_calibration --mode fast
```

## Lưu ý học thuật

- Đây là **tự xây pipeline chấm điểm** + train lớp Ridge; encoder BERT dùng pretrained.  
- `--mode fast` chỉ để kiểm tra luồng code; báo cáo đồ án nên có thêm kết quả `--mode bertscore`.  
- Không kết nối backend/frontend trong giai đoạn này.

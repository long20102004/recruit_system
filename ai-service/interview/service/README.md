> Module 3 v2: luồng chính hiện dùng BERTScore + rubric và calibration có nhãn tổng hợp. Xem `docs/Module3_Interview_Flow.md` để chạy, xem provenance và giới hạn xác minh. Các file `questions.json`/`answers.csv` cũ được giữ nguyên; bộ mới là `interview_bank_v2.json`/`interview_answers_v2.csv`.

# HireLens AI — Đánh giá phỏng vấn Spring Boot (Intern / Fresher)

Folder **độc lập** (không phụ thuộc backend/frontend). Pipeline:

1. **Feature**: BERTScore (P/R/F1) *hoặc* fast lexical overlap + **coverage** theo barem  
2. **Train**: Ridge regression map feature → điểm người chấm (0–10)  
3. **Infer**: chấm 1 câu trả lời + ý đủ/thiếu

## Cấu trúc

```
AI/
├── data/
│   ├── questions.json      # câu hỏi + barem (criteria + weight + hints)
│   └── answers.csv         # câu trả lời đã gán human_score
├── src/
│   ├── coverage.py
│   ├── features.py
│   ├── scoring.py          # logic chấm (CLI + API dùng chung)
│   ├── api.py              # FastAPI — Spring gọi endpoint này
│   ├── train_calibration.py
│   ├── predict_answer.py
│   └── run_demo.py         # chạy nhanh train lexical + chấm một câu
├── notebooks/train_on_colab.ipynb
├── output/                 # calibration_*.json sau khi train
└── requirements.txt
```

## API (Spring Boot gọi khi nộp câu trả lời)

Backend (`app.ai.base-url`) gọi `POST /v1/interview/evaluate` kèm đáp án mẫu + barem từ MySQL.

Trước hết cần đã train (`output/calibration_fast.json`):

```bash
cd AI
source .venv/bin/activate
pip install -r requirements.txt
python -m src.train_calibration --mode fast        # nếu chưa có

uvicorn src.api:app --reload --host 0.0.0.0 --port 8000
```

Giữ API chạy song song với Spring (`:8080`). Nếu AI tắt, Spring fallback rule (khi `app.ai.fallback-to-rule: true`).

- Swagger: http://localhost:8000/docs  
- Health: `GET /health`  
- Chấm điểm: `POST /v1/interview/evaluate`  

### Cách 1 — dùng `question_id` trong tập câu hỏi

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

## Fine-tune BERT (Mohler + data tự thu) — Google Colab

Pipeline: regression điểm **0–10** trên `bert-base-multilingual-cased`.

| Nguồn | Vai trò |
|-------|---------|
| `nkazi/MohlerASAG` (`raw` / `open_ended`) | Benchmark CS; điểm 0–5 ×2 → 0–10 |
| `data/answers.csv` + `questions.json` | Domain phỏng vấn Spring Boot |

```bash
# Local / Colab (trong thư mục AI, đã cài transformers datasets accelerate)
python -m src.finetune_bert --scenario combined --epochs 3
# hoặc: mohler | self | transfer
python -m src.finetune_bert --scenario transfer --mohler-epochs 2 --epochs 3
```

Colab: mở `notebooks/finetune_bert_colab.ipynb` → Runtime **GPU** → sửa `AI_DIR` → chạy.

Output: `output/bert_finetuned_<scenario>/model/` + `finetune_metrics.json`  
(metrics tách `mohler_test` / `self_test` để đưa vào báo cáo).

Nếu `load_dataset` báo gated: vào trang HF chấp nhận điều khoản + `huggingface-cli login`.

## Google Colab (calibration BERTScore — không phải fine-tune)

1. Nén / upload folder `AI` lên Drive (hoặc copy vào `/content/AI`).  
2. Mở `notebooks/train_on_colab.ipynb`.  
3. Runtime → **GPU**.  
4. Sửa đường dẫn `%cd` cho đúng chỗ bạn upload.  
5. Chạy cell `fast` trước, rồi `bertscore`.

## Danh sách câu hỏi (`question_id`) — Intern / Fresher CNTT đa mảng

Scope: sinh viên CNTT mới ra trường (`intern`–`fresher`). Có backend Spring, Java/SQL, frontend, **tester/QA**, Git/HTTP.

| ID | Track | Chủ đề |
|----|--------|--------|
| `sb-01`…`sb-05` | backend | Spring Boot / DI / REST / JPA |
| `java-01`, `java-02` | backend | OOP, List/Set/Map |
| `sql-01`, `sql-02` | database | JOIN, Index |
| `http-01`, `cs-01` | general_cs | HTTP methods, status codes |
| `fe-01`, `fe-02` | frontend | HTML/CSS/JS, React props/state |
| `qa-01`…`qa-03` | tester_qa | Test case, black/white-box, bug + regression |
| `git-01` | general_cs | commit / branch / merge |

Hiện **47 câu**, **940** câu trả lời có `human_score` (0–10), ~20 mẫu/câu — đủ để train calibration / fine-tune self-set. Chi tiết barem: `data/questions.json`. Sinh thêm: `python scripts/expand_train_data.py`.

## Đọc metrics như thế nào?

Trong `calibration_*.json`:

- `baseline_f1x10_test`: quy đổi thô F1×10 (chưa train)  
- `ridge_test`: sau calibration — nhìn **MAE** (càng thấp càng tốt) và **pearson** (càng gần 1 càng tốt)

Trên tập 52 mẫu lexical đã ghi, Ridge thường tốt hơn baseline F1×10. Số liệu đầy đủ trên toàn bộ answers.csv cần chạy lại và đưa vào báo cáo.

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
- `--mode fast` dùng để kiểm tra luồng mã; báo cáo đồ án nên có thêm kết quả `--mode bertscore`.  
- Backend gọi API này khi nộp câu trả lời phỏng vấn.

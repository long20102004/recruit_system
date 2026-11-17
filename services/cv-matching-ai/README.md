# CV–JD Matching AI

Serving code và dữ liệu từ `origin/locnh/matchCV`, commit `1983b20c95d2863502ad974b7766864907883c6d`.

Bổ sung khi tích hợp: adapter nhận CandidateProfile của Extraction, tính số tháng kinh nghiệm không trùng lặp, ưu tiên dữ liệu người dùng đã sửa và sắp xếp batch theo điểm matching cuối cùng.

```bash
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8002
```

- `POST /match/no-llm`: chấm điểm bằng graph + embedding, giải thích tất định; Recruitment đang dùng endpoint này.
- `POST /match`: có thể gọi OpenAI để giải thích nếu cấu hình API key.
- `POST /match_batch`: BM25 + semantic RRF để lấy ứng viên, rồi xếp theo điểm matching.
- `GET /health`: trạng thái tiến trình.

Điểm trả về trong thang 0–100. XGBoost chưa được đưa vào đường suy luận. Model embedding mặc định là `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`, được tải khi cần. Nếu không tải được, code dùng hash dự phòng và ghi log; backend này không đại diện chất lượng semantic.

```bash
MATCHMAKING_EMBEDDING_BACKEND=hash python -m pytest
python -m unittest discover -s tests -p test_extraction_adapter.py
```

# Module 2 — CV/JD Matchmaking

## Chạy local

```powershell
conda activate module2
python -m uvicorn app.main:app --reload
```

Mở `http://127.0.0.1:8000/docs` để gọi `POST /match`. Input gồm `candidate`, `jd`, và tùy chọn `weights`.
Có thể gọi `POST /match/no-llm` để kiểm tra nhanh mà không dùng OpenAI. API cũng chấp nhận schema cũ với `education` dạng object (`{"degree": "...", "major": "..."}`) và `education_requirement` của JD.
`POST /match_batch` nhận `jd`, `candidates`, `top_k` (mặc định 50) và tùy chọn `weights`; endpoint dùng BM25 + semantic RRF để lọc CV trước khi tính feature/scoring, không gọi LLM. Quan hệ kỹ năng được đọc từ `data/skills_graph.json`.

Mặc định ứng dụng dùng Sentence Transformer đa ngôn ngữ và tải model khi lần đầu cần embedding. Có thể đặt `EMBEDDING_MODEL` để đổi model. Khi có `OPENAI_API_KEY`, bước giải thích sẽ gọi OpenAI; nếu không, ứng dụng dùng explainer deterministic local để API vẫn chạy được.

## Test

```powershell
conda activate module2
$env:MATCHMAKING_EMBEDDING_BACKEND = "hash"
python -m pytest
```

Pytest được giới hạn ở thư mục `tests/`; thư mục `old-code/` chỉ là bản tham khảo và không được chạy như mã nguồn hiện tại.

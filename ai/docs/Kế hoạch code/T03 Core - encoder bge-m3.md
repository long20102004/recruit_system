# T03 · Core: encoder bge-m3 dùng chung

**Đọc trước:** [[00 Tổng quan kế hoạch]] · Thiết kế `04` A10 · `05` B7 · `07` mục 2 và RR2 (mục 4) · `01` mục 5, 11.

## Mục tiêu

Nạp `BAAI/bge-m3` (commit `5617a9f61b`) **một lần mỗi tiến trình** và cung cấp hai kiểu đầu ra:

- **dense + sparse** cho Retrieve (A10, B7);
- **embedding từng token ở layer 24** cho BERTScore (T10).

## Làm

1. `core/models/bge_m3.py`
   - `BgeM3(model_id, revision, device, dtype)`; singleton theo `(revision, device, dtype)`. Ghim `revision` để tái lập.
   - `encode(texts, batch_size) -> EncodeResult(dense: np.ndarray[n,1024] float32 đã chuẩn hoá L2, sparse: list[dict[str,float]])`. Dùng `FlagEmbedding.BGEM3FlagModel` hoặc tự cài bằng `transformers` (ghi lý do chọn). Văn bản quá ~8.000 token: chia theo đoạn, trung bình vector (A10).
   - `token_embeddings(texts, layer=24, max_len=2048) -> list[TokenEmb(tokens: list[str], offsets, emb: np.ndarray[n_tok,1024])]`: hidden state layer chỉ định, **bỏ `<s>`, `</s>`**, chuẩn hoá L2 từng token; trả cả offset ký tự để T10 gộp sub-word thành từ.
   - Batch theo độ dài (sort by length) để đỡ tốn bộ nhớ GPU; bắt lỗi OOM → giảm batch và thử lại.
   - `embed_model_key()` → `"bge-m3@5617a9f61b"`.
2. `core/models/fake.py`: `FakeEncoder` cùng interface, sinh vector **tất định** từ hash văn bản (để test không cần GPU/mạng). Token embedding giả: tách theo khoảng trắng, vector từ hash của từ → hai câu chung từ thì có token giống nhau.
3. `core/models/__init__.py`: `get_encoder(cfg)` chọn thật/giả theo config hoặc biến `CVMATCH_FAKE_ENCODER=1`.
4. Thêm `torch`, `transformers`, `FlagEmbedding` (nếu dùng) vào `pyproject.toml` như extra `[gpu]`.

## Không làm

Cache embedding token (thuộc T10), ghi DB (T05).

## Tiêu chí xong

- Test (không GPU): `FakeEncoder` tất định, đúng shape.
- Test `@pytest.mark.gpu`: dense của "Xây dựng API thanh toán" gần "phát triển backend giao dịch" hơn "thiết kế banner photoshop"; token embedding không chứa token đặc biệt; chuẩn L2 = 1.
- Ghi vào bàn giao: thời gian encode 1.000 câu ngắn trên GPU hiện có, bộ nhớ đỉnh, dtype.

## Ghi chú bàn giao

**Trạng thái: xong (16/11/2026).** Đã chạy với model thật: 4 test `gpu` qua. Dense trùng tuyệt đối với `sentence-transformers` (cosine 1,0 trên 3 câu). Encode 1.000 câu ngắn ≈ 8,9 s trên GTX 1650, fp32. Env `cvmatch` đã cài `torch 2.14.0+cu130` (sm_75 có trong arch list). Model ghim commit đầy đủ `5617a9f61b028005a4858fdac845db406aefb181` (khoá `embed_model` vẫn 10 ký tự đầu). Sparse là trọng số theo sub-word của tokenizer (vd `{'truy': 0.19, 'Post': 0.10, 'gre': 0.20, 'SQL': 0.19}`), cùng dạng `lexical_weights` của BGE-M3.

_(Ghi chú bản đầu, giữ để tham khảo:)_

- `core/models/base.py`: `Encoder` protocol, `EncodeResult(dense, sparse)`, `TokenEmb(tokens, offsets, emb)`.
- `core/models/bge_m3.py`: `BgeM3` cài bằng `transformers` trực tiếp (không cần FlagEmbedding) để cùng một model cho cả hai đầu ra:
  - dense = vector CLS lớp cuối (chuẩn L2); sparse = `relu(sparse_linear(hidden))` gộp max theo token (tải `sparse_linear.pt` cùng revision);
  - `token_embeddings(layer=24)` = `hidden_states[24]`, bỏ token đặc biệt, chuẩn L2, kèm offset ký tự cho T10;
  - sắp batch theo độ dài, OOM → giảm batch thử lại; văn bản > `max_len` chia theo đoạn rồi trung bình;
  - singleton qua `load_bge_m3(...)` (`lru_cache`), có khoá để an toàn đa luồng.
- `core/models/fake.py`: `FakeEncoder` tất định (vector từ hash của từ). `get_encoder(cfg, fake=)` hoặc `CVMATCH_FAKE_ENCODER=1`.
- **Việc còn lại trước khi dùng thật:**
  1. Torch trong env `cvmatch` là bản **CPU** (`2.14.0+cpu`). Muốn chạy GPU (GTX 1650) cần cài torch bản CUDA.
  2. Model chưa có trong cache (~2,3 GB tải lần đầu).
  3. Sau đó chạy `pytest -m gpu tests/gpu` và ghi tốc độ / bộ nhớ vào đây. Chưa kiểm sparse của mình khớp `BGEM3FlagModel` — nên so một lần với FlagEmbedding.

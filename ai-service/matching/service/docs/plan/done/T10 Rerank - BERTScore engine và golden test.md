# T10 · Rerank: BERTScore engine + golden test G1

**Đọc trước:** [[00 Tổng quan kế hoạch]] · Thiết kế `07` mục 1–4, 5.3 (phần căn khớp token), 6 (bảng cache), 7 · `10` (toàn bộ: cấu hình, cách đọc span, từng test) · `09` mục 4.2 · `01` mục 11.

## Mục tiêu

Một engine tính **ma trận `R_ij`** (BERTScore Recall, câu JD là tham chiếu) cho mọi cặp (câu JD, gạch CV), có cache token, có căn khớp từ để làm bằng chứng; và bộ **golden test** để giữ cấu hình đúng như đã test.

## Làm

1. `rerank/bertscore/prepare.py` — chuẩn bị đầu vào đúng thứ tự thiết kế 07 mục 2.1:
   1. lấy `text_raw` (không dùng `text`);
   2. đổi alias về tên chuẩn bằng `SkillMatcher` + `canonical_name` (`canonicalize_aliases`), làm việc trên vị trí ký tự để giữ hoa/thường phần còn lại;
   3. che số (`mask_numbers`): mọi dãy chữ số kể cả `40%`, `3.5` → `N`;
   4. không ghép chức danh.
   Trả cả văn bản đã chuẩn bị và ánh xạ vị trí về `text_raw` (để Explain tô đậm đúng chỗ).
2. `rerank/bertscore/cache.py`: khoá `sha256(văn bản đã chuẩn bị) + bertscore_config`. Hai tầng: LRU trong RAM + bảng `bertscore_token_cache` (hoặc file trên đĩa, theo config) lưu float16. Giới hạn `cache.token_lru_gb`. Hàm `purge(text_hashes)` cho việc xoá CV (nối vào lệnh delete của T05).
3. `rerank/bertscore/engine.py`:
   - `embed(texts) -> list[TokenEmb]`: tra cache, thiếu thì gọi `core/models` (layer 24, max_len 2048, bỏ token đặc biệt, L2) theo lô.
   - `recall_matrix(jd_sents, cv_bullets) -> R[|J|, |I|]` với `R_ij = mean_rows(max_cols(E_j · E_iᵀ))`; IDF tắt, không rescale; tính theo lô bằng tensor đệm + mask để nhanh trên GPU (hoặc numpy khi CPU).
   - Trả thêm `argmax` theo từng token của câu JD cho cặp được hỏi.
   - Tuỳ chọn trả Precision, F1 (cho thí nghiệm R-E3).
4. `rerank/bertscore/align.py`: với cặp (j, best_i): gộp sub-word thành **từ** (dùng offset của tokenizer), bỏ từ dừng (danh sách trong config), `sim(từ) = max` cosine các token con; `sim ≥ align.word_sim_min` → `matched_words`, còn lại `missing_words`. Từ trả về theo dạng `text_raw` gốc.
5. **Golden test G1** — `evaluation/golden/`:
   - `golden_pairs.yaml`: chép **nguyên văn** JD/CV của T01–T24, F01–F05 từ thiết kế 10 mục 4 (biến thể `pos`, `neg`, `real`…), kèm tiêu chí đạt ghi trong tài liệu.
   - Runner tính điểm S1/S2/S3, quy ra **% span** (span = T23 − T10) đúng cách đọc ở mục 2, in bảng giống tài liệu.
   - Chế độ `--bare` (mô hình trần: tắt đổi alias, tắt che số) phải tái tạo số liệu của file 10 (sai lệch nhỏ do phần cứng chấp nhận được, ghi lại).
   - Điều kiện qua: ≥ 25/26 đạt ở S2 và không test nào ✅ → ❌. Đánh dấu `@pytest.mark.gpu`.
6. Benchmark: 1 JD 3 trách nhiệm × 200 CV × 8 gạch (như file 10), báo thời gian lạnh/ấm, đỉnh GPU.

## Không làm

Hiệu chuẩn `lo/hi`, hệ số `m_i`, feature B4 (T11).

## Tiêu chí xong

- Test không GPU (FakeEncoder): `R` đúng shape; câu trùng hoàn toàn → `R = 1`; cache trúng ở lần gọi thứ hai; che số "giảm 40% trong 3.5 tháng" → "giảm N% trong N tháng"; đổi alias "Triển khai K8s" → "Triển khai Kubernetes".
- Golden G1 `--bare` chạy trên GPU, kết quả gần file 10 (đính kèm bảng vào bàn giao); chế độ đầy đủ: T06 tăng, T08 ≈ 0.
- Benchmark ≈ con số 116 ms/CV của file 10 trên cùng loại GPU (hoặc giải thích chênh).

## Ghi chú bàn giao

**Trạng thái: xong (16/11/2026).** 7 test đơn vị (FakeEncoder) + 2 test GPU golden (G1, G2); toàn bộ 156 test thường + 6 test GPU qua. Báo cáo: `ai-service/matching/service/reports/golden_bare.md`, `golden_full.md`.

- **Dùng:**
  - `BertScorer(encoder, cfg.bertscore, matcher, cache)`: `prepare`, `embed` (qua cache), `recall_matrix(jd_texts, cv_texts, precision=False) -> R[|J|,|I|]` (một lần cho cả pool, `reduceat` trên token CV ghép), `pair`, `purge_texts`, `attach_events` (nghe `cv_deleted` → xoá cache).
  - `prepare(text_raw, matcher, …) -> Prepared(raw, text, segments)` + `to_raw_span` (vị trí đã chuẩn bị → chuỗi gốc, cho Explain).
  - `align_words(jd_prep, jd_emb, cv_emb, word_sim_min) -> (matched, missing, detail)` — từ trả về theo chuỗi gốc, bỏ từ dừng.
  - `TokenCache(config_key, max_bytes, conn=None)`: LRU RAM + tuỳ chọn bảng `bertscore_token_cache` (float16).
  - CLI: `cvmatch eval golden [--bare] [--bench] [--out …]` (trả mã lỗi nếu S2 < 25/26 — dùng làm test hồi quy G1).
- **Kết quả G1 (mô hình trần, bge-m3 thật, GTX 1650, fp32): tái lập đúng file 10** — S1 24/25, S2 25/26, S3 25/26, chỉ trượt T19; Recall S2 khớp tới 4 chữ số. Lệch lớn nhất 0,019 ở T17.pos (pipeline luôn dọn ký tự rác PDF bằng `to_raw`, nên gần bản sạch hơn — chủ ý).
- **Kết quả G2 (qua chuẩn bị đầu vào):** vẫn 25/26. T06 viết tắt: +19% → **+50% span** (K8s → Kubernetes); T07 +74% → +87%; T08 số năm: 5y − 1y = **0** (che số — đúng ý đồ, B2 chấm số năm); T05 phủ định không đổi (cần cờ `has_negation` + `m_neg` ở T11).
- **Chi phí** (1 JD × 3 trách nhiệm × 200 CV × 8 gạch, S2): lạnh 75–94 ms/CV (file 10: 116 ms), **ấm (cache) 0,1–0,16 s cho cả 200 CV**, đỉnh GPU 2,2 GB.
- **Quyết định:**
  - Đổi alias chỉ khi alias **khác** tên chuẩn (không đổi "Java" → "java" chỉ vì KB ghi tên chuẩn chữ thường).
  - Che số chỉ số đứng riêng (`40%`, `3.5`, `5`), không che trong tên công nghệ (`K8s`, `S3`, `Python3`).
  - S1 nối các câu bằng xuống dòng (`to_raw` gộp thành khoảng trắng).
  - Gạch lược trong tài liệu (T13: 40 gạch, T16: 404 gạch) được sinh tất định theo đúng mẫu; S2/S3 không phụ thuộc.
- **Chưa làm:** đường tính `R` trên GPU (hiện numpy CPU; đủ nhanh ở quy mô pool 200), `bertscore_pair_cache` (bảng có sẵn, chưa dùng).

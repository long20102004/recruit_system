# T09 · Retrieve: Luồng C (JD → CV)

**Đọc trước:** [[00 Tổng quan kế hoạch]] · Thiết kế `06` mục 1–4 (toàn bộ) · `01` mục 3, 7, 8 · `07` mục 6 (`RerankRequest`) · `11` mục 1.2.

## Mục tiêu

`retrieve_for_jd(jd_id, options) -> RetrieveResult` chạy C1–C8, trả ≤ K CV kèm điểm 4 góc nhìn và giải thích sơ bộ, ghi log, tạo `RerankRequest`.

## Làm

1. `retrieve/views.py` — mỗi view là hàm `(jd_data, index, mask) -> np.ndarray[n_cv] | None` (None = view không khả dụng):
   - `dense`: `doc_matrix @ jd_dense`.
   - `bm25`: truy vấn = `jd_vector.bm25_query_tokens` (chế độ `bm25.query_mode`: `full_jd` | `title_skills`).
   - `skill`: vector `w_imp` của kỹ năng **bắt buộc** (có trong ontology) · `skill_matrix` / Σ`w_imp`; JD không có kỹ năng bắt buộc → None.
   - `resp`: ma trận trách nhiệm (bỏ `is_generic`) × `bullet_matrix`ᵀ → max theo nhóm CV (`bullet_cv_index`, dùng `np.maximum.reduceat` sau khi sắp gạch theo CV) → trung bình qua trách nhiệm. Không có trách nhiệm → None. CV không có gạch → giá trị theo quy ước ghi rõ (thiết kế: "thiếu dữ liệu", không phải 0 — đề xuất NaN rồi loại khỏi trung bình của CV đó; ghi lại lựa chọn).
   - Tính theo khối để không vượt RAM khi n_bullet lớn.
2. `retrieve/fusion.py`: `minmax` (max = min → 0), `dbsf` (thí nghiệm), `rrf` (dự phòng); `score_sum` = trung bình các view khả dụng; xếp hạng: `fused` ↓ → `s_skill` ↓ → `cv_id` ↑ (tất định).
3. `retrieve/flow_c.py`:
   - C1 đọc `jd_vector`, `jd_skill`, `jd_responsibility` (đúng bộ phiên bản; khác → báo cần chạy lại Luồng B).
   - C2 mask: active + latest + lọc cứng nếu bật (`hard_filters`), **CV thiếu trường thì cho qua**; loại trừ danh sách `exclude_cv_ids`.
   - C3–C5 như trên; số CV sau lọc < 20 → cảnh báo.
   - C6 `explanation_json`: kỹ năng bắt buộc khớp/thiếu; 2–3 gạch khớp nhất với trách nhiệm tương ứng; điểm 4 view.
   - C7 ghi `match_run` (config_json, K, 3 phiên bản) + `match_result` (`s_*`, `n_*`, `fused`, rank).
   - C8 dựng `RerankRequest` (contracts của T00), không gửi văn bản CV.
4. CLI: `cvmatch retrieve jd <jd_id> [--k 200] [--views dense,bm25,skill]` in bảng top 20.
5. Cấu hình `views_enabled` cho phép tắt từng view (phục vụ ablation RT-E1–E4 ở T14).

## Tiêu chí xong

- **Test vàng ví dụ 06 mục 4.5**: dựng 5 CV với điểm thô đúng bảng → sau min–max và trung bình ra đúng thứ hạng CV1, CV4, CV2, CV3, CV5 và tổng 0,87 / 0,80 / 0,74 / 0,25 / 0,00 (test trực tiếp `fusion` với điểm thô cho trước).
- JD không có kỹ năng bắt buộc → trung bình trên 3 view.
- Chạy hai lần cùng dữ liệu → kết quả giống hệt (kể cả hoà điểm).
- Đo thời gian C3 trên 10.000 CV tổng hợp × 30 gạch.

## Ghi chú bàn giao

**Trạng thái: xong (16/11/2026).** `retrieve/views.py`, `fusion.py`, `flow_c.py`, `cli.py`; 6 test đơn vị (gồm **test vàng ví dụ 06 mục 4.5**: đúng thứ hạng CV1, CV4, CV2, CV3, CV5 và tổng 0,87/0,80/0,74/0,25/0,00) + 5 test tích hợp. Toàn bộ 149 test qua.

- **Dùng:** `retrieve_for_jd(conn, idx, cfg, jd_id, K=, hard_filters=, exclude_cv_ids=, views=) -> RetrieveResult(run_id, items, warnings, views_used, request: RerankRequest)`. CLI: `cvmatch retrieve jd <jd_id> [--k] [--views dense,bm25]`.
- **Quyết định:**
  - CV không có gạch → view trách nhiệm `NaN` (thiếu dữ liệu), điểm tổng của CV đó là trung bình các view còn lại; không coi là 0.
  - View kỹ năng tính nhóm "A hoặc B" như **một** yêu cầu (w = max nhóm, ev = max lựa chọn), nhất quán với A1; kỹ năng không CV nào có vẫn nằm ở mẫu số.
  - Lọc cứng hiện hỗ trợ `location` (mặc định cho qua `remote`) và `min_years`; trường thiếu → cho qua; pool < 20 → cảnh báo `small_pool`.
  - `title_skills` (RT-E5) dựng token từ chức danh + tên kỹ năng lúc chạy; `full_jd` dùng `jd_vector.bm25_query_tokens`.
  - `match_run.config_json` lưu toàn bộ config + `config_hash`.
- **Chạy thật** (bge-m3 + KB `kb-2026-11-16-dev`, 5 CV mẫu + JD mẫu): backend Java hạng 1 (fused 1,0), designer cuối; chấm 33 ms.
- **Số đo** (10.000 CV / 300.000 gạch, FakeEncoder): C1–C8 = **1,17 s**, trong đó `bullet_sims` 1,06 s (chủ yếu đổi float16 → float32 toàn ma trận gạch). Ngoại suy 100.000 CV ≈ 12 s → **cần tối ưu khi lên quy mô**: nhân ma trận trên GPU theo khối (float16), hoặc giữ ma trận gạch đã lượng tử hoá int8.
- Kiểm tra lúc chạy với KB thật: JD mẫu chỉ gắn được Java, PostgreSQL, Kafka, Microservices — **thiếu Spring Boot trong KB** (xem T01).

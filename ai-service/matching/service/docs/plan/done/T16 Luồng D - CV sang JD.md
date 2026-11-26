# T16 · Luồng D: từ một CV tìm JD phù hợp (P3)

**Đọc trước:** [[00 Tổng quan kế hoạch]] · Thiết kế `06` mục 5 (toàn bộ) · `07` mục 8 · `08` mục 5 · `09` mục 3.3 · `11` mục 1.2 (`reverse.*`).

## Làm

1. `retrieve/jd_index.py` — chỉ trên JD `open` + mới nhất: chỉ mục BM25 kho JD (token từ `query_text` qua cùng hàm A9/B7), ma trận JD × kỹ năng (ô = `w_imp` kỹ năng bắt buộc) + mảng `tổng_w_imp`, ma trận trách nhiệm + `resp_jd_index`, ma trận dense JD. Dựng lại khi có `JdCommitted` / `JdStatusChanged`.
2. `retrieve/cv_to_jds.py` — D1–D8:
   - D1 CV đã có trong kho, hoặc chạy A1–A10 **không ghi** (chế độ tạm, xoá sau khi trả — theo chính sách Q mở 4).
   - D3: dense; BM25 với truy vấn `condensed_cv` (chức danh, skill token, từ khoá kinh nghiệm gần nhất, bỏ trùng) hoặc `full_cv`; skill với mẫu số `max(Σ w_imp, reverse.skill.min_imp_sum)`; resp giữ chiều "mỗi trách nhiệm JD tìm gạch CV".
   - D4: số JD < `reverse.min_pool_minmax` → RRF thay min–max. JD không có kỹ năng bắt buộc/trách nhiệm → không tính view đó cho riêng JD (theo đề xuất 06 mục 5.7).
   - D5 top `reverse.K = min(50, số JD mở)`; số JD ≤ K → chuyển hết. Tie-break theo `jd_id`.
   - D7 log `direction = 'cv_to_jd'`; trước khi trả kiểm lại `jd.status`.
3. Rerank chiều ngược (07 mục 8): tham chiếu vẫn là câu JD; N = 10; ≤ 60 JD thì chấm hết; A1 dùng `min_imp_sum`; `overqual_penalty` tắt.
4. Explain giọng ứng viên (08 mục 5): không hiện điểm ứng viên khác, không hiện điểm feature thô; nhấn "CV của bạn chưa thể hiện…".
5. API: `POST /match/cv/{cv_id}` và `POST /match/cv:preview` (CV tạm).
6. File kế hoạch ablation RT-R1…R5 cho T14.

## Tiêu chí xong

- **Test vàng ví dụ 06 mục 5.6**: JD-D chỉ 1 kỹ năng → điểm kỹ năng 0,33 với `min_imp_sum = 3`; thứ hạng A, B, D, C.
- Kho < 10 JD → dùng RRF.
- JD vừa đóng sau khi tính → bị loại khi trả.

## Ghi chú bàn giao

**Trạng thái: xong (23/11/2026).** Test: `tests/unit/test_retrieve_cv_to_jds.py` (ví dụ vàng 5.6 → A, B, D, C với tổng 0,92 / 0,76 / 0,42 / 0,00; JD-D 1 kỹ năng → 0,33), `tests/integration/test_flow_d_db.py`.

- `retrieve/jd_index.py` (`JdIndex`: chỉ JD open, bản mới nhất cùng bộ khoá; dựng lại toàn bộ khi `jd_committed` / `jd_status_changed`), `retrieve/cv_to_jds.py` (D1–D8; `condensed_cv` / `full_cv`; mẫu số `min_imp_sum`; JD thiếu kỹ năng bắt buộc / trách nhiệm → NaN cho riêng view đó; < `min_pool_minmax` JD → RRF + cảnh báo; tie-break s_skill → jd_id; log `direction = cv_to_jd`).
- Rerank chiều ngược dùng chung code (`Reranker.rerank` theo `request.direction`): một CV × ≤ K JD, BERTScore một ma trận cho mọi câu JD; A1/A2 mẫu số ≥ `min_imp_sum`; tắt phạt thừa B2, B3; `RerankRequest` thêm `cv_id`, `RerankCandidate.version`; `FinalItem.jd_id/jd_version`.
- **Lệch thiết kế (có lý do):** cổng must-have chiều ngược dùng độ phủ kỹ năng bắt buộc **không** áp mẫu số tối thiểu (`Scored.gate_a1`). Đo trên DB dev: CV có đủ kỹ năng của JD bị trần 50 chỉ vì JD đòi < 3 kỹ năng, trong khi giải thích ghi "không thiếu gì". `min_imp_sum` vẫn dùng cho điểm và xếp hạng.
- Explain hướng ứng viên: mẫu `templates/explain-candidate-1.0.j2` (`cand-1.0`): không hiện điểm số / điểm feature, "CV của bạn chưa thể hiện: …". `ExplainService.explain(run_id, item_id)` tự chọn giọng theo `rerank_run.direction`.
- API: `POST /match/cv/{cv_id}`, `POST /match/cv:preview` (CV tạm: nạp → match → giải thích ngay → **xoá hết**: CV, log nạp, match_run/rerank_run, cache BERTScore; không vào `CvIndex`; CV trùng nội dung CV trong kho thì dùng CV đó), `GET /match/{run_id}/jd/{jd_id}/explain`. Trước khi trả kiểm lại `jd.status`, JD vừa đóng bị loại + cảnh báo `jd_closed`. CLI `cvmatch retrieve cv <cv_id>`; `cvmatch rerank <run>` chạy cả hai chiều.
- Kế hoạch ablation `research/experiments/reverse_RT_R.yaml` (RT-R1…R5) cho T14.
- Còn treo: chính sách cho ứng viên xem "kỹ năng còn thiếu" (Q mở); `unknown_skill` vẫn đếm cụm của CV xem trước.
